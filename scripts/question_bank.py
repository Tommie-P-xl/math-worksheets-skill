"""Consent-gated global question bank. Storage operations use only Python stdlib."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
import tempfile
import time
import unicodedata
import uuid
import zipfile

SCHEMA_VERSION = 1
STAGES = ("小学", "初中", "高中")
TAG_CATEGORIES = ("stages", "subjects", "grades", "exams", "topics", "types", "methods")
DEMAND_TEXT = ("knowledge_span", "method_visibility", "calculation_load", "case_burden", "scaffolding")
DEFAULT_CONFIG = {"guide_max_chars": 6000, "backup_keep": 7}
ITEM_FIELDS = {"id", "title", "summary", "stem", "answer", "solution", "tags", "demand",
               "origin", "verification", "diagram", "sources", "family", "uncertainties", "duplicate_decision"}
DDL = """
CREATE TABLE IF NOT EXISTS problems (
 id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, payload TEXT NOT NULL,
 revision INTEGER NOT NULL, updated TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tags (
 problem_id TEXT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
 category TEXT NOT NULL, label TEXT NOT NULL, PRIMARY KEY(problem_id,category,label));
CREATE INDEX IF NOT EXISTS tag_lookup ON tags(category,label,problem_id);
CREATE TABLE IF NOT EXISTS guides (
 stage TEXT NOT NULL, subject TEXT NOT NULL, path TEXT UNIQUE NOT NULL,
 sha256 TEXT NOT NULL, revision INTEGER NOT NULL, sources TEXT NOT NULL,
 PRIMARY KEY(stage,subject));
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL,
 approval TEXT NOT NULL, receipt TEXT NOT NULL, before_json TEXT, after_json TEXT NOT NULL);
"""


class BankError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else encoded(value).encode("utf-8")).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path):
    def invalid(value):
        raise BankError(f"Non-finite JSON number: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=invalid)


def text_field(value, name, maximum, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > maximum:
        raise BankError(f"{name}: expected {'0' if empty else '1'}..{maximum} characters")
    return value


def normalize(value):
    value = unicodedata.normalize("NFC", value)
    value = re.sub(r"\\(?:left|right)\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s*([=+*/<>(),，。；;:$])\s*", r"\1", value)
    return re.sub(r"(?<=[\u3400-\u9fff]) (?=[\u3400-\u9fff])", "", value)


def fingerprint(item):
    return digest({"stem": normalize(item["stem"]), "givens": item.get("diagram", {}).get("givens", [])})


def validate_tags(tags):
    if not isinstance(tags, dict) or set(tags) - set(TAG_CATEGORIES):
        raise BankError("tags: unknown category; use " + ",".join(TAG_CATEGORIES))
    result = {}
    for category in TAG_CATEGORIES:
        values = tags.get(category, [])
        if not isinstance(values, list) or len(values) > 5:
            raise BankError(f"tags.{category}: at most 5 labels; summarize and obtain approval")
        for label in values:
            text_field(label, f"tags.{category}", 32)
            if label != label.strip():
                raise BankError(f"tags.{category}: trim surrounding whitespace")
        if len(set(values)) != len(values):
            raise BankError(f"tags.{category}: duplicate labels")
        result[category] = values
    if not result["stages"] or not result["subjects"] or set(result["stages"]) - set(STAGES):
        raise BankError("stages must use 小学/初中/高中; stages and subjects cannot be empty")
    return result


def validate_item(data):
    if not isinstance(data, dict) or set(data) - ITEM_FIELDS:
        raise BankError("question: expected an object with known schema fields")
    item = deepcopy(data)
    for name, limit in (("title", 120), ("summary", 240), ("stem", 20000), ("answer", 20000), ("solution", 40000)):
        text_field(item.get(name), name, limit)
    if "id" in item:
        text_field(item["id"], "id", 64)
    item["tags"] = validate_tags(item.get("tags"))
    demand = item.get("demand")
    if not isinstance(demand, dict) or set(demand) != set(DEMAND_TEXT) | {"reasoning_steps", "difficulty"}:
        raise BankError("demand: supply all seven fields from schema")
    for key in DEMAND_TEXT:
        text_field(demand.get(key), "demand." + key, 240)
    steps = demand.get("reasoning_steps")
    if type(steps) is not int or not 0 <= steps <= 100:
        raise BankError("reasoning_steps: integer 0..100, an estimated count")
    difficulty = demand.get("difficulty")
    if not isinstance(difficulty, dict) or set(difficulty) - {"estimate", "basis", "reason", "evidence"}:
        raise BankError("difficulty: expected estimate/basis/reason and optional evidence")
    if type(difficulty.get("estimate")) is not int or not 1 <= difficulty["estimate"] <= 5:
        raise BankError("difficulty.estimate: integer 1..5")
    if difficulty.get("basis") not in ("estimated", "observed"):
        raise BankError("difficulty.basis: estimated or observed")
    text_field(difficulty.get("reason"), "difficulty.reason", 240)
    if difficulty["basis"] == "observed":
        text_field(difficulty.get("evidence"), "observed difficulty cohort/sample/results", 600)
    elif "evidence" in difficulty:
        text_field(difficulty["evidence"], "difficulty.evidence", 600, empty=True)
    if item.get("origin") not in ("uploaded", "generated"):
        raise BankError("origin: uploaded or generated")
    verification = item.get("verification")
    if not isinstance(verification, dict) or set(verification) - {"status", "notes", "checks"}:
        raise BankError("verification: expected status/notes/optional checks")
    if verification.get("status") not in ("unverified", "mixed", "machine-checked", "reviewed"):
        raise BankError("verification.status: invalid")
    text_field(verification.get("notes"), "verification.notes", 1000)
    if not isinstance(verification.get("checks", []), list):
        raise BankError("verification.checks: expected verify.py entries")
    diagram = item.setdefault("diagram", {})
    if not isinstance(diagram, dict) or set(diagram) - {"givens", "format", "code", "layout_coordinates", "answer_overlay"}:
        raise BankError("diagram: unknown field")
    if diagram:
        if not isinstance(diagram.get("givens"), list) or len(encoded(diagram["givens"])) > 16000:
            raise BankError("diagram.givens: bounded semantic relationship list required")
        if diagram.get("format", "tikz") not in ("tikz", "pgfplots", "svg"):
            raise BankError("diagram.format: tikz/pgfplots/svg")
        text_field(diagram.get("code", ""), "diagram.code", 30000, empty=True)
        if len(encoded(diagram)) > 50000:
            raise BankError("diagram: at most 50000 characters")
    sources = item.setdefault("sources", [])
    if not isinstance(sources, list) or len(sources) > 100:
        raise BankError("sources: expected up to 100 provenance records")
    uncertainty = item.setdefault("uncertainties", [])
    if not isinstance(uncertainty, list) or any(not isinstance(s, str) for s in uncertainty):
        raise BankError("uncertainties: expected string list")
    text_field(item.setdefault("family", ""), "family", 120, empty=True)
    decision = item.get("duplicate_decision", {})
    if not isinstance(decision, dict) or set(decision) - {"action", "id"}:
        raise BankError("duplicate_decision: expected action and optional id")
    if decision and decision.get("action") not in ("same", "distinct"):
        raise BankError("duplicate_decision.action: same or distinct")
    if decision.get("action") == "same":
        text_field(decision.get("id"), "duplicate_decision.id", 64)
    return item


def resolve_home(explicit=None):
    if explicit or os.environ.get("MWS_DATA_HOME"):
        path = Path(explicit or os.environ["MWS_DATA_HOME"]).expanduser().resolve()
    elif os.name == "nt":
        path = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))) / "MathWorksheets"
    elif sys.platform == "darwin":
        path = Path.home() / "Library/Application Support/MathWorksheets"
    else:
        path = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "math-worksheets"
    path = path.resolve()
    skill = Path(__file__).resolve().parents[1]
    if path == Path(path.anchor) or path == Path.home().resolve() or path.is_relative_to(skill):
        raise BankError("home must be a dedicated directory outside the skill installation")
    parts = [p.lower() for p in path.parts]
    if "skills" in parts or any("/skills/" in p.as_posix().lower() for p in (path,)):
        raise BankError("home must survive skill uninstall: choose a directory outside skills")
    return path


def safe_child(root, relative):
    if not isinstance(relative, str) or "\\" in relative:
        raise BankError("invalid managed relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or ":" in relative:
        raise BankError("managed path must stay inside the data directory")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise BankError("managed path escapes the data directory")
    return target


def guide_key(stage, subject):
    if stage not in STAGES:
        raise BankError("guide stage must be 小学/初中/高中")
    if not isinstance(subject, str) or not re.fullmatch(r"[\w -]{1,32}", subject) or subject != subject.strip():
        raise BankError("subject must be a short filename-safe label")
    if subject.upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}:
        raise BankError("reserved filename")
    return f"guides/{stage}/{subject}.md"


class Bank:
    def __init__(self, home=None):
        self.home = resolve_home(home)
        self.db = self.home / "bank.sqlite"

    def config(self):
        path = self.home / "config.json"
        config = {**DEFAULT_CONFIG, **(load_json(path) if path.exists() else {})}
        if set(config) - set(DEFAULT_CONFIG):
            raise BankError("config.json: unknown field")
        if type(config["guide_max_chars"]) is not int or not 500 <= config["guide_max_chars"] <= 12000:
            raise BankError("guide_max_chars must be 500..12000")
        if type(config["backup_keep"]) is not int or not 1 <= config["backup_keep"] <= 100:
            raise BankError("backup_keep must be 1..100")
        return config

    @contextmanager
    def connection(self):
        if not self.db.exists():
            yield None
            return
        con = sqlite3.connect(self.db.as_uri() + "?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            if con.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise BankError("incompatible database schema; migrate with a compatible version")
            yield con
        finally:
            con.close()

    @contextmanager
    def writer(self):
        self.config()
        self.home.mkdir(parents=True, exist_ok=True)
        lock = (self.home / ".write.lock").open("a+b")
        locked = False
        con = None
        try:
            lock.seek(0)
            if lock.read(1) == b"":
                lock.write(b"0")
                lock.flush()
            deadline = time.monotonic() + 5
            while not locked:
                try:
                    lock.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except OSError:
                    if time.monotonic() >= deadline:
                        raise BankError("bank busy; another writer is active")
                    time.sleep(0.05)
            con = sqlite3.connect(self.db, timeout=5)
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys=ON")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, SCHEMA_VERSION):
                raise BankError("incompatible database schema")
            if version == 0:
                if con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone():
                    raise BankError("unrecognized existing database; will not initialize over it")
                con.executescript(DDL)
                con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                con.commit()
            if not (self.home / "config.json").exists():
                (self.home / "config.json").write_text(encoded(DEFAULT_CONFIG) + "\n", encoding="utf-8")
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except BaseException:
            if con is not None:
                con.rollback()
            raise
        finally:
            if con is not None:
                con.close()
            if locked:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            lock.close()

    def rows(self):
        with self.connection() as con:
            return [] if con is None else [dict(r) for r in con.execute("SELECT * FROM problems ORDER BY updated DESC,id")]

    def get(self, identity):
        with self.connection() as con:
            row = None if con is None else con.execute("SELECT * FROM problems WHERE id=?", (identity,)).fetchone()
        if row is None:
            raise BankError(f"unknown question: {identity}")
        return {"revision": row["revision"], "item": json.loads(row["payload"])}

    def sources(self, records, base):
        clean, attachments = [], {}
        allowed = {"file", "blob", "sha256", "size", "name", "locator", "label", "url", "title", "checked_at", "scope"}
        for source in records:
            if not isinstance(source, dict) or set(source) - allowed:
                raise BankError("source: unknown fields")
            entry = {k: v for k, v in source.items() if k not in {"file", "blob", "sha256", "size", "name"}}
            for key, value in entry.items():
                text_field(value, "source." + key, 2048, empty=True)
            if source.get("file"):
                path = Path(source["file"]).expanduser()
                if not path.is_absolute():
                    path = base / path
                path = path.resolve()
            elif source.get("blob"):
                path = safe_child(self.home, source["blob"])
                if not source["blob"].startswith("sources/"):
                    raise BankError("source blob must be in sources/")
            else:
                path = None
            if path is not None:
                text_field(entry.get("locator"), "source.locator (page/question or whole-question marker)", 240)
                if not path.is_file():
                    raise BankError(f"source file missing: {path}")
                sha = digest(path.read_bytes())
                suffix = path.suffix.lower() if re.fullmatch(r"\.[a-zA-Z0-9]{1,8}", path.suffix) else ""
                blob = source.get("blob") or f"sources/{sha}{suffix}"
                if source.get("sha256") and source["sha256"] != sha:
                    raise BankError("source changed since recorded hash")
                entry.update(blob=blob, sha256=sha, size=path.stat().st_size, name=source.get("name", path.name))
                attachments[blob] = str(path)
            elif not source.get("url"):
                raise BankError("source needs an accessible file/blob or URL")
            if "url" in entry and not re.match(r"^https?://[^/\s]+", entry["url"]):
                raise BankError("source URL must be http(s)")
            clean.append(entry)
        return self.unique_sources(clean), attachments

    @staticmethod
    def unique_sources(records):
        result, seen = [], set()
        for record in records:
            key = (record.get("sha256"), record.get("locator", ""), record.get("url", ""))
            if key not in seen:
                result.append(record)
                seen.add(key)
        if len(result) > 100:
            raise BankError("too many provenance records; review before merging")
        return result

    def prepare_question(self, file):
        file = Path(file).resolve()
        raw = load_json(file)
        item = validate_item(raw)
        incoming_uncertainties = list(item["uncertainties"])
        item["sources"], attachments = self.sources(item["sources"], file.parent)
        explicit_id = item.get("id")
        decision = item.pop("duplicate_decision", {})
        rows = self.rows()
        by_id = {r["id"]: r for r in rows}
        exact = next((r for r in rows if r["fingerprint"] == fingerprint(item)), None)
        # A photo/page locator identifies the same source occurrence, not a grade.
        incoming_sources = {(s.get("sha256"), s.get("locator", "")) for s in item["sources"] if s.get("sha256")}
        same_source = None
        for row in rows:
            source_set = {(s.get("sha256"), s.get("locator", "")) for s in json.loads(row["payload"])["sources"] if s.get("sha256")}
            if incoming_sources & source_set:
                same_source = row
                break
        target = by_id.get(explicit_id) if explicit_id else exact or same_source
        if explicit_id and target is None:
            raise BankError("explicit id does not exist; omit id for a new question")
        if decision.get("action") == "same":
            target = by_id.get(decision["id"])
            if target is None:
                raise BankError("duplicate target does not exist")
        if exact and target and exact["id"] != target["id"]:
            raise BankError("text already belongs to another question; consolidate with that record")
        before = json.loads(target["payload"]) if target else None
        mode = "update" if explicit_id else "merge" if target else "insert"
        near = []
        needle = normalize(item["stem"])[:2000]
        for row in rows[:300]:
            if target and row["id"] == target["id"]:
                continue
            other = json.loads(row["payload"])
            score = SequenceMatcher(None, needle, normalize(other["stem"])[:2000]).ratio()
            if score >= 0.82:
                near.append({"id": row["id"], "title": other["title"], "similarity": round(score, 3)})
        near = sorted(near, key=lambda x: -x["similarity"])[:5]
        if mode == "merge":
            if normalize(item["answer"]) != normalize(before["answer"]) and decision.get("action") != "same":
                raise BankError("existing answer differs; review and specify id for an explicit revision")
            merged = deepcopy(before)
            merged["tags"] = validate_tags({k: list(dict.fromkeys(before["tags"][k] + item["tags"][k])) for k in TAG_CATEGORIES})
            merged["sources"] = self.unique_sources(before["sources"] + item["sources"])
            item = merged
        elif target:
            item["id"] = target["id"]
        item = validate_item(item)
        if not target:
            item.pop("id", None)
        blockers = []
        if item["uncertainties"] or incoming_uncertainties:
            blockers.append("unresolved transcription/givens")
        if mode == "insert" and near and decision.get("action") != "distinct":
            blockers.append("review possible duplicates and set duplicate_decision")
        proposal = {"kind": "question", "mode": mode, "target": target["id"] if target else None,
                    "revision": target["revision"] if target else 0, "item": item,
                    "attachments": attachments, "blockers": blockers, "near": near}
        return proposal, digest(proposal), before

    def preview(self, file):
        proposal, receipt, before = self.prepare_question(file)
        item = proposal["item"]
        return {"kind": "question", "mode": proposal["mode"], "target": proposal["target"], "receipt": receipt,
                "can_commit": not proposal["blockers"], "blockers": proposal["blockers"],
                "review": {k: item[k] for k in ("title", "summary", "tags", "demand", "answer", "verification")},
                "changed_fields": [k for k in item if before is not None and item[k] != before.get(k)],
                "possible_duplicates": proposal["near"], "proposal_file": str(Path(file).resolve()),
                "question": "是否收录此题？这些年级、知识点、题型和难度信息是否符合预期？可修改；默认不收录。"}

    @staticmethod
    def approval(receipt, approved, note):
        if not approved or approved != receipt:
            raise BankError("explicit approval of the current preview digest required; nothing archived")
        text_field(note, "approval-note (actual user reply/message reference)", 2000)

    def auto_backup(self):
        if not self.db.exists():
            return
        with self.connection() as con:
            if con is None or not con.execute("SELECT 1 FROM events LIMIT 1").fetchone():
                return
        prefix = "auto-" + datetime.now().date().isoformat()
        folder = self.home / "backups"
        if not any(folder.glob(prefix + "-*.zip")):
            self.backup(folder / f"{prefix}-{uuid.uuid4().hex[:8]}.zip")
        files = sorted(folder.glob("auto-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[self.config()["backup_keep"]:]:
            # Only generated timestamp + UUID names are eligible for retention.
            if re.fullmatch(r"auto-\d{4}-\d{2}-\d{2}-[a-f0-9]{8}\.zip", old.name):
                old.unlink()

    def commit(self, file, approved=None, note=None):
        proposal, receipt, _ = self.prepare_question(file)
        self.approval(receipt, approved, note)
        if proposal["blockers"]:
            raise BankError("; ".join(proposal["blockers"]))
        with self.writer() as con:
            fresh, current, before = self.prepare_question(file)
            self.approval(current, approved, note)
            self.auto_backup()
            item = fresh["item"]
            identity = fresh["target"] or "q_" + uuid.uuid4().hex
            item["id"] = identity
            for blob, source in fresh["attachments"].items():
                target = safe_child(self.home, blob)
                target.parent.mkdir(parents=True, exist_ok=True)
                data = Path(source).read_bytes()
                expected = next(s["sha256"] for s in item["sources"] if s.get("blob") == blob)
                if digest(data) != expected:
                    raise BankError("source changed during commit; preview again")
                if target.exists():
                    if digest(target.read_bytes()) != expected:
                        raise BankError("stored source is corrupt; repair before committing")
                else:
                    temp = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
                    try:
                        temp.write_bytes(data)
                        os.replace(temp, target)
                    finally:
                        temp.unlink(missing_ok=True)
            revision = fresh["revision"] + 1
            con.execute("INSERT INTO problems VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET fingerprint=excluded.fingerprint,payload=excluded.payload,revision=excluded.revision,updated=excluded.updated",
                        (identity, fingerprint(item), encoded(item), revision, now()))
            con.execute("DELETE FROM tags WHERE problem_id=?", (identity,))
            con.executemany("INSERT INTO tags VALUES(?,?,?)", [(identity, k, v) for k, values in item["tags"].items() for v in values])
            con.execute("INSERT INTO events(time,kind,target,approval,receipt,before_json,after_json) VALUES(?,?,?,?,?,?,?)",
                        (now(), "question", identity, note, current, encoded(before) if before else None, encoded(item)))
        return {"id": identity, "revision": revision, "mode": fresh["mode"], "home": str(self.home)}

    def read_guide(self, stage, subject):
        relative = guide_key(stage, subject)
        path = safe_child(self.home, relative)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8-sig")
        cap = self.config()["guide_max_chars"]
        if not content.strip() or len(content) > cap:
            raise BankError(f"guide {path}: {len(content)} characters; must be 1..{cap}. Edit the file/config; no text was discarded")
        with self.connection() as con:
            row = None if con is None else con.execute("SELECT * FROM guides WHERE stage=? AND subject=?", (stage, subject)).fetchone()
        sha = digest(content.encode("utf-8"))
        return {"key": stage + "/" + subject, "stage": stage, "subject": subject, "path": str(path), "text": content,
                "sha256": sha, "revision": row["revision"] if row else 0,
                "external_edit": row is None or row["sha256"] != sha,
                "sources": json.loads(row["sources"]) if row else []}

    def prepare_guide(self, stage, subject, file, sources=None):
        relative = guide_key(stage, subject)
        content = Path(file).read_text(encoding="utf-8-sig")
        cap = self.config()["guide_max_chars"]
        if not content.strip() or len(content) > cap:
            raise BankError(f"guide proposal: {len(content)} characters; maximum {cap}; summarize before approval")
        refs = load_json(sources) if sources else []
        if not isinstance(refs, list) or len(refs) > 20:
            raise BankError("guide sources: expected up to 20 short provenance records")
        for source in refs:
            if not isinstance(source, dict) or set(source) - {"url", "title", "checked_at", "scope"}:
                raise BankError("guide source: unknown fields")
            for key in ("url", "title", "checked_at", "scope"):
                text_field(source.get(key), "guide source." + key, 1000)
            if not re.match(r"^https?://[^/\s]+", source["url"]):
                raise BankError("guide source URL must be http(s)")
        old = self.read_guide(stage, subject)
        proposal = {"kind": "guide", "stage": stage, "subject": subject, "path": relative, "text": content,
                    "sources": refs, "base_sha256": old["sha256"] if old else None,
                    "base_revision": old["revision"] if old else 0, "max_chars": cap}
        return proposal, digest(proposal), old

    def guide_preview(self, stage, subject, file, sources=None):
        proposal, receipt, old = self.prepare_guide(stage, subject, file, sources)
        return {"kind": "guide", "receipt": receipt, "key": stage + "/" + subject,
                "characters": len(proposal["text"]), "max_chars": proposal["max_chars"],
                "previous_characters": len(old["text"]) if old else 0,
                "proposal_file": str(Path(file).resolve()), "sources": proposal["sources"],
                "question": "是否保存/替换这一份学段学科命题文档？可先编辑草稿；默认不保存。"}

    def guide_commit(self, stage, subject, file, sources=None, approved=None, note=None):
        _, receipt, _ = self.prepare_guide(stage, subject, file, sources)
        self.approval(receipt, approved, note)
        path = safe_child(self.home, guide_key(stage, subject))
        old_bytes = path.read_bytes() if path.exists() else None
        written = False
        try:
            with self.writer() as con:
                proposal, receipt, old = self.prepare_guide(stage, subject, file, sources)
                self.approval(receipt, approved, note)
                self.auto_backup()
                path.parent.mkdir(parents=True, exist_ok=True)
                temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    temp.write_text(proposal["text"], encoding="utf-8", newline="\n")
                    current = self.read_guide(stage, subject)
                    if (current["sha256"] if current else None) != proposal["base_sha256"]:
                        raise BankError("guide edited during commit; preview again")
                    os.replace(temp, path)
                    written = True
                finally:
                    temp.unlink(missing_ok=True)
                revision = proposal["base_revision"] + 1
                con.execute("INSERT INTO guides VALUES(?,?,?,?,?,?) ON CONFLICT(stage,subject) DO UPDATE SET sha256=excluded.sha256,revision=excluded.revision,sources=excluded.sources",
                            (stage, subject, proposal["path"], digest(proposal["text"].encode("utf-8")), revision, encoded(proposal["sources"])))
                con.execute("INSERT INTO events(time,kind,target,approval,receipt,before_json,after_json) VALUES(?,?,?,?,?,?,?)",
                            (now(), "guide", stage + "/" + subject, note, receipt,
                             encoded(old) if old else None, encoded(proposal)))
        except BaseException:
            if written:
                if old_bytes is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(old_bytes)
            raise
        return {"key": stage + "/" + subject, "revision": revision, "path": str(path), "characters": len(proposal["text"])}

    def context(self, stage, subject, grades=(), topics=(), query="", limit=5, max_chars=10000):
        guide_key(stage, subject)
        if type(limit) is not int or not 1 <= limit <= 10:
            raise BankError("reference limit must be 1..10, questions and guides combined")
        if type(max_chars) is not int or not 1200 <= max_chars <= 20000:
            raise BankError("context character budget must be 1200..20000")
        terms = list(dict.fromkeys([*topics, *query.split()]))
        matches = []
        # SQL applies hard metadata filters before any payload is sent to an agent.
        clauses, params = [], []
        for category, labels in (("stages", [stage]), ("subjects", [subject]), ("grades", grades), ("topics", topics)):
            if labels:
                clauses.append("EXISTS (SELECT 1 FROM tags t WHERE t.problem_id=p.id AND t.category=? AND t.label IN (" + ",".join("?" for _ in labels) + "))")
                params.extend([category, *labels])
        with self.connection() as con:
            selected = [] if con is None else list(con.execute("SELECT p.* FROM problems p WHERE " + " AND ".join(clauses) + " ORDER BY updated DESC,id", params))
        for row in selected:
            item = json.loads(row["payload"])
            haystack = " ".join([item["title"], item["summary"], item["family"], item["stem"], *sum(item["tags"].values(), [])])
            score = sum(3 if term in item["tags"]["topics"] else 1 for term in terms if term.lower() in haystack.lower())
            if terms and not score:
                continue
            matches.append((score, item))
        matches.sort(key=lambda pair: -pair[0])
        references = []
        guide = self.read_guide(stage, subject)
        if guide:
            sections = re.split(r"(?m)(?=^#{1,4} )", guide["text"])
            ranked = sorted(enumerate(sections), key=lambda pair: -sum(t.lower() in pair[1].lower() for t in terms))
            excerpt, cut = "", False
            for _, section in ranked:
                if len(excerpt) + len(section) > 2400:
                    cut = True
                    if not excerpt:
                        excerpt = section[:2400]
                    continue
                excerpt += section
            references.append({"kind": "guide", "key": guide["key"], "path": guide["path"], "text": excerpt,
                               "truncated": cut, "external_edit": guide["external_edit"],
                               "topic_match": not terms or any(t.lower() in excerpt.lower() for t in terms)})
        for _, item in matches[:limit - len(references)]:
            references.append({"kind": "question", **{k: item[k] for k in ("id", "title", "summary", "tags", "demand", "family")},
                               "stem": item["stem"][:1600], "answer": item["answer"][:500], "solution": item["solution"][:900],
                               "givens": encoded(item["diagram"].get("givens", []))[:1200],
                               "verification": item["verification"]["status"],
                               "truncated": len(item["stem"]) > 1600 or len(item["answer"]) > 500 or len(item["solution"]) > 900 or len(encoded(item["diagram"].get("givens", []))) > 1200})
        result = {"references": references, "reference_count": len(references), "limit": limit,
                  "max_chars": max_chars, "needs_research": not any(r["kind"] == "question" or r.get("topic_match") for r in references),
                  "note": "Use suitable local material; if insufficient, make a short official lookup. No content is saved by retrieval."}
        while len(encoded(result)) > max_chars and references:
            references.pop()
            result["reference_count"] = len(references)
            result["needs_research"] = not any(r["kind"] == "question" or r.get("topic_match") for r in references)
            result["budget_reduced"] = True
        return result

    def stats(self):
        counts = {k: {} for k in TAG_CATEGORIES}
        unique = {k: 0 for k in TAG_CATEGORIES}
        with self.connection() as con:
            total = 0 if con is None else con.execute("SELECT COUNT(*) FROM problems").fetchone()[0]
            if con is not None:
                for row in con.execute("SELECT category,label,COUNT(*) n FROM tags GROUP BY category,label ORDER BY category,n DESC,label"):
                    category = row["category"]
                    unique[category] += 1
                    if len(counts[category]) < 5:
                        counts[category][row["label"]] = row["n"]
        sizes = {}
        for name in ("sources", "guides", "backups"):
            folder = self.home / name
            sizes[name] = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file() and not p.is_symlink()) if folder.exists() else 0
        sizes["database"] = sum(p.stat().st_size for p in self.home.glob("bank.sqlite*") if p.is_file())
        sizes["config"] = (self.home / "config.json").stat().st_size if (self.home / "config.json").exists() else 0
        guides = []
        for path in sorted((self.home / "guides").glob("*/*.md")):
            guides.append({"key": path.parent.name + "/" + path.stem, "path": str(path)})
        return {"home": str(self.home), "database": str(self.db), "exists": self.db.exists(), "questions": total,
                "guides": guides, "bytes": sizes, "total_bytes": sum(sizes.values()), "tags": counts,
                "unique_labels": unique, "tag_inventory": "top 5 per category; export for full detail", "config": self.config()}

    def doctor(self):
        errors, edits = [], []
        with self.connection() as con:
            if con is not None:
                integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    errors.append(integrity)
                if list(con.execute("PRAGMA foreign_key_check")):
                    errors.append("foreign key violations")
                for row in con.execute("SELECT * FROM problems"):
                    try:
                        item = validate_item(json.loads(row["payload"]))
                        if item.get("id") != row["id"] or fingerprint(item) != row["fingerprint"]:
                            errors.append("identity mismatch: " + row["id"])
                        tags = {(r["category"], r["label"]) for r in con.execute("SELECT category,label FROM tags WHERE problem_id=?", (row["id"],))}
                        expected = {(k, v) for k, vs in item["tags"].items() for v in vs}
                        if tags != expected:
                            errors.append("tag index mismatch: " + row["id"])
                        for source in item["sources"]:
                            if source.get("blob"):
                                p = safe_child(self.home, source["blob"])
                                if not p.is_file() or digest(p.read_bytes()) != source["sha256"]:
                                    errors.append("missing/corrupt original: " + source["blob"])
                    except (ValueError, KeyError, TypeError) as exc:
                        errors.append(f"{row['id']}: {exc}")
                registered = [dict(row) for row in con.execute("SELECT * FROM guides")]
            else:
                registered = []
        keys = {(row["stage"], row["subject"]) for row in registered}
        keys |= {(p.parent.name, p.stem) for p in (self.home / "guides").glob("*/*.md")}
        for stage, subject in sorted(keys):
            try:
                guide = self.read_guide(stage, subject)
                if guide is None:
                    errors.append("missing guide: " + stage + "/" + subject)
                elif guide["external_edit"]:
                    edits.append(guide["path"])
            except BankError as exc:
                errors.append(str(exc))
        return {"ok": not errors, "errors": errors, "user_edited_guides": edits, "home": str(self.home)}

    def backup(self, out):
        if not self.db.exists():
            raise BankError("no database to back up")
        out = Path(out).expanduser().resolve()
        if out.exists():
            raise BankError("backup destination already exists; choose a new filename")
        # The caller serializes writes when invoked automatically. Manual backups
        # also validate the guide snapshot against SQL hashes/external edits below.
        with tempfile.TemporaryDirectory(prefix="mws-backup-") as tmp:
            snapshot = Path(tmp) / "bank.sqlite"
            with self.connection() as source:
                target = sqlite3.connect(snapshot)
                try:
                    source.backup(target)
                finally:
                    target.close()
            files = {"bank.sqlite": snapshot.read_bytes()}
            config = self.home / "config.json"
            if config.exists():
                files["config.json"] = config.read_bytes()
            for folder in ("sources", "guides"):
                for path in sorted((self.home / folder).rglob("*")):
                    if path.is_file():
                        relative = path.relative_to(self.home).as_posix()
                        safe_child(self.home, relative)
                        files[relative] = path.read_bytes()
            manifest = {"schema": SCHEMA_VERSION, "created": now(), "files": {name: digest(data) for name, data in files.items()}}
            out.parent.mkdir(parents=True, exist_ok=True)
            temporary = out.with_name(out.name + "." + uuid.uuid4().hex + ".tmp")
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                    for name, data in files.items():
                        archive.writestr(name, data)
                    archive.writestr("manifest.json", encoded(manifest))
                os.replace(temporary, out)
            finally:
                temporary.unlink(missing_ok=True)
        return {"backup": str(out), "bytes": out.stat().st_size, "files": len(files), "sha256": digest(out.read_bytes())}

    def restore(self, file):
        if self.home.exists() and any(self.home.iterdir()):
            raise BankError("restore requires an absent/empty destination; existing bank left intact")
        self.home.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mws-restore-", dir=self.home.parent) as tmp:
            stage = Path(tmp) / "data"
            stage.mkdir()
            with zipfile.ZipFile(file) as archive:
                names = archive.namelist()
                if len(names) != len(set(names)) or "manifest.json" not in names:
                    raise BankError("invalid backup members")
                if sum(info.file_size for info in archive.infolist()) > 2 * 1024 ** 3:
                    raise BankError("backup exceeds 2 GiB restore limit")
                manifest = json.loads(archive.read("manifest.json"))
                if manifest.get("schema") != SCHEMA_VERSION or set(names) != set(manifest.get("files", {})) | {"manifest.json"}:
                    raise BankError("incompatible/incomplete backup manifest")
                if "bank.sqlite" not in manifest["files"]:
                    raise BankError("backup is missing database")
                for name, expected in manifest["files"].items():
                    if name not in {"bank.sqlite", "config.json"} and not name.startswith(("sources/", "guides/")):
                        raise BankError("unexpected backup file")
                    target = safe_child(stage, name)
                    data = archive.read(name)
                    if digest(data) != expected:
                        raise BankError("backup checksum mismatch: " + name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            checked = Bank(stage)
            checked.config()
            report = checked.doctor()
            if not report["ok"]:
                raise BankError("restored data failed validation: " + encoded(report["errors"]))
            if self.home.exists():
                self.home.rmdir()  # Destination was verified empty; never recursive.
            os.replace(stage, self.home)
        return {"restored": str(self.home), "questions": self.stats()["questions"]}

    def export(self, out):
        out = Path(out).resolve()
        if out.exists():
            raise BankError("export destination exists; choose a new filename")
        records = [{"kind": "question", "revision": row["revision"], "item": json.loads(row["payload"])} for row in self.rows()]
        for path in sorted((self.home / "guides").glob("*/*.md")):
            records.append({"kind": "guide", **self.read_guide(path.parent.name, path.stem)})
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(encoded(r) + "\n" for r in records), encoding="utf-8")
        return {"export": str(out), "records": len(records), "original_bytes_included": False}


def example():
    return {"title": "示例一次方程", "summary": "一步移项求解", "stem": "解方程 $x+1=3$。", "answer": "x=2",
            "solution": "两边减去1，得x=2。", "tags": {"stages": ["初中"], "subjects": ["数学"], "grades": ["七年级"],
            "exams": [], "topics": ["一元一次方程"], "types": ["计算题"], "methods": ["等式性质"]},
            "demand": {"knowledge_span": "等式性质", "reasoning_steps": 1, "method_visibility": "直接",
                       "calculation_load": "低", "case_burden": "无", "scaffolding": "明确求解目标",
                       "difficulty": {"estimate": 1, "basis": "estimated", "reason": "单步常规运算，未经作答数据校准"}},
            "origin": "generated", "verification": {"status": "unverified", "notes": "请独立求解并调用verify.py；题库不自动认证答案"},
            "diagram": {}, "sources": [], "family": "one-step-equation", "uncertainties": []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", help="global data home, not a skill directory")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("schema", "stats", "doctor", "init"):
        commands.add_parser(name)
    for name in ("preview", "commit"):
        command = commands.add_parser(name)
        command.add_argument("--file", required=True)
        if name == "commit":
            command.add_argument("--approved")
            command.add_argument("--approval-note")
    for name in ("guide-preview", "guide-commit", "guide-show"):
        command = commands.add_parser(name)
        command.add_argument("--stage", required=True, choices=STAGES)
        command.add_argument("--subject", required=True)
        if name != "guide-show":
            command.add_argument("--file", required=True)
            command.add_argument("--sources")
        if name == "guide-commit":
            command.add_argument("--approved")
            command.add_argument("--approval-note")
    context = commands.add_parser("context")
    context.add_argument("--stage", required=True, choices=STAGES)
    context.add_argument("--subject", required=True)
    context.add_argument("--grade", action="append", default=[])
    context.add_argument("--topic", action="append", default=[])
    context.add_argument("--query", default="")
    context.add_argument("--limit", type=int, default=5)
    context.add_argument("--max-chars", type=int, default=10000)
    show = commands.add_parser("show")
    show.add_argument("id")
    show.add_argument("--fields", default="title,summary,stem,answer,solution,tags,demand,verification")
    commands.add_parser("backup").add_argument("--out", required=True)
    commands.add_parser("restore").add_argument("--file", required=True)
    commands.add_parser("export").add_argument("--out", required=True)
    # Accept --home before or after a subcommand without losing the global value.
    for command in commands.choices.values():
        command.add_argument("--home", default=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        bank = Bank(args.home)
        if args.command == "schema":
            result = {"schema_version": SCHEMA_VERSION, "max_tags_per_category": 5, "max_references": 10,
                      "default_guide_max_chars": 6000, "question_example": example()}
        elif args.command in ("stats", "doctor"):
            result = getattr(bank, args.command)()
        elif args.command == "init":
            with bank.writer():
                pass
            result = bank.stats()
        elif args.command == "preview":
            result = bank.preview(args.file)
        elif args.command == "commit":
            result = bank.commit(args.file, args.approved, args.approval_note)
        elif args.command == "context":
            result = bank.context(args.stage, args.subject, args.grade, args.topic, args.query, args.limit, args.max_chars)
        elif args.command == "show":
            record = bank.get(args.id)
            fields = args.fields.split(",")
            if set(fields) - ITEM_FIELDS:
                raise BankError("unknown show field")
            result = {"id": args.id, "revision": record["revision"], **{key: record["item"].get(key) for key in fields}}
        elif args.command == "guide-show":
            result = bank.read_guide(args.stage, args.subject)
        elif args.command == "guide-preview":
            result = bank.guide_preview(args.stage, args.subject, args.file, args.sources)
        elif args.command == "guide-commit":
            result = bank.guide_commit(args.stage, args.subject, args.file, args.sources, args.approved, args.approval_note)
        elif args.command == "backup":
            if not bank.db.exists():
                raise BankError("no database to back up")
            with bank.writer():
                result = bank.backup(args.out)
        elif args.command == "restore":
            result = bank.restore(args.file)
        else:
            result = bank.export(args.out)
        print(encoded(result))
        return 1 if args.command == "doctor" and not result["ok"] else 0
    except (BankError, OSError, sqlite3.Error, zipfile.BadZipFile, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(encoded({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())

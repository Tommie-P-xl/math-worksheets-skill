"""Bind reviewed source transcription and opaque figures to current documents.

This checks provenance and review records, not OCR accuracy or image mathematics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from _tex_segments import blank_comments, segment_spans

IMAGE = re.compile(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^{}]+)\}")


def digest(text):
    return hashlib.sha256(text.strip().encode('utf-8')).hexdigest()


def validate(tex_path, manifest_path, role='worksheet'):
    tex_path, manifest_path = Path(tex_path), Path(manifest_path)
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    if data.get('mode') != 'reproduce':
        raise ValueError('source manifest mode must be reproduce')
    records = data.get('problems')
    if not isinstance(records, list) or not records or not all(isinstance(p, dict) for p in records):
        raise ValueError('source manifest needs one record per problem')
    tex = blank_comments(tex_path.read_text(encoding='utf-8'))
    spans = segment_spans(tex)
    if not spans or len(spans) != len(records):
        raise ValueError('document problem count differs from source manifest')
    if [p.get('id') for p in records] != list(range(1, len(records) + 1)):
        raise ValueError('source ids must follow document order, starting at 1')
    for p, (a, b) in zip(records, spans):
        if not isinstance(p.get('source'), str) or not p['source'].strip():
            raise ValueError(f"problem {p['id']}: missing original source description")
        if p.get('transcription_reviewed') is not True or p.get('uncertainties') != []:
            raise ValueError(f"problem {p['id']}: resolve and review transcription first")
        if role == 'worksheet' and p.get('block_sha256') != digest(tex[a:b]):
            raise ValueError(f"problem {p['id']}: document changed since source review")
    declared = data.get('assets', [])
    if not isinstance(declared, list) or not all(isinstance(p, dict) for p in declared):
        raise ValueError('assets must be a list')
    found = []
    for m in IMAGE.finditer(tex):
        owners = [i for i, (a, b) in enumerate(spans, 1) if a <= m.start() < b]
        if len(owners) != 1:
            raise ValueError('external figures must be inside their owning problem')
        name, pid = m.group(1), owners[0]
        matches = [x for x in declared if x.get('path') == name
                   and x.get('problem_id') == pid and x.get('role') == role]
        if len(matches) != 1:
            raise ValueError(f'problem {pid}: {name} needs exactly one asset record')
        asset = matches[0]
        if asset.get('role') not in ('worksheet', 'answer-key'):
            raise ValueError('asset role must be worksheet or answer-key')
        path = (tex_path.parent / name).resolve()
        if not path.is_relative_to(tex_path.parent.resolve()) or not path.is_file():
            raise ValueError(f'asset missing or outside work directory: {name}')
        if asset.get('sha256') != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError(f'asset changed since review: {name}')
        if asset.get('visual_reviewed') is not True or not asset.get('method'):
            raise ValueError(f'asset needs visual review and method: {name}')
        if asset.get('mathematical_content') is not False and asset.get('givens_reviewed') is not True:
            raise ValueError(f'asset labels/data need review against original and verification JSON: {name}')
        found.append((name, pid))
    # Reject unsupported/macro paths instead of silently overlooking an image.
    if len(found) != len(re.findall(r'\\includegraphics\b', tex)):
        raise ValueError('use literal includegraphics paths; unsupported image invocation')
    expected = [(x.get('path'), x.get('problem_id')) for x in declared if x.get('role') == role]
    if sorted(found) != sorted(expected):
        raise ValueError('asset records must match every image use in this document')
    return len(found)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tex')
    parser.add_argument('manifest')
    parser.add_argument('--role', choices=['worksheet', 'answer-key'], default='worksheet')
    args = parser.parse_args()
    try:
        n = validate(args.tex, args.manifest, args.role)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'Source review failed: {exc}', file=sys.stderr)
        return 1
    print(f'Source records bound; {n} external image(s) visually reviewed, not CAS-verified.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

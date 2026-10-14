"""Focused checks of preserved math gates, source fidelity and real ZIP/PDF builds."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/checks'))
from _tex_segments import blank_comments, segment_spans
from check_sources import digest, validate

BASH = shutil.which('bash')
if os.name == 'nt' and Path('C:/msys64/usr/bin/bash.exe').exists():
    BASH = 'C:/msys64/usr/bin/bash.exe'


def execute(script, args=(), cwd=None, env=None):
    result = subprocess.run([sys.executable, str(script), *map(str, args)],
                            cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8')
    return result


def sources_for(ws, assets=None):
    tex = blank_comments(ws.read_text(encoding='utf-8'))
    return {'mode': 'reproduce', 'problems': [
        {'id': i, 'source': f'User text question {i}', 'transcription_reviewed': True,
         'uncertainties': [], 'block_sha256': digest(tex[a:b])}
        for i, (a, b) in enumerate(segment_spans(tex), 1)], 'assets': assets or []}


def train_png(path):
    """A small schematic asset for testing real external-image embedding."""
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
    rows = bytearray()
    for y in range(50):
        rows.append(0)
        for x in range(160):
            black = (10 <= x <= 145 and 10 <= y <= 32) or any(
                (x-c)**2 + (y-35)**2 <= 36 for c in (30, 65, 105, 135))
            rows.extend((0, 0, 0) if black else (255, 255, 255))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 160, 50, 8, 2, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


class Sources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.ws = self.work / 'ws_sample.tex'
        self.ws.write_text(r'\begin{document}\problem[5cm]{Solve $x+1=3$.}\end{document}', encoding='utf-8')
        self.manifest = self.work / 'sources.json'
        self.data = sources_for(self.ws)

    def check(self, data=None):
        self.manifest.write_text(json.dumps(data or self.data), encoding='utf-8')
        return validate(self.ws, self.manifest)

    def test_review_bound_to_document(self):
        self.assertEqual(self.check(), 0)
        self.ws.write_text(self.ws.read_text().replace('x+1', 'x+2'), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed since'):
            self.check()

    def test_uncertain_or_unreviewed_transcription_blocks(self):
        for field, value in [('uncertainties', ['digit obscured']), ('transcription_reviewed', False)]:
            data = copy.deepcopy(self.data)
            data['problems'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(data)

    def test_asset_change_and_missing_review_block(self):
        self.ws.write_text(r'\begin{document}\problem[5cm]{Solve $x+1=3$.\includegraphics{assets/train.png}}\end{document}', encoding='utf-8')
        asset = self.work / 'assets/train.png'
        asset.parent.mkdir()
        asset.write_bytes(b'test-image-bytes')
        record = {'path': 'assets/train.png', 'problem_id': 1, 'role': 'worksheet',
                  'method': 'user-crop', 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest(),
                  'visual_reviewed': True, 'mathematical_content': True, 'givens_reviewed': True}
        self.data = sources_for(self.ws, [record])
        self.assertEqual(self.check(), 1)
        record['givens_reviewed'] = False
        with self.assertRaisesRegex(ValueError, 'labels/data'):
            self.check()
        record['givens_reviewed'] = True
        asset.write_bytes(b'changed-image')
        with self.assertRaisesRegex(ValueError, 'asset changed'):
            self.check()

    def test_external_path_and_orphan_image_block(self):
        self.ws.write_text(r'\includegraphics{train.png}\begin{document}\problem[5cm]{Solve $x+1=3$.}\end{document}', encoding='utf-8')
        self.data = sources_for(self.ws)
        with self.assertRaisesRegex(ValueError, 'owning problem'):
            self.check()

    def test_source_gate_enables_only_reviewed_images(self):
        self.ws.write_text(r'\begin{document}\problem[5cm]{Solve $x+1=3$.\includegraphics{train.png}}\end{document}', encoding='utf-8')
        (self.work / 'train.png').write_bytes(b'image')
        self.data = sources_for(self.ws, [{'path': 'train.png', 'problem_id': 1,
            'role': 'worksheet', 'method': 'user-crop', 'visual_reviewed': True,
            'mathematical_content': False, 'sha256': hashlib.sha256(b'image').hexdigest()}])
        self.check()
        verify = self.work / 'verify.json'
        verify.write_text(json.dumps({'problem_count': 1, 'problems': [
            {'id': 1, 'type': 'solve', 'expr': 'x+1-3', 'expected': [2]}]}))
        checker = ROOT / 'scripts/checks/check_prose_consistency.py'
        self.assertEqual(execute(checker, [self.ws, verify]).returncode, 2)
        self.assertEqual(execute(checker, [self.ws, verify, '--sources', self.manifest]).returncode, 0)


class Runtime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        for p in (ROOT / 'tests/fixtures').iterdir():
            shutil.copy2(p, self.work / p.name)

    def build(self, root=ROOT, flags=(), expected=0):
        self.assertTrue(BASH, 'Bash is required')
        self.assertTrue(shutil.which('pdftotext'), 'pdftotext is required')
        env = os.environ.copy()
        env.update(MWS_PYTHON=sys.executable.replace('\\', '/'), PYTHONUTF8='1', MSYS2_PATH_TYPE='inherit')
        args = [BASH, '-l', str(root / 'scripts/build.sh').replace('\\', '/'),
                str(self.work / 'verify_build_demo.json').replace('\\', '/'),
                '--outdir', str(self.work / 'out').replace('\\', '/'), *flags]
        p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', env=env)
        self.assertEqual(p.returncode, expected, p.stdout[-7000:] + p.stderr[-3000:])
        return p

    def test_cas_rejects_wrong_answer_before_compilation(self):
        path = self.work / 'verify_build_demo.json'
        data = json.loads(path.read_text())
        data['problems'][0]['expected'] = 99
        path.write_text(json.dumps(data))
        result = self.build(flags=['--worksheet-only'], expected=1)
        self.assertIn('gate: verify-ws', result.stderr)
        self.assertFalse((self.work / 'out').exists())

    def test_original_three_document_build(self):
        self.build()
        self.assertEqual(len(list((self.work / 'out').glob('*.pdf'))), 3)

    def test_reproduction_without_guide(self):
        ws = self.work / 'ws_build_demo.tex'
        path = self.work / 'sources_build_demo.json'
        path.write_text(json.dumps(sources_for(ws)), encoding='utf-8')
        self.build(flags=['--reproduce'])
        self.assertEqual(len(list((self.work / 'out').glob('*.pdf'))), 2)

    def test_reproduction_external_image_and_solution_plot(self):
        asset = self.work / 'assets/train.png'
        asset.parent.mkdir()
        train_png(asset)
        ws = self.work / 'ws_build_demo.tex'
        text = ws.read_text().replace(r'\input{worksheet-preamble}',
            r'\usepackage{graphicx}' + '\n' + r'\input{worksheet-preamble}')
        text = text.replace(r'\ansline', r'\includegraphics[width=3cm]{assets/train.png}\ansline', 1)
        ws.write_text(text, encoding='utf-8')
        ak = self.work / 'ak_build_demo.tex'
        plot = r'''
\begin{tikzpicture}
\begin{axis}[width=6cm,height=4cm,axis lines=middle,xmin=0,xmax=4,ymin=-1,ymax=6,xtick={2,3},ytick={2,4},xlabel={$x$},ylabel={$y$}]
\addplot[domain=0:4,samples=60,thick] {x^2-5*x+6};
\addplot[only marks] coordinates {(2,0) (3,0)};
\end{axis}
\end{tikzpicture}
'''
        ak.write_text(ak.read_text().replace(r'\end{enumerate}', plot + '\n' + r'\end{enumerate}'), encoding='utf-8')
        record = {'problem_id': 1, 'role': 'worksheet', 'path': 'assets/train.png',
                  'method': 'program-schematic', 'visual_reviewed': True,
                  'mathematical_content': False, 'sha256': hashlib.sha256(asset.read_bytes()).hexdigest()}
        (self.work / 'sources_build_demo.json').write_text(json.dumps(sources_for(ws, [record])), encoding='utf-8')
        self.build(flags=['--reproduce'], expected=2)
        self.assertEqual(len(list((self.work / 'out').glob('*.pdf'))), 2)
        if os.environ.get('MWS_TEST_OUTPUT'):
            target = Path(os.environ['MWS_TEST_OUTPUT'])
            target.mkdir(parents=True, exist_ok=True)
            for pdf in (self.work / 'out').glob('*.pdf'):
                shutil.copy2(pdf, target / pdf.name)

    def test_guide_only_and_worksheet_only(self):
        self.build(flags=['--worksheet-only'])
        env = os.environ.copy()
        env.update(MWS_PYTHON=sys.executable.replace('\\', '/'), PYTHONUTF8='1', MSYS2_PATH_TYPE='inherit')
        p = subprocess.run([BASH, '-l', str(ROOT / 'scripts/build.sh'),
            str(self.work / 'verify_ss_build_demo.json'), '--study-guide-only',
            '--outdir', str(self.work / 'guide')], env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(len(list((self.work / 'guide').glob('*.pdf'))), 1)

    def test_installable_zip_is_deterministic_and_runs(self):
        tool = ROOT / 'tools/package_skill.py'
        self.assertEqual(execute(tool, ['--outdir', self.work / 'a']).returncode, 0)
        self.assertEqual(execute(tool, ['--outdir', self.work / 'b']).returncode, 0)
        archive = next((self.work / 'a').glob('*.zip'))
        self.assertEqual(archive.read_bytes(), next((self.work / 'b').glob('*.zip')).read_bytes())
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            self.assertEqual([n for n in names if n.endswith('SKILL.md')], ['math-worksheets/SKILL.md'])
            self.assertFalse(any('/tests/' in n or '/tools/' in n or '/evals/' in n or '/docs/' in n for n in names))
            self.assertTrue(all(b'\r\n' not in z.read(n) for n in names if n.endswith('.sh')))
            z.extractall(self.work / 'installed')
        self.build(root=self.work / 'installed/math-worksheets', flags=['--no-study-guide'])
        self.assertEqual(len(list((self.work / 'out').glob('*.pdf'))), 2)

    def test_chinese_photo_reproduction_auto_engine_and_text(self):
        self.assertTrue(shutil.which('xelatex'), 'XeLaTeX is required for the Chinese test')
        spec = importlib.util.spec_from_file_location('photo_example', ROOT / 'tools/build_photo_example.py')
        example = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(example)
        example.EXAMPLE = self.work / 'photo'
        example.prepare()
        env = os.environ.copy()
        env.update(PYTHONUTF8='1', MWS_PYTHON=sys.executable.replace('\\','/'),
                   MSYS2_PATH_TYPE='inherit', MWS_LATEX_ENGINE='auto')
        result = subprocess.run([BASH, '-l', str(ROOT/'scripts/build.sh'),
            str(example.EXAMPLE/'verify_photo_folding.json'), '--reproduce',
            '--outdir', str(self.work/'chinese')], env=env, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2, result.stdout+result.stderr)
        self.assertIn('(engine: xelatex)', result.stdout)
        for name, expected in [('ws_photo_folding.pdf','类比探究'), ('ak_photo_folding.pdf','参考答案与说明')]:
            text = subprocess.run(['pdftotext', str(self.work/'chinese'/name), '-'],
                                  capture_output=True, text=True, encoding='utf-8', check=True).stdout
            self.assertIn(expected, text)


if __name__ == '__main__':
    unittest.main()

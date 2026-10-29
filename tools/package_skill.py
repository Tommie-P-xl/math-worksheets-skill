"""Create a reproducible, runtime-only CC Switch skill ZIP."""
import argparse
import hashlib
from pathlib import Path
import zipfile
from version import get_version

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    'templates/html-to-image/html-to-image.js', 'templates/html-to-image/LICENSE', 'templates/html-to-image/NOTICE.md',
    'VERSION', 'SKILL.md', 'LICENSE',
    'scripts/build.sh', 'scripts/check_log.py', 'scripts/compile.sh',
    'scripts/find_python.sh', 'scripts/geometry_labels.py', 'scripts/page_budget.py',
    'scripts/question_bank.py', 'scripts/bank_browser.py', 'scripts/bank_diagrams.py', 'scripts/bank_content.py', 'scripts/render_figures.py', 'scripts/render_meta.py',
    'scripts/render_quick_answers.py', 'scripts/run_verify.sh', 'scripts/verify.py',
    'scripts/checks/_probfig.py', 'scripts/checks/_probmeta.py',
    'scripts/checks/_tex_segments.py', 'scripts/checks/_units.py',
    'scripts/checks/check_answer_key.py', 'scripts/checks/check_answer_line.py',
    'scripts/checks/check_answer_slots.py', 'scripts/checks/check_facet_coverage.py',
    'scripts/checks/check_layout.py', 'scripts/checks/check_overprint.py',
    'scripts/checks/check_prose_consistency.py', 'scripts/checks/check_sources.py',
    'scripts/checks/check_ss_coverage.py', 'scripts/checks/check_study_guide.py',
    'scripts/checks/check_template_use.py',
    'templates/figure-macros.tex', 'templates/worksheet-preamble.tex',
    'templates/bank-browser.html', 'templates/bank-browser.js', 'templates/katex/LICENSE', 'templates/katex/NOTICE',
    'templates/katex/katex.min.js', 'templates/katex/katex.min.css',
    'templates/katex/contrib/auto-render.min.js',
    'templates/katex/fonts/KaTeX_AMS-Regular.woff2',
    'templates/katex/fonts/KaTeX_Caligraphic-Bold.woff2',
    'templates/katex/fonts/KaTeX_Caligraphic-Regular.woff2',
    'templates/katex/fonts/KaTeX_Fraktur-Bold.woff2',
    'templates/katex/fonts/KaTeX_Fraktur-Regular.woff2',
    'templates/katex/fonts/KaTeX_Main-Bold.woff2',
    'templates/katex/fonts/KaTeX_Main-BoldItalic.woff2',
    'templates/katex/fonts/KaTeX_Main-Italic.woff2',
    'templates/katex/fonts/KaTeX_Main-Regular.woff2',
    'templates/katex/fonts/KaTeX_Math-BoldItalic.woff2',
    'templates/katex/fonts/KaTeX_Math-Italic.woff2',
    'templates/katex/fonts/KaTeX_SansSerif-Bold.woff2',
    'templates/katex/fonts/KaTeX_SansSerif-Italic.woff2',
    'templates/katex/fonts/KaTeX_SansSerif-Regular.woff2',
    'templates/katex/fonts/KaTeX_Script-Regular.woff2',
    'templates/katex/fonts/KaTeX_Size1-Regular.woff2',
    'templates/katex/fonts/KaTeX_Size2-Regular.woff2',
    'templates/katex/fonts/KaTeX_Size3-Regular.woff2',
    'templates/katex/fonts/KaTeX_Size4-Regular.woff2',
    'templates/katex/fonts/KaTeX_Typewriter-Regular.woff2',
    'references/authoring.md', 'references/configuration.md',
    'references/figure-patterns.md', 'references/latex-templates.md',
    'references/manual-review-aid.md', 'references/problem-library.md',
    'references/question-bank.md', 'references/bank-browser.md', 'references/reproduction.md',
    'references/solutions.md', 'references/standards-map.md',
)


def package(outdir):
    get_version(ROOT)  # Validate the sole release source before creating an asset.
    files = [ROOT / name for name in RUNTIME_FILES]
    for path in files:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError(f'Missing or unsafe runtime file: {path.relative_to(ROOT)}')
    files.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    archive = outdir / 'math-worksheets.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            name = 'math-worksheets/' + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == '.sh' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = path.read_bytes()
            if path.suffix in {'.sh', '.py', '.md', '.tex', '.html', '.js'} or path.name == 'LICENSE':
                data = data.replace(b'\r\n', b'\n')
            z.writestr(info, data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert z.namelist().count('math-worksheets/SKILL.md') == 1
        assert all(n.startswith('math-worksheets/') for n in z.namelist())
        assert set(z.namelist()) == {'math-worksheets/' + name for name in RUNTIME_FILES}
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (outdir / (archive.name + '.sha256')).write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(f'{archive}: {len(files)} files, {archive.stat().st_size} bytes; SHA256 {checksum}')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', default=str(ROOT / 'dist'))
    package(parser.parse_args().outdir)

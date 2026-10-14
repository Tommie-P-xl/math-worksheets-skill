"""Create a reproducible, runtime-only CC Switch skill ZIP."""
import argparse
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def package(outdir):
    version = re.search(r'^  version: ([\d.]+)$', (ROOT / 'SKILL.md').read_text(encoding='utf-8'), re.M).group(1)
    files = [ROOT / 'SKILL.md', ROOT / 'LICENSE']
    for folder in ['scripts', 'templates', 'references']:
        files.extend(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.sort(key=lambda p: p.relative_to(ROOT).as_posix())
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    archive = outdir / f'math-worksheets-v{version}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            name = 'math-worksheets/' + path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if path.suffix == '.sh' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = path.read_bytes()
            if path.suffix in {'.sh', '.py', '.md', '.tex'} or path.name == 'LICENSE':
                data = data.replace(b'\r\n', b'\n')
            z.writestr(info, data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert z.namelist().count('math-worksheets/SKILL.md') == 1
        assert all(n.startswith('math-worksheets/') for n in z.namelist())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (outdir / (archive.name + '.sha256')).write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(f'{archive}: {len(files)} files, {archive.stat().st_size} bytes; SHA256 {checksum}')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', default=str(ROOT / 'dist'))
    package(parser.parse_args().outdir)

"""Build the offline submission ZIP using an explicit allowlist."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'deliverables/EE5110SegC_baseline_v1.0.0.zip'
    required = [ROOT / 'docs/report/baseline_report.pdf', ROOT / 'deliverables/baseline_demo.mp4',
                ROOT / 'assets/panda/panda.xml', ROOT / 'assets/ycb/ycb/foam_brick.xml']
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    files = [ROOT / name for name in ['main.py', 'README.md', 'requirements.txt',
             'requirements-video.txt', 'CHANGELOG.md', 'PROGRESS.md', 'CONTRIBUTING.md']]
    for directory in ['robot_manipulation', 'scripts', 'tests', 'docs', 'assets']:
        files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.append(ROOT / 'deliverables/baseline_demo.mp4')
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        print(f'{target}: {len(archive.namelist())} files, {target.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()

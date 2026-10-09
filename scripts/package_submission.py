"""Build the offline submission ZIP using an explicit allowlist."""
from pathlib import Path
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '2.0.0'], default='2.0.0')
    version = parser.parse_args().version
    target = ROOT / f'deliverables/EE5110SegC_baseline_v{version}.zip'
    report, video = {
        '1.0.0': ('baseline_report.pdf', 'baseline_demo.mp4'),
        '1.1.0': ('reliability_report_v1.1.0.pdf', 'reliability_demo_v1.1.0.mp4'),
        '1.2.0': ('obstacle_report_v1.2.0.pdf', 'obstacle_demo_v1.2.0.mp4'),
        '1.3.0': ('obstacle_reliability_v1.3.0.pdf', 'obstacle_demo_v1.3.0.mp4'),
        '1.4.0': ('transparent_sensing_v1.4.0.pdf', 'transparent_sensing_v1.4.0.mp4'),
        '2.0.0': ('clutter_v2.0.0.pdf', 'clutter_v2.0.0.mp4'),
    }[version]
    required = [ROOT / 'docs/report' / report, ROOT / 'deliverables' / video,
                ROOT / 'assets/panda/panda.xml', ROOT / 'assets/ycb/ycb/foam_brick.xml']
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    files = [ROOT / name for name in ['main.py', 'challenge_main.py', 'sensing_main.py', 'clutter_main.py', 'README.md', 'requirements.txt',
             'requirements-video.txt', 'CHANGELOG.md', 'PROGRESS.md', 'CONTRIBUTING.md']]
    for directory in ['robot_manipulation', 'scripts', 'tests', 'docs', 'assets']:
        files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.append(ROOT / 'deliverables' / video)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        print(f'{target}: {len(archive.namelist())} files, {target.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()

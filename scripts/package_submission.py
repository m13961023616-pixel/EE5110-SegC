"""Build the offline submission ZIP using an explicit allowlist."""
from pathlib import Path
import zipfile
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', choices=['1.0.0', '1.1.0', '1.2.0', '1.3.0', '1.4.0', '2.0.0', '2.1.0', '3.0.0'], default='3.0.0')
    version = parser.parse_args().version
    final_submission = version in ('2.1.0', '3.0.0')
    target = ROOT / f'deliverables/EE5110SegC_{"submission" if final_submission else "baseline"}_v{version}.zip'
    report, video = {
        '1.0.0': ('baseline_report.pdf', 'baseline_demo.mp4'),
        '1.1.0': ('reliability_report_v1.1.0.pdf', 'reliability_demo_v1.1.0.mp4'),
        '1.2.0': ('obstacle_report_v1.2.0.pdf', 'obstacle_demo_v1.2.0.mp4'),
        '1.3.0': ('obstacle_reliability_v1.3.0.pdf', 'obstacle_demo_v1.3.0.mp4'),
        '1.4.0': ('transparent_sensing_v1.4.0.pdf', 'transparent_sensing_v1.4.0.mp4'),
        '2.0.0': ('clutter_v2.0.0.pdf', 'clutter_v2.0.0.mp4'),
        '2.1.0': ('final_report_v2.1.0.pdf', 'demo_v2.1.0.mp4'),
        '3.0.0': ('exploration_report_v3.0.0.pdf', 'explorations_v3.0.0.mp4'),
    }[version]
    report_path = ROOT / ('output/pdf' if final_submission else 'docs/report') / report
    required = [report_path, ROOT / 'deliverables' / video,
                ROOT / 'assets/panda/panda.xml', ROOT / 'assets/ycb/ycb/foam_brick.xml']
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(path)
    if final_submission:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from check_completion_evidence import audit
        audit(ROOT / 'docs/validation/v2.1.0')
    if version == '3.0.0':
        from check_exploration_evidence import audit as audit_explorations
        audit_explorations(ROOT / 'docs/validation/v3.0.0')
    files = [ROOT / name for name in ['main.py', 'challenge_main.py', 'sensing_main.py', 'clutter_main.py', 'README.md', 'requirements.txt',
             'requirements-video.txt', 'CHANGELOG.md', 'PROGRESS.md', 'CONTRIBUTING.md']]
    for directory in ['robot_manipulation', 'scripts', 'tests', 'docs', 'assets']:
        files.extend(p for p in (ROOT / directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix != '.pyc')
    if version == '3.0.0':
        files.append(ROOT / 'exploration_main.py')
        files.extend((ROOT / 'exploration').glob('*.py'))
        files.append(ROOT / 'output/pdf/final_report_v2.1.0.pdf')
    files.append(ROOT / 'deliverables' / video)
    if final_submission:
        files.extend([report_path, ROOT / 'RUN_PROJECT.ps1', ROOT / 'requirements-report.txt',
                      ROOT / 'docs/FINAL_HANDOVER.md'])
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(set(files)):
            archive.write(path, path.relative_to(ROOT).as_posix())
        if final_submission:
            manifest = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(set(files))}
            archive.writestr('SUBMISSION_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            parts = Path(name).parts
            if Path(name).is_absolute() or '..' in parts or any(p in parts for p in ('.git', '.venv', '.env', '__pycache__')):
                raise ValueError(f'Unexpected archive entry: {name}')
        print(f'{target}: {len(archive.namelist())} files, {target.stat().st_size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()

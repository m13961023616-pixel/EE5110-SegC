"""Check ZIP integrity/hashes, then audit and physically run an isolated extraction."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=ROOT / 'deliverables/EE5110SegC_submission_v3.0.0.zip')
    parser.add_argument('--extract-to', type=Path, default=ROOT / 'outputs/submission_verification_v3')
    args = parser.parse_args()
    destination = args.extract_to.resolve()
    if destination.exists() and any(destination.iterdir()):
        parser.error('Use a new empty extraction folder')
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC check failed')
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate archive entries')
        for name in names:
            parts = PurePosixPath(name).parts
            if PurePosixPath(name).is_absolute() or '..' in parts or '\\' in name:
                raise ValueError(f'Unsafe archive path: {name}')
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError(f'Archive path leaves extraction root: {name}')
        manifest = json.loads(archive.read('SUBMISSION_MANIFEST.json'))
        if set(names) != set(manifest) | {'SUBMISSION_MANIFEST.json'}:
            raise ValueError('Archive and manifest differ')
        for name, expected in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                raise ValueError(f'Content hash mismatch: {name}')
        archive.extractall(destination)
    commands = [
        ['scripts/setup_assets.py'], ['scripts/setup_ycb.py'],
        ['scripts/check_completion_evidence.py'],
        ['clutter_main.py', '--headless', '--scene', 'dense', '--object', 'foam_brick',
         '--seed', '45', '--trials', '1', '--require-all-success', '--output', 'outputs/isolated_smoke'],
    ]
    if (destination / 'exploration_main.py').is_file():
        commands.extend([
            ['scripts/check_exploration_evidence.py'],
            ['exploration_main.py', '--case', 'soft_adaptive', '--seed', '43', '--trials', '1',
             '--require-all-success', '--output', 'outputs/isolated_soft'],
            ['exploration_main.py', '--case', 'recovery_retry', '--seed', '43', '--trials', '1',
             '--require-all-success', '--output', 'outputs/isolated_recovery'],
        ])
    for command in commands:
        subprocess.run([sys.executable, *command], cwd=destination, check=True)
    print(f'Verified CRC, {len(manifest)} SHA-256 hashes, isolated evidence and physical release: {args.archive}')


if __name__ == '__main__':
    main()

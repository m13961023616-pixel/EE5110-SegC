"""Download the official Panda model, pinned to a recorded Menagerie commit."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from download import fetch

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets' / 'panda'
LOCK = ROOT / 'assets' / 'panda.lock.json'
REPO = 'google-deepmind/mujoco_menagerie'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest_path = DEST / 'manifest.json'
    old = None
    if LOCK.exists() or manifest_path.exists():
        old = json.loads((LOCK if LOCK.exists() else manifest_path).read_text())
        if all((DEST / f).exists() and hashlib.sha256((DEST / f).read_bytes()).hexdigest() == h
               for f, h in old['sha256'].items()):
            print('Panda assets already verified:', old['commit'])
            return
        commit = old['commit']
    else:
        commit = json.loads(fetch(f'https://api.github.com/repos/{REPO}/commits/main'))['sha']
    prefix = 'franka_emika_panda/'
    if old is not None:
        files = [prefix + relative for relative in old['sha256']]
    else:
        tree = json.loads(fetch(f'https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1'))
        files = [item['path'] for item in tree['tree'] if item['type'] == 'blob'
                 and item['path'].startswith(prefix)
                 and item['path'].endswith(('.xml', '.obj', '.stl', 'LICENSE', 'README.md'))]
        if not files or tree.get('truncated'):
            raise RuntimeError('Incomplete upstream file listing; refusing partial asset setup.')

    def download(path):
        relative = path[len(prefix):]
        destination = DEST / relative
        if old is not None and destination.exists():
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            if digest == old['sha256'][relative]:
                return relative, digest
        content = fetch(f'https://raw.githubusercontent.com/{REPO}/{commit}/{path}')
        digest = hashlib.sha256(content).hexdigest()
        if old is not None and digest != old['sha256'].get(relative):
            raise RuntimeError(f'Upstream asset checksum differs from lock: {relative}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return relative, digest

    with ThreadPoolExecutor(max_workers=6) as pool:
        hashes = dict(pool.map(download, files))
    manifest_path.write_text(json.dumps({'repository': REPO, 'commit': commit,
                                       'sha256': hashes}, indent=2), encoding='utf-8')
    print(f'Downloaded {len(hashes)} model files; commit {commit}')


if __name__ == '__main__':
    main()

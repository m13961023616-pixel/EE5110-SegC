"""Fetch six real YCB meshes with textures and CoACD collision parts.

Dataset: YCB (CC BY 4.0). Simulation conversion: elpis-lab/YCB_Dataset (MIT).
Only download data, never execute upstream scripts. SHA-256 lock is committed.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/ycb'
LOCK = ROOT / 'assets/ycb.lock.json'
REPO = 'elpis-lab/YCB_Dataset'
OBJECTS = ('gelatin_box', 'pudding_box', 'tomato_soup_can', 'lemon', 'strawberry', 'foam_brick')


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'EE5110-YCB-baseline'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    old = json.loads(LOCK.read_text(encoding='utf-8')) if LOCK.exists() else None
    if old and all((DEST / p).exists() and hashlib.sha256((DEST / p).read_bytes()).hexdigest() == h
                   for p, h in old['sha256'].items()):
        print('YCB subset already verified:', old['commit'])
        return
    commit = old['commit'] if old else json.loads(fetch(f'https://api.github.com/repos/{REPO}/commits/main'))['sha']
    base = f'https://raw.githubusercontent.com/{REPO}/{commit}/'
    contents = {}
    paths = {'LICENSE', 'README.md'}
    for name in OBJECTS:
        path = f'ycb/{name}.xml'
        contents[path] = fetch(base + path)
        root = ET.fromstring(contents[path])
        for asset in root.find('asset'):
            if 'file' in asset.attrib:
                paths.add('ycb/' + asset.get('file'))
        paths.add(path)

    def download(path):
        if path not in contents:
            contents[path] = fetch(base + path)
        digest = hashlib.sha256(contents[path]).hexdigest()
        if old and digest != old['sha256'].get(path):
            raise RuntimeError(f'YCB checksum mismatch: {path}')
        destination = DEST / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(contents[path])
        return path, digest

    with ThreadPoolExecutor(max_workers=6) as pool:
        hashes = dict(pool.map(download, sorted(paths)))
    lock = {'dataset': 'Yale-CMU-Berkeley Object and Model Set', 'dataset_license': 'CC BY 4.0',
            'dataset_url': 'https://ycb-benchmarks.s3.amazonaws.com/index.html',
            'repository': REPO, 'commit': commit, 'objects': list(OBJECTS), 'sha256': hashes}
    if not old:
        LOCK.write_text(json.dumps(lock, indent=2), encoding='utf-8')
    (DEST / 'manifest.json').write_text(json.dumps(lock, indent=2), encoding='utf-8')
    print(f'Downloaded {len(hashes)} YCB files; commit {commit}')


if __name__ == '__main__':
    main()

"""Freeze all named CA exploration studies before running the held-out root seed."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from exploration.protocol import CASES, GATES, PAIRS
from exploration.provenance import source_hash


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'outputs/exploration_frozen')
    p.add_argument('--seed', type=int, default=20261026)
    p.add_argument('--workers', type=int, choices=(1, 2, 3, 4), default=3)
    a = p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        p.error('Choose a new directory; partial or failed results are never overwritten')
    a.output.mkdir(parents=True, exist_ok=True)
    frozen = source_hash()
    protocol = {'version':'3.0.0', 'seed':a.seed, 'source_sha256':frozen,
                'development_seeds':[1,2,3,43,1044], 'cases':CASES, 'pairs':PAIRS, 'gates':GATES,
                'workers':a.workers, 'completed':False,
                'scope':'bounded_independent_topic_screening_not_arbitrary_real_world_manipulation'}
    path = a.output/'protocol.json'; path.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    def run(name):
        if source_hash() != frozen:
            raise RuntimeError('Frozen engine changed')
        folder = a.output/name; folder.mkdir()
        print('Starting '+name,flush=True)
        with (folder/'run.log').open('w',encoding='utf-8') as stream:
            subprocess.run([sys.executable,str(ROOT/'exploration_main.py'),'--headless','--case',name,
                '--trials',str(CASES[name]['trials']),'--seed',str(a.seed),'--output',str(folder)],
                cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
        if source_hash() != frozen:
            raise RuntimeError('Engine changed during a case')
        summary = json.loads(next(folder.glob('summary_*.json')).read_text())
        print(f"{name}: {summary['successes']}/{summary['trials']}",flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(run,CASES))
    protocol['completed'] = True
    path.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    subprocess.run([sys.executable,str(ROOT/'scripts/check_exploration_evidence.py'),'--folder',str(a.output)],cwd=ROOT,check=True)


if __name__ == '__main__':
    main()

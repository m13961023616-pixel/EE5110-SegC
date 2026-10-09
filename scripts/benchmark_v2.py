"""Frozen balanced V2 physical-scene comparisons; keep every failure."""
from pathlib import Path
import argparse
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from clutter_main import source_hash

CASES={
    'fixed_clutter':('clutter','fixed',60),
    'active_clutter':('clutter','active',60),
    'recovery_clutter':('clutter','recovery',60),
    'isolated_active':('isolated','active',30),
    'obstacles_active':('obstacles','active',30),
    'dense_recovery':('dense','recovery',30),
}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases',nargs='+',choices=CASES,default=list(CASES))
    p.add_argument('--seed',type=int,default=20261601)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/v2_frozen')
    a=p.parse_args();frozen=source_hash()
    for name in a.cases:
        if source_hash()!=frozen:raise RuntimeError('Engine changed during frozen comparison')
        scene,mode,count=CASES[name]
        subprocess.run([sys.executable,str(ROOT/'clutter_main.py'),'--headless','--scene',scene,'--mode',mode,
                        '--trials',str(count),'--seed',str(a.seed),'--output',str(a.output/name)],check=True)


if __name__=='__main__':main()

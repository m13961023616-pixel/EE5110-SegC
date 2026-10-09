"""Frozen same-scene sensor comparison; no physical retries or resampling."""
from pathlib import Path
import argparse
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
CASES={'clean_single':('single',0.,1),'damaged_single':('single',.98,1),
       'temporal':('fusion',.98,1),'multiview':('fusion',.98,2)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed',type=int,default=20261501)
    p.add_argument('--trials',type=int,default=60)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/sensing_frozen')
    a=p.parse_args()
    for name,(mode,dropout,views) in CASES.items():
        subprocess.run([sys.executable,str(ROOT/'sensing_main.py'),'--headless','--mode',mode,
                        '--dropout',str(dropout),'--views',str(views),'--trials',str(a.trials),
                        '--seed',str(a.seed),'--output',str(a.output/name)],check=True)


if __name__=='__main__':main()

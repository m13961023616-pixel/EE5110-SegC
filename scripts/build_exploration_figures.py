"""Standard Matplotlib figures from audited records and actual demonstration traces."""
import csv
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'outputs/mplconfig'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
sys.path.insert(0,str(ROOT))


def main():
    folder=ROOT/'docs/images';folder.mkdir(parents=True,exist_ok=True)
    comparison=json.loads((ROOT/'docs/validation/v3.0.0/comparison.json').read_text())
    groups=comparison['groups']
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.labelcolor':'#153248','text.color':'#153248'})
    fig,ax=plt.subplots(figsize=(8,5.5))
    names=list(groups);y=np.arange(len(names));rates=np.array([groups[n]['successes']/groups[n]['trials'] for n in names])
    intervals=np.array([groups[n]['success_rate_95pct_interval'] for n in names])
    ax.barh(y,rates,color=['#399d91' if any(s in n for s in ('adaptive','robust','retry','points')) else '#7895b0' for n in names],height=.62)
    ax.errorbar(rates,y,xerr=np.maximum(0,np.vstack([rates-intervals[:,0],intervals[:,1]-rates])),fmt='none',ecolor='#233d52',capsize=2,lw=1)
    ax.set_yticks(y,[n.replace('_',' ') for n in names]);ax.invert_yaxis();ax.set_xlim(0,1.19)
    for i,n in enumerate(names):ax.text(1.025,i,f"{groups[n]['successes']}/{groups[n]['trials']}",va='center')
    ax.set_xticks([0,.25,.5,.75,1.],['0%','25%','50%','75%','100%']);ax.set_xlabel('Physical task success; bars show 95% Wilson intervals')
    fig.tight_layout();fig.savefig(folder/'exploration_success_intervals.png',dpi=220);plt.close(fig)

    demo=ROOT/'docs/validation/v3.0.0/demo'
    for name,filename in [('soft_adaptive','exploration_soft_trace.png'),('articulated','exploration_hinge_trace.png')]:
        with (demo/(name+'_trace.csv')).open(encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        time=np.array([float(r['time_s']) for r in rows]);time-=time[0]
        fig,ax=plt.subplots(figsize=(7.5,2.5))
        if name=='soft_adaptive':
            ax.plot(time,[100*float(r['edge_strain']) for r in rows],color='#087f82',label='Instantaneous maximum edge strain')
            ax.set_ylabel('Edge strain (%)');other=ax.twinx()
            other.plot(time,[float(r['normal_force_n']) for r in rows],color='#b87635',alpha=.7,label='Maximum finger normal force')
            other.set_ylabel('Normal force (N)');other.spines['top'].set_visible(False)
        else:
            ax.plot(time,np.rad2deg([float(r['hinge_rad']) for r in rows]),color='#087f82')
            ax.set_ylabel('Passive lid angle (degrees)')
        ax.set_xlabel('Simulation time since post-settling monitoring (s)')
        fig.tight_layout();fig.savefig(folder/filename,dpi=220);plt.close(fig)

    # Capture the estimator input before point-only clustering; no simulator labels enter the plot.
    from exploration.workcell import ResearchEnvironment
    import exploration.sensing as sensing
    env=ResearchEnvironment('novel',seed=300044);env.reset(np.random.default_rng(1044))
    original=sensing.point_state;clouds={}
    try:
        for method in ('single','raw_fusion','robust'):
            def capture(points,nominal_box=False):
                clouds[method]=points.copy();return original(points,nominal_box)
            sensing.point_state=capture
            try:sensing.PointObserver(100044,method,adverse=True)(env)
            except Exception as error:
                if type(error).__name__!='StageFailure':raise
    finally:
        sensing.point_state=original;env.close()
    fig,axes=plt.subplots(1,3,figsize=(8,2.7),sharex=True,sharey=True)
    for ax,method in zip(axes,('single','raw_fusion','robust')):
        points=clouds[method]
        ax.scatter(points[:,0],points[:,1],s=2,c=points[:,2],cmap='viridis',vmin=0,vmax=.08,rasterized=True)
        ax.set_title(method.replace('_',' '));ax.set_xlim(.32,.65);ax.set_ylim(-.17,.09);ax.set_aspect('equal');ax.set_xlabel('x (m)')
    axes[0].set_ylabel('y (m)')
    fig.tight_layout();fig.savefig(folder/'exploration_corrupted_points.png',dpi=220);plt.close(fig)
    print('Saved audited success intervals, true mechanics traces and corrupted point inputs')


if __name__=='__main__':main()

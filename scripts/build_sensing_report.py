"""Build a scoped sensor-investigation report from frozen trial evidence."""
from pathlib import Path
import json
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image
ROOT=Path(__file__).resolve().parents[1]
GROUPS=['clean_single','damaged_single','temporal','multiview']


def main():
    data={g:json.loads(next((ROOT/'docs/validation/v1.4.0'/g).glob('summary_*.json')).read_text()) for g in GROUPS}
    styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='Small',fontSize=9,leading=12,spaceAfter=9))
    story=[]
    def p(t,style='Small'):story.append(Paragraph(t,styles[style]))
    def table(rows):
        t=Table([[Paragraph(str(c),styles['Small']) for c in row] for row in rows],colWidths=[130,100,100,155],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce9f3')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),('VALIGN',(0,0),(-1,-1),'TOP')]))
        story.extend([t,Spacer(1,10)])
    p('Transparent-Appearance Object Sensing','Title')
    p('EE5110 Segment C | v1.4.0 | 9 October 2026')
    p('Research question: can additional observations recover a contact-based manipulation pipeline when its depth input loses most foreground returns? This investigates realistic sensing constraints using a deliberately simplified optical corruption model. It does not claim to solve real transparent glass perception.')
    p('Sensor and estimator separation','Heading2')
    p('MuJoCo ray casts generate ideal calibrated orthographic range observations from the collision surfaces, including table and robot occlusion. A 96 x 96 grid spans x=[0.32,0.63], y=[-0.20,0.20] m. One view is vertical; the second originates 0.35 m farther in x at height 0.70 m and looks toward the same table grid. Foreground returns independently drop to table height with probability 0.98, then receive 0.5 mm Gaussian z noise. This is a synthetic dropout model, not refraction, reflection, or a calibrated RGB-D device.')
    p('The estimator receives only measured world points, the public known-object mesh and object identity. It accepts points at heights 12-120 mm, requires 24 returns and fits an upright known rectangular footprint over 361 yaw hypotheses. The upper z quantile estimates the top. Neither pose nor simulator body ID enters the fit; insufficient points produce PERCEPTION_FAIL with no oracle fallback. T_world_object estimates generate the grasp candidates.')
    p('Fusion uses a bounded 64-frame budget. Temporal uses one view; multiview alternates the two calibrated views. Single-frame methods use the first observation from the same seeded sensor stream. Cameras and objects are static during capture; the nominal 30 Hz serial acquisition budget is 2.13 s for fusion versus 0.033 s for a single frame. Simulation does not physically advance during these synthetic observations.')
    p('Frozen new-seed paired evaluation','Heading2')
    p('Seed 20261501, 60 scenes per method, 20 per object: foam brick, gelatin box, pudding box. All four conditions share scene order, true settled pose, controller, collision model, force limit and success gates. No physical retries or resampling. Development seed 43 is excluded. This is three YCB box-like proxies, not a new public glass dataset.')
    rows=[['Method','Success','95% Wilson','Mean total wall time']]
    for g in GROUPS:
        s=data[g];lo,hi=s['success_rate_95pct_interval'];rows.append([g,f"{s['successes']}/60 ({s['success_rate']:.1%})",f'{lo:.1%}-{hi:.1%}',f"{s['mean_total_time_s']:.2f} s"])
    table(rows)
    story.append(PageBreak())
    p('Object coverage and retained failures','Heading2')
    for g in GROUPS:
        s=data[g]
        p('<b>'+g+':</b> '+', '.join(f"{o}: {v['successes']}/20" for o,v in s['per_object'].items())+'. Failures: '+str(s['failures']))
    p('Physical execution and validation','Heading2')
    p('Optical appearance removes visual texture and changes alpha only. These are transparent-appearance proxies with the original rigid masses, inertia and friction, not glass mechanics. Pick-and-place uses real actuator/contact physics. Success requires lift by 80 mm for 1 s, bilateral contact for at least 95% of samples, actual release, supported placement within 55 mm, final speed below 0.02 m/s, and force at most 40 N.')
    p('Ground-truth initial height is used only by the outcome evaluator, never substituted for an estimated grasp pose. Existing motion collision validation and held-object placement still use simulator geometry and true state. Therefore this is an estimated-grasp extension, not an end-to-end vision-only controller. Four new tests cover point-only pose fit, zero-return failure, state/physics preservation and actual estimated-pose release. Existing dataset and obstacle regressions also pass.')
    p('Important limits','Heading2')
    p('Independent dropout is optimistic: temporal fusion cannot repair permanently missing glass returns. Known box geometry, upright roll, known class, ideal calibration, metric point coordinates and a fixed height gate constrain the problem. Tall objects, clutter, reflective outliers, camera calibration error, unknown shape and real refractive effects are outside this experiment. Partial occlusion can bias the fitted pose even with clean depth. The clean single-view result is measured, not treated as a perfect oracle upper bound.')
    p('Run: python sensing_main.py --headless --mode fusion --views 2 --trials 3. Reproduce the four groups with scripts/benchmark_sensing.py; verify every record with scripts/check_sensing_evidence.py. JSONL retains true spawn pose for pairing, estimated pose, translation error, return count, frame/view count, all failures and physical metrics. Evidence: docs/validation/v1.4.0.')
    p('Source SHA-256: '+data['multiview']['source_sha256'])
    story.append(PageBreak())
    p('Actual estimated-pose physical release','Heading2')
    story.append(Image(str(ROOT/'docs/images/transparent_place_v1.4.0.png'),width=440,height=330))
    p('Pudding-box transparent-appearance proxy after actual release. Demonstration seed 44 is a development example and is not added to the formal 240-trial denominator. Video shows real simulated actuator/contact execution; no weld, adhesion or teleport is used.')
    p('Related work and simulation scope','Heading2')
    p('Dex-NeRF (Ichnowski et al., arXiv:2110.14217) investigates view-dependent evidence for real transparent-object manipulation. This project implements neither NeRF nor learned depth completion. MuJoCo visualization documentation describes simulation rendering; changing visual alpha alone is not evidence of a physically correct glass sensor. The explicit range corruption above defines the experiment independently of RGB appearance.')
    p('https://arxiv.org/abs/2110.14217<br/>https://mujoco.readthedocs.io/en/stable/programming/visualization.html')
    def footer(c,d):
        c.setFont('Helvetica',8);c.drawString(50,30,'EE5110 | Synthetic transparent sensing | v1.4.0');c.drawRightString(545,30,str(d.page))
    target=ROOT/'docs/report/transparent_sensing_v1.4.0.pdf'
    SimpleDocTemplate(str(target),leftMargin=50,rightMargin=50,topMargin=40,bottomMargin=50).build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)


if __name__=='__main__':main()

"""Ten-page report of every bounded exploration, including negative results."""
import argparse
import json
from pathlib import Path
from statistics import mean
import sys
import numpy as np
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_exploration_evidence import audit,load_case


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=ROOT/'docs/validation/v3.0.0')
    parser.add_argument('--output',type=Path,default=ROOT/'output/pdf/exploration_report_v3.0.0.pdf')
    args=parser.parse_args();data=audit(args.evidence);groups=data['groups']
    navy=colors.HexColor('#153248');teal=colors.HexColor('#087f82');pale=colors.HexColor('#eaf2f6')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle('BodyR',fontSize=9.2,leading=13.3,spaceAfter=8,textColor=navy))
    styles.add(ParagraphStyle('CellR',fontSize=8.1,leading=11))
    styles.add(ParagraphStyle('CaptionR',fontSize=8,leading=11,spaceAfter=9,textColor=colors.HexColor('#526675')))
    styles.add(ParagraphStyle('CodeR',fontName='Courier',fontSize=7.1,leading=10.5,spaceAfter=9))
    styles['Title'].textColor=navy;styles['Title'].fontSize=23;styles['Title'].leading=27
    styles['Heading1'].textColor=navy;styles['Heading1'].fontSize=18
    styles['Heading2'].textColor=teal;styles['Heading2'].fontSize=12
    story=[];width=174*mm
    def p(text,style='BodyR'):story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'Heading2')
    def page(text):story.append(PageBreak());p(text,'Heading1')
    def table(rows,fractions):
        t=Table([[Paragraph(str(c),styles['CellR']) for c in row] for row in rows],colWidths=[width*v/sum(fractions) for v in fractions],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pale),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7fafb')]),
             ('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
        story.extend([t,Spacer(1,9)])
    def image(name,w=160*mm,caption=None):
        from PIL import Image as PILImage
        path=ROOT/'docs/images'/name
        with PILImage.open(path) as pic:ratio=pic.height/pic.width
        story.append(Image(str(path),width=w,height=w*ratio))
        if caption:p(caption,'CaptionR')
    def result_table(names):
        rows=[['Condition','Final / first success','95% Wilson interval','Failure stages']]
        for name in names:
            s=groups[name];lo,hi=s['success_rate_95pct_interval']
            rows.append([name.replace('_',' '),f"{s['successes']}/{s['trials']} / {s['first_successes']}/{s['trials']}",
                         f'{lo:.1%} - {hi:.1%}',', '.join(f'{k}: {v}' for k,v in s['failures'].items()) or 'none'])
        table(rows,[1.4,1,1.1,1.8])

    p('Autonomous Manipulation:<br/>Six Exploratory Directions','Title')
    p('EE5110 Segment C | v3.0.0 | 25 October 2026 | 126 new physical episodes','CaptionR')
    h('Scope of this continuation')
    p('The course brief lists examples of work beyond a complete grasping baseline [1]. This continuation implements each concrete direction as an independent, bounded study: dense/occluded scenes, genuinely deformable and articulated objects, held-out irregular shapes, force/contact control, physical grasp-failure recovery and stronger sensing/physics uncertainty. It does not claim a universal controller that solves every combination of these problems.')
    table([['Direction','Implemented question / evidence'],
      ['Crowding and occlusion','Can the inherited observation policy withstand nearby free bodies, a physical screen and self-occlusion?'],
      ['Deformable / articulated','A real 3D elastic flex solid and a separate freely hinged assembly are physically picked, carried and released.'],
      ['Unseen irregular objects','Can point-only geometry replace a stored object template on held-out procedural instances?'],
      ['Force/contact awareness','Does measured normal-force regulation improve retention under unknown material/load variation?'],
      ['Failure detection / recovery','Can a failed physical partial closure be detected, followed by checked withdrawal and another grasp without scene reset?'],
      ['More realistic conditions','Spatial/temporal depth errors, outliers, calibration bias, actual mass/friction changes and actuator latency.']], [1.1,2.7])
    h('What was inherited and what is new')
    p('The preserved v2.1 baseline supplies Panda/YCB assets, actuator control, IK, collision checking, placement criteria and earlier 180-episode evidence. New code lives in exploration/ with exploration_main.py. It adds true flex/hinge models, procedural solids, an unmasked point-only observer, a separate force/recovery controller, 14 frozen conditions and mechanism-specific audits. Historical data are never presented as new experiments.')
    p('The report includes unfavorable outcomes: active observation regresses in the harder clutter scene, nominal-box and measured geometry tie on held-out shapes, and correlated raw fusion can be worse than one frame. Complete logs and failure trial IDs accompany every result.')

    page('1  Frozen screening design and results')
    p('New root seed 20261026 was fixed after development seeds 1, 2, 3, 43 and 1044. Fourteen conditions total 126 physical episodes. Each paired condition sees exactly the same initial generalized coordinates or complete settled YCB scene, material parameters and object-instance seed. Point-observation comparisons also record identical hashes of their first corrupted packet. Every failure remains in its original denominator.')
    result_table(list(groups))
    p('Most conditions have only six or twelve episodes. The intervals above are deliberately wide. These are screening experiments demonstrating implementations and failure modes, not a general reliability certification. The seven paired exact McNemar tests are exploratory and unadjusted; none is below 0.05 after Bonferroni correction across seven comparisons. Groups ran concurrently, so wall times are descriptive and are not controlled hardware speed comparisons. No aggregate success rate is used to conceal the different task definitions.','CaptionR')

    page('2  Dense clutter and heavy partial occlusion')
    h('Physical challenge and measured visibility')
    p('The scene retains five simultaneous YCB distractors with gravity/collision, a barrier, two posts and a 0.60 m high opaque camera-side screen. The inherited neighbor offsets are scaled to 76%, creating narrower gaps and possible contact during natural settling. No neighbor is removed or frozen during manipulation. This remains bounded tabletop crowding, not arbitrary stacked-pile rearrangement.')
    p('Visibility is measured before motion: target return counts with all scene geometry are divided by a target-only reference in the same ray grid. This evaluation-only reference excludes non-target geometry from ray visibility without stepping physics, then restores every group. It includes robot self-occlusion. Each episode has a view with less than 50% visible target returns. The controller still uses ideal instance masks and a known YCB box; this topic does not establish nonideal segmentation in clutter.')
    result_table(['crowding_single','crowding_active'])
    h('The negative result is retained')
    p('Fixed single-view observation completes 5/6, while the inherited active policy completes 3/6. Both reject trial 1 during planning. Active observation regresses trials 2 and 3: the objects are released and supported but finish 0.339 m and 0.068 m from the destination, outside the unchanged 55 mm gate. The data identify placement/retention failures; they do not isolate perception as the sole cause. Geometric confidence is therefore insufficient evidence of complete task success under this stronger scene.')
    image('exploration_crowding_place.png',116*mm,'Development demonstration, root seed 43: the single-view condition completes physical release. The opaque side screen and five live neighbors remain present. This clip is excluded from the 126-episode study.')

    page('3  A genuinely deformable grasped solid')
    h('Elastic model and contact-driven motion')
    p('The object is a three-dimensional Saint Venant-Kirchhoff elastic solid built with MuJoCo flexcomp [2]. A 3 x 3 x 3 grid has 27 geometric vertices and trilinear interpolation over eight dynamic corner nodes: 24 deformation DOFs. Mass is 50 g; Young modulus is sampled from 40-70 kPa, Poisson ratio 0.3 and Rayleigh damping 0.005 s. Integration uses discrete with a 1 ms timestep. There is no rigid collision stand-in, live-object teleport, adhesion or robot-object weld.')
    p('Grasp generation for this material study uses simulator geometry, so material effects are separated from perception error. The planner predicts a rigidly transported copy of the current deformed nodal shape in scratch data; this is an approximation, not predictive deformable-body planning. Live execution remains elastic contact dynamics. The center-height gate uses mean flex-vertex position. Relative edge-length changes are recorded throughout; success additionally requires maximum absolute edge strain at most 40%. This synthetic constitutive choice is not a calibrated real foam model.')
    result_table(['soft_fixed','soft_adaptive'])
    p('Fixed preload completes 2/6; closed-loop normal-force regulation completes 6/6 and recovers trials 3-6 without regressions. All four fixed-control failures stop on sustained contact loss. Across all episodes, mean peak edge strain is '+f"{groups['soft_fixed']['mean_max_strain']:.1%} versus {groups['soft_adaptive']['mean_max_strain']:.1%}. "+'The adaptive group has higher strain, rather than a demonstrated strain reduction; failed fixed episodes also have shorter exposure. The result supports retention within this tested material range, with an explicit force/deformation tradeoff.')
    image('exploration_soft_trace.png',166*mm,'Actual development trace: elastic edge strain and measured finger normal force. It is a single illustrative run, not an independent success-rate sample.')
    image('exploration_soft_adaptive_grasp.png',70*mm,'Actual elastic object at grasp in the recorded development run.')

    page('4  A passive articulated assembly')
    p('A 60 g base and 15 g lid are joined by a real hinge with range [-1.2,0] rad, spring stiffness 0.015 N m/rad, spring reference -0.5 rad and damping 0.001 N m s/rad. The initial angle is randomized in [-0.8,-0.3] rad. The hinge remains dynamic under gravity and finger contacts while the whole assembly is picked and placed. It is not replaced by a rigid mesh or locked to the gripper.')
    result_table(['articulated'])
    p(f"All 6/6 episodes complete the original lift, bilateral hold, release/support and settling gates. Mean within-episode hinge excursion is {groups['articulated']['mean_hinge_excursion_rad']:.3f} rad ({np.rad2deg(groups['articulated']['mean_hinge_excursion_rad']):.1f} degrees). The evaluation center is mass-weighted over the assembly's bodies. This is a feasibility study without a separate articulated-policy ablation; it does not demonstrate deliberate opening, closing or arbitrary articulated-object planning.")
    image('exploration_hinge_trace.png',166*mm,'Actual passive lid angle during the root-43 development demonstration; the joint is allowed to move rather than being commanded to this trace.')
    image('exploration_articulated_lift.png',108*mm,'Whole-assembly physical lift in the development recording.')

    page('5  Held-out irregular objects without CAD')
    h('Object instances and observer boundary')
    p('Seeded procedural solids include tapered, asymmetric, notched and wedge families with randomized metric dimensions. The wedge family is held out from the early geometry/controller tuning. New parameter instances are generated by seed 20261026+300000+i; there is no learned training set. These are held-out synthetic instances, not evidence of generalization to every unknown real object. The public-dataset course baseline remains the separate six-object YCB pipeline.')
    p('The observer receives full unmasked range points. Height filtering and voxel connected components select the component near a fixed user workspace hint (0.48,-0.035) m, chosen before scene generation. Minimum-area footprint fitting estimates orientation and extent. The unknown underside is approximated by the known support plane. No object class, stored target mesh or ideal instance label enters grasp estimation. A rejection test poisons the true-pose and template accessors and verifies that observation still succeeds without changing scene state.')
    p('Top candidates use measured support and bounded lateral offsets. Collision checking, held-object prediction and transfer centering still use simulator geometry/state. The study therefore isolates template-free grasp estimation; it is not an end-to-end image-only robot. The unknown-shape scene contains one target rather than the simultaneous crowded YCB arrangement.')
    result_table(['novel_prior','novel_points'])
    p('Both the generic 40 mm box-prior baseline and measured-geometry method complete 11/12. Trial 5 fails through contact loss in both. Thus removing the template is implemented and succeeds on most held-out instances, but this experiment shows no success-rate advantage over the simple box prior. The shared collision map and restricted dimensions make the task favorable; neither unknown semantic recognition nor full antipodal force-closure estimation is claimed.')
    image('exploration_novel_points_lift.png',112*mm,'Template-free grasp-estimation development example, excluded from the formal sample. The procedural shape is generated from source and a seed, rather than downloaded as a pre-known CAD template.')

    page('6  More realistic synthetic depth errors')
    table([['Error component','Frozen adverse condition'],
      ['Range grids','80 x 80 calibrated orthographic rays; three fixed viewpoints.'],
      ['Independent / persistent missing data','35% independent dropout plus spatial missing stripes occupying 22% of each period.'],
      ['Noise and temporal correlation','1 mm independent Gaussian noise; additional AR(1) drift with coefficient 0.85.'],
      ['Outliers','4% of returns get a random z offset within +/-25 mm.'],
      ['Calibration','A persistent 3D translation bias sampled within +/-2 mm.'],
      ['Observation budget','Single frame, raw 24-frame three-view fusion, or the same 24 packets with temporal voxel support.']], [1,2.5])
    p('The robust method requires a 4 mm voxel to receive support from at least three independent packets before taking its median. Counting packets, rather than repeated points inside one frame, suppresses transient outliers. All three methods use the same first corrupted packet, checked by SHA-256, and the two fusion methods use the same stream. True calibration bias remains and is not averaged away. Capture does not advance physical time; this is not a measured real-camera latency model.')
    result_table(['sensor_single','sensor_raw_fusion','sensor_robust'])
    p('Raw fusion completes only 1/12: persistent spatial support plus accumulated isolated returns can connect false foreground into implausibly large clusters. Temporal consistency reaches 9/12, versus single-frame 6/12. All three residual robust failures (trials 1,5,9) are wedges that lose bilateral contact, illustrating the remaining gap between a usable point cluster and a stable grasp. The exact causal effect of shape and perception error is not separately isolated.')
    image('exploration_corrupted_points.png',170*mm,'Actual adverse development inputs after the known support-height gate: raw fusion accumulates a foreground fog; cross-packet support rejects many transient points. The display uses no target instance labels.')
    p('These errors are more structured than independent depth dropout, but still synthetic. Alpha transparency and range-ray corruption do not simulate glass refraction, specular multipath, realistic RGB segmentation or a calibrated physical depth camera.','CaptionR')

    page('7  Contact regulation and physical recovery')
    h('Load, friction and actuator uncertainty')
    p('The force study changes actual rigid-body mass to 80-250 g, finger/object friction to 0.30-0.85 and actuator delay to 0-6 physics steps (0-12 ms). Both controllers start from the same nominal 4 N preload. The adaptive controller regulates measured bilateral normal force toward 5 N per finger, with bounded demand up to 32 N and the unchanged 40 N actuator limit. Both stop after 60 ms sustained contact loss. Force readings come from MuJoCo contacts and identities, not calibrated real tactile sensors.')
    result_table(['force_fixed','force_adaptive'])
    p('The adaptive method recovers trials 6 and 10, with no regressions, under exactly paired randomized physics. This supports bounded retention feedback in the sampled range; it is not evidence of real-robot transfer, general friction identification or optimal force control.')
    h('A genuinely executed failed closure and retry')
    p('The recovery condition injects one transient actuator-command fault: the first close remains at 58 mm, wider than the 40 mm target. The robot physically executes its approach and partial closure; missing bilateral contacts produce GRASP_FAIL. The policy then opens, collision-checks an upward withdrawal and home motion, reobserves and makes a second physical grasp. The target is never teleported and the scene is initialized exactly once. One-attempt and retry methods share the identical fault and initial state.')
    result_table(['recovery_single','recovery_retry'])
    p('All six first attempts fail as designed, and all six two-attempt episodes recover. This validates the mechanism under a controlled transient actuator fault. It is not a measured natural failure frequency or a demonstration that arbitrary slipped, collided or unreachable objects can be recovered. Slip/collision failures outside the permitted recovery stages still abort.')

    page('8  Reproduction, checks and contribution trace')
    h('Run each direction')
    p('Create a Python 3.12 .venv, install requirements.txt and verify assets using scripts/setup_assets.py and scripts/setup_ycb.py. The ZIP includes the pinned models/licenses but not Python, .venv or wheels. Use requirements-video.txt and requirements-report.txt for optional recordings/figures. Core physics remains MuJoCo 3.15.0 / NumPy 2.5.3; this study used Python '+data['provenance']['python']+'.')
    p('.venv/Scripts/python exploration_main.py --case crowding_single<br/>.venv/Scripts/python exploration_main.py --case soft_adaptive<br/>.venv/Scripts/python exploration_main.py --case articulated<br/>.venv/Scripts/python exploration_main.py --case novel_points<br/>.venv/Scripts/python exploration_main.py --case force_adaptive<br/>.venv/Scripts/python exploration_main.py --case recovery_retry<br/>.venv/Scripts/python exploration_main.py --case sensor_robust', 'CodeR')
    p('Each command defaults to three trials; add --trials 1 --video outputs/example.mp4 for one physical recording. The command-line entry is headless by default. Earlier GUI baseline functions remain available through main.py and clutter_main.py. Each case logs every failure, not just successes.')
    p('.venv/Scripts/python scripts/benchmark_exploration.py --output outputs/new_run<br/>.venv/Scripts/python scripts/check_exploration_evidence.py<br/>.venv/Scripts/python -m unittest discover -s tests -v<br/>.venv/Scripts/python scripts/record_exploration_demo.py<br/>.venv/Scripts/python scripts/build_exploration_figures.py<br/>.venv/Scripts/python scripts/build_exploration_report.py', 'CodeR')
    h('Validation contract')
    p('49 tests cover inherited behavior plus genuine flex deformation/release, a freely moving hinge, no-template observer isolation, actual partial-closure recovery, real material randomization and restoration of ray visibility groups. Evidence rejection tests catch fake rigid deformation labels, scene resets, stale source and force-limit violations. The new audit checks all 126 episodes, physical gates, mechanism fields, exact initial states/materials and paired corrupted packets. The earlier v2.1 180-episode audit remains valid because its engine files are unchanged.')
    p('The final ZIP includes sources, models/licenses, the report, captioned physical video and complete selected evidence. CRC and a per-file SHA-256 manifest are checked. An independent extraction additionally audits old/new evidence and executes actual soft-body release and physical failure recovery. Demonstration clips use development root 43 and are explicitly excluded from the 126 episodes. Their playback is labeled 2x.')
    p('Frozen new source SHA-256:<br/>'+data['source_sha256'],'CodeR')
    p('Authorship, student IDs and actual personal contributions must reflect the real group. The technical contribution trace above separates inherited baseline machinery from this continuation; it does not invent team membership or claim that AI-generated code alone establishes personal research contribution.','CaptionR')

    page('9  Limits, interpretation and references')
    table([['Topic','What the study does not establish'],
      ['Crowding','Arbitrary stacked piles, reliable nonideal segmentation in clutter, or uniformly beneficial active observation.'],
      ['Elastic / articulated','Calibrated foam constitutive laws, cloth/rope manipulation, active lid opening or predictive articulated/deformable planning.'],
      ['Unknown shapes','Unseen real semantic categories, arbitrary topology, fully observed underside, or end-to-end image-only control.'],
      ['Force / recovery','Real tactile calibration, physical hardware transfer, natural-failure recovery rates or safe recovery after every slip/collision.'],
      ['Sensing / statistics','True glass optics, unbiased persistent calibration, real-time camera acquisition, or broad success guarantees from six/twelve samples.']], [1,2.8])
    h('Evidence that matters')
    p('Completing a direction means implementing its physical/algorithmic mechanism, running declared experiments and retaining its limitations. It does not mean solving the entire research field. Here the negative active-view result, raw-fusion failure and wedge slip cases are findings rather than hidden exceptions. The new 126 records and old 180-record study remain separate; no pooled total is advertised as one success-rate experiment.')
    h('References and asset attribution')
    references=[
      '[1] EE5110 Segment C CA brief, supplied by the course. Baseline: workcell, random public-dataset objects, grasp generation/control and randomized evaluation. Exploratory bullets are suggested research directions; original slides are not redistributed in the ZIP.',
      '[2] MuJoCo XML reference, flexcomp and elasticity: <link href="https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-flexcomp" color="#087f82">mujoco.readthedocs.io</link>. The new soft object uses the simulator\'s reduced 3D elasticity mechanism, not a texture animation.',
      '[3] Google DeepMind MuJoCo Menagerie: <link href="https://github.com/google-deepmind/mujoco_menagerie" color="#087f82">github.com/google-deepmind/mujoco_menagerie</link>. Panda commit 0059d4335f8156206f63a35662313385f7ad6d74; original model LICENSE retained.',
      '[4] B. Calli et al., Benchmarking in Manipulation Research: The YCB Object and Model Set and Benchmarking Protocols, 2015. <link href="https://arxiv.org/abs/1502.03143" color="#087f82">arxiv.org/abs/1502.03143</link>. YCB data attribution: CC BY 4.0.',
      '[5] elpis-lab/YCB_Dataset conversion, MIT notice retained: <link href="https://github.com/elpis-lab/YCB_Dataset" color="#087f82">github.com/elpis-lab/YCB_Dataset</link>, commit 9e8c6488a2ff673d9aa48a91492fb89423c1b106.',
      '[6] Inherited project and tagged evidence: <link href="https://github.com/m13961023616-pixel/EE5110-SegC" color="#087f82">github.com/m13961023616-pixel/EE5110-SegC</link>. New data: docs/validation/v3.0.0; preserved study: docs/validation/v2.1.0.',
    ]
    for text in references:p(text,'CaptionR')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def footer(canvas,document):
        canvas.setFont('Helvetica',8);canvas.setFillColor(navy)
        canvas.drawString(18*mm,12*mm,'EE5110 | Six bounded exploratory directions | v3.0.0')
        canvas.drawRightString(192*mm,12*mm,str(document.page))
    SimpleDocTemplate(str(args.output),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,
                      topMargin=16*mm,bottomMargin=22*mm,title='Six Exploratory Directions in Autonomous Manipulation').build(story,onFirstPage=footer,onLaterPages=footer)
    print(args.output)


if __name__=='__main__':main()

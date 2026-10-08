"""Build an evidence-based course baseline report (requires reportlab)."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/validation/v1.0.0'


def main():
    summaries = {}
    for task in ('pick', 'place'):
        paths = sorted((EVIDENCE / task).glob('summary_*.json'))
        if len(paths) != 1:
            raise RuntimeError(f'Expected exactly one formal {task} evaluation')
        summaries[task] = json.loads(paths[0].read_text())
    output = ROOT / 'docs/report/baseline_report.pdf'
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles['BodyText'].leading = 13
    story = []

    def paragraph(text, style='BodyText'):
        story.extend([Paragraph(text, styles[style]), Spacer(1, 2 * mm)])

    def table(rows, widths):
        t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#18384a')),
                               ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                               ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                               ('GRID', (0, 0), (-1, -1), .3, colors.HexColor('#bbbbbb')),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('TOPPADDING', (0, 0), (-1, -1), 7),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
        story.extend([t, Spacer(1, 5 * mm)])

    paragraph('EE5110 Segment C', 'Title')
    paragraph('Autonomous Robotic Grasping - Baseline v1.0.0', 'Heading1')
    paragraph('Technical implementation and experimental report | 9 October 2026')
    paragraph('The system implements a simulated Panda workcell, random selection and placement of real YCB dataset objects, a geometry-based grasp algorithm, physical grasp execution, and randomized evaluation. Pick-and-place is also implemented. This report documents the baseline rather than claiming robust general grasping or perception from camera images.')
    paragraph('1. Requirements and evidence', 'Heading2')
    table([['Course baseline requirement', 'Implementation / evidence'],
           ['Simulated robotic workcell', 'MuJoCo, 7-DOF Panda, gripper, table, target'],
           ['Public 3D dataset; random objects', 'Six YCB models; seeded object / x / y / yaw'],
           ['Developed grasp pose algorithm', 'Four closing axes; mesh fit; IK/collision filtering'],
           ['Execute grasp or pick-and-place', 'Contact-based lift; transport, release, retreat'],
           ['Evaluate randomized trials', '60 pick + 60 place trials, all failures retained'],
           ['Report, video, source instructions', 'This report, baseline_demo.mp4, source ZIP / README']],
          [75 * mm, 98 * mm])
    paragraph('2. Models and assumptions', 'Heading2')
    paragraph('Robot assets are pinned to MuJoCo Menagerie commit 0059d4335f8156206f63a35662313385f7ad6d74. YCB simulation assets are pinned to elpis-lab/YCB_Dataset commit 9e8c6488a2ff673d9aa48a91492fb89423c1b106. SHA-256 manifests verify every downloaded file. Native metric dimensions, texture and declared masses are preserved; objects are not resized to fit the gripper.')
    paragraph('Selected objects: gelatin box, pudding box, tomato soup can, lemon, strawberry, and foam brick. Convex decompositions approximate collision surfaces. Inertia is approximated by a bounding-box tensor using the declared mass; friction is an explicit simulation parameter, not a measured material property. Packaging starts upright, with randomized yaw, then settles under gravity. Only one object is active per trial.')
    paragraph('Perception supplies simulator ground-truth object pose and known model geometry. Placement is randomized over x = 0.40-0.55 m, y = -0.12-0.12 m and yaw = -pi to pi. This baseline does not cover clutter, arbitrary roll/pitch, unknown objects, learned grasping or image-based pose estimation.')
    story.append(PageBreak())
    paragraph('3. Algorithm and physical execution', 'Heading2')
    paragraph('The grasp generator transforms real mesh vertices into the world frame, evaluates four symmetric top-grasp closing directions, rejects apertures above 80 mm, scores feasible widths, and selects the first collision-free pregrasp/approach candidate. Tall objects receive an elevated contact height to keep the palm clear. This deterministic heuristic is team code; mesh and robot data are external assets.')
    paragraph('Inverse kinematics uses damped least squares with joint limits. Joint paths and 6 mm Cartesian waypoints are checked on sampled joint interpolation, including robot/environment, self contact and predicted transported-object geometry. This is a structured free-space planner: it rejects blocked paths and does not search around obstacles. Collision sampling is not a continuous safety proof.')
    paragraph('Smooth joint commands drive official Panda actuators at a 2 ms simulation step. The gripper closes gradually. After closing, both fingers must contact the object. Objects move through MuJoCo contact forces only: execution uses no teleport, weld or attachment constraint. A relative grasp transform is used only in scratch planning data to predict transported-object collision.')
    paragraph('A successful pick must remain more than 80 mm above its initial center height throughout a 1 s hold, with bilateral finger contact on at least 95% of hold samples. For place, the object is transported to (0.48, 0.22) m, lowered, released and inspected after retreat. Success additionally requires target distance below 55 mm, table support, no finger contact and linear speed below 0.02 m/s.')
    paragraph('4. Randomized evaluation', 'Heading2')
    rows = [['Task', 'Seed', 'Success / trials', 'Rate', '95% Wilson interval']]
    for task, s in summaries.items():
        lo, hi = s['success_rate_95pct_interval']
        rows.append([task, str(s['seed']), f"{s['successes']} / {s['trials']}",
                     f"{s['success_rate']:.1%}", f'{lo:.1%} - {hi:.1%}'])
    table(rows, [22 * mm, 29 * mm, 40 * mm, 24 * mm, 58 * mm])
    rows = [['Object', 'Pick', 'Place']]
    for name in summaries['pick']['object_pool']:
        values = []
        for task in ('pick', 'place'):
            p = summaries[task]['per_object'].get(name, {})
            values.append(f"{p.get('successes', 0)} / {p.get('trials', 0)}")
        rows.append([name, *values])
    table(rows, [93 * mm, 40 * mm, 40 * mm])
    paragraph('Each task uses an independent seed and uniform object selection. The denominator includes initialization, candidate, planning, contact, slip and placement failures; failed trials are not resampled or discarded. JSONL contains every trial pose and outcome; JSON summaries include configuration, versions, failure counts, per-object results and timing. CSV provides a compact analysis view.')
    story.append(PageBreak())
    paragraph('5. Failure analysis and practical limits', 'Heading2')
    for task, s in summaries.items():
        paragraph(f"{task.title()} failures: " + ', '.join(f'{k}: {v}' for k, v in s['failures'].items()) + '.')
    paragraph('The largest practical weaknesses are object-specific contact geometry and slipping. A pudding box that tips onto its broad face may exceed the aperture; this is recorded as a grasp-generation failure. Fruit and packaging may shift during closing or lift. The system reports such failures rather than asserting a grasp from commanded motion. Better contact placement, recovery, adaptive force control and perception are future work beyond this baseline.')
    paragraph('Eight regression/integration checks passed locally: seeded reset, unreachable IK, robot/object intersection, resting object false-lift rejection, inactive-object collision isolation, false-place rejection, real YCB physical pick-place/release, and uncertainty boundaries. A fixed cube pick-place smoke and fixed YCB foam-brick pick-place smoke also passed. Cloud validation status is recorded in PROGRESS.md.')
    screenshot = ROOT / 'docs/images/ycb_place.png'
    if screenshot.exists():
        story.append(Image(str(screenshot), width=135 * mm, height=101.25 * mm))
        paragraph('Figure 1. Actual final scene after a successful YCB foam-brick place. The demonstration is a selected successful run; population results are given above.')
    paragraph('6. Reproduction and attribution', 'Heading2')
    paragraph('Use Python 3.12: pip install -r requirements.txt; python scripts/setup_assets.py; python scripts/setup_ycb.py; python main.py --headless --trials 60 --seed 20261009. Add --task place and seed 20261010 for the second experiment. See README for PyCharm, GUI, optional video recording and packaging instructions.')
    paragraph('YCB dataset: https://ycb-benchmarks.s3.amazonaws.com/index.html (CC BY 4.0). Simulation conversion: https://github.com/elpis-lab/YCB_Dataset (MIT). Robot: https://github.com/google-deepmind/mujoco_menagerie/tree/main/franka_emika_panda (upstream license bundled with downloaded assets). Source: https://github.com/m13961023616-pixel/EE5110-SegC .')

    def footer(canvas, doc):
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#536575'))
        canvas.drawString(20 * mm, 13 * mm, 'EE5110 Segment C | Baseline v1.0.0')
        canvas.drawRightString(190 * mm, 13 * mm, str(doc.page))

    SimpleDocTemplate(str(output), pagesize=(210 * mm, 297 * mm),
                      leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                      bottomMargin=22 * mm).build(story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    main()

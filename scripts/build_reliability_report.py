"""Create the v1.1 performance report from all four frozen-code evaluations."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ('iid_pick', 'iid_place', 'balanced_pick', 'balanced_place')


def main():
    summaries = {}
    for group in GROUPS:
        paths = list((ROOT / 'docs/validation/v1.1.0' / group).glob('summary_*.json'))
        if len(paths) != 1:
            raise RuntimeError(f'Missing or ambiguous evidence: {group}')
        summaries[group] = json.loads(paths[0].read_text())
    hashes = {s['source_sha256'] for s in summaries.values()}
    if len(hashes) != 1:
        raise RuntimeError('Evaluation groups used different source code')
    output = ROOT / 'docs/report/reliability_report_v1.1.0.pdf'
    styles = getSampleStyleSheet()
    styles['BodyText'].leading = 12
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
        story.extend([t, Spacer(1, 4 * mm)])

    paragraph('EE5110 Segment C', 'Title')
    paragraph('Baseline Reliability Improvement - v1.1.0', 'Heading1')
    paragraph('Target: at least 90% scene success for both pick and full pick-and-place.')
    paragraph('This update improves the complete system before advanced CA challenges. It retains all six real YCB objects, native scale and declared mass, the original x/y/yaw range, and the original success thresholds. All failed scenes remain in the denominator. There are no physical grasp retries, failed-object respawns, welds or teleport-based execution.')
    paragraph('1. Independent evaluation results', 'Heading2')
    rows = [['Group', 'Seed', 'Success / scenes', 'Rate', '95% Wilson interval']]
    for group, s in summaries.items():
        lo, hi = s['success_rate_95pct_interval']
        rows.append([group, str(s['seed']), f"{s['successes']} / {s['trials']}",
                     f"{s['success_rate']:.1%}", f'{lo:.1%} - {hi:.1%}'])
    table(rows, [32 * mm, 26 * mm, 40 * mm, 22 * mm, 54 * mm])
    rows = [['Version / scope', 'Pick', 'Full place']]
    rows.append(['v1.0.0, 60 IID scenes / task', '33 / 60 (55.0%)', '26 / 60 (43.3%)'])
    a, b = summaries['iid_pick'], summaries['iid_place']
    rows.append(['v1.1.0, 180 IID scenes / task', f"{a['successes']} / 180 ({a['success_rate']:.1%})",
                 f"{b['successes']} / 180 ({b['success_rate']:.1%})"])
    table(rows, [78 * mm, 48 * mm, 48 * mm])
    paragraph('Development used fixed scenes and seed 43. The four report seeds were reserved for evaluation after parameters were frozen. The primary IID groups sample object IDs uniformly and independently. Balanced groups shuffle one of each object per six-scene block, giving 20 trials per object per task. This provides additional object coverage rather than selecting an easy subset.')
    paragraph('The before/after comparison is a whole-system comparison: contact numerical settings, controller and canonical pudding-box support face were also corrected. It is not an isolated grasp-algorithm ablation or a paired identical-scene benchmark. Confidence intervals describe sampling uncertainty within this simulator and scope.')
    paragraph('Frozen source SHA-256: ' + '<font size="8">' + next(iter(hashes)) + '</font>')
    story.append(PageBreak())
    paragraph('2. Object coverage and failure accounting', 'Heading2')
    rows = [['Object', 'IID pick', 'IID place', 'Balanced pick', 'Balanced place']]
    for name in a['object_pool']:
        values = []
        for group in GROUPS:
            p = summaries[group]['per_object'][name]
            values.append(f"{p['successes']} / {p['trials']}")
        rows.append([name, *values])
    table(rows, [54 * mm, 30 * mm, 30 * mm, 30 * mm, 30 * mm])
    paragraph('The balanced place group includes pudding_box at 17/20 (85%), showing remaining scene variation despite the group meeting the overall target. Pooling the independently sampled IID and balanced groups, every object exceeds 90% in each task; the lowest pooled place estimate is pudding_box at 45/49 (91.8%). These are sample estimates, not object-level population guarantees.')
    for group, s in summaries.items():
        failures = ', '.join(f'{k}: {v}' for k, v in s['failures'].items()) or 'none'
        paragraph(f'{group}: {failures}.')
    paragraph('Each JSONL row records the object, initial pose, selected grasp, rejected planning candidates, actual aperture, peak actuator force, lift/contact evidence, placement evidence and terminal outcome. Initialization, generation, planning, execution, slip and release failures are counted. Source and model fingerprints, dependency versions and physical parameters are stored in each summary.')
    paragraph('The success standard is unchanged: during a 1 s hold, object-center height must always exceed initial height by 80 mm and bilateral contacts must occur in at least 95% of samples. Full place additionally requires distance below 55 mm from (0.48, 0.22) m, table support, release and linear speed below 0.02 m/s.')
    paragraph('3. Implemented corrections', 'Heading2')
    paragraph('<b>Consistent geometry.</b> Grasp and lowering geometry now uses the compiled YCB CoACD collision mesh in the correct world/body frame. The texture mesh can have different extremal vertices; using it as a contact surface caused millimetre-level height errors on small objects. Visual meshes, native dimensions and masses are unchanged.')
    paragraph('<b>Shape-aware candidates.</b> Rounded shapes gain inclined grasps; tall thin objects gain side approaches near an accessible edge. Straight top grasps remain alternatives. The planner rejects incompatible approaches using actual robot geometry. Candidate ranking does not depend on evaluation seeds or past trial labels.')
    paragraph('<b>Full-task preflight.</b> Candidate grasps are checked through lift and prospective place before execution, using isolated scratch data. At execution time, transfer/lowering is checked again against the current grasp. Candidate place centers are at most 20 mm per axis from the target center, inside the same unchanged acceptance region.')
    story.append(PageBreak())
    paragraph('4. Contact and control configuration', 'Heading2')
    paragraph('The original soft gripper could under-grip. The new controller closes gradually, detects bilateral contact, then holds a compliant aperture with a nominal 16 N tendon preload or a larger load-scaled request, capped by the 40 N actuator force limit. Position stiffness is 1000 N/m. This is bounded physical actuation, not an attachment mechanism. Peak actuator force is logged.')
    paragraph('Arm control adds model bias-force feedforward to reduce gravity-related endpoint error. Contact uses elliptic friction cones with impratio=10 and six-dimensional object contact, activating the existing rolling-friction coefficient. Numeric friction coefficients were not inflated to force success. These explicit simulation settings reduce soft-contact creep and improve contact stability.')
    paragraph('MuJoCo describes regularized contact creep and recommends elliptic cones with increased frictional impedance for reducing grasp slip: https://mujoco.readthedocs.io/en/stable/modeling.html . This is a numerical contact-model correction; material friction, compliance and object inertia are not validated against a real robot.')
    paragraph('5. Validation, reproduction and remaining scope', 'Heading2')
    paragraph('Ten regression/integration test methods cover false success, unreachable IK, collision detection, seeded reset, object isolation, scratch-only preview, and physical release. The six-object fixed-place test also verifies the actuator force bound. Cloud Windows/Python 3.12 validation is linked in PROGRESS.md. The offline submission ZIP is independently extracted and smoke-tested.')
    paragraph('Reproduce the four groups using python scripts/benchmark_reliability.py after installing requirements and running the two asset-download scripts. It writes a new output directory, checks full object coverage and matching source fingerprints, and returns failure if any group is below 90%. Individual commands and seeds are listed in docs/validation/v1.1.0/protocol.md.')
    paragraph('The scope remains known-object, single-object, oracle-pose simulation with random x/y/yaw and canonical initial support faces. Arbitrary orientation, clutter, image perception, learned grasping, real-object compliance/damage and real-robot transfer remain outside this performance claim. Advanced CA design has not started in this update.')
    screenshot = ROOT / 'docs/images/reliability_place_v1.1.0.png'
    if screenshot.exists():
        story.append(Image(str(screenshot), width=(280 / 3) * mm, height=70 * mm))
        paragraph('Actual post-release YCB simulation scene. The video is a selected demonstration; quantitative claims use all independent trials.')
    paragraph('<a href="https://ycb-benchmarks.s3.amazonaws.com/index.html">YCB data</a> (CC BY 4.0); '
              '<a href="https://github.com/elpis-lab/YCB_Dataset">simulation conversion</a> (MIT); '
              '<a href="https://github.com/google-deepmind/mujoco_menagerie/tree/main/franka_emika_panda">MuJoCo Menagerie Panda</a> '
              '(pinned commit and bundled license). '
              '<a href="https://github.com/m13961023616-pixel/EE5110-SegC">Project source and releases</a>.')

    def footer(canvas, doc):
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.HexColor('#536575'))
        canvas.drawString(18 * mm, 12 * mm, 'EE5110 Segment C | Reliability v1.1.0')
        canvas.drawRightString(192 * mm, 12 * mm, str(doc.page))

    SimpleDocTemplate(str(output), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm,
                      rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm).build(
                          story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == '__main__':
    main()

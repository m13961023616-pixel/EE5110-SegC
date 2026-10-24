"""Build a six-page report from audited evidence without overwriting history."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import mean
import sys
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                                Spacer, PageBreak, Image, KeepTogether)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_completion_evidence import audit, load_case

NAVY = colors.HexColor('#153248')
TEAL = colors.HexColor('#087f82')
PALE = colors.HexColor('#eaf2f6')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=ROOT / 'docs/validation/v2.1.0')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/pdf/final_report_v2.1.0.pdf')
    args = parser.parse_args()
    evidence = audit(args.evidence)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('BodyReport', fontName='Helvetica', fontSize=9.4, leading=13.5,
                             spaceAfter=8, textColor=NAVY))
    styles.add(ParagraphStyle('CellReport', fontName='Helvetica', fontSize=8.1, leading=11))
    styles.add(ParagraphStyle('CaptionReport', fontSize=8, leading=11, spaceAfter=9, textColor=colors.HexColor('#526675')))
    styles.add(ParagraphStyle('CodeReport', fontName='Courier', fontSize=7.4, leading=11, spaceAfter=7))
    styles['Title'].textColor = NAVY
    styles['Title'].fontSize = 24
    styles['Title'].leading = 28
    styles['Heading1'].textColor = NAVY
    styles['Heading1'].fontSize = 18
    styles['Heading2'].textColor = TEAL
    styles['Heading2'].fontSize = 12
    story = []
    width = 174 * mm

    def p(text, style='BodyReport'):
        story.append(Paragraph(text, styles[style]))

    def h(text):
        p(text, 'Heading2')

    def table(rows, fractions):
        data = [[Paragraph(str(cell), styles['CellReport']) for cell in row] for row in rows]
        t = Table(data, colWidths=[width * value / sum(fractions) for value in fractions], repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), PALE),
                              ('TEXTCOLOR', (0, 0), (-1, 0), NAVY),
                              ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafb')]),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                              ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                              ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
        story.extend([t, Spacer(1, 10)])

    def page(title):
        story.append(PageBreak()); p(title, 'Heading1')

    def picture(name, caption, image_width=142 * mm):
        path = ROOT / 'docs/images' / name
        story.append(Image(str(path), width=image_width, height=image_width * .75))
        p(caption, 'CaptionReport')

    p('Autonomous Manipulation<br/>in Physical Clutter', 'Title')
    p('EE5110 Segment C | Final project report | 25 October 2026 | v2.1.0', 'CaptionReport')
    h('Problem and investigation')
    p('A robot must select a public-dataset object, estimate a usable grasp, execute contact-based pick and place, and verify the result over randomized trials. The extension asks a narrower research question: <b>when nearby objects block an otherwise reachable vertical grasp, can a bounded set of inclined, offset alternatives recover the task without disturbing those neighbors?</b>')
    p('The inherited system already provides the baseline workcell, YCB loading, grasp generation, collision-checked motion, active synthetic observations and contact feedback. The continuation diagnoses palm-neighbor collisions, adds at most 16 mesh-derived alternatives, separates candidate rejection phases, corrects the destination visualization and performs a new paired ablation. Development demonstrations and historical results are kept separate from the new evaluation.')
    table([['Course baseline', 'Implementation / evidence'],
           ['Simulated robotic workcell', 'MuJoCo, seven-joint Franka Panda, table and actuated parallel jaws.'],
           ['Random public-dataset objects', 'Six YCB models; seeded object selection, position and yaw.'],
           ['Grasp poses and execution', 'Mesh-based candidates, numerical IK, checked paths, real contact and release.'],
           ['Randomized evaluation', 'Historical tagged studies plus the new 180-episode candidate-strategy ablation.']], [1, 2.3])
    picture('local_recovery_v2.1.0.png', 'Development example: an inclined grasp completes physical release behind the barrier. Root seed 20261608; excluded from the new evaluation denominator.', 110 * mm)

    page('1  Workcell, perception and physical gates')
    h('Scene and assets')
    p('The robot is the pinned Menagerie Panda model [2]. The public YCB subset [3,4] contains foam brick, gelatin box, pudding box, tomato soup can, lemon and strawberry. The three box-like objects are manipulation targets; the remaining models provide three or five simultaneous free-body distractors. Mass, mesh scale, gravity, friction and collision remain enabled. A barrier and two posts separate the pickup and destination regions. Target spawn x/y are [0.43,0.52] / [-0.105,-0.065] m, with random yaw; the destination is (0.48,0.30) m. Neighbor offsets have bounded jitter; this is structured tabletop clutter, rather than a stacked pile.')
    h('Explicit sensing assumptions')
    p('Visual transparency uses alpha 0.25 and removed texture; it does not simulate glass refraction. The sensor casts calibrated 96 x 96 orthographic rays from three views, with 98% independent missing returns, 10% permanently missing pixels per view and 0.5 mm z noise. The estimator fits a known box template to the masked measured points, using upright priors. Ideal simulator instance masks specify the target. There is no true-pose fallback in the estimator; collision maps, held-object prediction and outcome verification still use simulation state.')
    p('Active observations arrive in batches of eight: at least 16, at most 64 frames on the first attempt. Acceptance checks at least 48 distinct points, footprint error at most 6 mm, consecutive position change at most 3 mm and yaw change at most 0.08 rad. These heuristics are not a calibrated probability of correctness. Capture does not advance physics, so frames/30 is a nominal acquisition budget rather than measured real-camera latency.')
    table([['Independent success gate', 'Required condition'],
           ['Lift and hold', 'Above the original initial height +80 mm for 1 s; bilateral finger contact on at least 95% of hold samples.'],
           ['Place and release', 'No jaw contact, table support, XY error below 55 mm; final linear speed below 0.02 m/s after settling.'],
           ['Neighbor preservation', 'Maximum neighbor translation at most 20 mm over the monitored episode; zero unsafe contact steps.'],
           ['Penetration and actuation', 'Target/environment penetration at most 1 mm; jaw actuator force at most 40 N. Joint limits remain 0.5 rad/s and 2 rad/s2.']], [1.05, 2.3])
    p('Only initialization and scratch-state planning write hypothetical object transforms. Runtime manipulation uses actuator/contact dynamics, with no weld, adhesion or live-object teleport. Neighbor monitoring starts after the initial 0.8 s settling period. Neighbor rotations and surface damage do not have separate bounds.', 'CaptionReport')

    page('2  Algorithms and the continuation')
    h('Pipeline and planning')
    p('Estimated T_world_object feeds mesh-based candidate generation. Each candidate is screened through pregrasp, approach, lift and transfer/lowering previews before motion. A damped-Jacobian IK solver uses up to nine seeded solutions with static collision rejection. Cartesian edge checks sample joint configurations about every 0.015 rad. Compound clearance and side corridors use bounded RRT-Connect fallback. After closure, the robot lifts, verifies bilateral holding, transfers, lowers, opens, retreats and verifies stable placement.')
    d = Drawing(width, 58)
    labels = ['Estimate', 'Candidates', 'Preflight', 'Execute', 'Verify']
    step = width / len(labels)
    for i, label in enumerate(labels):
        x = i * step
        d.add(Rect(x, 18, step - 12, 30, fillColor=PALE, strokeColor=None, rx=4, ry=4))
        d.add(String(x + (step - 12) / 2, 29, label, textAnchor='middle', fontSize=9, fillColor=NAVY))
        if i < len(labels) - 1:
            d.add(Line(x + step - 10, 33, x + step - 2, 33, strokeColor=TEAL))
    story.append(d)
    h('Why re-observation was insufficient')
    p('The inherited clutter study has eight shared active/recovery planning failures, all foam brick. Replaying its trial 8 with scene/sensor/planner seeds 20262609 / 20361609 / 20461609 reproduces the complete settled scene exactly. Both original candidates fail during approach: all nine IK seeds converge to states with palm/tomato-can collision. Thus the aggregate IK_FAIL label concealed a geometric collision, rather than establishing that the pose was unreachable. Per-seed outcomes, contacted body/geometry and penetration now accompany failed IK calls; candidate records identify pregrasp, approach or task-preview rejection.')
    h('Bounded local alternatives')
    p('Original symmetric candidates retain their order and priority. For vertical approaches only, the generator rotates about the closing axis by +/-30 or +/-45 degrees, and shifts the pad center +/-12 mm along the original other horizontal axis. It requires at least 10 mm remaining template support on that axis. Projected mesh width plus the original 6 mm margin must remain at most 80 mm. At most 16 alternatives are appended; no true target pose or neighbor geometry is consulted by this generator.')
    p('Rotation around the closing axis preserves the aperture direction while moving the palm. Every new candidate still passes the full existing collision and downstream preview checks. Candidate expansion can improve reachability but can also cost planning time, create a less stable grasp or fail in denser geometry; the experiments retain those outcomes. The known three-neighbor development failure is recovered physically, while its five-neighbor counterpart remains a documented rejection.')
    h('Feedback and recovery scope')
    p('The inherited feedback controller monitors bilateral contacts during trajectories, stops after 40 ms sustained loss and increases bounded preload for weak contact. A recovery episode permits at most two attempts, re-observing or performing a checked open/withdraw/home sequence where allowed, without scene reset. The new ablation uses active sensing, ordinary control and one attempt in both arms to isolate candidate generation; it does not measure a feedback or retry benefit.')

    page('3  New frozen paired evaluation')
    p(f"The engine was frozen before the new root seed {evidence['seed']} was evaluated. Each method uses 60 three-neighbor and 30 five-neighbor episodes, balanced across three targets: 180 physical episodes total. Within each scene, methods share exact object identities, settled poses, estimated poses and scene/sensor/planner seeds. Physics, corruption, success gates and control are identical; only the candidate strategy changes. Every failure remains in the denominator.")
    rows = [['Condition', 'Success', '95% Wilson interval', 'Mean plan / total time']]
    for name, s in evidence['cases'].items():
        lo, hi = s['success_rate_95pct_interval']
        rows.append([name.replace('_', ' '), f"{s['successes']}/{s['trials']} ({s['success_rate']:.1%})",
                     f'{lo:.1%} - {hi:.1%}', f"{s['mean_planning_time_s']:.2f} / {s['mean_total_time_s']:.2f} s"])
    table(rows, [1.3, 1.1, 1.15, 1.35])
    h('Per-target final success')
    rows = [['Target', 'Baseline clutter', 'Local clutter', 'Baseline dense', 'Local dense']]
    for obj in ('foam_brick', 'gelatin_box', 'pudding_box'):
        cells = [obj.replace('_', ' ')]
        for s in evidence['cases'].values():
            stats = s['per_object'][obj]; cells.append(f"{stats['successes']}/{stats['trials']}")
        rows.append(cells)
    table(rows, [1.25, 1, 1, 1, 1])
    h('Paired changes and interpretation')
    for scene, comparison in evidence['paired'].items():
        recovered, regressed = comparison['recovered_trials'], comparison['regressed_trials']
        p(f"<b>{scene}:</b> {len(recovered)} failed scenes recovered; {len(regressed)} previously successful scenes regressed. Exact two-sided paired McNemar p = {comparison['exact_mcnemar_p']:.4f}. Recovery trial IDs: {recovered or 'none'}. Regression trial IDs: {regressed or 'none'}.")
    p('These finite-sample estimates concern the stated synthetic workcell. A rate near or above 90% is not a demonstrated lower bound on general clutter performance. The two scene conditions are reported separately, and no pooled rate is used to obscure the harder condition. Groups were run with overlapping local processes; wall times describe this execution environment and should not be treated as controlled hardware speed comparisons.')
    p('Provenance: Python '+evidence['provenance']['python']+', MuJoCo '+evidence['provenance']['mujoco']+', NumPy '+evidence['provenance']['numpy']+'. The protocol, full JSONL, CSV, summaries and recomputed paired comparisons are in docs/validation/v2.1.0.', 'CaptionReport')

    page('4  Failures, historical evidence and limits')
    h('Complete new failure accounting')
    for name, stats in evidence['cases'].items():
        failures = ', '.join(f'{stage}: {n}' for stage, n in stats['failures'].items()) or 'none'
        p(f"<b>{name}:</b> {failures}. Trial IDs: {stats['failure_trials'] or 'none'}.")
    # Derive detailed phase counts from complete logs, rather than hand-selected examples.
    for name in ('local_clutter', 'local_dense'):
        _, rows = load_case(args.evidence / name)
        phases = Counter(c.get('phase', 'unrecorded') for r in rows if not r['success']
                         for attempt in r['attempts'] for c in attempt.get('candidate_rejections', []))
        if phases:
            p(f"Rejected candidate phases in failed {name} episodes: "+', '.join(f'{key}={value}' for key,value in phases.items())+'. Counts are candidate rejections, not additional episodes.')
    h('Historical work retained, not reattributed')
    table([['Tagged study', 'Frozen historical result / scope'],
           ['v1.1.0 baseline', 'IID pick 178/180; place 175/180. Six public models, known pose, single target.'],
           ['v1.3.0 obstacle reliability', '22 cm barrier 112/120; 28 cm 108/120. Paired with exact historical v1.2 source.'],
           ['v1.4.0 synthetic sensing', 'Damaged single frame 0/60; multiview fusion 59/60. Single known box proxy.'],
           ['v2.0.0 physical clutter', 'Active/recovery three-neighbor 52/60; five-neighbor recovery 25/30. No formal retry gain.']], [1.1, 2.7])
    p('The full tagged audits cover 600 baseline, 360 obstacle, 480 obstacle-reliability, 240 sensing and 270 clutter records. They were rerun successfully against their original Git references. They validate the provenance and recorded criteria; they do not constitute 1,950 newly executed simulations on this computer. The new 180 episodes are distinct from those historical records.')
    h('What remains unverified')
    p('The generator adds a finite local family; it does not solve arbitrary 6D grasping or rearrangement. Target masks, calibration, template class, stable roll and simulator collision maps remain idealized. Alpha transparency does not model refraction, correlated optical failure or unknown transparent objects. Clutter is not stacked or dynamically rearranged. Discrete collision checks are not a continuous safety proof, contact-force limits are not calibrated real-robot guarantees, and no real hardware transfer is claimed.')
    p('The experiment supports an incremental, reproducible geometric intervention. It does not establish universal success, a new perception model, or an independent recovery-controller contribution. Team-specific authorship and personal contribution statements should reflect the actual group work; this report does not invent member identities.')

    page('5  Reproduction and deliverables')
    h('Run the principal functions')
    p('Use Python 3.12 and a project-local virtual environment. Core simulation dependencies remain pinned. The ZIP includes downloaded models and their licenses; a fresh Git clone must run both setup scripts. The ZIP does not include Python, installed wheels or .venv, so an entirely disconnected new machine still needs those dependencies prepared.')
    p('py -3.12 -m venv .venv<br/>.venv/Scripts/python -m pip install -r requirements.txt<br/>.venv/Scripts/python scripts/setup_assets.py<br/>.venv/Scripts/python scripts/setup_ycb.py', 'CodeReport')
    p('.venv/Scripts/python clutter_main.py --scene clutter --trials 3<br/>.venv/Scripts/python clutter_main.py --headless --scene dense<br/>.venv/Scripts/python scripts/check_completion_evidence.py<br/>.venv/Scripts/python -m unittest discover -s tests -v', 'CodeReport')
    p('Full rerun: scripts/benchmark_completion.py --output outputs/new_run --workers 1. Use a new directory. The default seed and all 180 samples are fixed in the saved protocol; --resume reuses complete groups and refuses partial-group overwrites. Serial workers are recommended for interpretable timing. For old evidence use explicit historical --source-ref tags, rather than assigning old hashes to the new engine.')
    h('Reviewable artifacts and checks')
    p('The final ZIP contains this report, a captioned introduction/demo video, sources, tests, instructions, pinned assets/licenses and all selected evidence. The video includes the original rejected development scene, a successful same-scene inclined grasp, and a five-neighbor release. These demos use development seeds and are excluded from the formal denominator. Camera/lighting changes are visualization only. The report is generated from audited JSON; historical reports and results are preserved.')
    p('Validation on this checkout: 39 automated tests passed, including three rejection tests for corrupted force/contact outcomes and stale source; all five historical evidence audits passed. The new audit verifies every episode, exact scene/observation pairing, source fingerprint, balance, attempts, force and scene gates. The packaged project is additionally extracted to an independent directory for its own audit and a physical release smoke test. The green destination marker now derives from Config, including its actual 55 mm acceptance radius.')
    p('Frozen engine SHA-256:<br/>'+evidence['source_sha256'], 'CodeReport')
    h('References and asset attribution')
    references = [
        '[1] MuJoCo documentation: <link href="https://mujoco.readthedocs.io/en/stable/overview.html" color="#087f82">mujoco.readthedocs.io/en/stable/overview.html</link>. Contact-dynamics simulation platform.',
        '[2] Google DeepMind, MuJoCo Menagerie, Franka Panda model. <link href="https://github.com/google-deepmind/mujoco_menagerie" color="#087f82">github.com/google-deepmind/mujoco_menagerie</link>. Commit 0059d4335f8156206f63a35662313385f7ad6d74; bundled model LICENSE retained.',
        '[3] B. Calli et al., Benchmarking in Manipulation Research: The YCB Object and Model Set and Benchmarking Protocols, 2015. <link href="https://arxiv.org/abs/1502.03143" color="#087f82">arxiv.org/abs/1502.03143</link>. YCB data attribution: CC BY 4.0.',
        '[4] elpis-lab/YCB_Dataset, simulation conversion. <link href="https://github.com/elpis-lab/YCB_Dataset" color="#087f82">github.com/elpis-lab/YCB_Dataset</link>. Commit 9e8c6488a2ff673d9aa48a91492fb89423c1b106; MIT conversion LICENSE retained.',
        '[5] Inherited project and exact baseline tags: <link href="https://github.com/m13961023616-pixel/EE5110-SegC" color="#087f82">github.com/m13961023616-pixel/EE5110-SegC</link>. Original course brief: EE5110 Segment C CA, supplied locally; course slides are not redistributed in the source repository.',
    ]
    for reference in references:
        p(reference, 'CaptionReport')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    def footer(canvas, document):
        canvas.setStrokeColor(PALE); canvas.line(18 * mm, 17 * mm, 192 * mm, 17 * mm)
        canvas.setFont('Helvetica', 8); canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, 12 * mm, 'EE5110 | Autonomous manipulation | v2.1.0')
        canvas.drawRightString(192 * mm, 12 * mm, str(document.page))
    SimpleDocTemplate(str(args.output), pagesize=(210 * mm, 297 * mm), leftMargin=18 * mm,
                      rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=23 * mm,
                      title='Autonomous Manipulation in Physical Clutter', author='EE5110 Segment C project').build(
                          story, onFirstPage=footer, onLaterPages=footer)
    print(args.output)


if __name__ == '__main__':
    main()

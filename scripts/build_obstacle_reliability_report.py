"""Create a compact report from exact-version paired reliability evidence."""
from pathlib import Path
import json
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ['v12_22', 'robust_22', 'v12_28', 'robust_28']


def main():
    data = {}
    for group in GROUPS:
        folder = ROOT / 'docs/validation/v1.3.0' / group
        summaries, logs = list(folder.glob('summary_*.json')), list(folder.glob('trials_*.jsonl'))
        assert len(summaries) == len(logs) == 1
        s = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        assert len(rows) == s['trials'] == 120
        data[group] = s, rows
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Small', fontSize=9, leading=12, spaceAfter=8))
    styles.add(ParagraphStyle(name='Cell', fontSize=8, leading=10))
    story = []

    def p(text, style='Small'):
        story.append(Paragraph(text, styles[style]))

    def h(text):
        p(text, 'Heading2')

    def table(rows, widths):
        cells = [[Paragraph('<font color="white">' + str(c) + '</font>' if i == 0 else str(c), styles['Cell'])
                  for c in row] for i, row in enumerate(rows)]
        t = Table(cells, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#18334a')),
                              ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                              ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7)]))
        story.extend([t, Spacer(1, 10)])

    p('Improving Obstacle-Transport Reliability', 'Title')
    p('EE5110 Segment C | v1.3.0 | 9 October 2026')
    h('Failure analysis and unchanged challenge')
    p('The v1.2.0 high-barrier investigation failed mainly in planning. A converged end-effector pose could still place the elbow or wrist inside the barrier; increasing tree search cannot fix a colliding goal. Local IK failure also hid feasible redundant configurations. Some packaging placement failures occurred near the rear table edge.')
    p('The improved robust planner filters static robot collision at each IK solution, tries up to nine bounded local seeds, adds an equivalent jaw-swapped grasp orientation, retains the top clearance route and adds checked side-corridor fallbacks. Placement centres prefer 25 mm toward the table interior, inside the unchanged 55 mm acceptance zone. The model, contact parameters, force limits, obstacle geometry, spawn distribution and target centre are unchanged.')
    h('Independent frozen-code paired evaluation')
    p('Development used seed 43 and replayed the 16 historical high-barrier failures, recovering 12. Those old scenes are diagnostics, not a fresh success-rate test. After freezing parameters, seed 20261401 supplies 120 scenes per condition: 20 per YCB object, for 480 trials. The comparator runs the exact source exported from Git tag v1.2.0. Each old/new pair uses the same object, scene seed and settled pose; planner randomness is isolated. Every failure remains in the denominator, without physical retry or resampling.')
    rows = [['Barrier / version', 'Success', 'Rate', '95% Wilson interval', 'Mean planning / total wall time']]
    for group in GROUPS:
        s, _ = data[group]
        lo, hi = s['success_rate_95pct_interval']
        rows.append([('22 cm' if group.endswith('22') else '28 cm') + (' / v1.2.0' if group.startswith('v12') else ' / robust'),
                     f"{s['successes']}/120", f"{s['success_rate']:.1%}", f'{lo:.1%} - {hi:.1%}',
                     f"{s['mean_planning_time_s']:.2f} / {s['mean_total_time_s']:.2f} s"])
    table(rows, [95, 60, 45, 105, 184])
    for height in ('22', '28'):
        a, b = data['v12_' + height][1], data['robust_' + height][1]
        recovered = sum(not x['success'] and y['success'] for x, y in zip(a, b))
        regressed = sum(x['success'] and not y['success'] for x, y in zip(a, b))
        p(f'<b>{height} cm paired changes:</b> {recovered} failures recovered, {regressed} formerly successful scenes regressed.')
    p('Rates apply only to this static-barrier family and known-pose single-object workcell. They are measured point estimates, not a universal 90% lower-bound guarantee. Timing is indicative wall time on the evaluation machine, including feasibility checking; parallel background runs can affect it.')
    story.append(PageBreak())
    h('Object coverage, physical gates and retained failures')
    rows = [['Object', 'v1.2 / 22 cm', 'Robust / 22 cm', 'v1.2 / 28 cm', 'Robust / 28 cm']]
    for obj in data['v12_22'][0]['object_pool']:
        rows.append([obj.replace('_', ' '), *[f"{data[g][0]['per_object'][obj]['successes']}/20" for g in GROUPS]])
    table(rows, [125, 91, 91, 91, 91])
    for group in GROUPS:
        s, _ = data[group]
        p('<b>' + group + ' failures:</b> ' + (', '.join(f'{k}={v}' for k, v in s['failures'].items()) or 'none') + '.')
    h('What was changed, and what was held fixed')
    p('IK accuracy remains 2 mm in position and 0.025 rad in rotation. The filter checks static robot/environment and self-collision while ignoring the grasped object for IK only; complete edge validation still checks robot, object and environment. The nine seeds are finite perturbations of the current seed, not random scene resampling. Equivalent jaw symmetry flips local x/y axes while keeping the grasp point, closing width and approach direction.')
    p('The obstacle remains centred at (0.485, 0.145) m, width 0.24 m, thickness 0.016 m and top 0.22/0.28 m. Spawn x/y and random yaw are exactly the v1.2.0 challenge settings. The place target remains (0.48, 0.30) m. Gripper force is capped at 40 N; speed/acceleration limits remain 0.5 rad/s and 2 rad/s2. RRT keeps its 180-iteration outer bound. No friction, mass, scale, solver parameter or collision tolerance was relaxed.')
    p('Full-task success still requires COM lift above initial + 80 mm for 1 s, bilateral contact on at least 95% of hold samples, table support after release, placement error below 55 mm and linear speed below 0.02 m/s. Physical object/barrier penetration above 1 mm disqualifies success. Preflight held-object transforms live only in scratch MjData; execution uses real contacts and actuators, without weld or teleport.')
    h('Validation and remaining limits')
    p('Nineteen local checks pass, including an exact elbow-collision regression with real release, jaw symmetry, live-state isolation, dataset tasks and asset verification. The offline source/model ZIP was extracted independently and checked for actual obstacle transport. Some feasible goal poses remain hard to find, and packaging can tip or collide on release. The known difficult fixed foam-brick high-barrier scene is not silently removed. The demonstration replays a recovered historical scene and is separate from the fresh random experiment.')
    p('Obstacle/object poses are known; there are no estimated cameras, dynamic obstacles, clutter, deformation, unseen objects or recovery. Collision sampling every 0.015 rad and contact monitoring every 2 ms are not a continuous safety proof. Held-object planning assumes an approximate rigid relative pose. Results are simulator evidence, not calibrated real-robot performance.')
    story.append(PageBreak())
    h('Actual recovered high-barrier trial')
    story.append(Image(str(ROOT / 'docs/images/obstacle_place_v1.3.0.png'), width=440, height=330))
    p('Recorded foam-brick physical release behind the 28 cm barrier. This replay uses scene seed 20262308 and planner seed 20361308, matching a previously rejected elbow-collision case; it is not included as an extra success in the formal 480-trial denominator.')
    h('Reproduction and provenance')
    p('Run scripts/benchmark_obstacle_reliability.py in a Git clone with v1.2.0 available. It exports the exact old engine into an ignored output folder and uses the same pinned models. Run scripts/check_obstacle_reliability.py to verify both source hashes, pairing, physical gates, force limits, all failures and measured improvement. In the offline ZIP, use --offline to check the retained old fingerprint without Git; current source is still hashed and checked.')
    p('Formal JSON/JSONL/CSV records: docs/validation/v1.3.0. Summary output-directory fields are normalized to repository-relative paths; no trial outcomes are edited. Existing v1.1.0 and v1.2.0 evidence is audited against its explicit historical tags, rather than being assigned to current code.')
    for label, group in [('Exact v1.2.0 source', 'v12_22'), ('Frozen v1.3.0 source', 'robust_22')]:
        p(label + ' SHA-256:<br/><font size="7">' + data[group][0]['source_sha256'] + '</font>')
    p('Planner reference: Kuffner and LaValle, RRT-Connect, ICRA 2000, DOI 10.1109/ROBOT.2000.844730. The reliability improvement here is a whole-pipeline comparison; individual contributions are not claimed as a separately measured ablation.')
    target = ROOT / 'docs/report/obstacle_reliability_v1.3.0.pdf'
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(18*mm, 12*mm, 'EE5110 | Obstacle reliability | v1.3.0')
        canvas.drawRightString(192*mm, 12*mm, str(doc.page))
    SimpleDocTemplate(str(target), pagesize=(210*mm, 297*mm), leftMargin=18*mm, rightMargin=18*mm,
                      topMargin=15*mm, bottomMargin=19*mm).build(story, onFirstPage=footer, onLaterPages=footer)
    print(target)


if __name__ == '__main__':
    main()

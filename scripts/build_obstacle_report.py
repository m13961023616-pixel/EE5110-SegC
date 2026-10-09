"""Build the three-page obstacle investigation report from retained evidence."""
from pathlib import Path
import json
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image

ROOT = Path(__file__).resolve().parents[1]
GROUPS = ['clear_direct', 'barrier_direct', 'barrier_rrt', 'barrier_clearance', 'tall_rrt', 'tall_clearance']
LABELS = ['Clear / direct', '22 cm / direct', '22 cm / RRT', '22 cm / hybrid', '28 cm / RRT', '28 cm / hybrid']


def main():
    records = {}
    for name in GROUPS:
        folder = ROOT / 'docs/validation/v1.2.0' / name
        summaries = list(folder.glob('summary_*.json'))
        logs = list(folder.glob('trials_*.jsonl'))
        assert len(summaries) == len(logs) == 1
        summary = json.loads(summaries[0].read_text())
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        assert len(rows) == summary['trials'] == 60
        records[name] = (summary, rows)
    hashes = {s['source_sha256'] for s, _ in records.values()}
    assert len(hashes) == 1
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySmall', fontSize=9, leading=12, spaceAfter=7))
    styles.add(ParagraphStyle(name='CellSmall', fontSize=8, leading=10))
    styles.add(ParagraphStyle(name='CaptionSmall', fontSize=8, leading=10, alignment=TA_CENTER, spaceAfter=8))
    story = []

    def paragraph(text, style='BodySmall'):
        story.append(Paragraph(text, styles[style]))

    def heading(text):
        paragraph(text, 'Heading2')

    def table(rows, widths):
        cells = [[Paragraph('<font color="white">' + str(cell) + '</font>' if index == 0 else str(cell),
                            styles['CellSmall']) for cell in row] for index, row in enumerate(rows)]
        t = Table(cells, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#18334a')),
                              ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                              ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                              ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
                              ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
        # Paragraph text colors must also be white in the header.
        for cell in cells[0]:
            cell.style = ParagraphStyle(name='HeaderCell', parent=styles['CellSmall'], textColor=colors.white)
        story.append(t)
        story.append(Spacer(1, 9))

    paragraph('Obstacle-Aware Physical Pick-and-Place', 'Title')
    paragraph('EE5110 Segment C | v1.2.0 | 9 October 2026', 'CaptionSmall')
    heading('Research question and controlled challenge')
    paragraph('Can collision-aware transit planning recover complete pick-and-place tasks when a solid barrier blocks the baseline Cartesian transfer? The original geometry-based grasp algorithm, contact-driven Panda control and physical success thresholds are retained. This is a static-obstacle investigation with known poses, not a vision or multi-object clutter system.')
    paragraph('Six YCB objects are balanced across 60 scenes per condition (10 each). All six conditions use the same object order and independent scene seeds, for 360 physical trials. Development used seed 43; frozen evaluation uses seed 20261301. All failures remain in the denominator; there is no physical retry or failed-scene resampling.')
    heading('Frozen evaluation results')
    rows = [['Condition', 'Success', 'Rate', '95% Wilson interval', 'Mean planning / total wall time']]
    for label, name in zip(LABELS, GROUPS):
        s, _ = records[name]
        lo, hi = s['success_rate_95pct_interval']
        rows.append([label, f"{s['successes']}/60", f"{s['success_rate']:.1%}",
                     f'{lo:.1%} - {hi:.1%}', f"{s['mean_planning_time_s']:.2f} / {s['mean_total_time_s']:.2f} s"])
    table(rows, [98, 52, 48, 110, 181])
    heading('Paired comparison, without selective reporting')
    for first, second, label in [('barrier_direct', 'barrier_clearance', '22 cm: direct to hybrid'),
                                  ('barrier_rrt', 'barrier_clearance', '22 cm: RRT to hybrid'),
                                  ('tall_rrt', 'tall_clearance', '28 cm: RRT to hybrid')]:
        a, b = records[first][1], records[second][1]
        wins = sum(not x['success'] and y['success'] for x, y in zip(a, b))
        regressions = sum(x['success'] and not y['success'] for x, y in zip(a, b))
        paragraph(f'{label}: {wins} failed scenes recovered; {regressions} previously successful scenes failed.')
    paragraph('The clear control uses the same shifted placement target and spawn range as the barrier groups. It is the relevant comparator; the historical v1.1.0 success rates come from a different workspace and are not presented as a paired algorithm comparison.')
    story.append(PageBreak())
    heading('Algorithm and physical execution')
    paragraph('<b>Direct:</b> existing collision-sampled Cartesian transfer, followed by candidate target offsets and joint IK. Obstructed tasks are safely rejected in preflight.<br/><b>RRT:</b> on transit collision, try the straight joint-space edge, then bounded bidirectional RRT-Connect. Trees grow with 0.25 rad steps, 15% opposite-root bias, at most 180 outer iterations and bounded connect loops. Every extension and shortcut uses the same robot and held-object collision checker.<br/><b>Hybrid:</b> first lift the object bottom above the barrier top plus 60 mm, transfer at that clearance, then return to the original transfer endpoint. Preserve grasp orientation on checked Cartesian segments; use RRT on blocked transit segments or if the clearance route fails.')
    paragraph('Preflight uses isolated MjData with an approximate rigid held-object transform; it never moves the real object. Execution uses actuator commands and actual contacts only. Each path is time-scaled with the unchanged 0.5 rad/s speed and 2 rad/s2 acceleration limits. During physics, object/barrier penetration is recorded every 2 ms and disqualifies a nominal success above 1 mm. The gripper force remains capped at 40 N.')
    heading('Environment and unchanged acceptance thresholds')
    paragraph('The fixed barrier is centered at (0.485, 0.145) m, width 0.24 m, thickness 0.016 m, with tops at 0.22 or 0.28 m. Challenge spawn x is [0.40, 0.55] m and y is [-0.10, 0.06] m, with random yaw. The placement center moves to (0.48, 0.30) m to leave usable space behind the barrier. Every comparator uses these same changes; object metric scale, mass, contact settings and stable support faces are unchanged.')
    paragraph('A successful task requires a COM lift above initial height + 80 mm for 1 s, bilateral contact on at least 95% of hold samples, release with table support, placement distance below 55 mm and linear speed below 0.02 m/s. The additional barrier gate requires no penetration above 1 mm. A verified lift alone does not count as full placement success.')
    story.append(Image(str(ROOT / 'docs/images/obstacle_place_v1.2.0.png'), width=360, height=270))
    paragraph('Actual fixed foam-brick trial after verified release. The demonstration camera views the placement side; only the camera differs from the benchmark.', 'CaptionSmall')
    story.append(PageBreak())
    heading('Object coverage and retained failures')
    rows = [['Object', 'Clear', 'Direct 22', 'RRT 22', 'Hybrid 22', 'RRT 28', 'Hybrid 28']]
    for obj in records['clear_direct'][0]['object_pool']:
        rows.append([obj.replace('_', ' '), *[f"{records[g][0]['per_object'][obj]['successes']}/10" for g in GROUPS]])
    table(rows, [119, 55, 63, 63, 63, 63, 63])
    for label, name in zip(LABELS, GROUPS):
        s, trial_rows = records[name]
        paragraph('<b>' + label + ' failures:</b> ' + (', '.join(f'{k}={v}' for k, v in s['failures'].items()) or 'none') + '.')
        if s['planner'] != 'direct':
            events = [e for r in trial_rows for e in r['search_events'] if e['method'] == 'rrt_connect']
            paragraph(f"RRT calls including candidate preflight: {len(events)}; calls with actual tree expansion: {sum(e['iterations'] > 0 for e in events)}. These are search invocations, not physical grasp attempts.")
    heading('Limits and interpretation')
    paragraph('Joint-space paths can change object orientation; kinematic clearance alone does not prove grip stability or tracking accuracy. The orientation-preserving route is more structured but adds motion and preflight cost. The recorded failure stages separate infeasible paths from actual execution and placement failures. Ten scenes per object are limited evidence; overall Wilson intervals and all per-object counts are shown rather than claiming universal reliability.')
    paragraph('Obstacle and object poses are known. The barrier family is fixed in position and width; there are no moving obstacles, estimated sensing, unseen shapes, deformation or recovery. Collision checks sample joint edges every 0.015 rad and physical contacts every 2 ms; these are not a continuous collision-free proof. Held-object motion in preflight is an approximation. No real-robot performance is claimed.')
    heading('Reproduction and provenance')
    paragraph('Run scripts/benchmark_obstacles.py for all six groups; run scripts/check_obstacle_evidence.py to audit pairing, fingerprint, physical gates and retained failures. Formal JSON/JSONL/CSV files are under docs/validation/v1.2.0. The source ZIP includes models, upstream licenses and run instructions. Sixteen local checks include a genuine blocked-route task, bounded search, deterministic paths and scratch-state isolation.')
    paragraph('Frozen source SHA-256:<br/>' + '<font size="7">' + next(iter(hashes)) + '</font>')
    paragraph('Reference: J. Kuffner and S. LaValle, RRT-Connect: An Efficient Approach to Single-Query Path Planning, ICRA 2000, DOI 10.1109/ROBOT.2000.844730. Primary paper: https://www.clear.rice.edu/comp450/papers/kuffner_lavalle_00.pdf', 'CellSmall')
    target = ROOT / 'docs/report/obstacle_report_v1.2.0.pdf'
    def footer(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(18 * mm, 12 * mm, 'EE5110 Segment C | Obstacle investigation | v1.2.0')
        canvas.drawRightString(192 * mm, 12 * mm, str(doc.page))
    SimpleDocTemplate(str(target), pagesize=(210*mm, 297*mm), leftMargin=18*mm,
                      rightMargin=18*mm, topMargin=15*mm, bottomMargin=19*mm).build(story, onFirstPage=footer, onLaterPages=footer)
    print(target)


if __name__ == '__main__':
    main()

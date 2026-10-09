"""Four-page report of frozen clutter episodes, assumptions and every failure."""
from pathlib import Path
import json
from statistics import mean, median
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image
ROOT=Path(__file__).resolve().parents[1]
GROUPS=['isolated_active','obstacles_active','fixed_clutter','active_clutter','recovery_clutter','dense_recovery']


def main():
    data={}
    for g in GROUPS:
        d=ROOT/'docs/validation/v2.0.0'/g
        s=json.loads(next(d.glob('summary_*.json')).read_text())
        r=[json.loads(l) for l in next(d.glob('trials_*.jsonl')).read_text().splitlines()]
        assert len(r)==s['trials'];data[g]=s,r
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodySmall',fontSize=9,leading=12,spaceAfter=9))
    styles.add(ParagraphStyle(name='CellSmall',fontSize=8,leading=10))
    story=[]
    def p(t,style='BodySmall'):story.append(Paragraph(t,styles[style]))
    def h(t):p(t,'Heading2')
    def table(rows,widths):
        t=Table([[Paragraph(str(c),styles['CellSmall']) for c in row] for row in rows],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce9f3')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.whitesmoke,colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.extend([t,Spacer(1,10)])
    p('Transparent Targets in Physical Clutter','Title')
    p('EE5110 Segment C | v2.0.0 | 9 October 2026')
    h('Objective and bounded workcell')
    p('The V2 extension combines estimated grasp poses, bounded active observations, contact feedback, limited recovery, simultaneous distractors and compound obstacles. A transparent-appearance target must be grasped by real contact, lifted, transported across the obstacle arrangement, released and verified inside the destination zone while preserving neighboring objects.')
    p('Three public YCB box-like targets are evaluated: foam brick, gelatin box and pudding box. Distractors are real free bodies selected from the remaining six-object YCB catalog. Clutter activates three distractors; dense activates all five. Collision, gravity, original mass and friction remain enabled throughout each episode. No distractor is hidden, frozen or disabled after initialization. Objects are initialized once, then settle for 0.8 s; recovery never resets or resamples the physical scene.')
    p('The compound arrangement contains a 0.24 m wide, 0.016 m thick, 0.22 m high barrier plus two separate 0.18 m high posts. Target x/y are randomized within [0.43,0.52] and [-0.105,-0.065] m, with random yaw. Distractors use nearby offset locations with jitter and random yaw; this is bounded tabletop clutter, not a touching or stacked pile. The destination remains (0.48,0.30) m.')
    h('Development sequence and implemented methods')
    p('<b>1. Active sensing:</b> calibrated synthetic orthographic views are enabled in batches of eight frames, with a 16-frame minimum and 64-frame maximum. Known-mesh fitting generates T_world_object. Acceptance requires at least 48 distinct foreground points, footprint extent error at most 6 mm, consecutive position change at most 3 mm and yaw change at most 0.08 rad. These are geometric heuristics, not a calibrated probability of correctness.')
    p('<b>2. Feedback/recovery:</b> finger normal forces and bilateral contact are monitored during motion. Low normal force can increase bounded preload; sustained bilateral contact loss for 40 ms stops transport. An episode allows at most two attempts. Observation or pre-motion planning failures trigger re-observation; grasp contact failure permits a collision-checked open/withdraw/home sequence and another candidate. Unsafe collision/slip/withdrawal failures abort.')
    p('<b>3-4. Obstacle/clutter integration:</b> grasp generation uses estimated poses and equivalent jaw orientations. Bounded multi-seed IK, checked clearance/side corridors and placement yaw alternatives cover the compound environment. Transit IK failure now still tries intermediate clearance poses; a dedicated foam-brick regression verifies this recovery. Every held-object prediction is scratch-only; live execution uses actuators and physical contacts.')
    story.append(PageBreak())
    h('Frozen independent evaluation')
    p('Development used seed 43 and deterministic regression scenes. After freezing engine code, seed 20261601 generates six balanced conditions, totaling 270 physical episodes. Each clutter method sees the exact same settled target and distractor poses. Fixed/active use one attempt; recovery uses active sensing, feedback and at most two attempts. Sensor corruption law and seeds are shared, but differing view schedules change the observation stream. Isolated/obstacle/dense conditions test different environments, not a single algorithm-only ablation.')
    rows=[['Condition','First success','Final success','95% Wilson','Mean frames','Mean total wall time']]
    for g in GROUPS:
        s,r=data[g];n=s['trials'];lo,hi=s['success_rate_95pct_interval']
        rows.append([g.replace('_',' '),f"{sum(x['first_attempt_success'] for x in r)}/{n}",
                     f"{s['successes']}/{n} ({s['success_rate']:.1%})",f'{lo:.1%}-{hi:.1%}',
                     f"{mean(x['observed_frames'] for x in r):.1f}",f"{s['mean_total_time_s']:.2f} s"])
    table(rows,[100, sixty:=60,70,85,60,114])
    h('Per-object final success')
    rows=[['Target',*['Isolated','Obstacles','Fixed clutter','Active clutter','Recovery clutter','Dense']]]
    for obj in ('foam_brick','gelatin_box','pudding_box'):
        rows.append([obj.replace('_',' '),*[f"{data[g][0]['per_object'][obj]['successes']}/{data[g][0]['per_object'][obj]['trials']}" for g in GROUPS]])
    table(rows,[95,55,55,65,65,80,74])
    for a,b in [('fixed_clutter','active_clutter'),('active_clutter','recovery_clutter')]:
        x,y=data[a][1],data[b][1]
        recovered=sum(not u['success'] and v['success'] for u,v in zip(x,y))
        regressed=sum(u['success'] and not v['success'] for u,v in zip(x,y))
        p(f'<b>{a} to {b}:</b> {recovered} failures recovered, {regressed} successful scenes regressed.')
    r=data['recovery_clutter'][1]
    p(f"Within recovery episodes, {sum(x['success'] and not x['first_attempt_success'] for x in r)} first-attempt failures were recovered; {sum(x['attempt_count']>1 for x in r)} episodes used another attempt. This mechanism must not be credited with recovery that the experiment did not observe.")
    p('Frame counts represent actual observations consumed by the policy. Nominal serial acquisition is frames/30 s; the synthetic scene does not physically advance during capture. Wall times include planning, physical simulation and recovery; concurrent local evaluations affect timing. Success rates are finite-sample estimates within the stated workcell, not general glass or arbitrary-clutter guarantees.')
    story.append(PageBreak())
    h('Physical task and scene-preservation gates')
    p('Success requires COM lift above the original episode initial height +80 mm for 1 s, bilateral contact on at least 95% of hold samples, actual release, table support, destination error below 55 mm and final linear speed below 0.02 m/s. Gripper actuator force stays at most 40 N; joint speed/acceleration limits remain 0.5 rad/s and 2 rad/s2. Neither friction nor success tolerances were relaxed.')
    p('The scene additionally requires zero monitored unsafe-contact steps, target penetration into a distractor or fixed obstacle at most 1 mm, and every distractor maximum translation at most 20 mm. Robot/distractor contact deeper than 0.5 mm is unsafe. A target-only successful place can still fail the overall scene gate. Displacement is tracked throughout execution, not just at the final frame. Object rotations and surface damage are not independently bounded.')
    h('Every failure remains in the denominator')
    for g in GROUPS:
        p('<b>'+g+':</b> '+(', '.join(f'{k}={v}' for k,v in data[g][0]['failures'].items()) or 'none')+'.')
    h('Sensor assumptions and remaining limitations')
    p('Transparent appearance removes printed texture and uses visual alpha 0.25, preserving rigid-body contact properties. The sensor uses 96x96 ideal orthographic range rays, 98% independent missing returns, 10% permanently missing pixels per view, and 0.5 mm Gaussian z noise. Three calibrated views include overhead and oblique directions. These are explicit synthetic optical-corruption conditions; alpha rendering does not simulate real glass refraction, specular errors or glass fracture.')
    p('Target selection uses an ideal simulator instance-mask channel. The estimator only receives masked measured points and known object class/mesh; it never substitutes true pose on failure. Upright roll and the 12-120 mm height gate are known priors. Collision checking, held-object relationships, lowering geometry, contact identity and outcome verification still use simulation state. This is not an end-to-end image-only controller or learned transparent-object recognition system.')
    p('Remaining failures include difficult arm/grasp configurations and task execution errors. A bounded re-observation policy cannot make a geometrically infeasible grasp feasible. Point-cloud confidence can be biased by persistent occlusion. Discrete joint checks every 0.015 rad and physical contact checks every 2 ms do not prove continuous collision safety. Dynamic obstacles, stacked clutter, arbitrary target shapes, calibrated optics and real-robot transfer remain unverified.')
    story.append(PageBreak())
    h('Actual dense-clutter physical release')
    story.append(Image(str(ROOT/'docs/images/clutter_place_v2.0.0.png'),width=420,height=315))
    p('Foam-brick transparent-appearance proxy released inside the destination behind the compound barrier, with five simultaneously active distractors. The demonstration uses development scene seed 1046 and sensor seed 100046 and is excluded from the 270-episode denominator. Camera and goal-marker adjustments are visualization only. Video and the physical log document real actuator/contact execution, without weld, adhesion or live-state teleport.')
    h('Validation and reproduction')
    p('34 local tests pass: existing baseline/assets/dataset/obstacle/sensing regressions plus bounded active observations, scene-preserving recovery, simultaneous distractors, displacement gates and actual transparent-clutter release. Historical evidence is audited against explicit v1.1.0-v1.4.0 Git tags. Current validation checks every attempt, the original-height gate, exact paired initial clutter, force bounds, all scene gates and the frozen engine fingerprint.')
    p('GUI: python clutter_main.py --scene clutter --trials 3<br/>Dense: python clutter_main.py --scene dense --trials 3<br/>Headless comparison: python scripts/benchmark_v2.py<br/>Evidence audit: python scripts/check_v2_evidence.py<br/>Re-record development video: python scripts/record_clutter_demo.py')
    p('Evidence: docs/validation/v2.0.0. JSONL keeps all attempts, failure stages, sensor checks, frame counts, initial scene poses, planner diagnostics and physical results. Only summary output paths are normalized to repository-relative directories. The offline ZIP includes Python sources, pinned models and licenses, report and actual video; it excludes credentials, environment folders and raw course attachments.')
    p('Frozen source SHA-256:<br/><font size="7">'+data['recovery_clutter'][0]['source_sha256']+'</font>')
    target=ROOT/'docs/report/clutter_v2.0.0.pdf'
    def footer(c,d):
        c.setFont('Helvetica',8);c.drawString(18*mm,12*mm,'EE5110 | Transparent proxy in physical clutter | v2.0.0');c.drawRightString(192*mm,12*mm,str(d.page))
    SimpleDocTemplate(str(target),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,
                      topMargin=15*mm,bottomMargin=19*mm).build(story,onFirstPage=footer,onLaterPages=footer)
    print(target)


if __name__=='__main__':main()

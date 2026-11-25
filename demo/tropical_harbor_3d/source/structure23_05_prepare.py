"""Combine the reviewed structure controls inside the owned GUI session."""
import bpy,json
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/terrain_structure_20261123';DOC=ROOT.parents[1]/'docs/reference_review_20261123'
upper=json.loads((DOC/'structure_upper_plan.json').read_text(encoding='utf8'))
lower=json.loads((DOC/'structure_lower_plan.json').read_text(encoding='utf8'))
spec={'routes':upper['routes']+lower['routes'],'platforms':upper['platforms']+lower['platforms'],'shore_sections':lower.get('shore_sections',[]),'rock_shoulders':[[21.4,56.0,2.7,2.2,.85],[22.0,59.5,2.2,1.8,-.48],[21.1,61.8,2.6,2.0,.62]]}
for r in spec['routes']:
    if r['name'].startswith('upper_'):r['shoulder_width']=max(r.get('shoulder_width',0),1.7)
    elif not r['name'].endswith('_entry'):r['shoulder_width']=max(r.get('shoulder_width',0),1.0)
    if r['name']=='lower_work_pier_descent':
        r['points']=[[12.0,34.8,1.37],[10.7,34.8,1.37],[9.4,34.8,.80],[8.3,34.8,.30]]
        r['halfwidth']=.65;r['shoulder_width']=.75;r['beach_end']=True
    if r['name']=='lower_trade_pier_descent':
        r['points']=[[13.48,10.8,1.18],[11.8,10.8,1.16],[10.4,10.8,.68],[9.3,10.8,.32]]
        r['beach_end']=True
    if r['name']=='lower_tavern_front':
        r['points']=[[11,37,1.56],[10,38.5,1.65],[9.98,40.5,1.65],[10.0,42.4,1.63],[10.35,43.7,1.55],[11.2,44.8,1.36],[12.05,46,1.22]]
    if r['name']=='upper_frontage_chapel_clinic_travel':
        for p in r['points']:
            if 30<=p[1]<=33.6:p[0]-=.4
    if r['name']=='upper_public_side_route_to_school':
        for p in r['points']:
            if 55<=p[1]<=56.8:p[0]-=.35
for p in spec['platforms']:
    p['blend_width']=max(p.get('blend_width',0),1.5)
spec['routes'] += [
 {'name':'north_lower_upper_ramp','kind':'path','points':[[13.2,18.8,1.445],[15,18.8,1.48],[17,18.8,2.02],[19.5,19.2,3.05],[21.5,21.2,4.02],[23.45,23.15,4.18]],'halfwidth':.7,'shoulder_width':1.45},
 {'name':'south_lower_upper_ramp','kind':'path','points':[[12,34.8,1.37],[14,34.8,1.4],[16.5,35.1,2.1],[18.9,35.7,3.5],[20.2,36.3,3.94],[21.4,36.5,3.94]],'halfwidth':.7,'shoulder_width':1.6}]
entry=json.loads((LOG/'entry_spec.json').read_text(encoding='utf8'))
spec['entrances']=entry['entrances']
import numpy as np
lower_names={'Trade':'trade','Sea Breeze':'seabreeze','Tavern':'tavern','Diner':'diner','Sari':'sari'}
for e in spec['entrances']:
    ends=np.array(e['expected_threshold_endpoints_godot']);mid=ends.mean(0);v=np.array(e['outside_direction_xz']);c=mid[[0,2]]
    bottom=mid[1]-e['expected_rise_m']
    if e['name'] in lower_names:
        r=next(r for r in spec['routes'] if r['name']=='lower_'+lower_names[e['name']]+'_entry')
        start=r['points'][0];a=c+v*.42;b=c-v*.10
        r['points']=[start,[float(a[0]),float(a[1]),float(bottom)],[float(b[0]),float(b[1]),float(bottom)]]
        r['halfwidth']=.86
    else:
        side=(ends[1,[0,2]]-ends[0,[0,2]])/2
        side*=1.10
        poly=[c-side-v*.12,c+side-v*.12,c+side+v*.68,c-side+v*.68]
        spec['platforms'].append({'name':e['name'].replace(' ','_').lower()+'_threshold_landing','kind':'court','polygon':np.array(poly).tolist(),'height':float(bottom),'blend_width':.8})
for p in spec['platforms']:
    if p['name'] in entry['platform_overrides']:p['graded_route_overrides']=entry['platform_overrides'][p['name']]
# A forecourt and the lane across it are one graded ground, including the
# entire stair width. Do not overlay a tiny uphill wedge across a lower lane.
levels=np.array([[2.6,1.575],[10,1.575],[18,1.445],[28.5,1.445],[33.2,1.55],[37,1.875],[42.4,1.875],[46,1.405],[62,1.405]])
for r in spec['routes']:
    if r['name'] in ('lower_trade_main','lower_seabreeze_market_main','lower_tavern_front','lower_diner_sari_main'):
        for p in r['points']:p[2]=float(np.interp(p[1],levels[:,0],levels[:,1]))
    if r['name'].endswith('_entry'):
        h=r['points'][-1][2]
        for p in r['points']:p[2]=h
    if r['name']=='lower_trade_pier_descent':
        r['points']=[[13.48,10.8,1.562],[12.2,11.2,1.53],[10.9,12.2,.9],[10.3,13.8,.30]]
    if r['name']=='lower_work_pier_descent':
        r['points']=[[12,34.8,1.687],[10.7,34.8,1.687],[9.1,34.8,.93],[7.8,34.8,.30]]
    if r['name']=='south_lower_upper_ramp':
        r['points']=[[12,34.8,1.687],[14,34.8,1.72],[16.5,35.1,2.4],[18.9,35.7,3.5],[20.2,36.3,3.94],[21.4,36.5,3.94]]
court_heights={'lower_trade_court':1.575,'lower_seabreeze_court':1.445,'lower_tavern_court':1.875,'lower_diner_court':1.405,'lower_diner_north_seating':1.405,'lower_diner_sari_shared_saddle':1.405,'lower_sari_court':1.405}
for p in spec['platforms']:
    if p['name'] in court_heights:p['height']=court_heights[p['name']]
for r in spec['routes']:
    if r['name']=='north_lower_upper_ramp':
        r['points'][2][2]=2.10;r['points'][3][2]=3.00
    if r['name']=='lower_tavern_front':r['points'][4][2]=1.75
    if r['name']=='upper_frontage_chapel_clinic_travel':
        r['points'][0][2]=4.22;r['points'][1][2]=4.22;r['points'][2][2]=4.14
# A broad shared shore reaches the same bench as its lane. The previous
# proposal's lower bench values would create a second ridge below the road.
main=[r for r in spec['routes'] if r['name'] in ('lower_trade_main','lower_seabreeze_market_main','lower_tavern_front','lower_diner_sari_main')]
for s in spec['shore_sections']:
    candidates=[r for r in main if r['points'][0][1]<=s[0]<=r['points'][-1][1]]
    if not candidates:continue
    pts=np.array(candidates[0]['points']);s[3]=float(np.interp(s[0],pts[:,1],pts[:,2]))
    s[2]=float(np.interp(s[0],pts[:,1],pts[:,0])-.72)
    s[1]-=.55 if not 37<s[0]<44 else .15
spec['platforms'].append({'name':'lower_market_side_court','kind':'court','polygon':[[14.40,14.3],[16.32,14.3],[16.32,17.20],[14.40,17.20]],'height':1.45,'blend_width':.45})
spec['platforms'].append({'name':'restaurant_planter_corner','kind':'court','polygon':[[15.55,20.25],[16.35,20.25],[16.35,21.05],[15.55,21.05]],'height':1.445,'blend_width':.55,'limits':{'face_slope_deg':22,'target_height_error_m':.12},'note':'Planted corner, not circulation; actual rigid planter feet separately verified.'})
# Two broad curved descents use a single continuous spline and height grade.
def bezier_route(r,controls,h0,h1):
    c=np.array(controls,float);t=np.linspace(0,1,25)[:,None]
    q=(1-t)**3*c[0]+3*(1-t)**2*t*c[1]+3*(1-t)*t*t*c[2]+t**3*c[3]
    f=t[:,0];h=h0+(h1-h0)*(f*f*(3-2*f))
    r['points']=[[float(x),float(z),float(hh)] for (x,z),hh in zip(q,h)]
for r in spec['routes']:
    if r['name']=='lower_trade_pier_descent':r['halfwidth']=.68
# Separate beach access and uphill access into staggered T junctions. The
# walking bench remains wider than the worn surface of the secondary paths.
for r in spec['routes']:
    if r['name']=='lower_work_pier_descent':
        r['points']=[[11.96,32.7,1.539],[10.8,32.7,1.539],[9.15,32.7,.90],[7.8,32.7,.30]]
        r['halfwidth']=.58;r['paint_halfwidth']=.48
    if r['name']=='south_lower_upper_ramp':r['paint_halfwidth']=.55
for r in spec['routes']:
    if r['name']=='lower_trade_pier_descent':
        # One graded connection descends seaward before turning to the pier.
        # Its low end no longer doubles back under the high main street.
        r['points']=[[13.70,14.0,1.51],[12.20,14.0,1.50],[11.20,13.2,1.00],
                     [10.30,11.6,.45],[10.30,10.5,.30],[10.70,9.8,.30],
                     [10.72,9.0,.30]]
        r['halfwidth']=.55;r['bench_margin']=.14;r['shoulder_width']=.60
        r['paint_halfwidth']=.46
# Lower the whole shore beside the descent, including the seaward remnant
# ridge. Each section shares one low bench and one real upper street edge.
spec['trade_access_sections']=[
    [7.0,10.70,10.85,.30],[8.0,10.55,11.35,.30],
    [9.0,10.30,11.35,.30],[9.8,10.30,11.40,.30],
    [10.5,9.75,11.00,.30],[11.6,9.75,11.00,.45],
    [12.4,10.15,11.45,.725],[13.2,10.65,11.85,1.00],
    [14.0,11.25,12.70,1.50],[15.3,11.70,12.90,1.49]]
spec['platforms'].append({'name':'trade_pier_sand_landing','kind':'sand_access',
    'polygon':[[10.60,8.04],[11.35,8.04],[11.35,9.96],[10.60,9.96]],
    'height':.30,'blend_width':.55,'paint_strength':.12})
# Read the actual outer top edge of the unchanged lowest wooden tread.
tread=bpy.data.objects['Pier_ShoreTread.014']
vv=np.array([tread.matrix_world@v.co for v in tread.data.vertices])
ii=np.flatnonzero((abs(vv[:,0]-vv[:,0].max())<1e-5)&(abs(vv[:,2]-vv[:,2].max())<1e-5))
assert len(ii)==2
ee=vv[ii][:,[0,2,1]];ee[:,2]*=-1
spec['entrances'].append({'name':'TradePierBottom','object':tread.name,'threshold_vertex_indices':ii.tolist(),
    'outside_direction_xz':[1,0],'expected_rise_m':float(ee[:,1].mean()-.30),'approach_depth_m':.50,
    'limits':{'rise_error_m':.035,'approach_cross_slope_deg':12,'approach_longitudinal_slope_deg':28},
    'source_evidence':'Actual unchanged outer top edge of Pier_ShoreTread.014 read in GUI MCP',
    'expected_threshold_endpoints_godot':ee.tolist()})
spec['audit_limits']={'routes':{'cross_slope_deg':12,'longitudinal_slope_deg':28,'target_height_error_m':.15},'platforms':{'face_slope_deg':12,'target_height_error_m':.12},'cargo_minimum_clearance_m':.77}
spec['session']={'pid':28032,'port':9881,'source':bpy.data.filepath}
(LOG/'design.json').write_text(json.dumps(spec,indent=2,ensure_ascii=False),encoding='utf8')
exec((ROOT/'source/structure23_junction_spec.py').read_text(encoding='utf8'),globals())
spec['junctions']=build_structure23_junctions(LOG/'design.json')['junctions']
(LOG/'design.json').write_text(json.dumps(spec,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'routes':len(spec['routes']),'platforms':len(spec['platforms']),'shore_sections':len(spec['shore_sections'])}))

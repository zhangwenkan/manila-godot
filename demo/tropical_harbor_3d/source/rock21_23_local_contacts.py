# Read-only contact review after the two final local terrain edits.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'), globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
def region(p):
    return (15.2<p.x<20 and 40<-p.y<44.7) or (9.2<p.x<13.7 and 58.9<-p.y<62.15)
report={'dirty_before':bpy.data.is_dirty,'objects':[],'grass':[]}
for col in ('Reference_Rocks','Reference_Foliage'):
    for o in bpy.data.collections[col].objects:
        if o.type!='MESH' or o.name=='L24_GrassTuftClusters':continue
        if col=='Reference_Foliage' and not o.name.startswith(('S20_CourtyardShrub','Tree_Trunk','Palm_Trunk')):continue
        p=center(o)
        if not region(p):continue
        pts=[o.matrix_world@v.co for v in o.data.vertices]
        bottom=min(v.z for v in pts);low=[v for v in pts if v.z<bottom+.04]
        foot=sum(low,Vector())/len(low)
        report['objects'].append({'name':o.name,'center':[p.x,-p.y,p.z], 'foot':[foot.x,-foot.y,foot.z], 'gap':foot.z-ground(foot.x,-foot.y), 'base_sample_min_gap':min(v.z-ground(v.x,-v.y) for v in low)})
o=bpy.data.objects['L24_GrassTuftClusters']
for p in o.data.polygons:
    vs=[o.matrix_world@o.data.vertices[i].co for i in p.vertices]
    root=(vs[0]+vs[1])/2
    if region(root):report['grass'].append({'polygon':p.index,'root':[root.x,-root.y,root.z], 'gap':root.z-ground(root.x,-root.y)})
g=report['grass'];report['grass_count']=len(g)
report['grass_gap_range']=[min((x['gap'] for x in g),default=0),max((x['gap'] for x in g),default=0)]
report['dirty_after']=bpy.data.is_dirty
(LOG/'local_contacts.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='grass'}))

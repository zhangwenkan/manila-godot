# Execute once in the owned Blender MCP GUI. Heights only; keep planar topology.
exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert terrain.get('rock21_grounded') and not terrain.get('rock21_wide_forms'),'Wrong stage'
positions=np.empty((len(mesh.vertices),3),np.float32);mesh.vertices.foreach_get('co',positions.ravel())
loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
starts=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_start',starts)
sizes=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_total',sizes)
colors=np.empty((len(mesh.loops),4),np.float32);mesh.color_attributes['LandUse'].data.foreach_get('color',colors.ravel())
np.savez_compressed(str(LOG/'before_wide_forms.npz'),positions=positions,loops=loops,starts=starts,sizes=sizes,colors=colors)
src=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
exec(src[src.index('def inside('):src.index('def cliff_value(')],globals())
# All nine rotated floor footprints keep their existing bearing ground.
floors=[[(p[0],-p[1]) for p in f['corners'][:4]] for f in found]
def ss(a,b,t):
    t=max(0.,min(1.,(t-a)/(b-a)));return t*t*(3-2*t)
def window(z,a,b,c,d):return ss(a,b,z)*(1-ss(c,d,z))
def protected(x,z):
    return max([1 if inside(x,z,p) else 1-ss(.25,1.25,edge_distance(x,z,p)) for p in floors]+[0])
# Fewer deliberate changes in direction: broad noses and a recessed grass saddle.
newtoe=[(35.7,21),(38,18.8),(40.5,17.5),(42,16.9),(44,17.1),(46,18.9),(48,21.3),(50,23.8),(52,26.1),(54,24.7),(56,21.8),(58.5,20),(61,20.6),(63,21.5),(66,22.2)]
newcrown=[(35.7,24),(38,21),(40.5,19.5),(42,18.6),(44,18.7),(46,20.9),(48,23.1),(50,26.5),(52,29.3),(54,27.6),(56,23.6),(58.5,22.1),(61,22.6),(63,23.7),(66,24.5)]
crest=[(35.7,4.14),(39,3.9),(41.5,3.25),(44,3.35),(47,3.6),(49,3.8),(52,3.3),(55,3.7),(58.5,3.65),(61,4.05),(66,4.29)]
etkeys=[(35.7,10.7),(39,10.9),(41,10.7),(43.6,12.0),(46,12.6),(49,13.1),(52.5,14.2),(55,12.8),(58,12.3),(60.5,12.7),(63,13.4),(66,12)]
efkeys=[(35.7,8.4),(39,8.3),(41,8.0),(43.6,8.5),(46,9.4),(49,10.0),(52.5,9.4),(55,9.7),(58,9.2),(60.5,10.5),(63,11.3),(66,9.3)]
old_vertex_colors=np.zeros((len(mesh.vertices),4),np.float32);counts=np.zeros(len(mesh.vertices),np.float32)
np.add.at(old_vertex_colors,loops,colors);np.add.at(counts,loops,1);old_vertex_colors/=np.maximum(counts,1)[:,None]
newcols=old_vertex_colors.copy();changed=0;oldsection=0
for v in mesh.vertices:
    x,y,h=map(float,v.co);z=-y
    if counts[v.index]==0 or not -15<z<66.2 or x<float(shore(z))+.10 or x>38:continue
    fw=protected(x,z);prior=old_vertex_colors[v.index].astype(float)
    if z>35.7:
        w=window(z,35.7,38.0,63.0,66.0)*ss(.15,.8,x-float(shore(z)))*(1-ss(35.5,37.5,x))
        # The entire cargo water basin is preserved including its seaward hull end.
        w*=1-window(z,60.6,62.0,68,69)*(1-ss(16.5,18.0,x))
        ft=line(z,newtoe);ct=line(z,newcrown);et=line(z,etkeys);ef=line(z,efkeys)
        lh=low(z);ch=line(z,crest);hh=high(z)
        inlet=max(window(z,41.9,43.1,44.4,46.1),window(z,50.0,51.8,53.7,55.4),.9*window(z,58.2,59.5,60.8,62.5))
        lip=lh*(1-inlet)+.32*inlet
        if x<=ef:target=min(h,.24);col=np.zeros(4)
        elif x<et:
            t=(x-ef)/(et-ef)
            cut=window(z,37.5,39,40.7,42.3)+.65*window(z,55,56.0,57.7,59)
            cut=min(cut,1)*(1-inlet)
            q=ss(0,1,t)*(1-cut)+float(np.interp(t,[0,.28,.52,.79,1],[0,.06,.74,.97,1]))*cut
            target=.24+(lip-.24)*q
            # Earth is exposed on the short cuts; grass runs down the lower ramps.
            g=ss(.34+.25*cut,.50+.24*cut,t)*(1-inlet*.25)
            earth=ss(.12,.25,t)*(1-g)*(1-inlet*.65)
            if inlet>.5:g*=ss(.30,.52,target)
            col=np.array([g,0,0,earth])
        elif x<ft:
            target=lip+(lh-lip)*ss(et,min(ft-.1,et+4.1),x)
            col=np.array([1,0,0,0])
            if inlet>.3:
                sand=1-ss(.32,.64,target);col=np.array([1-sand,0,0,0])
        elif x<ct:
            t=(x-ft)/(ct-ft)
            # Heavy shoulder, wide planar cheek, no ripples or repeated narrow shelves.
            q=float(np.interp(t,[0,.16,.30,.73,.87,1],[0,.025,.11,.89,.97,1]))
            saddle=window(z,48.8,50.8,53.4,55.4)
            q=q*(1-saddle)+ss(0,1,t)*saddle
            target=lh+(ch-lh)*q
            rock=ss(.10,.22,t)*(1-ss(.87,.97,t))*(1-saddle*.94)
            col=np.array([1-rock,rock,0,0])
        else:
            target=ch+(hh-ch)*ss(ct,ct+3.4,x)
            # Only preserve the former path where it lies above the new crown.
            path=float(prior[2]);col=np.array([1-path,0,path,0])
        if x>ct+3.4:target=h
        # Preserve foundation shapes and smoothly join the rock to them.
        w*=1-fw
        v.co.z=h*(1-w)+target*w;newcols[v.index]=prior*(1-w)+col*w;changed+=abs(v.co.z-h)>.002
    else:
        # Interrupt the older continuous bands at two broad, building-free entrances.
        coast=float(shore(z));earthwin=max(window(z,9,11.5,14,17),window(z,28,30.7,33.6,36.5))
        ew=earthwin*ss(coast+.2,coast+.7,x)*(1-ss(coast+8.2,coast+10.0,x))*(1-fw)
        if h<2.05 and ew>0:
            target=.24+1.18*ss(coast+1,coast+8.2,x)
            v.co.z=h*(1-ew)+target*ew
            g=ss(.35,.62,target);newcols[v.index]=prior*(1-ew)+np.array([g,0,0,0])*ew
            oldsection+=1
        rockwin=max(window(z,16,18.5,20,22.5),window(z,30.5,32,34,36.7))
        rw=rockwin*ss(17.5,19.5,x)*(1-ss(28.0,31,x))*(1-fw)
        if h>1.65 and rw>0:
            target=1.4+2.8*ss(18.5,29.5,x)
            v.co.z=float(v.co.z)*(1-rw)+target*rw
            newcols[v.index]=newcols[v.index]*(1-rw)+np.array([1,0,0,0])*rw
            oldsection+=1
mesh.color_attributes['LandUse'].data.foreach_set('color',newcols[loops].astype(np.float32).ravel())
mesh.update()
for p in mesh.polygons:p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(62))
terrain['rock21_wide_forms']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
(LOG/'wide_forms.json').write_text(json.dumps({'main_height_vertices':changed,'older_coast_vertices':oldsection,'toe':newtoe,'crown':newcrown,'crest':crest},indent=2),encoding='utf8')
print(json.dumps({'main_height_vertices':changed,'older_coast_vertices':oldsection,'saved':True}))

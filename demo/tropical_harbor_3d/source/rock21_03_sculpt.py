exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
LOG=ROOT/'captures/rock_earth_rebuild_20261121'
assert not terrain.get('rock21_sculpted'),'Already applied'
source=(ROOT/'source/rock21_01_rebuild.py').read_text(encoding='utf8')
definition=source[source.index('def inside('):source.index('# Dense internal sampling')]
old_bvh=ground_bvh
def oldground(x,z):
    h,*_=old_bvh.ray_cast(Vector((float(x),-float(z),80)),Vector((0,0,-1)),300)
    return h.z if h else -15
exec(definition,globals())
def mass_strength(z):
    return float(smooth(38,39.3,z)*(1-smooth(62.5,63.6,z)))*(1-.88*float(smooth(49.8,51,z)*(1-smooth(53,55,z))))
moved=0
for v in mesh.vertices:
    x,y,h=v.co;z=-y;ct=line(z,crown);ft=line(z,toe);lh=low(z);hh=high(z)
    if not 37.8<z<63.7 or not ft<x<ct or not lh+.04<h<hh-.025:continue
    if any(inside(x,z,p) or edge_distance(x,z,p)<.65 for p in floors):continue
    q=(h-lh)/(hh-lh);t=(x-ft)/(ct-ft)
    target=ft+(ct-ft)*float(np.interp(q,[0,.08,.30,.43,.48,.70,.90,1],[0,.43,.49,.56,.69,.76,.87,1]))
    # Three broad rounded rock faces, with staggered heights and terminating joints.
    relief=0
    for cz,ch,rz,rh,depth in [(40.3,2.9,1.65,.70,.32),(43.7,3.15,1.20,.68,.40),(46.5,2.3,1.35,.63,.24),(57.2,3.0,1.45,.76,.38),(59.9,2.2,1.2,.60,.33),(61.8,3.55,1.0,.55,.23)]:
        r=((z-cz)/rz)**2+((h-ch)/rh)**2
        relief+=depth*max(0,1-r)**.7
    w=mass_strength(z)*float(smooth(0,.12,q))*(1-float(smooth(.90,1,q)))
    v.co.x=x*(1-w)+(target-relief)*w;moved+=1
mesh.update()
# A vertex receives one weight irrespective of triangle orientation, removing serrated role edges.
colors={}
for v in mesh.vertices:
    x,y,h=v.co;z=-y
    if not 37.9<z<63.5:continue
    ct=line(z,crown);ft=line(z,toe);lh=low(z);hh=high(z)
    grain=.022*math.sin(z*3.1+x*1.7)+.012*math.sin(x*5.2-z*2.4)
    if ft-.18<x<ct+.3 and lh+.025<h<hh+.02:
        q=(h-lh)/(hh-lh)
        rock=float(smooth(.025,.085,q))*(1-float(smooth(.963,.995,q+grain*.15)))
        # The middle shoulder belongs to the rock mass; no green belt across its face.
        colors[v.index]=(1-rock,rock,0,0)
    elif x<line(z,earthtop)+.35:
        ef=line(z,earthfoot);et=line(z,earthtop);t=max(0,min(1,(x-ef)/max(.2,et-ef)))
        mouth=float(smooth(51,52,z)*(1-smooth(54.2,55.3,z)))
        grass=float(smooth(.48,.68,t+grain))*(1-mouth*.96)
        soil=float(smooth(.2,.4,t))*(1-grass)*float(smooth(.28,.50,h))
        colors[v.index]=(grass,0,0,soil) if h>.26 else (0,0,0,0)
ca=mesh.color_attributes['LandUse']
for p in mesh.polygons:
    for li in p.loop_indices:
        i=mesh.loops[li].vertex_index
        if i in colors:ca.data[li].color=colors[i]
for p in mesh.polygons:p.use_smooth=True
mesh.set_sharp_from_angle(angle=math.radians(65));mesh.update()
# Repaint the existing tile into irregular, partly terminating sediment joints.
n=1024;yy,xx=np.mgrid[0:n,0:n].astype(np.float32)/n
def smooth_array(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
rng=np.random.default_rng(27303)
noise=np.zeros((n,n),np.float32)
for freq,amp in [(1,.11),(3,.06),(9,.035),(27,.015)]:
    for k in range(4):noise+=amp/4*np.sin(math.tau*(xx*rng.integers(1,freq+1)+yy*rng.integers(1,freq+1))+rng.uniform(0,math.tau))
seams=np.zeros((n,n),np.float32)
for j,base in enumerate([.08,.37,.72]):
    curve=base+.018*np.sin(math.tau*(xx*(j+1)+j*.3))+.009*np.sin(math.tau*(xx*7+.4*j))
    dist=np.abs(yy-curve);dist=np.minimum(dist,1-dist)
    line_mask=1-smooth_array(.0015,.0055,dist)
    interrupted=.4+.6*smooth_array(-.1,.35,np.sin(math.tau*(xx*(j+1)+j*.21)))
    seams=np.maximum(seams,line_mask*interrupted)
for j,(cx,lo,hi) in enumerate([(.12,.08,.37),(.64,.08,.37),(.40,.37,.72),(.86,.37,.72),(.23,.72,1.08),(.76,.72,1.08)]):
    cy=(yy-lo)%1;valid=1-smooth_array(hi-lo-.025,hi-lo+.02,cy)
    bend=cx+.025*np.sin(cy*16+j)+.012*np.sin(cy*43+j)
    dx=np.abs(xx-bend);dx=np.minimum(dx,1-dx)
    seams=np.maximum(seams,(1-smooth_array(.0012,.0048,dx))*valid*.85)
base=np.array([.36,.405,.425]);rgb=base[None,None,:]*(1+noise[:,:,None])
rgb*=1-.20*seams[:,:,None]
height=.64+noise*.8-seams*.28
for name,data,linear in [('R27_Rock_Albedo',rgb,False),('R27_Rock_Height',np.repeat(height[:,:,None],3,axis=2),True)]:
    im=bpy.data.images[name];rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=np.clip(data,0,1)
    im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(OUT/(name+'.png'));im.save();im.pack()
terrain['rock21_sculpted']=True
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
refresh_height();export_land();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print(json.dumps({'sculpted_vertices':moved,'continuous_weight_vertices':len(colors)}))

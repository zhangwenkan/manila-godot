# Refine this new landform's actual contour and road direction in Blender MCP.
before_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())
old_sections=sections
def sections(z):
    ss=[list(s) for s in old_sections(z)]
    ewave=.14*math.sin(z*.91)+.055*math.sin(z*2.41)
    roadwave=.31*math.sin(z*.27)+.12*math.sin(z*.83)
    for i,s in enumerate(ss):
        d=s[0]
        if 1.35<d<5.5:s[0]+=ewave
        if 5.5<=d<10.1:s[0]+=roadwave*smooth(5.4,6.0,d)*(1-smooth(9.6,10.3,d))
        if 15.15<=d<=20:s[0]+=(.30*math.sin(z*.22)+.10*math.sin(z*.93))*smooth(14.85,16.0,d)*(1-smooth(19.0,20.3,d))
        if s[2]>.7 and 2<d<6:s[1]+=.035*math.sin(z*1.7)+.02*math.sin(z*3.5)
    assert all(b[0]>a[0] for a,b in zip(ss,ss[1:])),z
    return ss

# Read only the function body and replace the upper-path design, not old terrain.
code=(ROOT/'source/redesign_20_01_land.py').read_text(encoding='utf8')
node=next(n for n in ast.parse(code).body if isinstance(n,ast.FunctionDef) and n.name=='new_sample')
source=ast.get_source_segment(code,node)
start=source.index('    if 10.0<d<15.4:');end=source.index('    # Yard grass',start)
source=source[:start]+'''    if 10.0<d<15.4:
        slope=2.1
        for entry in [34.8,53.0]:
            cross=(z-entry-slope*(d-10.2))/math.sqrt(1+slope*slope)
            lane=1-smooth(.82,1.22,abs(cross))
            along=((d-10.2)+slope*(z-entry))/(1+slope*slope)
            ramp=h1+(h2-h1)*smooth(0,5.2,along)
            fade=smooth(10.0,10.5,d)*(1-smooth(14.8,15.4,d))
            weight=lane*fade
            h=h*(1-weight)+ramp*weight
            g*=1-lane;bare*=1-lane;worn=max(worn,lane)
'''+source[end:]
exec(source,globals())
vertices=[];colors=[]
for z in zs:
    ss=sections(z);ds=[]
    for i,(a,b) in enumerate(zip(ss,ss[1:])):ds.extend(a[0]+(b[0]-a[0])*k/counts[i] for k in range(counts[i]))
    ds.append(ss[-1][0])
    for d in ds:
        h,g,soil,path=new_sample(d,z,ss);vertices.append((shore(z)+d,-z,h));colors.append((g,soil,path,1))
assert len(vertices)==len(terrain.data.vertices)
terrain.data.vertices.foreach_set('co',np.asarray(vertices,np.float32).ravel())
terrain.data.color_attributes['LandUse'].data.foreach_set('color',np.asarray(colors,np.float32).ravel())
vi=np.empty(len(terrain.data.loops),np.int32);terrain.data.loops.foreach_get('vertex_index',vi)
terrain.data.uv_layers.active.data.foreach_set('uv',(np.asarray(vertices,np.float32)[vi,:2]/2.4).ravel())
terrain.data.update();terrain.data.set_sharp_from_angle(angle=math.radians(34))
bpy.context.view_layer.update();ground_bvh=BVHTree.FromObject(terrain,bpy.context.evaluated_depsgraph_get())

# Ground whole previously registered groups on the reshaped surface.
for item in moves:
    x,z=item['x'],item['z'];hit,_,_,_=before_bvh.ray_cast(Vector((x,-z,60)),Vector((0,0,-1)),300)
    if hit is None:continue
    delta=ground(x,z)-hit.z
    if abs(delta)<.00001:continue
    for name in item['objects']:
        ob=bpy.data.objects.get(name)
        if ob:ob.location.z+=delta

# Re-root grass vertices, keeping each three-vertex blade's original height.
tufts=bpy.data.objects['S23_GrassTufts'];td=tufts.data
for i in range(0,len(td.vertices),3):
    vs=[td.vertices[i+k] for k in range(3)];cx=(vs[0].co.x+vs[1].co.x)/2;cy=(vs[0].co.y+vs[1].co.y)/2
    delta=ground(cx,-cy)-.018-vs[0].co.z
    for v in vs:v.co.z+=delta
td.update()

# Independent shallow blade relief for grass lighting, not coarse soil grain.
n=512;hh=np.zeros((n,n),np.float32);rng=np.random.default_rng(23003)
for k in range(7300):
    x,y=rng.integers(0,n,2);length=int(rng.integers(3,9));lean=rng.uniform(-.45,.45)
    for t in range(length):
        px=(x+int(t*lean))%n;py=(y+t)%n
        hh[py,px]=max(hh[py,px],.10*math.sin(math.pi*t/length))
dx=np.roll(hh,1,1)-np.roll(hh,-1,1);dy=np.roll(hh,1,0)-np.roll(hh,-1,0)
normal=np.stack([dx*2,dy*2,np.ones_like(dx)],2);normal/=np.linalg.norm(normal,axis=2)[:,:,None]
rgba=np.ones((n,n,4),np.float32);rgba[:,:,:3]=normal*.5+.5
im=bpy.data.images.new('S23_GrassNormal',width=n,height=n);im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(rgba.ravel());im.filepath_raw=str(OUT/(im.name+'.png'));im.file_format='PNG';im.save();im.pack()
tx=landmat.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im;nm=landmat.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.35;landmat.node_tree.links.new(tx.outputs['Color'],nm.inputs['Color']);landmat.node_tree.links.new(nm.outputs['Normal'],landmat.node_tree.nodes.get('Principled BSDF').inputs['Normal'])
samples=[round(ground(shore(z)+d,z),5) for z in np.arange(-30,90.001,.25) for d in np.arange(-20,50.001,.25)]
(OUT/'shore_relief_height.json').write_text(json.dumps({'d0':-20,'z0':-30,'step':.25,'columns':281,'rows':481,'heights':samples}),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landscape_redesign_mcp.blend'))
print('CONTOURS_UPDATED',len(vertices),'shared vertices; diagonal upper streets')

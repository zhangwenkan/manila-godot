# Executed in the verified Blender MCP namespace after land authoring.
C=bpy.data.collections['Reference_Terrain'];patches=[]
def turf_patch(label,z0,z1,front,back,overhang=False):
    nz=max(3,round((z1-z0)/.20));nx=14;vs=[];faces=[];ends=[]
    for j in range(nz+1):
        z=z0+(z1-z0)*j/nz
        edge=front(z);rear=back(z)
        scallop=.065*math.sin(z*8.7)+.035*math.sin(z*16.2)
        f=edge+scallop-.13 if overhang else edge+scallop
        end_taper=.15+.85*smooth(0,.65,min(z-z0,z1-z))
        b=f+max(.15,(rear+.11*math.sin(z*2.0)+.06*math.sin(z*6.1)-f)*end_taper)
        for i in range(nx+1):
            t=i/nx;d=f+(b-f)*t;x=shore(z)+d
            support=max(d,edge+.22) if overhang else d
            h=ground(shore(z)+support,z)+.10+.025*math.sin(z*3.4+d*5.1)+.018*math.sin(z*8.1-d*3.2)
            vs.append((x,-z,h))
        ends.append((z,f,b,edge))
    w=nx+1
    for j in range(nz):
        for i in range(nx):
            a=j*w+i;faces.append((a,a+w,a+w+1,a+1))
    # Watertight side ribbons physically expose a dark root thickness.
    perimeter=list(range(w))+[j*w+nx for j in range(1,nz+1)]+[nz*w+i for i in range(nx-1,-1,-1)]+[j*w for j in range(nz-1,0,-1)]
    topfaces=len(faces)
    for k,a in enumerate(perimeter):
        b=perimeter[(k+1)%len(perimeter)];pa=vs[a];pb=vs[b];n=len(vs)
        vs.extend([(pa[0]+.035,pa[1],pa[2]-.12),(pb[0]+.035,pb[1],pb[2]-.12)])
        faces.append((a,b,n+1,n))
    # The underside closes the real turf thickness under its projecting lip.
    bottom_start=len(vs)
    for x,y,h in vs[:(nx+1)*(nz+1)]:vs.append((x+.035,y,h-.12))
    for face in faces[:topfaces]:faces.append(tuple(bottom_start+i for i in reversed(face)))
    ob=mesh('R21_Turf_'+label,vs,faces,turfmat);ob.data.materials.append(rootmat)
    ids=np.ones(len(faces),np.int32);ids[:topfaces]=0
    shading=np.zeros(len(faces),np.bool_);shading[:topfaces]=True
    ob.data.polygons.foreach_set('material_index',ids);ob.data.polygons.foreach_set('use_smooth',shading)
    patches.append((ob,ends,nx,nz))
    return ob

# Broad, discontinuous planted shelves enclose the lower working coves.
for i,(a,b) in enumerate([(4,6.2),(11.2,34.8),(46,60.4),(69,71.5),(75,78.7)]):
    turf_patch('Waterfront%02d'%i,a,b,edge1,lambda z:5.45+.28*math.sin(z*.56),True)
# Extend two planted fingers into side yards instead of a uniform verge.
for i,(a,b) in enumerate([(33.0,36.0),(51.7,54.6),(19.0,21.6)]):
    turf_patch('YardFinger%02d'%i,a,b,lambda z:6.9+.18*math.sin(z*1.1),lambda z:edge2(z)-.45)
for i,(a,b) in enumerate([(38.8,42.0),(50.2,54.5),(64.5,67.0)]):
    turf_patch('UpperGarden%02d'%i,a,b,lambda z:15.0+.20*math.sin(z),lambda z:edge3(z)-.55)
# Two lower shelves interrupt the former single high wall behind the shops.
for i,(a,b) in enumerate([(3,10.0),(14,26.8),(31.2,41.9),(46.2,58.8),(63.2,78.3)]):
    turf_patch('MiddleShelf%02d'%i,a,b,lambda z:edge2(z),lambda z:edge2(z)+1.55,True)
    turf_patch('UpperStreetLip%02d'%i,a,b,lambda z:edge2(z)+2.02,lambda z:edge2(z)+2.77,True)
for i,(a,b) in enumerate([(3,26.5),(31,58.8),(63,79)]):
    turf_patch('ForestFoot%02d'%i,a,b,lambda z:edge3(z),lambda z:edge3(z)+2.0,True)
    turf_patch('ForestGround%02d'%i,a,b,lambda z:edge3(z)+2.6,lambda z:35.0,True)

# Small connected blade fans provide a broken silhouette at the lip and
# clustered surface relief; broad turf bodies remain readable underneath.
rr=random.Random(212020);verts=[];faces=[]
for ob,rows,nx,nz in patches:
    for j in range(nz):
        z,f,b,e=rows[j];zn=rows[j+1][0]
        count=max(3,int((b-f)*(zn-z)*18))
        for q in range(count):
            zz=rr.uniform(z,zn);t=rr.random();d=f+(b-f)*t
            x=shore(zz)+d
            jf=min(nz-1,j);ii=min(nx-1,int(t*nx));tx=t*nx-ii;tz=(zz-z)/(zn-z)
            aa=ob.data.vertices[jf*(nx+1)+ii].co.z;bb=ob.data.vertices[jf*(nx+1)+ii+1].co.z
            cc=ob.data.vertices[(jf+1)*(nx+1)+ii].co.z;dd=ob.data.vertices[(jf+1)*(nx+1)+ii+1].co.z
            h=(aa*(1-tx)+bb*tx)*(1-tz)+(cc*(1-tx)+dd*tx)*tz-.012
            # Limit broad forest fill; concentrate blades where the silhouette is seen.
            if b-f>5 and t>.20 and rr.random()<.85:continue
            for k in range(5):
                angle=rr.random()*math.tau;rad=rr.uniform(.012,.055);length=rr.uniform(.07,.17);width=rr.uniform(.015,.032)
                px=x+math.cos(angle)*rad;py=-zz+math.sin(angle)*rad;dx=math.cos(angle)*width;dy=math.sin(angle)*width;n=len(verts)
                verts.extend([(px-dx,py-dy,h),(px+dx,py+dy,h),(px+math.cos(angle)*.06,py+math.sin(angle)*.06,h+length)])
                faces.append((n,n+1,n+2))
blade=mesh('R21_TurfBladeFans',verts,faces,turfmat)
blade.data.uv_layers.active.data.foreach_set('uv',np.tile(np.array([0,0,1,0,.5,1],np.float32),len(faces)))

# Query the actual authored ground for runtime placement, with no engine meshes.
data={'d0':0,'z0':0,'step':.25,'columns':145,'rows':329,'heights':[]}
for j in range(329):
    z=j*.25
    for i in range(145):data['heights'].append(round(ground(shore(z)+i*.25,z),5))
(OUT/'shore_relief_height.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
bpy.context.view_layer.update()
(LOG/'turf_authored.json').write_text(json.dumps({'patches':len(patches),'blade_triangles':len(faces),'height_samples':len(data['heights'])},indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/reference_harbor_mcp.blend'))
print('RELIEF_TURF',len(patches),'solid patches',len(faces),'blade triangles')

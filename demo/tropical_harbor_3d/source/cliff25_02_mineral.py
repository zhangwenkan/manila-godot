"""C25 mineral iteration 3; execute only through owned GUI Blender MCP.
Hand-placed fracture planes follow the three sculpt groups. No global layer curves,
cell tessellation or repeating tile; established two-chart runtime contract kept.
"""
import bpy, os, json, numpy as np, struct, zlib, hashlib
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/cliff_contacts_20261125';OUT=ROOT/'assets/reference'
assert os.getpid()==9864 and bpy.types.blendermcp_server.port==9881 and not bpy.app.background
assert Path(bpy.data.filepath).name=='harbor_shore_control_mcp.blend'

def ss(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def smooth_noise(x,y,scale,seed):
    """Rotated interpolated hash noise, subordinate grain rather than structure."""
    qx=(.827*x+.562*y)/scale;qy=(-.562*x+.827*y)/scale
    ix,iy=np.floor(qx),np.floor(qy);tx,ty=qx-ix,qy-iy
    tx,ty=tx*tx*(3-2*tx),ty*ty*(3-2*ty)
    def hashed(a,b):
        n=np.sin(a*127.1+b*311.7+seed*74.27)*43758.5453123
        return n-np.floor(n)
    low=hashed(ix,iy)*(1-tx)+hashed(ix+1,iy)*tx
    high=hashed(ix,iy+1)*(1-tx)+hashed(ix+1,iy+1)*tx
    return low*(1-ty)+high*ty-.5

def polygon_sdf(x,y,points):
    """Positive-inside distance to an explicitly placed irregular plane."""
    inside=np.zeros(x.shape,bool);distance2=np.full(x.shape,np.inf,np.float32)
    for (ax,ay),(bx,by) in zip(points,points[1:]+points[:1]):
        dx,dy=bx-ax,by-ay
        t=np.clip(((x-ax)*dx+(y-ay)*dy)/max(dx*dx+dy*dy,1e-9),0,1)
        distance2=np.minimum(distance2,(x-ax-t*dx)**2+(y-ay-t*dy)**2)
        if abs(dy)>1e-8:
            inside^=((ay>y)!=(by>y)) & (x<(bx-ax)*(y-ay)/dy+ax)
    distance=np.sqrt(distance2)
    return np.where(inside,distance,-distance)

W,H=2048,1024
yy,xx=np.mgrid[:H,:W].astype(np.float32);U,V=(xx+.5)/W,(yy+.5)/H
rgb=np.zeros((H,W,3),np.float32)+[.405,.425,.396];height=np.full((H,W),.5,np.float32)
# Name, polygon (chart Z,H metres), mineral color, relief, two broad plane tilts.
# Overlapping unequal planes stop locally; no uniform dark seam traces every edge.
main_planes=[
('sea_lower_cool_return',[(21.7,1.05),(24.4,1.16),(25.15,2.03),(24.4,2.94),(22.55,3.32),(21.7,2.7)],[.346,.389,.387],.37,-.012,.025),
('sea_main_warm_face',[(22.1,2.04),(23.27,1.76),(25.98,2.70),(26.56,3.68),(25.23,4.42),(22.45,4.05)],[.474,.473,.423],.60,.020,.038),
('sea_broken_cap',[(22.14,3.76),(23.5,3.87),(24.74,4.46),(23.82,4.73),(22.06,4.39)],[.542,.533,.459],.69,-.034,.026),
('sea_short_return',[(25.17,1.18),(26.55,1.34),(27.28,2.29),(26.72,3.61),(25.94,3.29),(25.25,2.29)],[.347,.394,.384],.34,-.030,.018),
('sea_oblique_break',[(24.05,2.30),(25.13,2.50),(25.52,2.93),(24.98,3.20),(23.72,2.62)],[.419,.438,.394],.46,-.030,.052),
('clinic_lower_buttress',[(26.34,1.02),(28.25,1.16),(29.65,2.25),(29.24,2.92),(27.97,3.36),(26.74,2.65)],[.381,.415,.394],.48,.031,.015),
('clinic_primary_fracture',[(26.67,2.42),(27.55,2.59),(28.81,2.22),(30.51,3.23),(30.06,4.60),(28.45,4.68),(27.08,3.88)],[.503,.491,.431],.67,.005,.037),
('clinic_upper_cool_return',[(29.30,3.00),(30.39,2.90),(31.20,3.57),(31.29,4.63),(30.09,4.71)],[.364,.408,.401],.39,-.018,.044),
('clinic_lower_shadow_plane',[(28.47,1.05),(30.31,1.25),(31.29,2.19),(30.67,3.07),(29.82,2.85)],[.321,.370,.374],.27,.020,.010),
('clinic_tip_warm_face',[(30.50,1.55),(31.43,1.54),(33.73,3.05),(34.40,4.11),(33.64,4.65),(31.77,3.94),(30.87,2.93)],[.455,.465,.421],.57,.018,.030),
('clinic_tip_cut',[(32.47,1.32),(34.62,1.55),(34.70,3.56),(33.64,3.38),(32.89,2.48)],[.351,.393,.385],.35,-.034,.042),
('clinic_short_cap',[(31.61,3.59),(32.62,3.83),(33.23,4.43),(32.48,4.52),(31.65,4.03)],[.544,.529,.456],.72,-.028,.022),
]
rear_planes=[
('tavern_left_recess',[(36.95,1.28),(38.50,1.40),(39.20,2.58),(38.72,3.27),(37.35,3.82)],[.340,.386,.381],.34,.013,.023),
('tavern_wedge_front',[(37.40,2.05),(38.68,1.74),(40.62,2.69),(41.07,3.66),(39.64,4.62),(38.08,4.02)],[.485,.481,.427],.64,.016,.035),
('tavern_upper_chipped_cap',[(37.58,3.71),(39.05,4.13),(39.67,4.66),(38.40,4.78),(37.48,4.35)],[.539,.526,.456],.71,-.032,.014),
('tavern_center_undercut',[(39.08,1.22),(41.13,1.42),(41.71,2.43),(40.86,3.03),(40.09,2.77)],[.333,.382,.380],.29,.019,.018),
('tavern_diagonal_return',[(40.39,2.74),(41.21,2.43),(42.71,3.34),(43.43,4.70),(41.80,4.57)],[.387,.427,.403],.42,-.008,.052),
('tavern_right_outcrop',[(41.82,1.54),(43.00,1.52),(44.98,2.81),(45.41,3.89),(44.18,4.58),(42.67,3.45)],[.479,.470,.411],.62,.018,.023),
('tavern_right_cool_end',[(44.02,1.32),(45.55,1.38),(45.61,3.99),(44.96,3.71),(44.29,2.53)],[.354,.395,.380],.37,-.020,.023),
('tavern_small_slant_cap',[(42.53,3.02),(43.25,3.16),(44.11,3.96),(43.50,4.13),(42.76,3.59)],[.539,.518,.444],.74,-.027,.034),
]
# Short ledges terminate at different heights. No chart-spanning paired courses.
main_ledges=[
([(22.51,2.03),(23.32,2.09),(24.06,2.48),(24.73,2.59)],.075,.085,.58),
([(25.12,3.27),(25.63,3.52),(26.21,3.65)],.055,.060,.45),
([(27.02,2.58),(27.51,2.63),(28.14,2.46),(28.71,2.39)],.095,.100,.82),
([(29.91,3.45),(30.37,3.63),(30.65,4.10)],.050,.055,.42),
([(31.22,2.29),(31.76,2.48),(32.38,2.98)],.075,.075,.67),
([(32.96,3.73),(33.49,3.91),(33.93,4.02)],.043,.050,.38),
]
rear_ledges=[
([(37.87,2.39),(38.47,2.52),(39.08,2.94)],.075,.085,.72),
([(39.41,3.85),(39.91,4.03),(40.38,4.20)],.045,.055,.42),
([(40.84,2.80),(41.33,2.99),(41.85,3.39)],.088,.095,.73),
([(42.51,2.07),(43.04,2.21),(43.72,2.61)],.068,.073,.59),
([(43.63,3.94),(44.17,4.16),(44.47,4.20)],.044,.051,.40),
]
# Hand-distributed exposed fracture runs, in chart metres. Each run has a
# distinct direction and a few unequal flakes which die away or step sideways.
# This is the middle structural scale between the twenty large planes and grain.
# Z,H,length,thickness,vertical rise per metre,seed.
main_weathering=[
(22.45,2.70,.90,.32,.18,11),(23.25,3.49,1.22,.28,.26,12),
(24.07,2.87,.95,.40,-.13,13),(24.83,3.80,.76,.29,.34,14),
(23.08,1.76,.88,.25,.15,15),(25.18,2.00,.72,.35,.47,16),
(25.75,3.04,1.02,.31,.54,17),(26.15,3.86,.63,.25,-.20,18),
(27.12,2.03,.91,.34,.26,21),(27.84,3.34,1.15,.41,.12,22),
(28.65,3.85,1.29,.32,.27,23),(28.49,2.91,.87,.28,-.18,24),
(29.32,1.82,1.16,.31,.38,25),(29.91,3.06,.92,.40,.29,26),
(30.36,4.12,.69,.29,-.10,27),(31.22,2.28,.84,.35,.51,28),
(31.55,3.30,1.10,.34,.17,29),(32.16,3.83,.97,.28,.34,30),
(32.76,2.56,1.12,.36,.27,31),(33.24,3.51,.88,.30,-.19,32),
(33.93,4.01,.65,.27,.20,33),
]
rear_weathering=[
(37.71,2.17,.86,.29,.31,41),(38.10,3.44,1.12,.31,.18,42),
(38.83,2.94,.98,.38,.39,43),(39.32,3.90,.87,.27,-.16,44),
(39.51,2.13,.98,.33,.23,45),(40.08,3.21,1.05,.40,.47,46),
(40.79,4.01,.85,.31,.17,47),(41.12,2.33,.99,.31,-.11,48),
(41.73,3.45,1.10,.38,.33,49),(42.38,2.66,.92,.27,.21,50),
(42.96,3.74,1.13,.32,.45,51),(43.52,2.13,.78,.31,-.19,52),
(44.10,3.06,1.11,.37,.19,53),(44.65,3.98,.79,.30,.36,54),
]

def weathered_run(z,h,colors,face_h,spec):
    cz,ch,length,thick,slope,seed=spec
    # Work in each run's oblique local frame. Unevenly spaced layers cannot
    # become a material-wide horizontal stripe or regular masonry grid.
    qx=z-cz;qy=h-ch-slope*qx
    inside=(np.abs(qx)<length*.9)&(np.abs(qy)<thick*1.65)
    if not inside.any():return
    rows,cols=np.where(inside)
    r0,r1,c0,c1=rows.min(),rows.max()+1,cols.min(),cols.max()+1
    x,y=qx[r0:r1,c0:c1],qy[r0:r1,c0:c1]
    rng=np.random.default_rng(seed)
    local_colors=colors[r0:r1,c0:c1]
    local_height=face_h[r0:r1,c0:c1]
    for j in range(3+(seed%2)):
        # Flakes range from a dominant slant to smaller chipped ends. Some
        # run tips overlap, others leave intact rock; they never fill a cell grid.
        extent=length*rng.uniform(.43,.82)*(1-.13*j)
        depth=thick*rng.uniform(.25,.49)
        offset_x=length*rng.uniform(-.24,.24)
        offset_y=thick*(-.68+j*.47)+rng.uniform(-.045,.045)
        points=[(-extent*.53,-depth*.31),(-extent*.24,-depth*.55),
                (extent*.15,-depth*.39),(extent*.53,depth*.03),
                (extent*.29,depth*.40),(extent*.03,depth*.53),
                (-extent*.33,depth*.21)]
        px,py=x-offset_x,y-offset_y
        edge_noise=smooth_noise(px,py,.052,seed+j)*.020
        d=polygon_sdf(px,py,points)+edge_noise
        m=ss(-.018,.025,d)
        across=np.clip(py/max(depth,.001),-.65,.65)
        # Asymmetric weathered face + shadow at its cut edge, not an outlined patch.
        contrast=rng.uniform(.022,.045)*(1-.12*j)
        local_colors+=(m*(-contrast*.50+contrast*across))[...,None]
        local_height+=m*(.038+.065*across)*(1-.10*j)
        edge_y=-depth*.34+.15*px
        edge_extent=ss(-extent*.52,-extent*.30,px)*(1-ss(extent*.23,extent*.48,px))
        cut=np.exp(-((py-edge_y)/(.020+depth*.12))**2)*edge_extent
        worn=np.exp(-((py-edge_y-.047)/(.028+depth*.10))**2)*edge_extent
        local_colors+=(-.043*cut+.026*worn)[...,None]*(1-.12*j)
        local_height+=(-.112*cut+.065*worn)*(1-.12*j)
    # A sparse shorter transverse chip interrupts the small layers, so the run
    # is a broken rock patch rather than four uniform stacked raised ribbons.
    chip_z=length*(.10 if seed%2 else -.17)
    chip_line=chip_z-.19*y
    gate=ss(-thick*.82,-thick*.48,y)*(1-ss(thick*.30,thick*.70,y))
    scar=np.exp(-((x-chip_line)/.027)**2)*gate
    local_colors-=scar[...,None]*.026
    local_height-=scar*.077

params=[(.02,.66,22.,12.8,.9,4.,False),(.70,.98,37.3,8.,1.25,3.4,True)]
for u0,u1,z0,zspan,h0,hspan,rear in params:
    columns=np.flatnonzero((U[0]>=u0-.015)&(U[0]<=u1+.015))
    z=z0+(U[:,columns]-u0)/(u1-u0)*zspan;h=h0+(V[:,columns]-.02)/.96*hspan
    coarse=smooth_noise(z,h*.8,1.23,14 if rear else 8)
    mineral=smooth_noise(z,h,.31,55);fine=smooth_noise(z,h,.037,81);chips=smooth_noise(z,h,.11,93)
    colors=np.zeros(z.shape+(3,),np.float32)+[.420,.438,.416]
    colors+=(coarse*.027+mineral*.018+fine*.007)[...,None]
    face_h=.49+coarse*.075+mineral*.019+fine*.005
    for name,points,tint,level,tilt_z,tilt_h in (rear_planes if rear else main_planes):
        sdf=polygon_sdf(z,h,points)+chips*.042+fine*.012
        m=ss(-.035,.035,sdf)
        cz=sum(p[0] for p in points)/len(points);ch=sum(p[1] for p in points)/len(points)
        plane_tilt=tilt_z*(z-cz)+tilt_h*(h-ch)
        broad=np.clip((z-cz)*.006+(h-ch)*.010,-.025,.025)
        tint=np.array(tint,np.float32)
        tone=float(tint.mean())
        # Keep the structural twenty planes but compress both their luminance
        # and warm/cool separation: no isolated beige painted triangles.
        rock_tint=np.array([.420,.438,.416],np.float32)+.35*(tone-.427)+.16*(tint-tone)
        plane_color=rock_tint+(broad+coarse*.027+mineral*.018+fine*.008)[...,None]
        colors=colors*(1-m[...,None])+plane_color*m[...,None]
        local_h=.5+.56*(level-.5)+plane_tilt*.65+coarse*.033+mineral*.024+fine*.005
        face_h=face_h*(1-m)+local_h*m
    for spec in (rear_weathering if rear else main_weathering):
        weathered_run(z,h,colors,face_h,spec)
    for points,recess_width,lip_width,strength in (rear_ledges if rear else main_ledges):
        line=np.interp(z,[p[0] for p in points],[p[1] for p in points])
        span=points[-1][0]-points[0][0]
        gate=ss(points[0][0],points[0][0]+span*.18,z)*(1-ss(points[-1][0]-span*.22,points[-1][0],z))
        d=h-line-chips*.038-fine*.012
        recess=np.exp(-((d+.028)/recess_width)**2)*gate*strength
        lip=np.exp(-((d-.095)/lip_width)**2)*gate*strength
        colors+=(-.061*recess+.031*lip)[...,None]
        face_h+=-.13*recess+.085*lip
    # Sparse elongated inclusions follow fracture directions, never circular spots.
    rng=np.random.default_rng(20261125+(1 if rear else 0))
    for i in range(22 if rear else 32):
        cz=rng.uniform(z0-.1,z0+zspan+.1);ch=rng.uniform(h0+.2,h0+hspan-.2)
        extent=rng.uniform(.16,.58);q=(h-ch)-rng.uniform(.28,.64)*(z-cz)
        patch=np.exp(-((z-cz)/extent)**2-(q/rng.uniform(.045,.13))**2)
        sign=-1 if i%3==0 else 1
        colors+=patch[...,None]*np.array([.011,.008,.003],np.float32)*sign
        face_h+=patch*.012*sign
    rgb[:,columns,:]=np.clip(colors,.245,.615)
    height[:,columns]=np.clip(face_h,.055,.94)

def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
def save_rgb(path,pixels):
    data=np.uint8(np.clip(pixels[::-1],0,1)*255+.5)
    raw=b''.join(b'\0'+row.tobytes() for row in data)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))
color_path=OUT/'C25_CliffRegion_Color.png';save_rgb(color_path,rgb)
name='C25_CliffRegion_Color';im=bpy.data.images.get(name)
if im:bpy.data.images.remove(im)
im=bpy.data.images.load(str(color_path));im.name=name;im.colorspace_settings.name='sRGB';im.pack()
name='C25_CliffRegion_Height';old=bpy.data.images.get(name)
if old:bpy.data.images.remove(old)
hi=bpy.data.images.new(name,width=W,height=H,alpha=False,float_buffer=True)
hi.colorspace_settings.name='Non-Color'
rgba=np.ones((H,W,4),np.float32);rgba[...,:3]=height[...,None]
hi.pixels.foreach_set(rgba.ravel());hi.filepath_raw=str(OUT/'C25_CliffRegion_Height.exr');hi.file_format='OPEN_EXR';hi.save();hi.pack()
im.use_fake_user=True;hi.use_fake_user=True
np.savez_compressed(LOG/'mineral_fields.npz',height=height,color=rgb)
report={'iteration':3,'charts':2,'size':[W,H],'non_repeating':True,'actual_geometry_separate':True,
'hand_planes':len(main_planes)+len(rear_planes),'short_ledges':len(main_ledges)+len(rear_ledges),
'weathering_runs':len(main_weathering)+len(rear_weathering),'weathering_scale_m':[.65,1.29],
'large_plane_color_compressed':True,'structural_midsize_flakes':True,
'no_chart_spanning_layers':True,'height_range_m':.16,'color_sha256':hashlib.sha256(color_path.read_bytes()).hexdigest(),
'height_minmax':[float(height.min()),float(height.max())],
'color_minmax':[rgb.min(axis=(0,1)).tolist(),rgb.max(axis=(0,1)).tolist()],
'image_contract_unchanged':True,'preview_rebind_required':True,'source_save_required':True,'visual_accepted':False}
(LOG/'mineral.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))

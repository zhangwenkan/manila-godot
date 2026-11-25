# Refine this turn's textures and extend the sample to Rosie's adjoining face.
# Reusable surface generator only; does not replay any old terrain mutation.
import bpy,json,math,numpy as np
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent;LOG=ROOT/'captures/rock_path_sample_20261123';OUT=ROOT/'assets/reference'
terrain=bpy.data.objects['C25_ContourBuiltCoast'];mesh=terrain.data
routes=json.loads((LOG/'routes.json').read_text())
# Soften route direction changes by rounding corners within the existing graded corridor.
for r in routes:
 if r.get('rounded'):continue
 points=np.array(r['points'],float)
 if len(points)>2:
  rounded=[points[0].tolist()]
  for i in range(1,len(points)-1):
   p=points[i];a=p+(points[i-1]-p)*.17;b=p+(points[i+1]-p)*.17
   for t in [0,.25,.5,.75,1]:rounded.append(((1-t)**2*a+2*(1-t)*t*p+t*t*b).tolist())
  rounded.append(points[-1].tolist());r['points']=rounded
 r['rounded']=True
(LOG/'routes.json').write_text(json.dumps(routes,indent=2),encoding='utf8')
coords=np.array([v.co[:] for v in mesh.vertices],np.float32);loops=np.array([l.vertex_index for l in mesh.loops])
mesh.uv_layers[0].data.foreach_set('uv',np.column_stack(((coords[loops,0]-8)/26,(-coords[loops,1]-10)/45)).astype(np.float32).ravel())
mesh.uv_layers['RockRegion'].data.foreach_set('uv',np.column_stack(((-coords[loops,1]-10)/45,(coords[loops,2]-.7)/4.4)).astype(np.float32).ravel())
src=(ROOT/'source/sample23_05_surfaces.py').read_text(encoding='utf8')
src=src.replace('37*(uu+.5)/w','45*(uu+.5)/w').replace('37*(v+.5)/n','45*(v+.5)/n').replace("-10)/37*n","-10)/45*n").replace("'z and elevation, 37m by4.4m'","'z and elevation, 45m by4.4m'").replace("'x8..34,z10..47'","'x8..34,z10..55'")
src=src.replace('[.445,.469,.466]','[.365,.396,.393]')
src=src.replace('duration=.52+.48*ss(-.45,.35,np.sin(z*.31+j*1.7))','duration=ss(-.12,.55,np.sin(z*.48+j*1.7))')
src=src.replace('+lip*.026-seam*.036*duration','+lip*.026*duration-seam*.036*duration')
src=src.replace('-under*.09+lip*.12','-under*.09*duration+lip*.12*duration')
src=src.replace('nz[y0:y1+1,x0:x1+1][valid]=tri.normal.z','nz[y0:y1+1,x0:x1+1][valid]=(a*mesh.vertices[tri.vertices[0]].normal.z+b*mesh.vertices[tri.vertices[1]].normal.z+c*mesh.vertices[tri.vertices[2]].normal.z)[valid]')
src=src.replace('# Remove diffuse former yellow pads;', '''# Smooth only the regional role field at about 7 cm, not the geometry.
fy=np.fft.fftfreq(n)[:,None];fx=np.fft.rfftfreq(n)[None,:]
kernel=np.exp(-2*np.pi*np.pi*3.2**2*(fx*fx+fy*fy))
for channel in range(4):land[:,:,channel]=np.fft.irfft2(np.fft.rfft2(land[:,:,channel])*kernel,s=(n,n)).real
# Remove diffuse former yellow pads;''')
src=src.replace('pathweight*=ss(.55,.82,nz)*ss(.30,.65,heightfield)','pathweight*=ss(.30,.65,heightfield)')
src=src.replace("rgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=rgb", "exec(facet_code,globals())\nrgba=np.ones((h,w,4),np.float32);rgba[:,:,:3]=rgb",1)
facet_code=r'''
# Broad uneven faces between bedding levels. Not one repeated tile or random noise.
def patch(poly):
 inside=np.zeros(z.shape,bool);distance=np.full(z.shape,100,np.float32)
 for (a,b),(c,d) in zip(poly,poly[1:]+poly[:1]):
  if abs(d-b)>1e-8:inside^=((b>e)!=(d>e)) & (z<(c-a)*(e-b)/(d-b)+a)
  dx,dy=c-a,d-b;q=np.clip(((z-a)*dx+(e-b)*dy)/(dx*dx+dy*dy),0,1)
  distance=np.minimum(distance,np.hypot(z-a-q*dx,e-b-q*dy))
 return ss(0,.045,distance)*inside
panels=[
 ([(11,1.11),(13.8,1.06),(14.4,1.64),(12.6,1.77),(11.2,1.58)],.025),
 ([(14.0,1.75),(17.7,1.65),(18.1,2.37),(15.7,2.46),(14.6,2.26)],-.018),
 ([(18.5,2.37),(20.8,2.51),(21.1,3.12),(19.2,3.26),(18.4,2.91)],.028),
 ([(22.0,1.02),(24.3,1.12),(24.8,1.76),(23.2,1.81),(22.3,1.55)],-.026),
 ([(23.1,1.83),(25.8,1.71),(26.2,2.49),(24.8,2.55),(23.4,2.37)],.038),
 ([(26.2,1.21),(28.1,1.15),(28.7,1.78),(27.1,1.87),(26.4,1.64)],.021),
 ([(26.0,2.57),(28.8,2.49),(29.2,3.25),(27.7,3.18),(26.4,3.01)],-.029),
 ([(23.4,3.31),(25.2,3.23),(26.8,3.34),(26.5,4.02),(24.1,3.98)],.025),
 ([(29.2,1.82),(31.8,1.73),(32.3,2.42),(30.8,2.50),(29.5,2.31)],.026),
 ([(35.9,1.09),(38.6,1.06),(38.9,1.72),(37.3,1.80),(36.2,1.59)],.027),
 ([(38.9,1.82),(41.4,1.77),(41.8,2.45),(40.5,2.58),(39.2,2.34)],-.028),
 ([(36.5,2.41),(39.0,2.52),(39.4,3.17),(37.7,3.25),(36.8,3.05)],.036),
 ([(41.8,1.11),(43.9,1.17),(44.5,1.80),(43.2,1.89),(42.2,1.63)],.031),
 ([(42.0,2.60),(44.5,2.51),(45.4,3.18),(43.7,3.30),(42.3,3.06)],.036),
 ([(45.0,1.89),(47.5,1.74),(48.2,2.41),(46.7,2.56),(45.5,2.38)],-.026),
 ([(48.2,2.49),(50.4,2.53),(51.0,3.21),(49.5,3.28),(48.5,3.04)],.028),
 ([(51.2,1.12),(53.6,1.2),(54,1.8),(52.7,1.85),(51.4,1.59)],.025)]
for poly,tint in panels:
 m=patch(poly);rgb+=m[:,:,None]*np.array([tint,tint*.93,tint*.83])
 # Gentle plane tilt within a wide facet, not a puffed stone outline.
 center=sum(p[0] for p in poly)/len(poly)
 tilt=np.clip((z-center)/2,-1,1)
 height+=m*(.035*tilt+.025*np.sign(tint))
# Break the uniform rails: interrupted sloped ledges and tapering recesses.
for k,(a,b,c,d) in enumerate([(22.2,1.53,24.8,1.80),(25.7,2.18,28.6,2.56),(36.6,2.85,39.3,3.17),(41.9,1.45,44.4,1.79),(44.0,2.82,46.5,3.18),(48.4,2.12,50.5,2.48)]):
 q=np.clip((z-a)/(c-a),0,1);line=b+(d-b)*q
 fade=ss(a,a+.3,z)*(1-ss(c-.3,c,z));dist=e-line
 recess=np.exp(-((dist+.025)/.04)**2)*fade
 highlight=np.exp(-((dist-.055)/.08)**2)*fade
 rgb+=(-.025*recess+.013*highlight)[:,:,None]
 height+=-.07*recess+.04*highlight
'''
exec(compile(src,'sample23_regional_generator','exec'),globals())
terrain['sample23_surface_revision']=2
print('Refined nonrepeating broad rock faces; darker neutral base; rounded road boundaries; sample now z10..55')

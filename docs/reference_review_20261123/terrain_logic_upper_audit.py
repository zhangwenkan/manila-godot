"""Read-only terrain / occupancy / camera audit. No Blender or runtime writes."""
from pathlib import Path
import json,math,numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[2]
DEMO=ROOT/'demo/tropical_harbor_3d'
OUT=Path(__file__).with_suffix('');OUT.mkdir(exist_ok=True)
CAP=DEMO/'captures/art_20261123_220019_536387'
raw=np.load(DEMO/'captures/road_contacts_20261123/grade_before_after.npz')
p=raw['positions'].astype(float);tri=raw['triangles']
v=np.column_stack((p[:,0],p[:,2],-p[:,1]))
a=v[tri[:,0]];e1=v[tri[:,1]]-a;e2=v[tri[:,2]]-a
nn=np.cross(e1,e2);nn/=np.linalg.norm(nn,axis=1)[:,None]
land=np.load(DEMO/'captures/road_contacts_20261123/land_data.npz')
roles=land['land'];height=land['height'];normal=land['normal']
views={
 'town_market_chapel':([-4,12,26],[20,4,15]),
 'town_civic_street':([-2,13,43],[19,4,29]),
 'town_north_shops':([-4,13,66],[19,4,52]),
 'town_landward':([39,16,67],[18,3,53]),
 'terrace_cross_street':([7,7,48],[24,4,44]),
 'shore_grass_bank':([-2,6,60],[15,1.5,54]),
 '07_landward_connections':([33,12,48],[18,3,43]),
 'shared_supply_yard':([7,9,57],[18,2.3,53]),
}
def axes(name):
 eye,target=map(lambda x:np.array(x,dtype=float),views[name]);forward=target-eye;forward/=np.linalg.norm(forward)
 right=np.cross(forward,[0,1,0]);right/=np.linalg.norm(right);up=np.cross(right,forward)
 return eye,forward,right,up
def mapdata(x,z):
 ix=int(np.clip((x+4)/48*2048,0,2047));iy=int(np.clip((z+15)/97*2048,0,2047))
 return {'roles_grass_rock_path_soil':roles[iy,ix].tolist(),'residual_sand':max(0,float(1-roles[iy,ix].sum())),
         'map_normal_up':float(normal[iy,ix]),'map_height':float(height[iy,ix])}
def raycast(name,px,py):
 eye,f,r,up=axes(name);d=f+r*((px+.5-800)/450*math.tan(math.radians(48)/2))+up*((450-py-.5)/450*math.tan(math.radians(48)/2));d/=np.linalg.norm(d)
 h=np.cross(np.broadcast_to(d,e2.shape),e2);det=np.einsum('ij,ij->i',e1,h);ok=abs(det)>1e-10
 inv=np.zeros(len(det));inv[ok]=1/det[ok];s=eye-a;u=inv*np.einsum('ij,ij->i',s,h);q=np.cross(s,e1)
 w=inv*(q@d);t=inv*np.einsum('ij,ij->i',e2,q);ok&=(u>=0)&(w>=0)&(u+w<=1)&(t>0)
 if not ok.any():return None
 i=np.flatnonzero(ok)[np.argmin(t[ok])];hit=eye+d*t[i]
 return dict(view=name,pixel=[px,py],godot_xyz=hit.tolist(),triangle=int(i),face_slope_degrees=float(np.degrees(np.arccos(np.clip(abs(nn[i,1]),0,1)))),**mapdata(hit[0],hit[2]))
def ground(x,z):
 # Exact XY triangle, ray from overhead.
 aa=a[:,[0,2]];b=e1[:,[0,2]];c=e2[:,[0,2]];d=np.array([x,z])-aa
 den=b[:,0]*c[:,1]-b[:,1]*c[:,0];valid=abs(den)>1e-10
 u=np.divide(d[:,0]*c[:,1]-d[:,1]*c[:,0],den,out=np.zeros(len(den)),where=valid)
 w=np.divide(b[:,0]*d[:,1]-b[:,1]*d[:,0],den,out=np.zeros(len(den)),where=valid)
 valid&=(u>=-1e-8)&(w>=-1e-8)&(u+w<=1+1e-8)
 if not valid.any():return None
 ids=np.flatnonzero(valid);hh=a[ids,1]+u[ids]*e1[ids,1]+w[ids]*e2[ids,1];i=ids[np.argmax(hh)]
 return dict(godot_xyz=[x,float(hh.max()),z],triangle=int(i),face_slope_degrees=float(np.degrees(np.arccos(np.clip(abs(nn[i,1]),0,1)))),**mapdata(x,z))
def project(name,xyz):
 eye,f,r,up=axes(name);d=np.array(xyz)-eye;depth=d@f
 return [float(800+(d@r)/depth*450/math.tan(math.radians(48)/2)),float(450-(d@up)/depth*450/math.tan(math.radians(48)/2))]
def crop(view,box,label):
 im=Image.open(CAP/(view+'.png')).crop(box);out=Image.new('RGB',(im.width,im.height+28),(24,28,30));out.paste(im,(0,28));ImageDraw.Draw(out).text((8,7),label,fill='white');out.save(OUT/(label+'.png'))
def topmap():
 bounds=(17,8,31,65);x0,z0,x1,z1=bounds;scale=18;W=int((x1-x0)*scale);H=int((z1-z0)*scale)
 yy,xx=np.mgrid[0:H,0:W];x=x0+(xx+.5)/scale;z=z0+(yy+.5)/scale
 ix=((x+4)/48*2048).astype(int);iy=((z+15)/97*2048).astype(int)
 role=roles[iy,ix];sand=np.maximum(0,1-role.sum(-1));palette=np.array([[80,140,48],[130,137,137],[181,155,112],[126,84,46]])
 rgb=role@palette+sand[...,None]*np.array([239,216,161]);h=height[iy,ix];shade=np.clip(.84+h*.04,.75,1.04)
 rgb*=shade[...,None];contour=np.abs(h/.25-np.round(h/.25))<.055;rgb[contour]*=.70
 im=Image.fromarray(np.uint8(np.clip(rgb,0,255)));canvas=Image.new('RGB',(W+100,H+60),(245,245,245));canvas.paste(im,(50,35));d=ImageDraw.Draw(canvas)
 for zz in range(10,66,5):
  y=35+(zz-z0)*scale;d.line([(50,y),(W+50,y)],fill=(40,40,40),width=1);d.text((4,y),f'z{zz}',fill='black')
 for xx in range(18,32,2):
  x=50+(xx-x0)*scale;d.text((x-8,10),f'x{xx}',fill='black')
 fps=json.loads((DEMO/'captures/road_contacts_20261123/active_footprints.json').read_text(encoding='utf8'))
 for ob in fps:
  if not ob['name'].startswith('Town_Floor'):continue
  lo,hi=ob['bounds_blender']
  if lo[0]<20:continue
  box=[50+(lo[0]-x0)*scale,35+(-hi[1]-z0)*scale,50+(hi[0]-x0)*scale,35+(-lo[1]-z0)*scale]
  d.rectangle(box,outline=(250,250,250),width=2);d.text((box[0]+2,box[1]+2),ob['name'].split('.')[-1],fill='white')
 canvas.save(OUT/'upper_roles_elevation.png')
def main():
 topmap()
 files=sorted(CAP.glob('*.png'));sheet=Image.new('RGB',(4*400,math.ceil(len(files)/4)*247),(24,28,30));sd=ImageDraw.Draw(sheet)
 for k,file in enumerate(files):
  im=Image.open(file);im.thumbnail((400,225));x=(k%4)*400;y=(k//4)*247
  sheet.paste(im,(x,y+22));sd.text((x+4,y+4),file.stem,fill='white')
 sheet.save(OUT/'final_33_index.jpg',quality=92)
 for args in [
  ('town_market_chapel',(1240,400,1600,725),'U1_clinic_grass_right_angle'),
  ('town_market_chapel',(1260,400,1440,560),'U2_clinic_rock_road_invasion'),
  ('town_market_chapel',(640,360,1040,535),'U3_chapel_access'),
  ('terrace_cross_street',(775,330,990,600),'U4_travel_entry'),
  ('shore_grass_bank',(1030,180,1410,455),'U5_school_front'),
  ('town_north_shops',(620,300,1000,485),'U6_upper_connectivity'),
 ]:crop(*args)
 sample_points={
  'town_market_chapel':[(1490,531),(1500,560),(1492,600),(1510,645),(1310,478),(1320,489),(1330,497),(1303,488),(886,432),(929,448),(974,436),(1011,427),(1003,448),(692,407)],
  'terrace_cross_street':[(914,456),(917,475),(914,488),(900,491),(839,560)],
  'shore_grass_bank':[(1173,280),(1176,311),(1180,359),(1184,405),(1105,293),(1070,312)],
  'town_north_shops':[(696,393),(698,407),(700,419),(749,398),(838,365),(895,348)],
 }
 samples=[]
 for name,pts in sample_points.items():
  for px,py in pts:
   row=raycast(name,px,py)
   if row:samples.append(row)
 xsections=[]
 for z in [14.8,18.4,20.0,28.0,29.8,30.5,31.2,32.0,46.5,59.25]:
  for x in np.arange(19,24.51,.25):
   row=ground(float(x),z)
   if row:xsections.append(row)
 route_samples=[]
 routes=json.loads((DEMO/'captures/rock_path_sample_20261123/routes.json').read_text(encoding='utf8'))
 for name,pts in [('clinic_ramp',[(21.8,30.5),(22.3,30.75),(22.63,30.915)]),
                  ('chapel_ramp',[(22.3,15.3),(22.55,16.1),(22.7,16.5),(22.9,16.9),(23.4,17.3),(23.9,17.6),(24,18),(24,18.5),(23.8,19.1),(23.2,19.5)]),
                  ('travel_entry',[(21.75,46.5),(22.0,46.5),(22.1,46.5)])]:
  route=next(r for r in routes if r['name']==name);ra=np.array(route['points'][:-1]);rb=np.diff(np.array(route['points']),axis=0)
  length=np.linalg.norm(rb,axis=1);tangent=rb/length[:,None]
  for x,z in pts:
   row=ground(x,z);offset=np.array([x,z])-ra;fraction=np.clip((offset*rb).sum(1)/length**2,0,1)
   idx=np.argmin(np.linalg.norm(ra+fraction[:,None]*rb-np.array([x,z]),axis=1));n=nn[row['triangle']];gradient=-n[[0,2]]/n[1]
   row.update(route=name,local_longitudinal_slope_degrees=float(np.degrees(np.arctan(gradient@tangent[idx]))),
              local_transverse_slope_degrees=float(np.degrees(np.arctan(gradient@np.array([-tangent[idx,1],tangent[idx,0]])))))
   route_samples.append(row)
 (OUT/'samples.json').write_text(json.dumps({'pixels':samples,'cross_sections':xsections,'route_samples':route_samples},ensure_ascii=False,indent=2),encoding='utf8')
 for row in samples:print(json.dumps(row))
 print('wrote',OUT)
if __name__=='__main__':main()

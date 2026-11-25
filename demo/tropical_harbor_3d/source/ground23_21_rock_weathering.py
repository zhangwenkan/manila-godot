"""Author a restrained weathered mineral surface in the owned live Blender MCP.

The continuous mesh carries the large shoulders. This image supplies mineral
variation and worn irregularities, not a triangular substitute for rock mass.
Never reruns any preceding script body. Does not save or export geometry.
"""
import ast
import bpy
import json
import math
import struct
import zlib
from pathlib import Path
import numpy as np

assert not bpy.app.background
ROOT=Path(bpy.data.filepath).parent.parent
OUT=ROOT/'assets/reference';LOG=ROOT/'captures/ground_integration_20261123'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('ground23_stronger_forms')
for helper in ast.parse((ROOT/'source/ground23_02_surfaces.py').read_text(encoding='utf8')).body:
    if isinstance(helper,ast.FunctionDef) and helper.name in ('ss','noise','save_image'):
        exec(compile(ast.Module(body=[helper],type_ignores=[]),'G23 stateless image helper','exec'),globals())

for name in ('G23_Rock.png',):
    before=LOG/('v5_'+name)
    if not before.exists():before.write_bytes((OUT/name).read_bytes())
n=2048
broad=noise(n,5,3101);patch=noise(n,17,3102)
medium=noise(n,43,3103);grain=noise(n,197,3104)
height=.50+broad*.27+patch*.22+medium*.075+grain*.014
# Mineral tint is independent of the sun. Sparse pale inclusions and damp
# pockets remain irregular patches, without an outlined grid or cell rims.
mineral=ss(.08,.32,patch+medium*.25)
warm=ss(.04,.30,noise(n,9,3105))
rgb=np.empty((n,n,3),np.float32);rgb[:]=[.402,.422,.390]
rgb+=(broad*.050+patch*.070+medium*.034+grain*.016)[...,None]
rgb+=mineral[...,None]*[.020,.017,.012]
rgb+=warm[...,None]*[.014,.006,-.007]
# A few discontinuous weathered fractures. Their endpoints dissolve inside
# the face; they never enclose each patch or continue as regular strata.
Y,X=np.mgrid[0:n,0:n].astype(np.float32)/n
rng=np.random.default_rng(3124)
for k in range(24):
    cx,cy=rng.random(2);angle=rng.uniform(-.85,.85)
    length=rng.uniform(.045,.14);width=rng.uniform(.0009,.0023)
    dx=(X-cx+.5)%1-.5;dy=(Y-cy+.5)%1-.5
    u=dx*math.cos(angle)+dy*math.sin(angle)
    v=-dx*math.sin(angle)+dy*math.cos(angle)
    v+=.004*np.sin(u*80+rng.uniform(0,6.28))
    cut=(1-ss(length*.52,length,abs(u)))*np.exp(-(v/width)**2)
    cut*=ss(-.18,.10,medium+patch*.45)
    height-=cut*rng.uniform(.025,.065)
    rgb-=cut[...,None]*rng.uniform(.008,.021)
image=save_image('G23_Rock',rgb,height)
for material in bpy.data.materials:
    if not material.use_nodes:continue
    for node in material.node_tree.nodes:
        if node.type=='TEX_IMAGE' and (node.name in ('G23_Rock','G23Preview Rock','G23 existing rock surface') or (node.image and node.image.name=='G23_Rock')):
            node.image=image
step=8/n
slope=np.hypot(np.roll(height,-1,0)-np.roll(height,1,0),np.roll(height,-1,1)-np.roll(height,1,1))*.24/(2*step)
report={'authoring':'owned GUI Blender MCP','role':'Rock','tile_m':8,'height_range_m':.24,
    'size':n,'rgb_mean':rgb.mean((0,1)).tolist(),'height_range':[float(height.min()),float(height.max())],
    'slope_p50_p90_p99':np.percentile(slope,[50,90,99]).tolist(),
    'sun_shadows_baked':False,'triangulated_height_field':False,
    'geometry_modified':False,'source_save_required':True,
    'design':'Weathered mineral patches and sparse interrupted fractures; primary rock mass is real continuous geometry'}
(LOG/'rock_weathering_21.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))

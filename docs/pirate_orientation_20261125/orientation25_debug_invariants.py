import bpy,json,importlib.util
from pathlib import Path
ROOT=Path(bpy.data.filepath).parent.parent
LOG=ROOT/'captures/pirate_orientation_20261125'
spec=importlib.util.spec_from_file_location('orientation_inv',ROOT.parent.parent/'docs/pirate_orientation_20261125/pirate_orientation25_invariants.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
old=json.loads((LOG/'island_local_before.json').read_text(encoding='utf8'))
new=mod.capture_island_local()
def diffs(a,b,p=''):
    if type(a)!=type(b):return [(p,type(a).__name__,type(b).__name__,str(a)[:200],str(b)[:200])]
    if isinstance(a,dict):
        out=[]
        for k in a.keys()|b.keys():out+=diffs(a.get(k),b.get(k),p+'/'+k)
        return out
    if isinstance(a,list):
        if len(a)!=len(b):return [(p,'length',len(a),len(b))]
        out=[]
        for i,(x,y) in enumerate(zip(a,b)):out+=diffs(x,y,p+'/'+str(i))
        return out
    return [] if a==b else [(p,a,b)]
raw=diffs(old['invariant'],new['invariant'])
normalized=diffs(old['invariant'],json.loads(json.dumps(new))['invariant'])
report={'raw_count':len(raw),'raw_first':raw[:12],'normalized_count':len(normalized),'normalized_first':normalized[:60],'root':new['assembly_world']}
(LOG/'invariants_diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report))

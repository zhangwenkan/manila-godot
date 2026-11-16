"""Read-only probe of shipped reference resources and metadata."""
from pathlib import Path
import UnityPy,json,struct
DATA=Path("D:/steam/steamapps/common/I Just Wanted to Fish Demo/I Just Wanted to Fish_Data")
OUT=Path("demo/tropical_harbor_3d/captures/reference_style_audit_20261112")
OUT.mkdir(exist_ok=True)
env=UnityPy.load(str(DATA/"sharedassets1.assets"))
assets=next(f for f in env.files.values() if hasattr(f,"objects"))
out={"source":"Shipped serialized assets, not official full source.","materials":[],"behaviours":[]}
for pid in [7972,7976,7974,7973,8002,8003,8007,8005,8008,8004,8009,7975]:
 o=assets.objects[pid];head=o.parse_monobehaviour_head()
 row={"id":pid,"class":head.m_Script.read().m_ClassName,"bytes":o.byte_size}
 try:row["tree"]=o.read_typetree()
 except Exception as e:row["tree_error"]=str(e)
 raw=o.get_raw_data();row["hex"]=raw.hex()
 out["behaviours"].append(row)
for o in assets.objects.values():
 if o.type.name!="Material":continue
 m=o.read()
 if not any(k in m.m_Name.lower() for k in ["hut","rock","stone","sand","grass","terrain","ink","square","sett","kerb"]):continue
 try:shader=m.m_Shader.read().m_ParsedForm.m_Name
 except Exception:shader="unknown"
 row={"id":o.path_id,"name":m.m_Name,"shader":shader,"keywords":getattr(m,"m_ValidKeywords",[]),"floats":dict(m.m_SavedProperties.m_Floats),"colors":{k:[v.r,v.g,v.b,v.a] for k,v in m.m_SavedProperties.m_Colors},"textures":[]}
 for k,v in m.m_SavedProperties.m_TexEnvs:
  if v.m_Texture.path_id:
   t=v.m_Texture.read()
   row["textures"].append({"property":k,"name":t.m_Name,"id":v.m_Texture.path_id,"scale":[v.m_Scale.x,v.m_Scale.y]})
 out["materials"].append(row)
(OUT/"serialized_probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
print(json.dumps({"materials":[{k:m[k] for k in ["id","name","shader","keywords","textures"]} for m in out["materials"]],"behaviours":[{k:v for k,v in b.items() if k not in ["hex","tree"]} for b in out["behaviours"]]},ensure_ascii=False))


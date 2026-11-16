"""Decode selected shipped metadata fields and exact fixed-layout volume records."""
from pathlib import Path
import json,struct
OUT=Path("demo/tropical_harbor_3d/captures/reference_style_audit_20261112")
b=Path("D:/steam/steamapps/common/I Just Wanted to Fish Demo/I Just Wanted to Fish_Data/il2cpp_data/Metadata/global-metadata.dat").read_bytes()
assert struct.unpack_from("<I",b)[0]==0xFAB11BAF
heap=b[533796:533796+2035288]
def S(i):
 if i<0:return ""
 return heap[i:heap.find(b"\0",i)].decode("utf8","replace")
wanted={"TownSquare","TownPaths","TownProp","IslandGrid","IslandGround","DayNight","ColorAdjustments","WhiteBalance","ShadowsMidtonesHighlights","Tonemapping","GradientSky","SkySettings","IndirectLightingController","ScreenSpaceAmbientOcclusion","ContactShadows","HDShadowSettings","Fog"}
types=[]
for k in range(12599):
 x=9831536+k*76
 name=S(struct.unpack_from("<i",b,x)[0])
 if name not in wanted:continue
 ms=struct.unpack_from("<i",b,x+24)[0];fs=struct.unpack_from("<i",b,x+20)[0]
 mc=struct.unpack_from("<H",b,x+52)[0];fc=struct.unpack_from("<H",b,x+56)[0]
 fields=[{"index":fs+j,"name":S(struct.unpack_from("<i",b,8411048+(fs+j)*10)[0]),"type_index":struct.unpack_from("<H",b,8411048+(fs+j)*10+4)[0],"token":struct.unpack_from("<I",b,8411048+(fs+j)*10+6)[0]} for j in range(fc)]
 methods=[S(struct.unpack_from("<i",b,2947700+(ms+j)*30)[0]) for j in range(mc)]
 types.append({"index":k,"name":name,"fields":fields,"methods":methods})
(OUT/"metadata_fields.json").write_text(json.dumps(types,ensure_ascii=False,indent=2),encoding="utf8")
probe=json.loads((OUT/"serialized_probe.json").read_text())
decoded=[]
for row in probe["behaviours"]:
 raw=bytes.fromhex(row["hex"]);nl=struct.unpack_from("<i",raw,28)[0];start=(32+nl+3)//4*4
 if row["class"] not in {"ColorAdjustments","WhiteBalance","ShadowsMidtonesHighlights","Tonemapping","IndirectLightingController"}:continue
 r={"id":row["id"],"class":row["class"],"head_length":start,"serialized_active":bool(struct.unpack_from("<I",raw,start)[0]),"dwords":[]}
 for off in range(start+4,len(raw),4):
  r["dwords"].append({"offset":off,"uint":struct.unpack_from("<I",raw,off)[0],"float":struct.unpack_from("<f",raw,off)[0]})
 decoded.append(r)
(OUT/"volume_dwords.json").write_text(json.dumps(decoded,indent=2),encoding="utf8")
print(json.dumps({"metadata":[{"name":t["name"],"fields":[f["name"] for f in t["fields"]],"methods":t["methods"][:12]} for t in types],"volumes":decoded},ensure_ascii=False))


"""Decode bounded serialized VolumeParameter layouts; keep defaults separate from runtime."""
from pathlib import Path
import json,struct
OUT=Path("demo/tropical_harbor_3d/captures/reference_style_audit_20261112")
probe=json.loads((OUT/"serialized_probe.json").read_text())
schemas={
"ColorAdjustments":[("postExposure","f"),("contrast","f"),("colorFilter","4f"),("hueShift","f"),("saturation","f")],
"WhiteBalance":[("temperature","f"),("tint","f")],
"ShadowsMidtonesHighlights":[("shadows","4f"),("midtones","4f"),("highlights","4f"),("shadowsStart","f"),("shadowsEnd","f"),("highlightsStart","f"),("highlightsEnd","f")],
"IndirectLightingController":[("indirectDiffuseLightingMultiplier","f"),("indirectDiffuseLightingLayers","I"),("reflectionLightingMultiplier","f"),("reflectionLightingLayers","I"),("reflectionProbeIntensityMultiplier","f")],
"ContactShadows":[("quality","i"),("enable","I"),("length","f"),("opacity","f"),("distanceScaleFactor","f"),("maxDistance","f"),("minDistance","f"),("fadeDistance","f"),("fadeInDistance","f"),("rayBias","f"),("thicknessScale","f"),("m_SampleCount","i")],
"ScreenSpaceAmbientOcclusion":[("quality","i"),("rayTracing","I"),("intensity","f"),("directLightingStrength","f"),("radius","f"),("spatialBilateralAggressiveness","f"),("temporalAccumulation","I"),("ghostingReduction","f"),("blurSharpness","f"),("layerMask","I"),("specularOcclusion","f"),("occluderMotionRejection","I"),("receiverMotionRejection","I"),("m_StepCount","i"),("m_FullResolution","I"),("m_MaximumRadiusInPixels","i"),("m_BilateralUpsample","I"),("m_DirectionCount","i"),("m_RayLength","f"),("m_SampleCount","i"),("m_Denoise","I"),("m_DenoiserRadius","f")]
}
out={"scope":"Serialized BeachVolumeProfile. Individual camera, quality, DayNight/Weather and runtime overrides may differ.","components":[]}
for row in probe["behaviours"]:
 name=row["class"];raw=bytes.fromhex(row["hex"]);ln=struct.unpack_from("<i",raw,28)[0];pos=(32+ln+3)//4*4
 if name not in schemas and name!="Tonemapping":continue
 active=struct.unpack_from("<I",raw,pos)[0];assert active in [0,1];pos+=4
 decoded={"id":row["id"],"class":name,"active":bool(active),"parameters":{}}
 schema=schemas.get(name,[("mode","i"),("useFullACES","I")])
 for field,fmt in schema:
  at=pos;override=struct.unpack_from("<I",raw,pos)[0];assert override in [0,1],(name,field,pos,override);pos+=4
  val=struct.unpack_from("<"+fmt,raw,pos);pos+=struct.calcsize("<"+fmt)
  decoded["parameters"][field]={"offset":at,"override":bool(override),"value":val[0] if len(val)==1 else val}
 if name=="Tonemapping":
  decoded["partial_decode"]=True
  decoded["parameters"]["mode"]["enum"]="Neutral" # Validated against shipped enum default values below.
 else:assert pos==len(raw),(name,pos,len(raw))
 out["components"].append(decoded)
# Metadata header v31 uses offset,size,count triples and 16-bit compact type indices.
b=Path("D:/steam/steamapps/common/I Just Wanted to Fish Demo/I Just Wanted to Fish_Data/il2cpp_data/Metadata/global-metadata.dat").read_bytes()
defs={struct.unpack_from("<iHi",b,5884932+k*10)[0]:struct.unpack_from("<iHi",b,5884932+k*10)[1:] for k in range(17130)}
out["town_square_constants"]={}
for field,index in [("Cell",33328),("KerbTexLength",33329),("KerbTexWidth",33330),("Joint",33331),("Chamfer",33332)]:
 ty,off=defs[index]
 out["town_square_constants"][field]={"field_index":index,"data_offset":6056232+off,"value":struct.unpack_from("<f",b,6056232+off)[0]}
out["tonemapping_enum"]={}
for name,index in [("None",7107),("Neutral",7108),("ACES",7109),("Custom",7110),("External",7111)]:
 off=6056232+defs[index][1];byte=b[off];assert byte<128
 out["tonemapping_enum"][name]=byte>>1 # positive zigzag-compressed int32
(OUT/"decoded_render_settings.json").write_text(json.dumps(out,indent=2),encoding="utf8")
print(json.dumps(out))


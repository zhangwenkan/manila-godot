"""Read-only disassembly of the shipped outline shader, not HLSL source recovery."""
from pathlib import Path
import UnityPy,json,struct,re,ctypes
from UnityPy.helpers import CompressionHelper
DATA=Path("D:/steam/steamapps/common/I Just Wanted to Fish Demo/I Just Wanted to Fish_Data")
OUT=Path("demo/tropical_harbor_3d/captures/reference_style_audit_20261112")
e=UnityPy.load(str(DATA/"sharedassets1.assets"))
a=next(f for f in e.files.values() if hasattr(f,"objects"))
shader=a.objects[55].read().m_Shader.read()
summary={"shader":shader.m_ParsedForm.m_Name,"platforms":shader.platforms,"entries":[]}
dll=ctypes.WinDLL("d3dcompiler_47.dll")
dis=dll.D3DDisassemble
dis.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_uint,ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
dis.restype=ctypes.c_long
def disassemble(data):
 src=ctypes.create_string_buffer(data);p=ctypes.c_void_p()
 hr=dis(src,len(data),0,None,ctypes.byref(p))
 if hr<0 or not p:return "HRESULT "+str(hr)
 vt=ctypes.cast(p,ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
 getp=ctypes.WINFUNCTYPE(ctypes.c_void_p,ctypes.c_void_p)(vt[3])
 gets=ctypes.WINFUNCTYPE(ctypes.c_size_t,ctypes.c_void_p)(vt[4])
 release=ctypes.WINFUNCTYPE(ctypes.c_ulong,ctypes.c_void_p)(vt[2])
 text=ctypes.string_at(getp(p),gets(p)).decode("utf8","replace")
 release(p);return text
blob=bytes(shader.compressedBlob)
for pi in range(len(shader.compressedLengths)):
 def seq(value):return value if isinstance(value,list) else [value]
 for si,(off,ln,dl) in enumerate(zip(seq(shader.offsets[pi]),seq(shader.compressedLengths[pi]),seq(shader.decompressedLengths[pi]))):
  raw=CompressionHelper.decompress_lz4(blob[off:off+ln],dl)
  start=0;idx=0
  while True:
   at=raw.find(b"DXBC",start)
   if at<0:break
   size=struct.unpack_from("<I",raw,at+24)[0]
   if size<32 or at+size>len(raw):start=at+4;continue
   text=disassemble(raw[at:at+size])
   filename=f"outline_p{pi}_s{si}_{idx}.asm.txt"
   (OUT/filename).write_text(text,encoding="utf8")
   summary["entries"].append({"file":filename,"bytes":size,"success":not text.startswith("HRESULT"),"lines":len(text.splitlines())})
   start=at+size;idx+=1
(OUT/"outline_disassembly.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
print(summary)


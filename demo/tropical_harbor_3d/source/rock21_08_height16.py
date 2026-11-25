exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
import struct,zlib
assert not terrain.get('rock21_height16'),'Already applied'
src=(ROOT/'source/rock21_05_surface.py').read_text(encoding='utf8')
exec(src[src.index('n=1024;'):src.index('for name,data,linear')],globals())
def png16(path,values):
    a=(np.clip(values,0,1)*65535+.5).astype('>u2')
    def chunk(name,data):return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    data=b''.join(b'\0'+row.tobytes() for row in a[::-1])
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',a.shape[1],a.shape[0],16,0,0,0,0))+chunk(b'IDAT',zlib.compress(data,9))+chunk(b'IEND',b''))
png16(OUT/'R27_Rock_Height.png',height)
im=bpy.data.images['R27_Rock_Height'];im.unpack(method='REMOVE');im.filepath=str(OUT/'R27_Rock_Height.png');im.reload();im.colorspace_settings.name='Non-Color';im.pack()
terrain['rock21_height16']=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_shore_control_mcp.blend'))
print('16-bit uncompressed rock height saved and packed')

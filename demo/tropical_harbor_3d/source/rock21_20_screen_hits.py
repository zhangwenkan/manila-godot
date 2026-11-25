exec((Path(bpy.data.filepath).parent/'shore_21_context.py').read_text(encoding='utf8'),globals())
def hitpixels(eye,aim,pixels):
    eye=Vector((eye[0],-eye[2],eye[1]));aim=Vector((aim[0],-aim[2],aim[1]))
    f=(aim-eye).normalized();right=f.cross(Vector((0,0,1))).normalized();up=right.cross(f)
    out=[]
    for u,v in pixels:
        d=(f+right*((u/800-1)*(1600/900)*math.tan(math.radians(24)))+up*((1-v/450)*math.tan(math.radians(24)))).normalized()
        p,n,i,_=ground_bvh.ray_cast(eye,d,150)
        out.append({'pixel':[u,v],'xyz':list(p) if p else None,'normal':list(n) if n else None,'face':i})
    return out
print(json.dumps({'earth':hitpixels((-2,6,60),(15,1.5,54),[(1150,640),(1170,652),(1190,670),(1180,680)]),'rock':hitpixels((7,7,48),(24,4,44),[(520,735),(550,745),(565,735),(530,720)])}))

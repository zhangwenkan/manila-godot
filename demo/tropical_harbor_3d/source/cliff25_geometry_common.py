"""Pure section mapping for the cliff25 terrain proposal; does not author a mesh.

Coordinates are Godot X,Z,H in metres. Geometry execution belongs exclusively
to cliff25_01_sculpt.py inside the verified GUI Blender MCP session.
"""
import numpy as np

MASSES = [
    {
        'name': 'seabreeze_rear_turn', 'z_range': (22.2, 27.55),
        'z_fade': (.85, .65), 'x_fade': (.40, .30),
        'sections': [
            (23.0, [(19.60,1.23),(20.00,1.42),(20.38,2.18),(20.98,3.63),(21.65,4.03),(22.25,4.13)]),
            (25.0, [(19.55,1.24),(19.92,1.46),(20.24,2.04),(20.73,3.83),(21.48,4.22),(21.70,4.25)]),
            (26.8, [(19.48,1.26),(19.67,1.43),(20.05,2.50),(20.28,3.62),(20.72,4.34),(21.02,4.40)]),
        ],
    },
    {
        'name': 'clinic_primary_buttress', 'z_range': (26.95, 33.50),
        'z_fade': (.90, .90), 'x_fade': (.70, .32),
        'sections': [
            (27.5, [(18.65,1.27),(19.05,1.48),(19.35,2.63),(19.85,2.88),(20.33,4.20),(20.65,4.42)]),
            (29.0, [(16.85,1.23),(17.60,1.50),(18.10,2.62),(18.78,2.89),(19.58,4.13),(20.15,4.40)]),
            (30.0, [(17.15,1.22),(17.85,1.46),(18.47,2.28),(18.70,3.18),(19.55,4.13),(20.20,4.36)]),
            (31.5, [(18.00,1.24),(18.63,1.52),(19.20,2.19),(19.58,3.35),(20.12,3.91),(20.58,4.18)]),
            (32.8, [(18.35,1.39),(18.95,1.70),(19.35,2.10),(19.65,2.47),(20.03,3.55),(20.55,4.04)]),
        ],
    },
    {
        'name': 'tavern_rear_wedge', 'z_range': (37.6, 45.0),
        'z_fade': (.90, 1.15), 'x_fade': (.55, .35),
        'sections': [
            (38.2, [(17.65,1.70),(18.25,1.94),(18.65,2.32),(19.10,2.75),(19.90,3.73),(20.55,4.01)]),
            (40.2, [(16.90,1.67),(17.45,1.92),(17.95,2.98),(18.75,3.13),(19.65,4.02),(20.50,4.15)]),
            (42.0, [(17.05,1.66),(17.55,2.14),(17.92,3.20),(18.63,3.30),(19.30,3.97),(20.35,4.20)]),
            (43.8, [(17.50,1.62),(18.00,1.88),(18.25,2.27),(18.55,2.73),(19.25,3.49),(20.10,4.23)]),
        ],
    },
]

def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0.0,1.0)
    return t*t*(3.0-2.0*t)

def rounded_polyline(x, knots, radius=.11):
    """Mostly planar face segments with compact rounded joins, not an S-cliff."""
    knots=np.asarray(knots,float)
    y=np.interp(x,knots[:,0],knots[:,1])
    for i in range(1,len(knots)-1):
        x0,h0=knots[i]
        r=min(radius,.28*(x0-knots[i-1,0]),.28*(knots[i+1,0]-x0))
        left=(h0-knots[i-1,1])/(x0-knots[i-1,0])
        right=(knots[i+1,1]-h0)/(knots[i+1,0]-x0)
        t=(x-(x0-r))/(2*r)
        # Quadratic integral of a linearly varying derivative. End heights
        # and end slopes match the two planar segments exactly.
        curved=h0-left*r+2*r*(left*t+.5*(right-left)*t*t)
        take=np.abs(x-x0)<r
        y=np.where(take,curved,y)
    return y

def mass_field(x,z,mass):
    """Return target height, section weight, normalized cross-face station.

    Weights include X/Z boundary fades only, NOT road/floor/root protection.
    The authoring caller must apply its separately checked protection field.
    """
    x,z=np.broadcast_arrays(np.asarray(x,float),np.asarray(z,float))
    rows=mass['sections']; zs=np.array([q[0] for q in rows])
    j=np.clip(np.searchsorted(zs,z,side='right')-1,0,len(rows)-2)
    u=np.clip((z-zs[j])/(zs[j+1]-zs[j]),0,1)
    # Eased station interpolation avoids a thin crease at control sections;
    # the in-plane profile still consists of broad planes and short joins.
    t=u*u*(3-2*u)
    target=np.zeros_like(x); toe=np.zeros_like(x); crest=np.zeros_like(x)
    for i in range(len(rows)-1):
        take=j==i
        if not np.any(take):continue
        a,b=rows[i][1],rows[i+1][1]
        # Move corresponding section breakpoints, rather than averaging two
        # spatially offset cliffs (which would create an unintended double wall).
        knots=(1-t[take,None,None])*np.asarray(a)[None]+t[take,None,None]*np.asarray(b)[None]
        xx=x[take]
        segment=np.clip(np.sum(xx[:,None]>=knots[:,:,0],axis=1)-1,0,knots.shape[1]-2)
        rid=np.arange(len(xx));ka=knots[rid,segment];kb=knots[rid,segment+1]
        section_height=ka[:,1]+np.clip((xx-ka[:,0])/(kb[:,0]-ka[:,0]),0,1)*(kb[:,1]-ka[:,1])
        for corner in range(1,knots.shape[1]-1):
            x0,h0=knots[:,corner,0],knots[:,corner,1]
            r=np.minimum(.11,.28*np.minimum(x0-knots[:,corner-1,0],knots[:,corner+1,0]-x0))
            left=(h0-knots[:,corner-1,1])/(x0-knots[:,corner-1,0])
            right=(knots[:,corner+1,1]-h0)/(knots[:,corner+1,0]-x0)
            ucorner=(xx-(x0-r))/(2*r)
            curved=h0-left*r+2*r*(left*ucorner+.5*(right-left)*ucorner*ucorner)
            section_height=np.where(abs(xx-x0)<r,curved,section_height)
        target[take]=section_height
        toe[take]=(1-t[take])*a[0][0]+t[take]*b[0][0]
        crest[take]=(1-t[take])*a[-1][0]+t[take]*b[-1][0]
    z0,z1=mass['z_range']; f0,f1=mass['z_fade']; xf0,xf1=mass['x_fade']
    weight=smoothstep(z0,z0+f0,z)*(1-smoothstep(z1-f1,z1,z))
    weight*=smoothstep(toe-xf0,toe+.05,x)*(1-smoothstep(crest-.02,crest+xf1,x))
    cross=np.clip((x-toe)/np.maximum(crest-toe,.01),0,1)
    return target,weight,cross

def cliff25_fields(x,z):
    """All named fields for authoring or matching region LandUse/UV design."""
    return {mass['name']:mass_field(x,z,mass) for mass in MASSES}

def cliff25_section_metadata():
    return {'coordinate_order':'Godot X,Z,H','masses':MASSES,
            'weights':'Z and X footprint fades only; live terrain locks applied separately',
            'regional_chart_ranges':[[22.2,33.5,.9,4.8],[37.6,45.0,1.3,4.6]]}

from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from model_lib import *
root=activate()
assert not root.get('office_complete'), 'Office already detailed; inspect before rerunning'
# Remove only this task's named blockout meshes, never user objects.
for obj in list(collection().objects):
    if obj.name.startswith('INS_Blockout'):
        data=obj.data
        bpy.data.objects.remove(obj,do_unlink=True)
        if data.users==0: bpy.data.meshes.remove(data)
office=bpy.data.objects['Office']
roof=bpy.data.objects['Roof']
front=.6
back=3.30


def front_wall(name,left,right,top,opening):
    a,b,bottom,upper=opening
    for suffix,l,r,lo,hi in [('L',left,a,.62,top),('R',b,right,.62,top),('Sill',a,b,.62,bottom),('Lintel',a,b,upper,top)]:
        if r-l>.01 and hi-lo>.01:
            box('INS_'+name+'_'+suffix,((l+r)/2,front+.1,(lo+hi)/2),(r-l,.20,hi-lo),'INS_Wall',office)
    # Narrow board battens stop at the actual opening, not across the window.
    x=left+.07
    while x<right:
        spans=[(.66,top-.04)] if x<a or x>b else [(.66,bottom-.02),(upper+.02,top-.04)]
        for lo,hi in spans:
            if hi>lo: box('INS_BoardJoint',(x,front-.018,(lo+hi)/2),(.035,.04,hi-lo),'INS_Trim',office,.003)
        x+=.245


def window(name,x,z,w,h,y=front):
    frame=group('INS_'+name,office)
    box('INS_'+name+'_Recess',(x,y+.13,z),(w,.065,h),'INS_Dark',frame,.012)
    for a in [-1,1]:
        for b in [-1,1]:
            box('INS_'+name+'_Glass',(x+a*w*.244,y+.084,z+b*h*.245),(w*.455,.024,h*.438),'INS_GlassLight' if a+b==0 else 'INS_Glass',frame,.003)
    for dx in [-w/2,0,w/2]:
        box('INS_'+name+'_Mullion',(x+dx,y-.045,z),(.07,.15,h+.12),'INS_Cream',frame,.008)
    for dz in [-h/2,0,h/2]:
        box('INS_'+name+'_Transom',(x,y-.05,z+dz),(w+.15,.15,.075),'INS_Cream',frame,.008)
    box('INS_'+name+'_Sill',(x,y-.12,z-h/2-.07),(w+.28,.36,.12),'INS_Trim',frame)
    for dx in [-w/2-.12,w/2+.12]:
        box('INS_WindowOuterTrim',(x+dx,y-.015,z),(.13,.17,h+.34),'INS_Trim',frame)

front_wall('MainFacade',-3.6,0,3.55,(-3.22,-.38,1.26,2.42))
front_wall('LeftFacade',-5.6,-3.6,2.73,(-5.20,-4.02,1.25,2.32))
front_wall('RightFacade',0,1.7,2.93,(.42,1.35,.62,2.62))
for x,w,h in [(-1.8,3.6,3.55),(-4.6,2,2.73),(.85,1.7,2.93)]:
    box('INS_BackWall',(x,back-.10,(h+.62)/2),(w,.20,h-.62),'INS_Wall',office)
    box('INS_InteriorFloor',(x,1.95,.68),(w-.1,2.5,.12),'INS_Wood',office)
    for y in [.64,3.28]:
        box('INS_WallFootrail',(x,y,.79),(w,.13,.20),'INS_Trim',office)
        box('INS_WallHeadrail',(x,y,h-.07),(w,.16,.16),'INS_Trim',office)
for x,h in [(-5.6,2.73),(1.7,2.93)]:
    box('INS_EndWall',(x,1.95,(h+.62)/2),(.20,2.7,h-.62),'INS_Wall',office)
    for i in range(12):
        box('INS_EndBoardSeam',(x+(-.11 if x<0 else .11),.72+i*.222,(h+.62)/2),(.035,.035,h-.66),'INS_Trim',office,.003)
for x,h in [(-5.65,2.78),(-3.60,3.59),(0,3.59),(1.75,2.99)]:
    for y in [.54,3.32]:
        box('INS_CornerPost',(x,y,(h+.58)/2),(.14,.17,h-.58),'INS_Trim',office)
window('MainWindow',-1.8,1.84,2.84,1.16)
window('LeftWindow',-4.61,1.785,1.18,1.07)
# Door is an inset assembly inside a real opening.
door=group('INS_Entry',office)
box('INS_DoorLeaf',(.885,.72,1.63),(.89,.10,1.97),'INS_Wood',door)
for x in [.37,1.40]:
    box('INS_DoorJamb',(x,.51,1.64),(.13,.22,2.14),'INS_Cream',door)
box('INS_DoorLintel',(.885,.51,2.69),(1.16,.22,.16),'INS_Cream',door)
box('INS_DoorGlass',(.885,.647,2.03),(.61,.04,.70),'INS_Glass',door)
for x in [.55,1.22]:
    box('INS_DoorGlassFrame',(x,.607,2.03),(.065,.09,.82),'INS_Trim',door)
for z in [1.61,2.445]:
    box('INS_DoorGlassFrame',(.885,.607,z),(.74,.09,.065),'INS_Trim',door)
cylinder('INS_BrassKnob',(1.17,.548,1.40),.047,.06,'INS_Cream',door,12,(0,-1,0))
for i in range(3):
    box('INS_EntryStep',(.885,.06-i*.23,.58-i*.09),(1.44,.52,.14),'INS_Stone',door,.025)
# Front and back gables have thickness; the small front attic window is recessed.
for y in [front,back-.14]:
    mesh('INS_MainGable',[(-3.6,y,3.54),(0,y,3.54),(-1.8,y,4.99),(-3.6,y+.14,3.54),(0,y+.14,3.54),(-1.8,y+.14,4.99)],[(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)],'INS_Wall',office,.006)
# Attic box projects from the gable so its dark recess is not a flat decal.
box('INS_AtticOpening',(-1.8,.47,4.18),(.69,.15,.64),'INS_Dark',office)
for dx in [-.25,.0,.25]:
    box('INS_AtticWindowBar',(-1.8+dx,.365,4.18),(.055,.08,.57),'INS_Cream',office,.005)
for z in [3.89,4.47]:
    box('INS_AtticFrame',(-1.8,.365,z),(.68,.09,.07),'INS_Trim',office)
for i in range(12):
    x=-3.5+i*.29
    ztop=4.99-abs(x+1.8)*1.45/1.8
    if ztop>3.7:
        box('INS_GableBoard',(x,.58,(ztop+3.6)/2),(.026,.035,ztop-3.6),'INS_Trim',office,.002)
box('INS_InsuranceSignBacking',(-1.8,.30,3.17),(3.63,.20,.64),'INS_Dark',office,.022)
box('INS_InsuranceSignFace',(-1.8,.184,3.17),(3.44,.035,.49),'INS_Cream',office,.008)
text('INS_InsuranceLettering','INSURANCE CO.',(-1.8,.155,3.16),3.12,'INS_Dark',office)
for x in [-3.43,-.17]:
    for z in [2.98,3.36]:
        cylinder('INS_SignBolt',(x,.15,z),.025,.025,'INS_Iron',office,8,(0,-1,0))
# Multiple connected roof levels, not intersecting generic gables.
for side in [-1,1]:
    a=(-1.8,.31,5.12); b=(-1.8,3.63,5.12)
    c=(-1.8+side*2.04,3.63,3.65); d=(-1.8+side*2.04,.31,3.65)
    slab('INS_MainRoof_'+str(side),[a,b,c,d],.14,'INS_Tin',roof)
    beam('INS_GableBargeboard',a,d,.14,'INS_Trim',roof)
    beam('INS_BackBargeboard',b,c,.13,'INS_Trim',roof)
    beam('INS_EaveFascia',d,c,.15,'INS_Trim',roof)
    for i in range(9):
        y=.34+i*.402
        beam('INS_RoofStandingSeam',(-1.8,y,5.138),(-1.8+side*2.04,y,3.667),.032,'INS_Iron',roof,bevel=0)
    for t in [.34,.69]:
        x=-1.8+side*2.04*t; z=5.12-1.47*t+.019
        beam('INS_RoofHorizontalLap',(x,.32,z),(x,3.61,z),.028,'INS_Tin',roof,bevel=0)
beam('INS_RidgeCap',(-1.8,.22,5.13),(-1.8,3.71,5.13),.17,'INS_Tin',roof)
for name,a,b in [('Left',(-3.54,3.23),(-5.86,2.80)),('Right',(-.06,3.30),(1.99,2.99))]:
    slab('INS_'+name+'LeanRoof',[(a[0],.29,a[1]),(a[0],3.61,a[1]),(b[0],3.61,b[1]),(b[0],.29,b[1])],.12,'INS_Tin',roof)
    for y in [.29,3.61]:
        beam('INS_WingBargeboard',(a[0],y,a[1]-.05),(b[0],y,b[1]-.05),.11,'INS_Trim',roof)
    beam('INS_WingFascia',(b[0],.28,b[1]-.05),(b[0],3.62,b[1]-.05),.14,'INS_Trim',roof)
    for i in range(9):
        y=.34+i*.4
        beam('INS_WingRoofSeam',(a[0],y,a[1]+.02),(b[0],y,b[1]+.02),.027,'INS_Iron',roof,bevel=0)
# Entry awning sits beneath the low wing, with wall brackets and a rolled edge.
slab('INS_DoorCanopy',[(.07,.63,2.85),(1.65,.63,2.85),(1.65,-.40,2.68),(.07,-.40,2.68)],.10,'INS_Tin',office)
for x in [.13,1.58]:
    beam('INS_CanopyBracket',(x,.49,2.27),(x,-.30,2.65),.068,'INS_Iron',office)
beam('INS_CanopyLip',(.02,-.41,2.68),(1.70,-.41,2.68),.10,'INS_Trim',office)
# Side rain pipes and gutter have real round profiles.
for x in [-5.88,2.02]:
    tube('INS_Downpipe',[(x,3.35,2.83),(x,3.49,2.70),(x,3.49,.88),(x+.12,3.49,.75)],.047,'INS_Iron',office)
root['office_complete']=True
bpy.context.view_layer.update()
print('OFFICE_DETAILED',len(office.children_recursive),len(roof.children_recursive))

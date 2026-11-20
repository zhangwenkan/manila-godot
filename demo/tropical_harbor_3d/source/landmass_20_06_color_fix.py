# Correct generated image values; this Blender save path writes pixel values directly.
for im in images.values():
    pixels=np.empty(len(im.pixels),np.float32);im.pixels.foreach_get(pixels);pixels=pixels.reshape((-1,4))
    rgb=pixels[:,:3];pixels[:,:3]=np.where(rgb<=.0031308,rgb*12.92,1.055*np.maximum(rgb,0)**(1/2.4)-.055)
    im.pixels.foreach_set(pixels.ravel());im.save();im.pack()
export_land()
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'source/harbor_landform_mass_mcp.blend'))
print('COLOR_FIXED four authored source images saved and repacked')

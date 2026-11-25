# Close only this turn's already-saved, verified independent GUI session.
import json
assert not bpy.data.is_dirty, 'Unsaved changes: do not close'
terrain=bpy.data.objects['C25_ContourBuiltCoast']
assert terrain.get('rock21_soil_patch') and terrain.get('rock21_prop_misclassification_corrected')
report={'source':bpy.data.filepath,'pid':os.getpid(),'dirty':bpy.data.is_dirty,
        'final_patch_saved':True,'close_scheduled':True}
root=Path(bpy.data.filepath).parent.parent
(root/'captures/rock_earth_rebuild_20261121/session_close.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def close_verified_session():
    bpy.ops.wm.quit_blender()
    return None
bpy.app.timers.register(close_verified_session,first_interval=2.0)
print(json.dumps(report))

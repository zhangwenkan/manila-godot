extends SceneTree

const OUT = "res://demo/tropical_harbor_3d/captures/cliff_contacts_20261125/"
const ART = "res://demo/tropical_harbor_3d/assets/reference/"

func format_description(value: int) -> Dictionary:
    match value:
        Image.FORMAT_RF: return {"name":"RF", "channels":1, "dtype":"<f4"}
        Image.FORMAT_RGF: return {"name":"RGF", "channels":2, "dtype":"<f4"}
        Image.FORMAT_RGBF: return {"name":"RGBF", "channels":3, "dtype":"<f4"}
        Image.FORMAT_RGBAF: return {"name":"RGBAF", "channels":4, "dtype":"<f4"}
        Image.FORMAT_RH: return {"name":"RH", "channels":1, "dtype":"<f2"}
        Image.FORMAT_RGH: return {"name":"RGH", "channels":2, "dtype":"<f2"}
        Image.FORMAT_RGBH: return {"name":"RGBH", "channels":3, "dtype":"<f2"}
        Image.FORMAT_RGBAH: return {"name":"RGBAH", "channels":4, "dtype":"<f2"}
        Image.FORMAT_RGB8: return {"name":"RGB8", "channels":3, "dtype":"u1"}
        Image.FORMAT_RGBA8: return {"name":"RGBA8", "channels":4, "dtype":"u1"}
        _: return {"name":"other", "enum":value}

func record_image(img: Image, filename: String) -> Dictionary:
    if img == null or img.is_empty():
        return {"error":"No image"}
    var compressed := img.is_compressed()
    var decompress_result := OK
    if compressed:
        decompress_result = img.decompress()
    var data := img.get_data()
    var output := FileAccess.open(OUT + filename, FileAccess.WRITE)
    output.store_buffer(data)
    output.close()
    return {"width": img.get_width(), "height":img.get_height(), "mipmaps":img.get_mipmap_count(),
        "initially_compressed":compressed, "decompress_result":decompress_result,
        "format":format_description(img.get_format()), "byte_count":data.size(), "raw_file":filename}

func _init() -> void:
    var result: Dictionary = {"godot":Engine.get_version_info(), "textures":{}}
    for name in ["C25_CliffRegion_Color.png", "C25_CliffRegion_Height.exr", "C25_GroundDetail.png"]:
        var row: Dictionary = {}
        var source := Image.load_from_file(ProjectSettings.globalize_path(ART + name))
        row["source"] = record_image(source, "audit_" + name + "_source.bin")
        var texture := load(ART + name) as Texture2D
        if texture == null:
            row["cache"] = {"error":"Texture load failed"}
        else:
            row["cache"] = record_image(texture.get_image(), "audit_" + name + "_cache.bin")
        result["textures"][name] = row
    var output := FileAccess.open(OUT + "godot_texture_cache_probe.json", FileAccess.WRITE)
    output.store_string(JSON.stringify(result, "  "))
    output.close()
    print("CLIFF25_CACHE_PROBE_COMPLETE")
    quit(0)

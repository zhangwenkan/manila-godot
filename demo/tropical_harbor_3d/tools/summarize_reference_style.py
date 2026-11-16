"""Make a compact research manifest and annotate existing images, not models."""
from collections import Counter
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
ART = ROOT / "demo/tropical_harbor_3d"
OUT = ART / "captures/reference_style_audit_20261112"
CURRENT = ART / "captures/art_20261112_135029_417323/shipyard_combined_reference.png"
REFERENCE = Path("C:/Users/51440/.watch-skill/frames/bf8303ead581ce39/frame_0000.jpg")
CONCEPT = Path("C:/Users/51440/Downloads/Create_stock_value_board_3e7c69c9_2K.jpg")


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf8"))


def save_manifest():
    probe = read("serialized_probe.json")
    geometry = read("current_geometry_diagnosis.json")
    native = read("ground_native_evidence.json")
    names = {"M_Hut", "M_HutDock", "M_Rock_Slab", "M_SquareSetts", "M_SquareKerb"}
    materials = [{"id": m["id"], "name": m["name"], "shader": m["shader"],
                  "smoothness": m["floats"].get("_Smoothness"),
                  "metallic": m["floats"].get("_Metallic"),
                  "normal_scale": m["floats"].get("_NormalScale"),
                  "textures": [t for t in m["textures"] if t["property"] != "_MainTex"]}
                 for m in probe["materials"] if m["name"] in names]
    ink = next(m for m in probe["materials"] if m["name"] == "M_InkOutline")
    paving = [o for o in geometry["stones"] if "terrace paving" in o["name"]]
    adjacent = []
    for i, a in enumerate(paving):
        ba = np.array(a["bounds_world"])
        amin, amax = ba.min(0), ba.max(0)
        for b in paving[i + 1:]:
            bb = np.array(b["bounds_world"])
            bmin, bmax = bb.min(0), bb.max(0)
            if not np.allclose([amin[2], amax[2]], [bmin[2], bmax[2]], atol=1e-5):
                continue
            for axis in (0, 1):
                other = 1 - axis
                overlap = min(amax[other], bmax[other]) - max(amin[other], bmin[other])
                gap = max(amin[axis], bmin[axis]) - min(amax[axis], bmax[axis])
                if overlap > 0.1 and 0 < gap < 0.08:
                    adjacent.append(round(float(gap), 4))
    blend = read("outline_bindings_and_state.json")["state"]["rtBlend0"]
    summary = {
        "date": "2026-11-12",
        "scope": "Research of shipped serialized resources and native code; no runtime assets changed by this study.",
        "materials": materials,
        "outline": {"parameters": ink["floats"], "colors": ink["colors"],
                    "blend0": {k: v["val"] for k, v in blend.items()},
                    "interpretation": "Depth curvature and normal discontinuity; roughness tags can skip or soften; output tint multiplies destination."},
        "current_stones": {"count": len(geometry["stones"]), "paving_count": len(paving),
                           "paving_dimensions": [{"dimensions": list(k), "count": v} for k, v in
                               Counter(tuple(round(v, 4) for v in o["dimensions"]) for o in paving).items()],
                           "paving_adjacent_gap_samples": len(adjacent),
                           "paving_adjacent_gap_counts": dict(Counter(adjacent)),
                           "bevel_width_counts": dict(Counter(round(m["width"], 4) for o in geometry["stones"] for m in o["bevels"])),
                           "coordinates": "Saved Blender MCP audit in source units; do not interpret reference Cell as a visible brick size."},
        "native_method_count": len(native["methods"]),
        "native_source_hashes": {k: native[k] for k in ["dll_sha256", "metadata_sha256"]},
        "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                          [ART / "assets/coast/shipyard_combined.glb", ART / "source/harbor_coast_mcp.blend"]},
        "verified_distinctions": [
            "TownSquare.Field samples a regular connected grid with OnGround and planar UVs; Cell is not an individual stone size.",
            "TownSquare.Kerb invokes Slab; Slab samples ground, uses 0.003 half-joint and caps chamfer at 0.015.",
            "TownSquare.GroundY has a drape branch calling IslandTiles.Hit; OnGround returns the sampled height in local coordinates.",
            "BeachVolumeProfile SSAO is inactive; ContactShadows component is active but enable is false. Runtime overrides remain unverified.",
            "SoftInk scales line strength; it is not an image blur. M_Hut/M_HutDock smoothness 0.07 corresponds to the outline soft roughness tag 0.93."
        ]
    }
    (OUT / "research_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    return summary


def make_board():
    canvas = Image.new("RGB", (1800, 1390), "#f4f1e9")
    draw = ImageDraw.Draw(canvas)
    font_path = "C:/Windows/Fonts/msyh.ttc"
    bold_path = "C:/Windows/Fonts/msyhbd.ttc"
    font = lambda n, bold=False: ImageFont.truetype(bold_path if bold else font_path, n)
    title, h2, body, small = font(42, True), font(28, True), font(25), font(22)
    dark, muted = "#203f3b", "#5b6b65"

    def wrap(text, ft, width):
        result, line = [], ""
        for ch in text:
            if ch == "\n" or (line and draw.textlength(line + ch, font=ft) > width):
                result.append(line)
                line = "" if ch == "\n" else ch
            else:
                line += ch
        if line:
            result.append(line)
        return result

    draw.text((40, 24), "修船厂为什么与海岸不搭", font=title, fill=dark)
    draw.text((42, 83), "当前模型诊断（未修改）  ·  参考图机位不同，仅比较构造、边缘与落地关系", font=small, fill=muted)
    src = Image.open(CURRENT).convert("RGB")
    draw.rounded_rectangle((32, 131, 1152, 771), radius=12, fill="white")
    canvas.paste(src.resize((1100, 619), Image.Resampling.LANCZOS), (42, 142))

    callouts = [
        ((723, 698), "#b8663e", "1  外轮廓像独立底座", "石坞的长直边和连续高差，直接截在沙地上。保留凹槽功能，先处理侧后方贴地与岸边过渡。"),
        ((924, 555), "#586f85", "2  铺地与挡墙同样厚重", "顶面、压顶、挡墙都由整块石反复排列。区分浅铺装与承重外缘，让接缝退到适当层级。"),
        ((905, 328), "#8c6545", "3  铁皮细线争夺注意力", "压型沟、板缝、边框与锈迹需要主次。深灰蓝和重锈保留；用完整板面承接局部磨损。"),
        ((1196, 622), "#607d4c", "4  建筑与地面缺少衔接", "周围仍是空沙地和占位环境。用有限的作业地、沙土压边和植物过渡连接这栋建筑。"),
    ]
    for i, (xy, color, heading, description) in enumerate(callouts):
        x = 42 + round(xy[0] * 1100 / 1600)
        y = 142 + round(xy[1] * 619 / 900)
        draw.ellipse((x-18, y-18, x+18, y+18), fill=color, outline="white", width=3)
        label = str(i+1)
        draw.text((x-draw.textlength(label, font=small)/2, y-16), label, font=small, fill="white")
        cy = 146 + i * 157
        draw.rounded_rectangle((1172, cy, 1758, cy+145), radius=12, fill="white")
        draw.rectangle((1172, cy+18, 1178, cy+126), fill=color)
        draw.text((1194, cy+12), heading, font=h2, fill=color)
        for j, line in enumerate(wrap(description, body, 538)):
            draw.text((1194, cy+54+j*31), line, font=body, fill=dark)
    draw.text((42, 783), "本项目 · 2026-11-12 已保存实机图。标记指出诊断位置，不表示已实施修改。", font=small, fill=muted)
    draw.line((42, 835, 1758, 835), fill="#c8cec1", width=2)
    draw.text((42, 858), "参考游戏实景：色面与边线有主次", font=h2, fill=dark)
    draw.text((922, 858), "用户概念图：建筑、作业地与沙草连贯", font=h2, fill=dark)
    ref = Image.open(REFERENCE).convert("RGB")
    concept = Image.open(CONCEPT).convert("RGB")
    canvas.paste(ref.resize((836, 470), Image.Resampling.LANCZOS), (42, 902))
    canvas.paste(concept.resize((836, round(concept.height*836/concept.width)), Image.Resampling.LANCZOS), (922, 902))
    # Source frames are resized only; no colour adjustment, sharpening or new geometry.
    canvas.save(OUT / "style_diagnosis.png")
    manifest = {"purpose": "Existing-frame diagnostic annotations, not a new render or a matched-camera quality comparison.",
                "images": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in [CURRENT, REFERENCE, CONCEPT]],
                "processing": "Resizing for a labelled contact sheet and numbered markers only. No colour adjustments or sharpening."}
    (OUT / "annotation_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8")


if __name__ == "__main__":
    summary = save_manifest()
    make_board()
    print(json.dumps({"native_methods": summary["native_method_count"], "stones": summary["current_stones"], "image": str(OUT / "style_diagnosis.png")}, ensure_ascii=False))

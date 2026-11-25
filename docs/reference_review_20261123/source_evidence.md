# 原作岩岸与门前通路：新机原始数据复核 · 2026-11-23

本轮只读研究，没有调用 Blender MCP，没有修改运行模型、材质或场景。先检查两份接续包，随后在 **`F:/钓鱼游戏analysis/update_2026-11-17/`** 找到完整拆解快照。以下优先依据该新版快照；接续包里的旧规格和 11 月 12 日原生反汇编仅作历史对照。

## 1. 数据位置、版本与可复核范围

- 完整新版数据根：`F:/钓鱼游戏analysis/update_2026-11-17/`。`README.md` 和新版报告注明 0.1.1 / Unity 6000.3.8f1 / IL2CPP v39。
- 场景绑定：`scenes/level2.json`；资源身份、尺寸、导出像素哈希：`asset_inventory.json`；材质：`materials.json` 与 `exported_all/materials/*.json`；模型：`exported_all/meshes/*.obj`；图片：`exported_all/textures/*.png`。
- 本轮精简证据：`demo/tropical_harbor_3d/captures/fish_rock_road_study_20261123/reference_data/current_snapshot_evidence.json`，包含选择的节点、完整材质、纹理记录、网格边界与 UV 分析。`uv_mapping_summary.json` 保存拟合结果。
- 当前查到的是拆解快照。旧安装目录 `D:/steam/steamapps/common/I Just Wanted to Fish Demo/analysis` 不存在，已查看的 Steam 库没有该游戏；该分析目录也不含发布的 DLL、metadata、resources.assets。不能声称本轮再次核对了新机已安装游戏二进制。
- `package_manifest.json` 保存快照的 `GameAssembly.dll` SHA-256：`ef016fa865c755879449c9f0472397aac7f6067cc72d6c1b1765dec1c4e71bb4`；`global-metadata.dat`：`39f067288601bc5b8ccb9a80e31f90c91fa9e9fa8b6d6df7712f6b3e133a2d03`。这两项为快照记录，不是本轮对发布文件的新计算。
- 本轮实际计算的五个 OBJ 哈希，按导出脚本原方法统一为 LF 后全部匹配 `asset_inventory.json` 的 `obj_sha256`；原文件是 CRLF，直接字节哈希不同不表示模型变了。East 颜色、East 法线、RockDetail、HomeBase 颜色的 RGBA 像素哈希也全部精确匹配快照。

两份接续包中的 `reference_research` 主要保留文字；精简包新版子树排除依赖后只有 35 个 txt/md 文件。完整数据在上述独立目录，不应继续因为接续包缺文件而认定新机没有原始模型或贴图。

## 2. 岩岸真实网格与主图映射

`level2.json` 中 `/Environment/Island Terrain/East/East_7_4` 绑定 mesh `sharedassets2.assets:1907`，材质 `M_TerrainEast_Demo:110`；`East_7_5` 绑定同一材质。`/Environment/Island Terrain/Hill/Hill_6_1` 绑定 mesh `1910`，材质 `M_TerrainHill_Demo:111`。所查地形节点为零位移、单位旋转和单位缩放；它们有 MeshFilter、MeshRenderer、MeshCollider。

| 导出 OBJ | 顶点 / 三角形 | Y 范围 |
| --- | ---: | ---: |
| `East_7_4_Demo__sharedassets2.assets_1907.obj` | 8,587 / 16,780 | 1.034～3.613 m |
| `East_7_5__sharedassets2.assets_650.obj` | 9,409 / 18,432 | −2.071～3.434 m |
| `Hill_6_1_Demo__sharedassets2.assets_1910.obj` | 5,227 / 10,125 | 3.186～5.712 m |
| `Hill_6_2_Demo__sharedassets2.assets_1911.obj` | 3,686 / 7,108 | 3.123～6.196 m |

路径均位于新版根下 `exported_all/meshes/`。在 `East_7_5` 的同一 OBJ 坐标 X=−54 剖面，本轮重新读到 Z=−26 时 Y=0.292315394，Z=−24 时 Y=2.8189888，Z=−22 时 Y=3.14177895。约 2.5 m 的阶地落差是几何，不是颜色带或法线图假高度。

使用每个面的实际顶点与 UV 索引拟合，East 两块都满足：

```text
U = (−X − 26) / 46
V = ( Z + 44) / 56
```

这里 X/Z 严格指 **OBJ 导出坐标**，不将导出轴符号直接冒称 Unity 世界轴符号。最大 UV 残差为 2.90×10⁻⁸，两个方向 R² 均大于 0.9999999999999。即这两块共享一张覆盖约 46×56 m 平面的大图坐标。它们不是把一张几米大小的通用岩图反复铺满。

Hill 两块同样是平面映射：`U=(−X−4)/102`，`V=(Z−12)/114`，最大残差 1.56×10⁻⁸。纹理总图覆盖范围比单个 12 m 地块大得多；各地块只使用主图的一部分。

这也说明主图在陡坡会被拉伸：`East_7_5` 最陡三角形的 `abs(normal.y)=0.04096`，其实际三角形面积约为水平投影面积的 24.4 倍。该数是几何面积比，不能直接称某一方向纹理被拉长 24.4 倍，也不能据此断言实际游戏已经出现可见拉丝。原 shader 是否用额外细节或其他映射补偿，当前缺少编译程序，尚不能确定。

## 3. 岩岸材质分工：配套主图与共用细节图

最新两个材质均绑定 `resources.assets:214 → Shader Graphs/TerrainEast`。精确材质路径：

- `F:/钓鱼游戏analysis/update_2026-11-17/exported_all/materials/M_TerrainEast_Demo__sharedassets2.assets_110.json`
- `F:/钓鱼游戏analysis/update_2026-11-17/exported_all/materials/M_TerrainHill_Demo__sharedassets2.assets_111.json`

| 材质属性 | East 纹理身份及尺寸 | Hill 纹理身份及尺寸 |
| --- | --- | --- |
| `_BaseColorMap` | `T_TerrainEast_Albedo_Demo:413`，4096² | `T_TerrainHill_Albedo_Demo:371`，8192² |
| `_NormalMap` | `T_TerrainEast_Normal_Demo:191`，4096² | `T_TerrainHill_Normal_Demo:301`，4096² |
| `_MaskMap` | `T_TerrainEast_Mask_Demo:399`，4096² | `T_TerrainHill_Mask_Demo:394`，4096² |
| `_RockDetail` | 共同绑定 `T_RockDetail_Demo:296`，512² | 同左 |

以上身份均来自 `sharedassets2.assets`。主图 `m_WrapU/V/W=1`，细节图为 `0`；本轮保留原始序列化值，分别对应 clamp 与 repeat。材质纹理 scale=(1,1)、offset=(0,0)。

颜色图本身保留整个地形分区、草沙与岩带的布局，法线图与遮罩分别是独立资源，不能把原作的岩面结构归结为一张重复裂纹。**配套颜色图、法线图、遮罩和 512² 细节图同时存在**是绑定事实；它们的具体混合公式还不能由名称代替。

`shaders.json` 只保存 shader 属性列表与 subshader 数量。实际导出脚本 `analyze_update.py` 第 376～378 行也只写这两类数据，没有写出编译 subprogram；该目录不存在对应的发布 `resources.assets`。因此 `_RockDetail` 的 RGBA 究竟对应哪种法线、微高差、遮罩组合，其取样方向与权重公式 **尚未核实**。不能把它当普通 RGB 岩色贴图，也不能因为有高频通道就断言作者使用了三平面法线。

网格 inventory 中所查 East/Hill 的 vertex-color 通道维数为 0；部分新版地块的 UV0 是 4 维，而 OBJ 只保留其中二维。因此也不能直接说没有其他自定义权重，更不能把本项目 `LandUse` 颜色属性当作原作已核实机制。

轻量研究图均在 `reference_data/`，仅缩小、按实际 UV 范围裁切、或分通道显示，没有改变颜色/曝光，也没有导入运行场景：

- `terrain_texture_sets_preview.jpg`：East/Hill 颜色、原始法线、遮罩并列。
- `rock_detail_channels.png`：RockDetail 原 RGB 和 R/G/B/A 通道；**不是解码后的法线效果图**。
- `East_7_4_Demo_albedo_uv_window.jpg`、`East_7_5_albedo_uv_window.jpg`、`Hill_6_1_Demo_albedo_uv_window.jpg`、`Hill_6_2_Demo_albedo_uv_window.jpg`：相应网格 UV 边界所覆盖的主图窗口，窗口矩形含模型范围外部分纹素时不视作该模型实际使用。

## 4. Home_Path 是独立薄踏面，不能作为全部土路证据

新版 `scenes/level2.json` 的 `/Home/Home_Path` 明确绑定 `Home_Path:2634` 与 `M_HomeBase:31`。对应路径：

- `exported_all/meshes/Home_Path__sharedassets2.assets_2634.obj`
- `exported_all/materials/M_HomeBase__sharedassets2.assets_31.json`
- `exported_all/textures/T_HomeBase_Albedo__sharedassets2.assets_155.png`
- `exported_all/textures/T_HomeBase_Normal__sharedassets2.assets_304.png`

它有 5,824 顶点、3,840 三角形、单 submesh。只为分析按位置精度 10⁻⁵ m 合并共位顶点，得到 **30 个不相连的实体踏面组件**；每个厚度都约 0.088 m，平面包围宽约 0.372～0.483 m、深约 0.291～0.415 m。整体高程 0.396～0.791 m。没有写回或修改 OBJ。

HomeBase 是建筑共用图集，不能用整图中有木板就断言 Home_Path 是木路。`home_path_uv_albedo_used.png` 与 `home_path_uv_overlay.png` 按实际面 UV 标出使用区，主要为灰色、不规则圆踏面与苔绿斑、短侧面条，可称薄踏石/踏面样本；它不是连续裸土路模型。

材质为 HDRP/Lit，BaseColor 与 Normal 实际有绑定，Mask/Height/Detail 无绑定；`_SurfaceType=0`、`_AlphaCutoffEnable=0`、`_Smoothness≈0.07`、白色乘色。这里只说明这个实例；不能据此要求原作每条土路用独立网格，也不能由它推出视频里黄色门前通路的实现。

## 5. 旧 TownSquare / TownPaths 的边界

11 月 12 日反汇编仍能验证旧 `TownSquare.Field → OnGround → GroundY → IslandTiles.Hit` 的连续贴地铺装，以及单独 `Kerb/Slab` 的立体路沿。旧 `TownPaths.Redraw/Upload`、字段 `mask/wear/sand/sandNormal` 与 `_TownPathRect/_TownPathLook/_TownPathTint` 是另一条路径层证据。

但新版 `declarations.cs.txt`、`ac_classes.txt` 已没有 `TownPaths/TownSquare`；`新旧代码差异明细.md` 第 65～67 行明确记录这一差异并关联本 Demo 的内容范围重组。因此旧方法不可直接冒充 11 月 17 日版所有地面或任一宣传片的实现。也没有找到名为 `LandUse` 的已核实原作材质权重定义。

旧证据本轮仅从 `02-history-materials.zip` 提取 14 份、共 240,840 字节，保存在 `reference_data/`；`extraction_manifest.json` 记录来源成员及 SHA-256。它们与新版数据来源清楚分开。

## 对这一轮修改的直接意义

先用有真实面积与侧面的地形体量、独立走向的坡顶与坡脚、明确的高低通路建立岸地；再将与地形布局相配套的大块岩色/岩面明暗、较小的裂隙细节分开处理。当前仅使用小块重复岩纹不能等同于上述原作分工。具体绘制或建模实现是本项目设计决定，不冒称已经恢复作者工作流。

本轮到此停止技术追查：原始主图和真实几何已经足以纠正制作重点；仍未知的 shader 通道公式不以猜测补全，技术证据也不代表本项目已经获得视觉验收。

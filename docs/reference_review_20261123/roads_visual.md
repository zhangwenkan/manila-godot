# 2026-11-23 原作门前道路与当前黄色地面复核

本次只读核对作者视频帧、既有原生代码研究、当前运行代码与 GLB。没有调用 Blender MCP，没有运行旧建模脚本，没有改动运行资产、材质、光照或镜头。下面的方向是设计判断，不是已实施结果，也不是用户视觉验收。

## 实际看过的图与来源

| 图 | 来源与观察用途 |
| --- | --- |
| [城镇门口与圆亭](images/05_detail_town.jpg) | 作者 Demo 发布片 13.900 秒／帧 417 与 15.133 秒／帧 454 的既有双帧细节图。观察入口支路、共同路口与建筑踏步。 |
| [城镇整体](images/06_town_context_46p8s.jpg) | 作者开发回顾片 46.8 秒／帧 1404。观察主路宽窄、分叉和草地区域。与前图属于同一城镇，不能计作另一独立城镇样本。 |
| [桥头地面](../../demo/tropical_harbor_3d/captures/rock_earth_rebuild_20261121/04_bridge_ground_detail.jpg) | 既有 Day40 片 0.000 秒／帧 0 的桥头裁图。观察木桥接裸土及草边关系。 |
| [当前最终城镇图](../../demo/tropical_harbor_3d/captures/art_20261121_220358_404352/town_civic_street.png) | 11 月 21 日岩土重建最终图。观察礼拜堂、医院、餐厅、酒吧旁的黄色地面。此次没有重新运行游戏截图。 |

前两张旧作者帧在当前工程未解包，从 `F:\马尼拉godot\manila-codex-handoff-20261117-100405\02-history-materials.zip` 中按原字节提取到本目录的 `images/`。ZIP 内原路径分别为 `manila-godot/demo/tropical_harbor_3d/captures/author_videos_20261113/fishstand_demo/05_detail_town.jpg` 与 `.../bush_development/06_town_context_46p8s.jpg`。

SHA-256：

- `05_detail_town.jpg`：`cd63b328e639686c823d5e77497fdaeff24b8ae43594c7f6ac6ef6768fffcbee`。
- `06_town_context_46p8s.jpg`：`adf620d4d53bda9c823b08961a98f4aa635792e347ff8189162652a85f534bfa`。

视频来源、时码与原视频哈希沿用 [作者发布片研究](../reference_review_20261113/author_fishstand_demo.md)、[开发回顾研究](../reference_review_20261113/author_bush_development.md)、[作者视频复核](../reference_review_20261113/author_video_review.md)。这些视频与本机安装 Demo 的版本对应没有被证实。

## 视觉证据与判断边界

| 项目 | 原作图里实际可见 | 当前图的差异／判断 | 尚不能断言 |
| --- | --- | --- | --- |
| 道路连接 | 较宽来路在圆亭附近展开成共同路口，再以较窄支路接木屋门前踏步；桥端直接接宽裸土面。建筑之间保留草地块。 | 当前确实有通路，不能称完全没有路网。但后方浅黄带更像横向窄条，门口、共同院地和主要来路的主次不够清楚。 | 不保证视频中每扇门都完整露出与路的接触点，也不能由几帧还原全城路径图。 |
| 宽度 | 主路、交汇面、短入口有明显宽窄关系；不是沿所有墙脚铺同宽一圈。 | 当前上层窄条的宽度与亮度节奏较相似；酒吧旁通海口则是另一种较大片浅黄面，不能将二者混为一条路。 | 没有从透视截图测量可靠的米制路宽。 |
| 边界 | 草土边清楚、形状不规则，有较大尺度的进退；桥头裸土是相对完整平面，草与花断续停在路边。不是把整块边界大范围糊成黄色雾。 | 当前部分窄路呈亮色带，边界与地形坡度叠合后，局部更像色带而非受踩踏的共同空间。 | 自然边界不等于所有边缘都锯齿、随机微波纹，也不要求统一柔化建筑硬边。 |
| 颜色／表面 | 桥头偏灰褐；城镇土沙地在暖光下呈橙褐。城镇图有方向性波纹，桥头有足迹；旧 `T_TownPath_Albedo` 实际也是黄褐低对比斑块。 | 当前浅黄地面与绿色对比强、部分区域偏平，产生较统一的黄带观感。这是观察判断，不能直接归因为某一张贴图，也不能把问题简化为“原作从来不用黄色”。 | 城镇帧有暖主光、长影与窗灯，不能照取 RGB 当作本项目日间底色，也不能只凭图分离材质和曝光贡献。 |
| 高差／接地 | 桥端接地，门前局部有踏步；圆亭底部是窄环形基座。没有看到整条裸土路像独立厚板架起。 | 当前地形确有高差；需要让道路在可通行坡度、门台和院地之间形成有目的的连接，不能用统一黄色覆盖高差。 | 图不足以证明道路比草地低多少厘米、是否存在路槽，或所有建筑基础的完整剖面。 |
| 网格实现 | 视频只证明外观；旧代码有石铺广场和路径遮罩，新版场景则有独立 `Home_Path` 渲染对象，须分版本解释。 | 当前主要道路已经是共享地形上的材质区域。把它改成独立薄片不是由现有证据推出的必需步骤。 | 不能把视频中的裸土路认定为 `TownSquare.Field`，也不能声称已复原作者每一步制作工艺或全游戏统一使用一种路径方案。 |

## 当前实现：黄色不只来自道路

运行入口 [reference_environment.gd](../../demo/tropical_harbor_3d/environment/reference_environment.gd) 加载 `terrain.glb`，对 `Ref_L24_Landform` 使用 [landform_mass.gdshader](../../demo/tropical_harbor_3d/materials/landform_mass.gdshader)。当前 GLB 的节点为 `C25_ContourBuiltCoast`、网格为 `R27_RockEarthFinal_SharedCoast`。主要道路位于该共享地表，并不是旧版悬浮道路薄片。

shader 把顶点 `COLOR` 作为 `LandUse`：R 为草，G 为岩，B 为路径，A 为土；四通道未分配的余量作为沙滩。权重分别平方后再归一化。对应外观来源必须分开检查：

| 地面类别 | 当前来源 | 对本次问题的意义 |
| --- | --- | --- |
| 路径 | B 通道，`L24_Path.png`，4.8 米三平面采样尺度。 | 改路径贴图只改变有 B 权重的位置，不能自动重建门前路网与宽度。历史纹理生成脚本的基础色是 `ba9f68`，不是最终屏幕颜色。 |
| 坡土 | A 通道，`R27_Earth_Albedo.png` 与高度法线。 | 岩土轮次已换 R27；不应把土坡颜色与道路纹理混记。 |
| 沙滩及低洼通海口 | 未分配权重，shader 中常量 `vec3(0.66, 0.50, 0.285)`，该分支没有颜色纹理采样。 | 部分大片黄色来自沙面。只替换 `L24_Path.png` 不能消除这些区域的统一黄面。 |

[rock21_14_wide_forms.py](../../demo/tropical_harbor_3d/source/rock21_14_wide_forms.py) 的 `inlet` 在低处生成不足 1 的草／土总权重，剩余量由 shader 变为沙；新岩冠以上才显式恢复原有 B 路径权重，建筑基础保护范围又混合保留旧值。因此当前酒吧旁通海口、医院前路与土坡虽然都可能呈黄褐，来源并不相同。脚本只是本次只读核对的历史依据，**不得重新执行**。

[control_20_03_path_topology.py](../../demo/tropical_harbor_3d/source/control_20_03_path_topology.py) 曾把道路左右边界作为约束插入共享地形，标记 `(0, 0, 1, 0)`；其中一段上坡路历史半宽为 0.62 米、末四站为 0.8 米。这不是所有当前道路的宽度，也不保证后续重建完全保留这些值。[地形重设记录](../harbor-landscape-redesign-20261120.md) 已说明旧 12 条叠加通路归档。当前 `town.glb` 的 29 个材质批次与 `coast.glb` 的 12 个批次没有道路材质；建筑台阶、木台等局部构件仍可以独立存在。

## 原作代码究竟证明什么

[既有代码研究](../harbor-style-integration-study.md) 和迁移 ZIP 内 `reference_style_audit_20261112/ground_native_evidence.json` 的方法索引证明以下**旧版本**实现，不能直接覆盖 11 月 17 日新版 Demo 或作者视频：

- `TownSquare.Field` 建立连续铺地网格，经 `OnGround → GroundY` 贴地，UV 按平面位置与 tile 生成；`Kerb → Slab → Quad` 另做有厚度路沿。这是石广场证据。
- `Cell = 0.5` 是网格采样步长，不是可见石砖大小；`lift = 0.02`、`kerbRise = 0.04`、`drape = true` 是构造默认值，不是上述裸土道路的实测高度。
- 另有 `TownPaths.Redraw / Upload` 路径／磨损遮罩逻辑，TerrainEast 有 `_TownPathRect`、`_TownPathLook`、`_TownPathTint` 绑定。不能把独立的路径系统与石广场混为一套几何。
- 视频不足以把每一片裸土准确对应到遮罩、独立网格或 decal；不能声称作者裸土路必须用独立网格，也不能据此将本项目土路全部改为石铺装。

**新版证据另行成立。** `F:\马尼拉godot\马尼拉-精简接续-20261120\reference_research\update_2026-11-17\新旧代码差异明细.md` 第 65–67 行列出 `TownPaths`、`TownSquare` 等普通短名已不再存在，结合 `DemoCut` 范围重组理解；本次检索同目录 `declarations.cs.txt` 与 `ac_classes.txt` 也未找到这两项。不能拿旧路径遮罩继续概括新版全部地面。

同目录 `scenes_hierarchy.txt` 第 3846 行明确有 `Home_Path [MeshFilter, MeshRenderer]`，与 `Home_Floor`、`Home_Vines` 等家园构件同组。随后找到完整快照 `F:\钓鱼游戏analysis\update_2026-11-17`，并据场景、网格、材质与 UV 进一步核实：**这个名字不能当成连续土路的证据，它是薄实体踏面组成的另一类路径。** 具体见下一节。新版家园对象、旧城镇类与作者视频画面三类证据须保持区分。

## 补充：实际纹理与新版 Home_Path 的证据

除前述四张场景图，本次另外实际看了以下三张表面证据：

1. [旧城镇路径颜色图](F:/钓鱼游戏analysis/exported_all/textures/T_TownPath_Albedo_137.png)。实际是黄褐色、低对比细斑块，未见该图本身画出道路边界或石板缝。它足以纠正“原作土路底色一定更灰”的过度判断；但仅看此图也不能认定城镇视频每一处路都直接由它呈现。
2. [新版 HomeBase 完整图集缩略](images/HomeBase_full_1024.jpg)。原图 `T_HomeBase_Albedo__sharedassets2.assets_155.png` 为 4096²，缩略仅用于查看，未改原图。图集同时包含长板面、不规则圆踏面、短侧边和苔绿斑，服务多个 Home 构件。不能把整张图里有木板，推成 `Home_Path` 就是木路。
3. [Home_Path 实际 UV 使用区](../../demo/tropical_harbor_3d/captures/fish_rock_road_study_20261123/reference_data/home_path_uv_albedo_used.png)。只保留该网格覆盖的纹理区域，实际可见灰色不规则圆踏面、局部苔绿与短侧面条；不是长木板面，也不是黄褐连续土面。外观更符合踏石路径；“石”是表面外观判断，薄实体的数量与厚度则有几何证据。

完整快照 `scenes/level2.json` 把 `/Home/Home_Path` 绑定到 mesh `2634`、材质 `M_HomeBase` `31`。材质 JSON 为 `exported_all/materials/M_HomeBase__sharedassets2.assets_31.json`：`HDRP/Lit`，颜色图 `155`、法线图 `304`（2048²），不透明且未启用 Alpha Cutoff；没有 Mask／Height／Detail 贴图绑定。

实际 OBJ `exported_all/meshes/Home_Path__sharedassets2.assets_2634.obj` 为 5,824 顶点／3,840 三角面。运行证据子任务只为分析按 1e-5 精度归并同位置顶点后，得到 30 个连通组件，各组件 Y 厚度约 0.088；X 尺寸约 0.372–0.483、Z 尺寸约 0.291–0.415，数值为模型坐标单位。没有将这项分析写回网格。

以上绑定与几何复核集中保存在 [current_snapshot_evidence.json](../../demo/tropical_harbor_3d/captures/fish_rock_road_study_20261123/reference_data/current_snapshot_evidence.json)。它补证新版确实存在独立实体踏面，并不证明作者视频裸土路使用同一种方法，也不要求本项目所有门前土路都换成 30 块踏石。

## 建议的下一步设计

先按门口、踏步、共同院地、桥头与作业区确认人实际要走的线，画出一条主来路、几处扩大的交汇面及较窄门前支路，再设计草地保留区域。宽度变化应来自转弯、停留、会合和入口，不是沿每栋建筑复制同宽色条。

随后分别处理路径、坡土与沙口：路径需要与院地共享使用逻辑；沙口需要有可信的海滩向内陆过渡；坡土需要服从实际坡面。保持可读的草土边界和较完整土面，局部放入磨损与足迹方向；不要用大片混色、随机碎边或覆盖道路的植被代替空间设计。

继续使用共享地形可以满足这些目标。是否另做网格应由厚度、台阶、排水沟或明确硬质铺装等造型需要决定，不应仅因当前黄带不好看就推断其技术结构必然错误。以正常游戏机位看门口连通、主次和大色块，再用局部图检查接地；技术完整性仍不等于视觉成功。

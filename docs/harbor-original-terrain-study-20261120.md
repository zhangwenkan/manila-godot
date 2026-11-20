# 原作岸坡与高差：纠正地形设计方向 · 2026-11-20

用户再次否定 `harbor_landscape_redesign_mcp.blend` 的实机结果：土坡像干画笔刷出的几道色带，连地形形状都没有建立，要求回看《I Just Wanted to Fish》的岸边山坡与高差做法。此前“重建完成”“连通性通过”不代表形体方向成立。本轮回查真实录像、作者发布片及已安装 Demo 网格；只新增研究图和记录，没有继续修改运行资产。

## 实景里有什么

原作实录20秒沙湾有清楚的 **上层草地—岩岸立面—低处草带—沙滩**。顶边和脚线有各自的前凸、后退和转角；低处草带宽度变化，草沙边界另有走向。它们共同构成完整高地，沿岸没有统一同高同宽的棕色坡带。

作者发布片10.167秒的瀑布，更清楚地显示了宽高台、被水切开的凹口、向前突出的两侧岩脊、低处水潭和站人的岩台。体块的顶面、侧面与遮挡关系在纹理之前成立。Day40桥头则采用较低土岸与裸土通路，两侧另有高岩体；不能把所有岸段都设计成同一种高墙。

实景图与观察：[岸崖](../demo/tropical_harbor_3d/captures/fish_terrain_study_20261120/visual_review/reference_coastal_cliff.jpg)、[瀑布](../demo/tropical_harbor_3d/captures/fish_terrain_study_20261120/visual_review/reference_waterfall_landform.jpg)、[桥头](../demo/tropical_harbor_3d/captures/fish_terrain_study_20261120/visual_review/reference_river_ground.jpg)、[逐项观察及来源](../demo/tropical_harbor_3d/captures/fish_terrain_study_20261120/visual_review/findings.md)。图像只做裁剪、缩小和标题标注。作者宣传片与本机地图具体位置尚未对应。

## 已核实的实际网格

本机 `analysis/update_2026-11-17/scenes/level2.json` 中，`/Environment/Island Terrain/East` 和 `/Hill` 对象绑定 MeshFilter、MeshRenderer、MeshCollider；所查对象与父链均为零位移、单位旋转和单位缩放。

| 所查原网格 | 可以直接证明的形体 |
| --- | --- |
| `East_7_4_Demo__sharedassets2.assets_1907.obj`、`East_7_5__sharedassets2.assets_650.obj` | 相邻岸坡片，具有低岸、陡折面与宽高地，整体高程约−2.07～3.61m |
| `Hill_6_1_Demo__sharedassets2.assets_1910.obj`、`Hill_6_2_Demo__sharedassets2.assets_1911.obj` | 内陆山坡片，高程约3.12～6.20m；平缓面、凹口与陡折面并存 |

在 `East_7_5` 的同一 X=−54 剖面上，Z=−26 时高0.292m，Z=−24时高2.819m，Z=−22时高3.142m；随后高地仍缓慢起伏。约2.5m的落差确实存在于顶点中。坡面从近水平到陡直都有，不能由一种坡度重复铺满沿岸。

已生成[无贴图网格与真实剖面图](../demo/tropical_harbor_3d/captures/fish_terrain_study_20261120/reference_mesh_and_section.png)。这只是读取原 OBJ 的研究绘图，没有将原作模型或纹理导入本项目。灰色照明来自绘图器，非原作游戏渲染，未添加或夸张高度；不声称这两片网格就是20秒画面的确切位置。

具体场景绑定、父链、网格统计和原生调用证据：[original_mesh_evidence.json](../demo/tropical_harbor_3d/captures/fish_terrain_research_20261120/original_mesh_evidence.json)。

## 制作机制的证据边界

`IslandTiles.Find` 寻找已有场景对象并读取 Collider bounds，`Hit` 对 Collider 做射线。`IslandGrid.Load` 读取 TextAsset.bytes，`Height/Normal` 查询保存的高度；IGRD记录为811×621、0.5m步长、毫米高度编码。这是地面查询数据与碰撞接口，**不能据此推断它负责实时创建渲染山坡**。

旧《Godot4-地形植被与风动》把查询缓存与建模生成流程合并概括，不能继续拿它作为当前“按横断面挤出就等于原作地形”的依据。程序制作名单已确认使用 Unity、Blender 和 Blender MCP；但具体岸坡所用的雕刻笔刷、修改器或生成脚本仍未找到。岩面裂纹哪些由几何、贴图或法线承担，也不能逐条由截图断定。

## 当前实现为什么不对

`redesign_20_01_land.py` 仍以一套横断面沿岸展开，`redesign_20_03_contours.py` 只是小幅摆动轮廓。连续网格解决了连通性，却没有设计山体的大轮廓。基本平行的坡顶／坡脚／材质边界与宽混色，共同造成画笔带观感。继续加草、波纹、颗粒或改土色，都无法补出缺失的宽台地、前凸岸头、内凹谷口与转向侧面。

新的形体设计应先划出有面积和体积的高地：前凸的岸头、退后的湾口、容纳建筑的宽台地，以及绕行升高的通路；各段具有不同断面和终止关系。较高落差以有侧向转折的土石体成立，低岸自然接沙。先用无贴图单色模型在正常机位和侧面检查轮廓、遮挡与行走关系，再安排草／裸土／岩及纹理。不得把“换新源”“网格连通”“没有裂口”继续当作形体设计已成功。


## 按用户要求继续核对上层源码目录

用户明确目录为 `D:/steam/steamapps/common/I Just Wanted to Fish Demo/analysis`，并要求无源码时查上层。已递归核对完整游戏目录及数据目录；排除analysis后共有34个发布文件，内容是EXE、DLL、Unity场景／资源包、IL2CPP元数据及配置，没有`.cs`、`.blend`、`.fbx`、`.unity`、`.meta`、`.shadergraph`、`.sln`、Unity源工程包或ZIP/7z归档。

- `GameAssembly.dll`：编译后的游戏逻辑。
- `I Just Wanted to Fish_Data/il2cpp_data/Metadata/global-metadata.dat`：类型和方法元数据。
- `sharedassets2.assets` / `.resS`：实际模型、材质、贴图等资源。
- 上述四份文件的SHA-256全部与2026-11-17拆解快照一致，当前研究模型确实对应本机当前安装包。

随包原始对话文本 `Derya__sharedassets2.assets_3466.txt` 的注释直接引用 `BlenderSource/Island/PLAN.md`、`BlenderSource/Home/PLAN.md` 和 `Assets/NPC/Scripts/Dialogue.cs`；这提供了作者工程结构线索，但被引用的文件本身没有随此安装目录保留。

进一步核对原生静态初始化代码，已确证 `CreditsScreen.Tools` 数组为 **Unity、Blender、Blender MCP**，不是孤立字符串推测。证据文件为 `analysis/update_2026-11-17/native_asm/CreditsScreen_3509.asm`，`.cctor` 从第1191行开始；RVA `0x6800cd` 建立长度3数组，`0x6800f4 / 0x680112 / 0x680130` 从RIP槽读取编码值 `0xa0004793 / 0xa00011d1 / 0xa00011d3`，v39字符串索引 `9161 / 2280 / 2281` 分别对应三个工具名；`0x680155` 写入静态区 `+0x10`，对应声明中的 `Tools` 字段。这个结果确认作品使用过这些工具，不能进一步断言某一片岸坡的具体笔刷或生成命令。

因此最终地形模型可以直接分析，作者完整建模操作历史在这份本地发布包中没有查到。不能把尚未恢复的制作脚本称为已知，也不能再因缺少操作历史退回只凭截图猜形体。扫描及哈希记录见 `captures/fish_terrain_study_20261120/source_inventory.json`。

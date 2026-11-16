# 修船厂与海岸风格统一复核 · 2026-11-12

> 2026-11-13 品质目标更新：货仓“还行”不等于最终标准，现有船也仍需消除塑料玩具感；后续以原作多场景为依据，不能向现有货仓品质看齐。见 [最新纠正与开工依据](harbor-quality-reset-20261113.md)。

> 2026-11-13 多图续接：已复核 [旧录像 40 帧](reference_review_20261113/index.md)，并完成 [六段作者视频的三组研究](reference_review_20261113/author_video_review.md)，新增神龛/鱼摊/灌木迭代方法及河岸、瀑布、城镇证据。硬棱、直边和深投影仍可保留；重点转为岸侧通路、局部高差、承重外缘与铁皮细节主次。本轮仍为研究，未修改运行资产。

本轮从会话 `01a1ce3e-4baa-7422-928c-081aea796aa6` 续接。最新要求是保留深灰蓝、做旧和锈迹斑斑，深入研究《I Just Wanted to Fish》的构件、贴图、光照、投影与岸线关系，解释修船厂为什么仍显生硬、不搭。用户已认可厂房与船坞的基本造型；浅色化不是最终方向。

**主要问题是建筑、地面和边缘的处理方式尚未统一。** 当前石坞的铺地、挡墙、压顶具有近似的块体与接缝语言，外轮廓形成连续硬质底座；它又直接接上缺乏局部过渡的沙地。铁皮细密的沟槽、板缝和表面痕迹增加了另一套细节密度。单独改变颜色深浅无法消除这些差异。

本次读取的是用户提供的已安装版本的序列化资源、导出网格/贴图、IL2CPP 元数据和编译后的原生代码，并复看实际游戏画面。它们不是官方完整源工程。下文区分已核实机制、画面判断和本项目建议；原作的石广场也不是修船坞，不能照搬其用途和高度。

![当前模型诊断与参考画面](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/style_diagnosis.png)

图上方是中断前保存的本项目截图，未做新建模或调色；下方分别为参考游戏实景和用户概念图。不同机位只用于解释视觉关系，不是同机位质量对比。概念图不能证明参考游戏的技术实现。

## 1. 地面：原作区分了铺装面与立体路沿

这次补读了实际 `GameAssembly.dll`，以 `Assembly-CSharp.dll` 的 6,225 项方法指针表匹配元数据 token，并结合 PE 的 chained unwind 范围反汇编 22 个相关方法。关键证据不再仅是方法名。

| 已核实代码 | 实际行为 | 对本项目的意义 |
| --- | --- | --- |
| `TownSquare.Field` | 在宽、深方向建立相连的网格，逐点调用 `OnGround`，UV 用平面位置除以 `tile`，再写入连续三角形索引 | 大片铺地的砖缝主要由配套颜色/法线贴图表达，不是把每块砖都做成独立厚盒子 |
| `TownSquare.OnGround → GroundY` | 坐标变换后取地面高度，再把结果转回局部坐标；`GroundY` 的 drape 分支调用 `IslandTiles.Hit` | 铺装按所在位置落地，不只是把一个平底台座移动到岸边 |
| `TownSquare.Kerb → Slab → Quad` | 路沿另行分段，采样地面，生成有厚度的石条与倒角面 | 真正改变轮廓的外缘使用几何，面内铺装与轮廓构件分工 |
| `TownPaths.Redraw / Upload` | 另有磨损/路径遮罩生成与上传逻辑；地形 `TerrainEast` 编译绑定含 `_TownPathRect`、`_TownPathLook`、`_TownPathTint` | 地表还有独立的路径处理层，不能把场景融合完全归给建筑本色 |

`Cell = 0.5` 是铺装网格采样步长，不是可见石砖尺寸。`Joint = 0.006`、`Chamfer = 0.015` 是路沿石相关常量；在 `Slab` 实际指令中可见半接缝 `0.003`，以及倒角取 `min(0.015, 0.4 × 半净宽)` 的约束。不能把它们概括为“原作每块砖都是 0.5 米并倒角 1.5 厘米”。

构造函数默认 `lift = 0.02`、`kerbRise = 0.04`、`drape = true`，表明这套广场首先是靠地面成立的浅铺装。这是构造默认值，不是对某一截图实时实例数值的读取，也不是要求把本项目有维修凹槽的船坞削平。

当前保存的 Blender MCP 只读审计显示：

- 346 个石构件均使用 `0.013`、1 段倒角。**已经有倒角**，不能再以“没有倒角”解释全部问题。
- 其中两侧 terrace paving 为 88 块，80 块约 `0.61 × 0.75 × 0.18`，8 块约 `0.61 × 0.44 × 0.18`。
- 对这组铺地的相邻包围盒复核，146 个有效相邻间距均约 `0.02`。实际空隙加两侧倒角和阴影，会形成比空隙更宽的可见分隔。
- 顶面铺装、挡墙和外露压顶都呈现稳定、重复的厚块体。截图中，长直外缘及侧后方与沙地的连续高差，比石面微小颗粒更影响“摆件感”。

原作 `T_SquareSetts_Albedo` 本身也有规则砖列。因此无需把所有石块随机打乱。应保留可用的施工秩序，让**铺地薄、承重处厚、外缘有转折、落地处有过渡**。

证据：[原生代码方法索引](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/ground_native_evidence.json)、[Field](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/TownSquare_Field.native.asm.txt)、[Slab](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/TownSquare_Slab.native.asm.txt)、[GroundY](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/TownSquare_GroundY.native.asm.txt)、[本项目石材统计](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/research_summary.json)。

## 2. 线条：描边有选择，柔和不等于模糊

小屋和码头的可见材质实际使用 `HDRP/Lit`，不是靠简单两段明暗着色完成全部风格。`level1` 的全屏 Custom Pass 绑定 `M_InkOutline → FullScreen/BeachInkOutline`；中断前已成功反汇编其片元程序，本轮重新核对了参数槽与混合状态。

其可读逻辑为：

1. 从深度与法线缓冲取中心、左右和上下邻点，跳过背景及超过最大距离的像素。
2. 用深度的二阶差异和法线方向差异找边。深度不是只比较相邻像素是否不同；法线也有门槛，细小凹凸不会自动全部变成线。
3. 根据粗糙度标记跳过或减弱某些边。中心或邻点接近 `_CharRoughness = 0.667` 时直接跳过；两侧接近全粗糙且深度接近时，抑制内部边缘变化。字段名提示作者意图，但不能据此断言每个角色/叶片在运行时都被正确标记。
4. 中心粗糙度接近 `_SoftRoughness = 0.93` 时，线条强度乘 `_SoftInk = 0.5`。小屋/码头 smoothness 为 `0.07`，与这个软线标记相对应。
5. 输出 `lerp(白色, OutlineColor, 边强度)`，再与已有画面作乘法混合。第 0 渲染目标为 `SrcBlend = DstColor`、`DstBlend = Zero`。

关键参数为描边色 `(0.20, 0.27, 0.30)`、Opacity `0.85`、DepthThreshold `0.6`、NormalThreshold `0.5`。`Thickness = 1.5` 还经过屏幕高度换算并受至少一个采样像素限制，不能直接叫“固定 1.5 像素线”。这些参数是已保存材质值，不保证任意游戏帧都没有覆盖。

**SoftInk 在这里降低线的强度，并不进行图像模糊。** 因而可以保留清楚的轮廓，同时减少黑硬感。深灰蓝屋顶不必变浅：较完整的亮暗面、保有颜色的暗部、适当的边线强度，可以让深色成立。

本项目如果以后试做这种边缘处理，应把软线/不描边的用途设计清楚，避免所有石缝、压型沟和道具细节同时加重。也不宜让本来用于反射的 roughness 变成难维护的隐藏开关；Godot 中可使用明确的材质分类或遮罩。描边仍不能补出缺失的岸边高差和贴地关系。

证据：[着色器反汇编](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/outline_p0_s0_1.asm.txt)、[绑定与混合状态](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/outline_bindings_and_state.json)。

## 3. 材质：大面、接缝、磨损与微凹凸分工

| 原作材质 | Shader | Smoothness | 已绑定表面图 |
| --- | --- | ---: | --- |
| `M_Hut` / `M_HutDock` | HDRP/Lit | 0.07 | Albedo + Normal |
| `M_Rock_Slab` | HDRP/Lit | 0.12 | Albedo + Normal |
| `M_SquareSetts` / `M_SquareKerb` | HDRP/Lit | 0.20 | Albedo + Normal |

这几种材质没有独立 Mask/AO 贴图绑定。地形则不同：`M_TerrainTown_Demo` 使用 `Shader Graphs/TerrainEast`，绑定 Albedo、Normal、Mask 和 RockDetail。不能把建筑的材质结论扩展为全游戏所有表面。

之前的无光照取证投影已显示，小屋的梁板分工、接缝和板内明暗在仅使用 Albedo 时仍可见；实际实景再叠加几何法线、法线贴图、照明与选择性描边。现有证据不能确定每一处颜色明暗究竟出自手绘还是烘焙，也不能把带通道打包的原作 Normal 当普通 RGB 图直接评价。

对应当前铁皮，深灰蓝、旧漆、赭红锈层与少量裸钢仍应保留。需要重新组织的是信息层次：

- 整片屋面、墙面先形成可读的深色块面；檐口、山墙、天窗边框明确构造。
- 压型沟提供较小的连续节奏，板材搭接提供较大的分区；两种线不应同样突出。
- 锈层沿积水、搭接、螺钉、下缘和合理破漆位置发展，并保留成片旧漆。“锈迹斑斑”可以覆盖明显面积，不必转成满面均匀小斑或每块相同的圆块。
- 颜色变化、凹凸和反射变化各有尺度。大锈色块不应自动成为鼓起的浮雕；裸钢、残漆、氧化层需要保留反射差异，不能整栋变成同一种哑光材料。
- 布、木、石、铁共用同一环境和观察距离，但不应共享完全相同的纹理频率与高光响应。

参考游戏没有提供这座工业铁皮厂房的同类资产。本段铁皮方案是依据已核实机制作出的设计判断，不是声称找到了原作铁皮的完整配方。

## 4. 光影：不能把存在组件当成运行已启用

对 `BeachVolumeProfile` 的原始记录按字段布局解码，并检查参数 override 与记录长度：

| 组件/参数 | 保存值 | 解释边界 |
| --- | --- | --- |
| Tonemapping | Neutral | 枚举已与元数据默认值核对；不是此前假设的 ACES |
| ColorAdjustments | exposure 0、contrast 10、saturation 0、hue 0、白色 filter | 不支持“主要靠全场提亮、降饱和得到风格”的推断 |
| ShadowsMidtonesHighlights | shadows 约 `(0.96, 1, 1.05, 0)` | 有轻微冷暗部设置，中间调与亮部为中性保存值 |
| SSAO | 组件 active = false | 内部虽然仍存 intensity 1.2 等数值，这些不能作为它已生效的证据 |
| ContactShadows | 组件 active = true，但 enable = false | 同样不能用保存的 length/opacity 宣称已启用 |
| IndirectLightingController | 多个 multiplier = 1 | 基础配置，不是游戏截图实际环境填充的完整答案 |

`DayNight` 的原生 `EnsureVolume / ApplyVolume` 确有运行时配置路径；因此这份静态 Volume 不能代表一天中每一帧、每一画质档位。原作相关 renderer 投射并接收阴影，没有对应的烘焙 lightmap 绑定；不能由静态 SSAO 关闭推断“没有任何接触明暗”。

当前项目使用固定白天、ACES、环境光 0.42、SSAO 半径 0.45/强度 0.85、方向光阴影。这些差异值得进行受控画面对比，但不能把 Unity 的 Neutral 编号、lux 或 AO 数值直接搬给 Godot。

下一轮光影关注三件事：深色铁皮的暗面仍可读、承托和檐下投影有体积、砂地与石台的接触不过黑。保持日光方向、机位和屏幕覆盖，先核查接缝几何与法线，再逐项比较填充、AO、色调映射及有限边缘处理。不要通过全场提亮掩盖局部问题。

证据：[解码后的参数](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/decoded_render_settings.json)、[原始序列化探针](../demo/tropical_harbor_3d/captures/reference_style_audit_20261112/serialized_probe.json)、[当前环境代码](../demo/tropical_harbor_3d/environment/harbor_environment.gd)。

## 5. 适用于现有修船厂的落地顺序

保留 B 厂房 + A 石坞/维修船/石阶的主轮廓，保留深灰蓝旧铁皮方向。第一处样区选**右侧前沿石台—铺地—侧面沙地—厂房墙脚**：同一处能够检验用户指出的生硬边缘、接缝、投影与环境不搭。

| 顺序 | 具体处理 | 观察到什么才算方向成立 |
| --- | --- | --- |
| 1. 石坞角色与落地 | 保留凹槽净空和承重挡墙；减弱顶面铺地的厚盒感；压顶与外缘少量有设计的转折/磨耗；侧后方用贴地作业地、沙土压边与有限植物衔接 | 从航行机位看，石坞成为岸边的一部分，通道和维修用途仍清楚 |
| 2. 铁皮的主次 | 在深灰蓝和明显锈蚀下，分开大板面、搭接、压型沟、紧固件、漆层/锈层/裸钢 | 缩小先看到厂房结构，靠近再看到旧铁表面；不出现满面细线和圆斑 |
| 3. 明暗与线条 | 同机位分别比较现有光照、适当的暗部填充与有限有色边线；保持主投影，控制接缝/AO/描边叠加 | 深色不堵死，边缘清楚但没有统一黑硬框；既有船桥也协调 |
| 4. 推广并验证 | 样区方向成立后推广到本件石木布铁，唯一主场景下检查整体、低角度、道具、侧背面，再跑相关三船同步航行与 A/B/C 到港回归 | 画面与运行均有证据，技术通过仍不冒充用户视觉认可 |

自然过渡必须有用途：门前出入、工具搬运、岸边压土或稀疏生长。不要沿石台均匀摆一圈植物遮住问题，也不要把工作台、船托和航道挤满。当前周围树房仍为占位，对整体协调有影响；这不等于本轮自动获得其他建筑精修授权。

所有后续几何、UV、Blender 材质/贴图操作仍须经过本项目独立 Blender MCP。允许 MCP 的 `execute_blender_code`；不得把本次参考中的运行时造网格方法搬成 Godot 建模捷径。研究方法与本项目制作工具约束是两回事。

## 6. 保存状态与研究复现

本轮新增的是研究证据、只读分析工具、诊断图与文档，未按新结论改动运行模型、纹理、灯光或相机。当前默认 GLB 仍是中断前已保存的浅灰蓝试版，25 网格/材质、257,455 三角面；深灰蓝与新的岸边处理尚未落实，也未获得视觉验收。

上个会话已经完成但来不及写入主文档的状态，经本轮读取现存记录核实如下：

- `captures/art_20261112_135029_417323/`：12 张同机位图、424 项专项检查；geometry/UV/normals/transforms 审计与修改前一致，21 张新风格纹理有源 PNG 与 GLB 内嵌字节核对。
- `captures/art_20261112_135541_914695/`：18 张局部航行图、16,767 项检查，日志记录限时预览退出。它是旧会话的运行证据，本轮没有重复跑游戏。
- 用户随后认为提亮版改善了部分问题，但仍不搭，并明确要求保留深色旧铁皮、深入研究整体风格。上列技术检查不能推翻该反馈。

研究目录：`demo/tropical_harbor_3d/captures/reference_style_audit_20261112/`。其中 `research_summary.json` 保存选定材质、石材间距统计和 DLL/元数据/本项目源文件哈希；`annotation_manifest.json` 保存图像来源与处理方式。所有图仅缩放排版并标注，没有调色、锐化、补画模型或伪装成新的实机结果。

可复用工具：

- `tools/inspect_reference_ground_code.py`：只读 DLL/元数据，匹配方法 token，处理 chained unwind，保存原生反汇编。未执行原生代码。
- `tools/probe_reference_metadata.py`：修正紧凑字段记录的读取，type index 为 16 位、后随 32 位 token；此前错误的 32 位 type index 已更正。字段名与常量的既有证据未依赖错误值。
- `tools/summarize_reference_style.py`：读取既有证据及截图，生成紧凑统计和诊断图，不创建/修改三维模型。

此前报告的两条限制现已更新：描边的逐像素逻辑已部分恢复并核对混合状态；Volume 的若干 active/enable/override 已解码。仍未读取特定参考视频帧的完整运行时渲染状态，不能承诺复制一组参数就能复制原作画面。

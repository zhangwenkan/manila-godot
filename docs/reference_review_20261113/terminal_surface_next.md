# 终点码头下一步表面审查

2026-11-13，只读审查。依据终点自身的最新深海军蓝／左长桥记录、现存 GLB JSON、Godot 材质覆盖、保存 MCP 操作及 11-10 最新终点截图；不以货仓作为质量基线。未触碰 Blender、GUI 或共享运行文件。主代理当前修船厂／船木实作尚未纳入本审查。

查看 `terminal_navy_arrival_review_20261110/navy_before_after.jpg`，并把 `art_20261110_142803_514766/` 的 `terminal_05_joinery.png`、`terminal_05b_crane.png`、`terminal_03_low.png`、`terminal_04_back.png` 缩为一张 1280×776 临时板。共两张观察图，未逐张加载原大图。下面是正常构图可见的优先级，不把缩图看不清微纹理说成贴图缺失。暖灰墙、深海军蓝配色、左长桥及三泊位保持。

| 优先级／部位 | 下一步具体动作 | 源对象前缀、材质、导出节点 | 风险 |
| --- | --- | --- | --- |
| 1：A/B/C 前沿工作甲板与入口踏步 | 大甲板仍先读作均匀长平条。先取门前至一席泊位的小段，让宽缓板内风化、踏步前鼻摩擦、端部／系缆处磨损分别成立；长板大面保持连续，承托与外缘更深。不要逐板大幅换色或加密黑线 | `Terminal_Craft` 中 `Terminal deck *` → `HarborCraft_WorkingTimber` → `TerminalMesh_HarborCraft_WorkingTimber`；`Terminal Entry step*` → `HarborCraft_WeatheredTimber` → `TerminalMesh_HarborCraft_WeatheredTimber`。均为 `assets/coast/harbor_terminal.glb` | `terminal_29` 明确甲板与 `crane_wood` 合计 139 件共用 WorkingTimber 图集，不能全材质统一提亮／改纹而带动吊架。踏步材质已在后续风化阶段换掉，不能按初版 deck 材质名找。左长桥另在 `assets/harbor_landing_mcp.glb`，是 `PierWood_Lit`，不能覆盖成终点木材 |
| 2：入口门罩的曲线檐木、门框和柱脚 | 当前外轮廓与梁柱用途已成立，但正常近景仍偏连续整齐。先处理一处“曲线檐木末端—支柱—门框脚”：暴露端面、遮蔽接口、手触／脚触部位各有不同表面；削弱每条长边同样完整的印模感，保留木构直边和受力关系 | `Terminal Entry porch shaped verge*`、`Terminal Porch post*`、`Terminal West entry doorframe*`、必要时 `Terminal Gallery pillar*` → `HarborCraft_WeatheredTimber`；导出 `TerminalMesh_HarborCraft_WeatheredTimber`，同一 `harbor_terminal.glb` | 此图集也含塔楼角柱、其他檐木及踏步的有限区域，先按对象 UV 定位；曲梁使用弧长映射，不能换成长梁平铺。已有端裂／风化和约毫米级轮廓磨损，不需再整批倒角／加面数。不要把墙面一并弄脏或加黑 |
| 3：门罩／低廊蓝瓦，随后才扩至主塔 | 当前蓝色小方块差异在近景仍可读，先实机核对是否出现逐瓦棋盘感；若有，把相邻瓦的整体色差收拢，让风化集中在露边、搭接和少量矿物斑，保持大片坡面。不是重新换配色，也不是磨圆全部瓦边 | `Terminal Entry porch slate*`、`Terminal Gallery slate*`；其后才是 `Terminal West main roof slate*`、`Terminal West high roof slate*`、`Terminal East roof slate*`。材质 `HarborCraft_Terminal_Slate`，节点 `TerminalMesh_HarborCraft_Terminal_Slate`，同一 GLB | **当前实际内嵌颜色图是 `HarborCraft_NavySlate_albedo`**，法线／粗糙度才是 `HarborCraft_SeaWornSlate_normal/roughness`。改旧 `SeaWornSlate_albedo` 可能没有效果。541 片已有实体薄边、搭接和缺口；不要再全面加几何。第三项应服从新实机结果，不因缩图直接重做屋顶 |

源均为 `source/harbor_coast_mcp.blend` 的 `Terminal_Craft`。上表源对象前缀来自保存的 MCP 调用／日志，尚未重新连 Blender 核对源当前名单；导出节点与材质名则已从当前磁盘 GLB 实读。不要操作导出日志中自动产生的 `.007` 等合并副本后缀。

运行覆盖已核实：`environment/coastal_town.gd:73` 的 `_materials` 保留 `HarborCraft_` 配色与贴图；WeatheredTimber／WorkingTimber specular 分别 0.16／0.20，Slate 0.36，未把这些材质强压 roughness=0.93。GLB 三者粗糙度图都存在且 factor 默认 1，不能把“哑光”简单归因于标量过低。`terminal_life.gd` 只为 Flags／Flame 等另设动态材质；吊物、绳、卷筒、滑轮有 `TerminalRig_*` 节点依赖，若碰到吊架必须保留轴心和命名。

建议先仅处理第 1 项一段甲板＋一个踏步，再同时间／同光照检查近景、船侧低角和原桥接口；第 2 项只取一个连接部位；第 3 项先看本轮实机。现有截图是 11-10 保存证据，不能冒充主代理本轮实作后的终点验收。

# 11 月 23 日岩岸与道路修改：验证准备

本文件只读核对现有入口后编写。没有启动 Godot，没有调用 Blender MCP，没有修改运行资产。实际建模、导出、导入和截图由主代理串行执行。**另一个“孤屿霜尘”项目的 Blender 进程不可触碰**；不按进程名批量关闭，不沿用历史 PID，也不把默认 MCP 会话当成本项目会话。

## 最短本机命令

在 PowerShell 执行；已核实以下 Python 与 Godot 可执行文件存在。桌面 Godot 同名项是目录，必须指定里面的 exe。

```powershell
Set-Location -LiteralPath 'F:\马尼拉godot\manila-godot'
$env:GODOT_EXE = 'C:\Users\derwyn king\Desktop\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64.exe'
& 'D:\Python\python.exe' 'demo/tropical_harbor_3d/tools/capture_art.py' rebuild-shore 1600x900 --background
```

该命令已经依次完成 headless 导入和正常 Windows/Vulkan 后台截图。**无需在它之前重复运行导入。** `capture_art.py` 第 91～96 行为两段进程：导入上限 120 秒、截图上限 110 秒。`capture_process.py` 在独立不可见 Windows desktop 中创建并限时回收它自己启动的子进程，不切换用户桌面，不按名字杀进程。截图阶段不能改为 `--headless`，否则不再是实际渲染截图。

现有模式分别为：

| 命令模式 | 用途与范围 |
| --- | --- |
| `rebuild-shore` | 4 张固定图：`02_town_waterfront`、`03_mid_coast`、`terrace_cross_street`、`shore_grass_bank`。`checks=0`、`screenshots_only=true`，不跑航行与性能。适合先看酒吧—餐厅岩面。 |
| `rebuild-sample` | 按当前代码输出 23 张，包括 `town_civic_street`、`town_market_chapel`、`shared_supply_yard` 等。保留初始构图检查，但在完整航行/玩法/性能前返回。当前四图模式未包含医院/礼拜堂道路视图，道路样段需要这个现成模式或由主代理明确增补定向截图分支。 |
| `rebuild` | 完整新版验证，当前为 33 张；随后运行航道净空、独立航道、镜头路线、三船同步、暂停/反向、到港分配及点选检查，最后取既有 local view 的约 5 秒性能样本。 |

完整命令：

```powershell
& 'D:\Python\python.exe' 'demo/tropical_harbor_3d/tools/capture_art.py' rebuild-sample 1600x900 --background
& 'D:\Python\python.exe' 'demo/tropical_harbor_3d/tools/capture_art.py' rebuild 1600x900 --background
```

按需要依次执行，不要求每次小改都同时跑上述两条。**没有 `full` 参数**；也不要使用旧 `layout`/`preview` 当作默认新基准验证。`--background` 可以放末尾，脚本先移除它，再读取模式与分辨率。分辨率只接受 1600x900 或 2560x1440。

如只想先核对导入而暂不截图，现成等效命令为下式；若紧接着使用 capture_art，它仍会再次导入：

```powershell
& $env:GODOT_EXE --headless --path 'F:\马尼拉godot\manila-godot' --editor --import --quit
```

以上命令是准备说明，本子任务没有执行。

## 每次截图后的最小核对

输出在 `demo/tropical_harbor_3d/captures/art_YYYYMMDD_HHMMSS_microseconds/`。读取 `import.log`、`preview.log` 和 `art_result.json`；确认两个进程退出为 0、没有 `ERROR`/`SCRIPT ERROR`、帧数和模式符合本次目的。脚本将 ERROR 视为失败，但不会自动将 WARNING 视为失败，因此仍应查看新出现的 WARNING。

先实际看同机位的正常整屏，再看样段局部；明确灰墙是否减少、露岩与草冠是否自然转折、门前主路/支路/院地是否连成合理出入关系。几何或截图成功不代表视觉通过。`art_preview.gd:329` 始终设置 `visual_accepted=false`；这也是正确的证据边界。

最终用 `rebuild` 验证本轮导出后的真实场景。性能只和本机相同分辨率/相同测试视图对比；11 月 21 日最终 28.12 ms / p95 29.57 ms 只能作为历史短样本，不是固定性能门槛。

## 当前材质入口与容易漏掉的条件

- 根 `project.godot` 唯一入口为 `demo/tropical_harbor_3d/fleet_harbor.tscn`，`import/blender/enabled=false`，运行只加载 GLB。
- `environment/reference_environment.gd:4` 预载 `materials/landform_mass.gdshader`。`_build_sand()` 加载 `assets/reference/terrain.glb`，只对材质名 **`Ref_L24_Landform`** 的 surface 设置 ShaderMaterial。该历史名字不代表使用被否定的 L24 模型；若导出时改名，应同步检查这段匹配，避免误以为新 shader 已接入。
- 目前草为 `L24_Grass.png`、路为 `L24_Path.png`，土/岩为四张 `R27_*`。`landform_mass.gdshader` 使用顶点 `COLOR`：R 草、G 岩、B 路、A 土，未分配权重为沙地。改纹理绑定时保留颜色数据和明确的线性/颜色空间含义。
- 当前四张 R27 导入有 mipmaps；Albedo `compress/mode=2`，Height `compress/mode=0`。高度是线性数据，不应声明 `source_color`，不应无意套颜色压缩；其导数曾放大量化误差。新的区域图/高度若采用不同布局，取样边界与 repeat/clamp 必须和作者定义一致，不能直接复用旧平铺参数。
- `reference_environment.gd` 同时含光照设置，本轮改材质入口时只审查必要资源/参数段；日光、曝光、环境光、阴影方向和正常镜头保持既有基准，才能比较岩土本身。
- `terrain.glb` 在运行时生成 trimesh 碰撞。地形视觉网格、碰撞和另存高度查询缓存需要对应同一次最终导出。

## 现有导出与高度缓存方法

当前可编辑源为 `demo/tropical_harbor_3d/source/harbor_shore_control_mcp.blend`，地形对象 `C25_ContourBuiltCoast`。只在已核实 PID、完整源路径和端口的独立 Blender MCP 会话内建模、改 UV/材质/贴图和导出。

`source/shore_21_context.py` 只读可查的辅助定义说明：

1. `export_land()` 只选当前地形，使用 GLB、`use_selection=True`、`export_apply=True`、`export_yup=True`、`export_texcoords=True`、`export_normals=True`、`export_materials='EXPORT'`、`export_vertex_color='ACTIVE'`。新区域若采用别的对象，要明确加入本轮导出对象或合入目标地形，不能假设单对象 exporter 会自动包含它。
2. `refresh_height()` 对实际地形 BVH 向下射线。Godot `(x,y,z)` 对应此源 Blender `(x,-z,y)`；采样以 `x=shore(z)+d`，不是直接把 `d` 当世界 x。
3. 当前 JSON 为 `d0=-20,z0=-30,step=.25,columns=281,rows=481`，共 135,161 个有限高度值，按 z 行、d 列顺序排列。当前值域约 −6.99572～7.64143 m。`reference_environment.gd:_sand_height()` 按同一坐标求双线性插值。
4. 地形改后先 `view_layer.update()` 并重建 BVH，再生成高度缓存；不能复用改前 BVH。11 月 21 日最终 `rock21_22_soil_patch.py:54–55` 正是刷新 BVH→高度→GLB→保存源的顺序。
5. 植被/岸石/杂物若实际随地形调整，按集合分别导出 `Reference_Foliage→foliage.glb`、`Reference_Rocks→rocks.glb`、`Reference_Coast→coast.glb`。现有 `export_collection` 辅助从求值后 mesh 复制、按材质合并，源组件保持可编辑；只读提取函数定义可参考，禁止重放包含材质替换等前序动作的整份旧 JSON。

**禁止重放历史一次性建模/接地/逆转脚本**，尤其 rock21 第 12、15、19 步。旧 `rock21_10_core_audit.py` 也固定了 11 月 21 日日志目录、旧 baseline 和边界索引前缀假设，不能直接运行后当作新一轮报告。若复用其检查方法，需换成本轮独立记录、实际修改前快照和适用的索引假设。

地形专项以新增内部开边、非流形、倒面/退化、建筑基础/门口承托、局部道具接地、货轮及航道净空、稀疏高度缓存对照为主。先确保修改真正改善可见结果，再做必要完整回归。

## 本轮前后对照保留清单

`captures/fish_rock_road_study_20261123/runtime_readonly_hashes.json` 已有研究结束时 20 个文件的 SHA-256，可作本轮前候选依据；主代理应在实际改动前确认未发生其他变化并另存本轮 before，不覆盖旧研究记录。仓库已有大量迁机 `.import` 变化和 11 月 21 日未提交资产，不能用“相对 HEAD 有差异”当成本轮修改清单。

**预期保持逐字节一致的 8 个运行 GLB**（均在 `assets/reference/`）：

`town.glb`、`cargo_port.glb`、`boat.glb`、`cargo_ginseng.glb`、`cargo_jade.glb`、`cargo_nutmeg.glb`、`cargo_silk.glb`、`ocean.glb`。

同时保留并对照：`fleet_harbor.tscn`、`fleet_harbor.gd`、`fleet/fleet_camera.gd`、`fleet/harbor_route.gd`、`fleet/fleet_state.gd`、`materials/reference_water.gdshader`、原环境光照段和三船同步/真实 A-B-C 行为。`project.godot` 的现有 4.7 特征与导入设置不回退。

**应备份、可能因本轮授权变化的文件**：当前 `.blend`（本地保留不入 Git）、`terrain.glb`、`shore_relief_height.json`、`landform_mass.gdshader`、`reference_environment.gd`、新旧岩土/道路贴图及对应 `.import`。`coast.glb/foliage.glb/rocks.glb` 只有确实需要重接地或局部调整时才变化，并记录实际涉及集合。

保存修改前/后相同分辨率与机位的图，优先 `02_town_waterfront`、`03_mid_coast`、`terrace_cross_street`、`shore_grass_bank`，道路额外保留 `town_civic_street`、`town_market_chapel`。最终源保存、dirty=false 和本轮独立进程退出只由主代理在实际会话中确认；不影响“孤屿霜尘”的 Blender。

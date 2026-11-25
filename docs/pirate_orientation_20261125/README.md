# 已有海盗岛刚体摆位：本轮辅助文件

这些文件只定义函数，不在导入时操作 Blender。所有实际源读取、快照、变换、导出和审计由本轮拥有者在已核实 PID/端口/源的独立 GUI Blender MCP 中执行。目录名沿用任务开始日期；实际时间以报告为准。

## 入口与边界

- `pirate_orientation25_invariants.py`：`capture_island_local()` 只读返回岛局部数据；真正变换之前，由拥有者把返回值一次写入本轮 `island_local_before.json`。`check_island_local(log_path)` 对照该实际快照，不能重写它。
- `pirate_orientation25_export.py`：`export_pirate_orientation25(expected_pid, expected_port, expected_source, log_path, expected_assembly_world)`。这是旧 definition-only exporter 的专用副本，保留临时网格副本、材质组导出、恢复与单资产替换流程；不调用旧快照、建模、岸石或视觉修正入口。
- `pirate_orientation25_audit.py`：`audit_pirate_orientation25(expected_pid, expected_port, expected_source, log_path, expected_assembly_world, contract_path, maximum_world_x=-10.5)`。局部地形/底裙/接地契约可只读使用上轮 `build.json`，不能重跑生成它的脚本。

模块依赖 `__file__`，用 `importlib.util.spec_from_file_location()` 加载，不要只把源码 `exec` 到缺少文件路径的命名空间。调用顺序为真实快照 → 目标矩阵确定 → 根刚体变换 → 本轮 exporter → 本轮 source audit；之后仍需独立 Godot 回归、视觉检查、保存核对与正常退出。

`expected_assembly_world` 必须是设计所要求的 Blender 空间 4×4 根矩阵。它用来检查执行结果，不能把不确定的当前矩阵读回去当成正确目标。除目标位置/水平朝向外，检查不允许缩放、倾斜、镜像或竖直平移。

## 与旧脚本的关键差异

原 `pirate25_export.py` 针对“新岛”设计：新日志下已有岛 GLB 会被拒绝；把已有岛加进旧对象世界摘要又会错误阻止本次刚体变化。原 audit 同样要求岛使用全新对象。这些入口不能直接用于本轮。

本轮的真实 `before_manifest.json` 仍应记下岛原 GLB 供追溯，但只有其他 15 个 GLB 被锁定不可变。第一次替换仅接受 manifest 中的原岛哈希；同一轮后续导出仅接受本轮已完成导出报告中的哈希。未记录的外部变化仍拒绝。GLB 导出还检查组件合并后网格/三角面/材质/图像数量、打包图字节和材质语义未改变。

非岛对象仍锁定原世界变换、原始顶点/拓扑/UV/材质槽和所属集合。已有岛使用独立局部快照：原始网格、UV、逐面材质、平滑标记、修饰器参数、子物体局部变换/父逆矩阵、层级、集合和可见性保持；岛根只允许整体平移和水平旋转。19 个岛材质的节点输入、连线、图像引用与打包字节另行核对。这不是对材质所有 RNA 属性的完整证明。

## 本轮已发现的读取兼容性

Blender 5.3 的 EnumProperty 没有 `is_array`，现用 `getattr(..., False)`；枚举集合规范化为排序列表。材质连线的 Python 元组在快照 JSON 中会变成列表，现对当前读取结果做同样 JSON 规范化后比较。

在根尚未移动、原始网格/局部变换/材质没有变化时，已实证部分木件的 evaluated 网格摘要不稳定。因此不会把该字节摘要差异冒称真实形状改变：原始数据与修饰器仍精确锁定，evaluated 的计数/UV层名/材质槽保持核对，摘要变化单独记录。对发生摘要变化的对象，当前一次审计连续求值两次，核对坐标有限、数量一致、最大局部位置差不超过 0.00002 米，并记录边界。该数值检查只证明当前连续读取的一致性，不替代缺失的历史 evaluated 坐标快照；原快照未被覆盖。

## 审计分工

源审计的最大 X 检查只是岛边界约束，21 个支撑点只覆盖契约锚点，不等于全道具接地或船体扫掠。三条航线、真实 A/B/C、事件与普通机位、回切、移动后的浅水遮罩，以及完整运行/性能检查由运行侧负责。源与运行检查通过都不表示视觉验收。

所有脚本需要本轮真实快照和会话信息，不应批量重放。`.blend` 源仍只在本地保留。

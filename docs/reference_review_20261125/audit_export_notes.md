# 岩壁与地表续作：只读审计及导出兼容说明

日期：2026-11-25。当前工作目录为 `captures/cliff_contacts_20261125`，独立 GUI 会话身份为 PID9864／9881；身份必须由调用方在每次 MCP 操作中核对。此说明及配套脚本不连接 Blender，不制作、导出或保存模型。

## 已准备的审计输入

`prepare_cliff25_audit.py` 从本轮 `design.json`、`baseline.npz`、`before_manifest.json` 和会话记录生成：

- `audit_spec.json`：15 条路线、22 片平台、15 个路口／42 道门、12 个实际入口；沿用道路横坡12°、纵坡28°、高程误差0.15m，平台坡度12°、高程误差0.12m，以及货轮最低0.77m标准，没有放松原检查。
- `protected_terrain_faces.npz`：本轮基线与全部真实道路矩形、院地多边形及路口多边形相交的7,929个三角面和4,594个顶点。相交计算支持凹多边形，包含跨过轮廓、但顶点不在轮廓内的三角面。
- `audit_preparation.json`：输入哈希、各范围的面数和限制。仅为审计准备，不代表已完成现场审计。

纯结构检查已有全宽0.1m路站和院地／路口网格采样，但并非所有相交三角面的穷举。本轮目标是保持已修路床，故附加整三角面顶点锁定检查，可避免采样遗漏窄三角面或边缘尖坎。保护文件应在改形前使用；不要只锁位于路廓内的顶点。建筑楼板另由原结构审计按9栋真实楼板、当前姿态和地面相对接触核对。

`cliff25_live_audit.py` 只定义 `audit_cliff25`，父代理可经已核对的真实 GUI MCP 执行：

```python
ns = {}
exec(compile(Path('F:/马尼拉godot/manila-godot/docs/reference_review_20261125/cliff25_live_audit.py').read_text(encoding='utf-8'), 'cliff25_live_audit.py', 'exec'), ns)
result = ns['audit_cliff25'](9864, check_export=False)
assert result['technical_pass'] is True
```

新导出后使用 `check_export=True`，将校验实际 GLB 与现场三角面在20μm精度下一致。只有本轮确实审查并授权重导 Town 道具时才传 `allow_town_props=True`；楼板几何和姿态保护仍保留。新审计使用本轮 baseline，不会覆盖旧 `terrain_structure_20261123` 日志。

该包装器会检查设计／基线哈希，并将全宽道路、院地、路口相交面的任一顶点超过20μm变化记为失败。这是当前“路床锁定”的精确检查，不是视觉标准。若之后有明确设计修改需要改路床，应重新审查设计与检查范围，不能只为通过检查重做基线或放宽限制。

## 复用纯导出函数

`source/structure23_export.py` 的 `export_structure23` 可以显式接收本轮 `log_path`，无需执行任何历史制作入口：

```python
export_structure23(
    expected_pid=9864,
    log_path='captures/cliff_contacts_20261125',
    changed_collections=['Reference_Foliage', 'Reference_GroundCover'],
)
```

上例集合名单仅演示接口；实际名单必须对应本轮真实修改。源内网格／材质变化若顶点数、包围盒和矩阵未变，不能依靠自动检测，必须显式列出。地形会与本轮 baseline 做坐标／三角索引比较；若只改地形颜色、UV或材质而几何不变，需要 `force_terrain=True`。

本轮36文件备份已提供需要的 `session_start.json`、`baseline.npz`、`objects_before.json`、`before_manifest.json`。manifest覆盖9个固定GLB（town、cargo_port、boat、四货物、ocean、停用ground_rock）；除非显式声明 `Reference_Town`，Town整组变化会阻止导出。首次完整导出不传 `only_collections`；该参数要求已有本轮成功且已保存的 `export.json`，不能拿上一轮清单冒充。

需特别注意四处旧函数约定：

1. 导出函数仍读取 `captures/rock_path_sample_20261123/foundations.json`，其9栋原楼板与当前源保持一致，允许作为只读保留证据复用。当前变换证据来自本轮 `objects_before.json`。
2. 导出地形时会重写已有 `UVMap`、`RockRegion`、`GroundRegion` 三层映射。若本轮有自定义区域UV，不要写进这些层后期待原值保留；可用独立新层，或针对本轮审查修改导出函数，记录实际约定。
3. 地形材质槽0必须有 Principled BSDF 及名为 `G23_LandUse` 的有效图像节点，Base Color必须恰好一个输入。函数暂把LandUse接到Base Color输出GLB，再恢复原插槽；新预览材质应兼容该过程。
4. 原 `structure23_final_readonly.py` **不可直接当本轮收尾入口**：它硬编码旧LOG、旧props/manual_props闭合、旧预览节点名、旧码头净空路径和允许Town变化。应使用本轮独立审计输入，并另外核对当前源保存、打包图／磁盘纹理、导出／Godot缓存、实际影响物件接地和最终截图时序。

`export_progress.json` 会持续更新；MCP传输超时不代表导出已停止，不可重复发送。成功必须看到 `status=completed`、`source_saved=true`、恢复材质、移除临时导出集合和最终源哈希，并在随后独立MCP调用中确认同一磁盘SHA且 `dirty=false`。首版导出函数内部立即读取dirty=true，随后独立probe同源SHA、dirty=false；应记录两个观察，不推断内部刷新原因，也不为了即时flag重复保存。正常退出后再运行完整Godot截图／航行检查。

## 本轮最终只读入口

`cliff25_support_readonly.py` 定义 `audit_cliff25_support(9864)`。它读取上一轮props/manual JSON仅作为已审查的组合件归属目录，实际位置使用本轮immutable矩阵，比较旧地形和现场地形下的真实最低25mm支撑顶点。它不会执行旧制作脚本或应用旧变换；完整箱／桶／桌椅保持语义组合，悬挂货袋明确排除地面支撑。新恶化支撑、未知受影响对象、缺失地面或取样错误均阻止通过。记录覆盖范围和局限；不能代替视觉复看。

`cliff25_final_readonly.py` 定义 `final_cliff25_readonly(9864)`：执行check_export=True的全结构／全三角面保护，保存final结构报告，核对导出与磁盘源hash、现场clean、恢复的C25岩色／法线预览、9张当前打包图与磁盘一致、9楼板、当前轮8个运行代码文件快照（7原运行文件＋shader）、真实支持组。仅环境绑定与shader有明确允许变更，其余6文件要求一致。输出 `final_readonly.json`；在道具修正和最终保存后执行。

`audit_cliff25_final_runtime.py --capture <完整截图目录> --output <审计JSON>` 在Blender关闭后独立读磁盘；检查9固定GLB、本轮sculpt实际三角面、LandUse量化值、6旧＋3新增贴图及缓存、7运行资产、代码快照与当前独立live报告。新增贴图引用 `runtime_texture_audit.json`，逐项重验源／缓存／shader哈希和导入参数；图更新后必须重跑Godot像素probe及该专项报告。要求同PID／端口、同源hash且clean的正常退出记录，随后33张完整运行图和航行／性能采样；6图零检查预览不能通过。

## 当前证据边界

新 `session_start.json` 记录源SHA为 `791081d9a9b653e63523396c660b636d53c4c191bc1301a2d093044d801973d2`，但其 `dirty` 字段是 **true**。不能写成新会话启动后一直dirty=false；这不影响磁盘源哈希的已核对事实，最终须在实际保存后独立确认干净状态。

本轮manifest包含7个运行文件的真实备份（包括正确的 `environment/reference_environment.gd` 路径），与上一轮缺失快照的证据条件不同。材质绑定与shader属于可能有意修改文件；航线／镜头／状态文件仍应按实际备份保持核对，不可把所有`.gd`统一判成必须不变。

此代理尚未执行现场MCP审计、导出、Godot运行或视觉验收。

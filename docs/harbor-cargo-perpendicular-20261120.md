# 起点货轮垂直海岸、吊机沿岸 · 2026-11-20

> 后续：方向保留，船/吊机结构已按用户新图重做。当前模型与最终图见 [参考结构重建记录](harbor-cargo-reference-structure-20261120.md)；下文为本次方向纠正时的历史快照。

用户指出沿岸横泊货轮挡住后排建筑，认可起点所在航段；进一步明确“吊机平行于海岸线，货轮垂直于海岸线，朝向海洋”。本次只处理这组落位/泊位衔接，其他建筑质量问题等待用户逐个说明。最初整组40°斜转是理解错误，已被撤销，不能当成当前成果或获得认可。

用户同时要求：核对每个建筑时正面观察，尽量不包含旁边建筑。以后以正面单体图为主要判断依据，另留实际场景图核对遮挡，不能用混杂周边建筑的斜侧全景代替单体检查。本次 `port_front_isolated` / `port_vessel_front_isolated` 使用同主场景和日光，暂时隐藏周边美术与三艘玩法船，截图后恢复，再跑航行检查；没有删除周边场景。

## 当前落位与源

独立 Blender MCP 从已保存的 `source/reference_harbor_mcp.blend` 续作；本轮前备份在 `captures/cargo_orientation_20261120/before/`。货轮保持18.65m尺寸，Blender Z单独转-90°，中心 Godot (10.8,0,59.2)，带船楼的一端沿世界-X朝海；吊机仍沿世界Z岸线方向，位置相对上轮平移 (4.37,0,5.2)。没有整体斜转、压缩船型或改相机来冒充转船。

垂直货轮的一端需要岸内水域，建立狭长泊位与两侧薄岸壁、压顶/护舷/系缆柱、端墙及系缆绳。原整块侧向石台54件归档到 `Archive_CargoParallelQuay`，避免石台穿过新船位。地形仅在本泊位改形；水下草面改为沙底，海面shader、日光/曝光保留。船壳628个水下顶点射线检查无相交，最低海床余量约0.639m。原有木码头不相交，未搬动。泊位内一棵棕榈32组件完整移至(13,69)岸地。

`town.glb` 与 `coast.glb` 相对本轮前逐字节一致；其他建筑模型、三船模型、三条物理航线、默认航行镜头和真实A/B/C均未改。变化的运行模型是 `cargo_port.glb`、`terrain.glb`、`foliage.glb`；`.blend`仍只保留本地，MCP JSON是会话依赖的编辑轨迹，不可直接重放。

## 验证与交付

最终 `captures/art_20261120_012148_955854/`：38图、17,942项航行/镜头/点选/到港检查通过，日志无ERROR/SCRIPT ERROR，后台限时退出。原有单体/侧后/整场景图仍作补充，新增的两个正面单体图优先交付。所有12个GLB非空/UV/法线审计通过。源已保存且无未保存改动，本项目独立建模会话正常关闭，其他Blender与原Godot编辑器保留。

轻量图位于 `captures/cargo_orientation_20261120/`：`cargo_front_final.jpg` 是正面原图的明确裁切（无锐化），`cargo_front_full.jpg` 为完整正面，`compare_01_gameplay_initial.jpg` 与 `compare_port_whole.jpg` 为原机位对照。技术记录：`source_final.json`、`perpendicular_clearance_final.json`、`asset_audit.json`、`final_validation.json`。

当前只代表按明确方向完成可评价的落位调整；仍待用户评价，不能把本轮方向纠正写成船/吊机质感全面验收。

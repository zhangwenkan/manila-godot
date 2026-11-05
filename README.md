# 马尼拉港

在 Godot 4.6 中打开本目录的 `project.godot`，按 **F5** 运行。

也可以双击根目录的 `open_godot.bat`，它会打开根工程并选中港口主场景。编辑器窗口标题应显示 `manila-godot`。如果旧的 `Tropical Water Study` 编辑器仍开着，先关闭它；旧窗口会继续按子工程路径重写贴图导入记录。

唯一主场景为 `demo/tropical_harbor_3d/fleet_harbor.tscn`，水、船、正常栈桥、破桥和交互都在此入口。原来的独立水体工程已并入根工程。历史角色和 UI 文件保留为开发资料，不是当前入口。

- 点击船只或顶部货物按钮查看船只，点击空位派遣船员。
- **栈桥 / P** 查看栈桥；**总览 / V** 返回港口；**空格** 暂停；**Esc** 退出。
- `python demo/tropical_harbor_3d/tools/capture_art.py`：从同一主场景生成限时美术截图。
- `python demo/tropical_harbor_3d/tools/capture_fleet.py`：从同一主场景检查已有交互并截图。

运行工具可用 `GODOT_EXE` 指定引擎路径。截图和日志保存在 `demo/tropical_harbor_3d/captures`。美术截图仍需人工验收。

当前船和正常栈桥已更新木纹及材质；破桥保持旧材质供对照。美术参考仍以《I Just Wanted to Fish》为准。

2026-11-05 验证：状态检查 452 项、几何检查 2435 项、实际交互检查 193 项通过。美术截图从默认入口运行，无引擎错误或材质警告。`capture_fleet.py` 的最后一条旧水体逐像素比较仍失败：现有两套 shader 的船边水线及深度采样本就不同；本轮只更新其资源路径，没有修改水体算法。这项失败不计作通过。

# 本机 Blender MCP

2026-11-21 安装并验证。使用原作者发布的 `mcp-for-blender==2.2.8`（原项目名 Blender MCP），主包与全部30个依赖已从 PyPI 重新下载，存放在本目录忽略的 `.packages-online/`。独立 Python 3.11 运行时恢复自完整接续包，MCP及其依赖使用此次联网下载文件重新安装。

- Blender：`D:\blender5.3\blender.exe`，5.3.0。
- 安装目录：`C:\Users\derwyn king\AppData\Local\ManilaBlenderMCP`。
- 插件：`C:\Users\derwyn king\AppData\Roaming\Blender Foundation\Blender\5.3\scripts\addons\blender_mcp.py`，已启用并保存偏好。
- Codex：用户 `config.toml` 中的 `mcp_servers.blender`，stdio入口为安装目录 `venv\Scripts\mcp-for-blender.exe`。配置修改前已保留备份。
- 独立连接：`127.0.0.1:9879`；启动等待120秒，工具等待240秒；遥测关闭。

## 启动项目独立会话

在 PowerShell 运行：

```powershell
& 'F:\马尼拉godot\manila-godot\tools\blender_mcp\start_blender.ps1' -BlendFile 'F:\马尼拉godot\马尼拉-精简接续-20261120\manila-godot\demo\tropical_harbor_3d\source\harbor_shore_control_mcp.blend'
```

脚本隐藏启动独立GUI进程，检查端口占用，返回PID与日志路径；只连接保存的源，不执行建模，不保存源。源仍在接续包内，正式制作前按项目约定恢复工作副本。已启用插件时直接打开普通Blender窗口可能使用插件默认端口9876，项目连接应使用上面的独立启动脚本。每次实际操作前仍须核对PID、文件路径和9879端口。

Codex需要重新加载MCP配置；若当前聊天没有出现Blender工具，重新打开Codex后继续。不要把未在本轮聊天热加载工具误认为安装失败。

## 验证

此次完整stdio测试通过initialize、list_tools（10个工具）、execute_blender_code只读查询：Blender 5.3.0，正确源文件，16,145对象，dirty=false，127.0.0.1:9879。随后通过MCP退出独立进程；未保存模型。源SHA-256为 `4e08d5b7ef91cd56e8bdab5c4add2c81d47cd55ecd3d1a1c6c1a62977c06aec5`。

31个wheel完整性通过CRC，主包SHA-256与PyPI发布记录一致：`43d730537cf9fe2c24edfe3204e399f55ab88f97ce4768c07785624e518d3e88`。`pip check`通过。首次重装后的大场景启动超过原等待时间，已提高启动等待并复测成功。

机器相关日志/报告在`.logs/`，安装文件、日志及缓存不提交Git。沙箱CLI可能以`CodexSandboxOffline`解析用户目录，因此其中直接运行`codex mcp get blender`可能读到另一个用户目录；真实用户环境已经验证配置有效，不应因此删除或重复创建配置。

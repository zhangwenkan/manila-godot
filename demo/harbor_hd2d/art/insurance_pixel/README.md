# 保险码头像素风局部样板

## 当前状态

这是第七轮的**材质与结构局部样板，不是完整保险码头，也尚未替换游戏中的保险公司**。

输入为本机 `C:/Users/51440/Downloads/harbor dock 3d model.glb`。它已通过本地 Blender-MCP 导入独立、锁定选择的 Reference 场景；样板另建硬边分件、UV、像素图集和位图招牌，没有沿用输入模型的网格、4K 纹理或法线贴图。

**视觉核对未完成。** 当前输出图的读取未能提供可靠的目视检查，不能据技术检查声称贴近参考图、已实现 HD-2D 风格或已通过美术验收。为避免继续扩大错误方向，制作停在局部样板阶段。

## 直接查看

在 Godot 编辑器打开 [sample_review.tscn](sample_review.tscn)，按 **F6（运行当前场景）**，不是 F5。

- **原始 GLB**：显示 Downloads 中的完整输入；仅统一尺寸、平移，朝向和原图投影尚未校准。这个按钮依赖上述本机绝对路径。
- **灰模样板**：只查看新样板的局部几何。
- **像素样板**：新绘图集、位图字牌与硬边表面。
- **像素倍率 1× / 2×**：切换 3D 子视口的显示倍率，界面不降分辨率。
- **滚轮**缩放，**按住右键拖动**旋转；**复位视角**恢复默认机位。关闭窗口退出。

三种视图共用一个独立 World3D 与正交相机，切换不改变机位。但完整原模型与局部样板的构图内容不同，**不是已配准的重建前后对比**。

### 最近一次自动预览

[查看六张对照图](../../preview/v7-insurance-pixel/sample-r3/)：

1. [原始输入／默认机位](../../preview/v7-insurance-pixel/sample-r3/01_original_front.png)
2. [局部结构灰模](../../preview/v7-insurance-pixel/sample-r3/02_sample_clay.png)
3. [像素样板 2×](../../preview/v7-insurance-pixel/sample-r3/03_sample_pixel_2x.png)
4. [像素样板 1×](../../preview/v7-insurance-pixel/sample-r3/04_sample_pixel_1x.png)
5. [像素样板／侧面机位](../../preview/v7-insurance-pixel/sample-r3/05_sample_side_2x.png)
6. [原始输入／侧面机位](../../preview/v7-insurance-pixel/sample-r3/06_original_side.png)

图片均为 2048×1152。较早的 `sample/`、`sample-r2/` 保留，未覆盖；第一轮曾在退出时报材质错误，不作为干净运行的验证记录。

## 文件与制作内容

- [可编辑 Blender 源文件](source/insurance_pixel_sample.blend)：一个样板场景，39 个独立网格分件，两张贴图已打包。没有原始高面数 Reference、用户原场景、相机或灯光对象。
- [局部样板 GLB](insurance_pixel_sample.glb)：仅供样板查看，不满足完整 Demo 的六组资产合同。
- [像素图集](source/textures/sample_atlas.png)：512×512，蓝灰墙板、灰褐屋顶、暗红钢架和木板；有限色板、规则板缝、阶梯状磨损块。
- [位图字牌](source/textures/sample_signs.png)：256×64，`INSURANCE CO.` 与 `CARGO CRANE`，自绘 5×7 字形。
- [制作记录](source/sample_build.json)、[导入记录](source/reference_import.json)与本目录下制作脚本保留，`source/.gdignore` 防止 Godot 导入制作源。

当前只做了墙窗切片、山墙与厚屋顶、简化红门架及大三角撑、招牌、两块木平台样板。**完整分级侧翼、门／台阶／雨棚、吊臂／拉索／卷扬／吊钩、码头支桩／杂物与拖船均未完成。**

这批几何由分步 Python 经正在运行的本地 Blender-MCP 创建；纹理由本地 Python/Pillow 绘制。未调用外部模型生成或视觉服务，未上传输入模型、参考图或项目资产。

## 材质及运行差异

- 新硬边分件使用平面法线，roughness=1、metallic=0、specular=0，没有生成模型的法线贴图。
- 图集 UV 密度为 24 texels／模型单位，字牌为完整字串保留独立映射；尚未完成全资产像素轴向、屏幕像素尺度和远景可读性的目视核对。
- Blender 图像节点为 Closest。GLB 内含基础材质和图像，最近邻 sampler；不同 glTF 查看器仍可能使用不同光照或生成 mipmaps，不保证呈现与 Godot 样板相同。
- Godot 样板逐 surface 复制材质后显式设置 nearest／无高光，不改共享材质。PNG 无损导入、关闭 mipmaps，GLB 关闭自动 LOD。
- 光照复用港口 Demo 的环境光／太阳设置，但这里不生成港口、不使用全局效果或新风格 shader。实际游戏远景、吊机观察近景及 minification 表现仍未验证。

运行导出当前为 **4 组网格、464 个三角面、9 个材质、2 张图像**，无相机、动画或骨架。四组为 Office／Roof／Crane／Dock，缺少 Props／Tug。这些数字只记录文件结构，不代表美术质量。

## 已检查与未检查

2026-10-12 的技术检查：

- 另起 Blender 后台进程重开源文件通过：39 个闭合可编辑分件；单分件无退化面／重复面、全为平面法线；两张 packed 最近邻纹理；图集的 354 条检查边符合 24 texels／单位。
- Godot 4.6.1、D3D12／Mobile 实窗预览通过，2.5 秒退出、保存六图，日志无 `ERROR`。经根 Viewport 注入输入检查模型按钮、1×／2×、滚轮、右键拖动、在 GUI 上释放右键及复位。不是人工点击或操作系统级鼠标自动化，也不构成美术验收。
- 第一轮切换／退出时出现 `Parameter "material" is null`。改为缓存三个对照实例并保留动态 GLTFDocument／GLTFState 后，后两次预览日志中均未复现。
- Downloads 原 GLB 的 SHA-256 保持 `b809395557fa853da7ef64f20a267515974bc3e5d58598a8ba64c86f4317a85c`。Blender 原活动场景仍为 Scene、原 Cube 仍被选中，原 Cube／Light／Camera 对象保留。
- 另存源文件时曾出现 Blender 内置笔刷材质路径无法相对化的警告；独立重开与样板材质检查通过，未为了消除此警告改动用户 Blender 偏好或原文件。

尚未检查／完成：参考图投影标志点校准、完整建筑剪影、跨分件非预期穿插、像素纹理视觉质量、原始 GLB 在其他查看器中的基础显示，以及主 Demo 的岗位／水侧／航道净空与整套回归。

**下一阶段须先取得这个样板的风格反馈，再对齐完整大形，扩展建筑、吊机机构和拖船，最后才接入独立 Demo。** 当前 F5 主游戏、正式 UI-05、旧保险资产与第六轮吊机观察功能均未改动；没有提交或推送。

## 限时重跑预览

从项目根目录调用本机 Godot；输出目录必须是一个尚不存在的新目录：

```sh
"C:/Users/51440/Desktop/Godot_v4.6.1-stable_win64.exe" --path . --rendering-method mobile --rendering-driver d3d12 res://demo/harbor_hd2d/art/insurance_pixel/sample_review.tscn -- --capture --output=res://demo/harbor_hd2d/preview/v7-insurance-pixel/sample-new
```

自动模式有 55 秒内部超时并主动退出；本次验证另有 60 秒外部进程超时。源码制作脚本也采用拒绝覆盖策略，不要为了重跑而删除已有成果或重置用户 Blender 场景。

# 程序像素海面

当前主场景已经接入 `PixelOcean`，运行项目即可看到动画。它覆盖背景中的海水，位置在背景之上、三艘船之下。

海水颜色、短线波纹、深水色块、沙滩白沫和水中倒影由 `scene/shader/pixel_ocean.gdshader` 生成。原画提供岸线形状；程序水面不采样原画的海水颜色或水纹。这是原画风格的程序复刻，波纹的位置和形状并非逐像素拷贝。

## 查看和调整

- 运行 `scene/scene_bg.tscn` 查看完整场景。临时隐藏场景树中的 `PixelOcean`，就能对照原图。
- 选择 `PixelOcean`，展开 **Material → Shader Parameters** 调整效果。默认每 2 个世界像素为一格，动画按每秒 12 帧更新纹路。
- `Animation Enabled` 控制动画开关，`Playback Speed` 调整整体速度；打开 `Animate In Editor` 可在编辑器里预览动画。
- 参数 `use_layout = false` 可显示独立生成的矩形海面。应用到其他尺寸时，同时调整 ColorRect 尺寸、`ocean_size` 和深水位置。

| 参数 | 默认值 | 作用 |
| --- | --- | --- |
| `pixel_size` | 2 | 像素颗粒大小 |
| `animation_fps` | 12 | 动画的时间步长 |
| `flow_speed` | 5 | 水平水纹流动速度 |
| `ripple_density` | 0.42 | 短线波纹密度 |
| `ripple_strength` | 0.95 | 短线波纹亮度 |
| `deep_start` | 1064 | 深水色块开始出现的世界 Y 坐标 |
| `deep_transition` | 60 | 深水色块逐渐连成一片的范围 |
| `foam_strength` | 0.72 | 岸边白沫强度 |
| `shadow_strength` | 0.78 | 码头和木桩倒影强度 |
| `grain_strength` | 0.009 | 水色中的细微颗粒 |

`Palette` 分组控制港内、外海、深水、浅滩、波纹和白沫颜色。所有纹路使用水面的局部坐标，镜头平移不会改变纹路所在的位置。计时由 GDScript 驱动，暂停场景树也会暂停水面。

## 岸线数据

`scene/image/ocean_layout.png` 是布局数据，不是海面画稿。四个通道分别存储：

| 通道 | 内容 |
| --- | --- |
| R | 可以覆盖海水的区域 |
| G | 到实体边缘的距离，范围 0–128 像素 |
| B | 到沙滩边缘的距离，范围 0–192 像素 |
| A | 实体轮廓向水中投射的阴影范围 |

保留该纹理的无损导入、关闭 mipmaps、关闭 `Fix Alpha Border`；Alpha 同样是数据，不能做透明边缘修色。着色器使用最近邻采样，以保留岸线轮廓。

如更换原画，可以用下面的工具重新提取布局。脚本的船体排除区域、沙滩区域和码头区域针对当前 6144 × 1152 场景编写，更换岸线构图后需要相应调整。运行游戏不需要 Python。

```powershell
python tools/build_ocean_layout.py
```

生成工具需要 Pillow、NumPy 和 OpenCV。它只输出布局信息，不保存原画的水色或波纹。

## 渲染验证

用真实渲染器运行，不能使用 `--headless`：

```powershell
godot --path . --script res://tools/ocean_visual_check.gd
```

脚本保存原图、程序海面、镜头平移、独立海面和完整游戏截图到 `.godot/ocean_visual_check/`，检查岸上采样像素不变、海面随时间变化、暂停后画面稳定，以及镜头平移前后的像素一致性。加上 `-- --record` 可导出六秒对比用动画帧。

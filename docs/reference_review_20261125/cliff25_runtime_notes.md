# C25区域岩面运行接入 · 2026-11-25

主代理明确授权后，已实际编辑两个运行代码文件：

- `demo/tropical_harbor_3d/materials/landform_mass.gdshader`
- `demo/tropical_harbor_3d/environment/reference_environment.gd`

没有连接Blender或制作贴图，没有运行Godot；本次仅做运行接口，主代理统一导入、编译和实拍。局部接触数据接口尚未修改，等待主代理确定参数。

## 已接入内容

`_bind_cliff_region()` 独立查验并绑定 `C25_CliffRegion_Color.png` 和 `C25_CliffRegion_Height.exr`。它先将 `cliff_region_enabled` 设为false，只有两个资源均存在且加载为Texture2D后才设为true；主表面仍需G23完整集合启用，新增区域才能生效。缺少任一新图会保留原G23表现。

shader采用已确认的两组世界Z/H加X斜项映射，主岩图幅U .02–.66、背岩 .70–.98，V .02–.98。主岩Z21.8–34.3、背岩Z37.4–45.1，X15.7–26；边缘平滑衰减，Z34.3–37.4的上下连接坡不带新增层理。表面角色仍由当前LandUse决定，只改变岩角色。新图每像素增加两次纹理采样，不采用额外三平面采样。

局部岩色完整采用新区域RGB。区域高度范围默认0.16m，原G23岩高场在区域内降到0.020m作微细节，范围外仍保持原0.24m。新增高度先单独求导，再乘区域权重与岩权重；不对区域边缘或地类mask求导，不制造接缝凸线。区域权重为0时，原岩RGB、原高度范围和其余地类计算保持原值。地类竞争、路／草／沙处理、光照、镜头未改变。

shader修改前SHA256：`9769768d1374b993826c0d2cd7a0c5083a57da483a0006d1f824cab33662f7ca`。

修改后SHA256：`92400871d970eea64ca2849b12f6bdbf36036876dbdbeff3d26018857b029695`。

修改前shader完整文本保留于 `landform_mass.cliff25.before.gdshader`。可审查候选与当前接入内容一致；`cliff25_shader_patch.py`本身仍只提供补丁文本生成器，不能作为重复应用入口。`git diff --check`无错误（仅换行提示）。

## 两张图的导入配置建议

以项目已验证的G23颜色图和S23单R float EXR导入配置为依据，不直接复制旧UID或缓存路径。

| 参数 | Color PNG | Height EXR |
| --- | --- | --- |
| shader sampler | `source_color` | 不加`source_color`，R为线性数据 |
| `compress/mode` | 0，保持sRGB像素 | 3，保留未压缩浮点数据 |
| `compress/normal_map` | 2，禁自动法线处理 | 2，禁自动法线处理 |
| `mipmaps/generate` | true | true |
| `process/hdr_as_srgb` | false | false |
| `process/hdr_clamp_exposure` | false | false |
| `process/fix_alpha_border` | false | false |
| `process/premult_alpha` | false | false |
| `process/size_limit` | 0 | 0 |
| `detect_3d/compress_to` | 0 | 0 |
| shader repeat/filter | repeat_disable / linear_mipmap_anisotropic | 同左 |

EXR由Blender保存为单R float数据，RGB色图保存为真正sRGB颜色。Godot导入后需确认EXR缓存仍为浮点而未降8位，并抽样对照源值；颜色图检查缓存RGBA与源值。两张图共同采用PNG首行为高处的图幅方向，UV在shader中作 `1-(.02+.96*v)` 翻转。新`.import`应在实际源图存在并首次导入后设置并重导，避免虚构UID／缓存名。

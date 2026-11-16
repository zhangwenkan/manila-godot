# 现有录像的区域、角度与来源覆盖审计

日期：2026-11-13。范围：本地已有录像抽帧 40 张，加 1 张已存在的 Steam 截图候选文件。只做文件读取、缩小索引与记录；没有启动或控制游戏、浏览器、Blender 或 Godot，没有新拍游戏画面，没有修改模型、材质或运行代码。

本审计按 `$harbor-blender-craft` 的实际图像证据要求执行。**40 帧不等于 40 个参考场景。** 本次可见内容主要是同一连续滨海环境中的 4 个相邻子区域：栈桥及泊船、沙湾与岸上岩台、沿岸沙地通路、渔屋与断桥水道；不能据此声称已经覆盖多张地图、多座房屋或工业港区。区域名称为本审计的画面描述，不是经过游戏源码核实的地名。

## 来源与处理

| 项目 | 核实状态 |
| --- | --- |
| 录像 | `C:/Users/51440/WorkBuddy AI/2026-11-02-00-03-24/forkedpush_2106313584829431901/video/forkedpush_2106313584829431901.mp4` |
| 录像原始信息 | 2560 × 1440，约 59.940 fps，9703 帧，161.878383 秒；取自已有 manifest |
| SHA-256 | `367dc92813e7a942308da030fa4307925e8a3ecf0251b7b45c29b4b94d1d26f6`；本轮后台重新读取源视频计算，与既有 manifest 一致 |
| 抽帧 | 原 manifest 33 帧 + supplement 7 帧，共 40 个不同时间点；本轮没有重新解码/补抽或开启游戏 |
| 本地 Steam 文件 | `C:/Users/51440/Downloads/ss_7433c905e17043cc1f176912b35e27cf1f5101d7.1920x1080.jpg` |
| Steam 来源归属 | 主代理已通过[官方商店 appdetails 接口](https://store.steampowered.com/api/appdetails?appids=5351000&l=english)核实该截图标识属于 Demo app 5351000；本子任务未自行访问接口。**本地 JPEG 与官方原始图片是否字节一致未核验**，拍摄日期、版本和相机参数仍未知 |
| Steam 图的覆盖贡献 | 画面仍为沙湾钓鱼：岸边圆石、沙岸弧线及紫/黄珊瑚组合与录像沙湾一致，未新增城镇、工业区或建筑背面。来源可靠性提升不等于场景覆盖增加 |
| 图像处理 | 仅等比例缩小及 JPEG 编码；无调色、锐化、生成或替换内容。索引每格约 540 × 304，适合区域/构图审计，不足以支持微细贴图结论 |

完整源文件信息、逐 PNG SHA-256、分页槽位和缩图参数保存在 [index_manifest.json](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_manifest.json)。原始帧位于 `demo/tropical_harbor_3d/captures/reference_recording_review_20261112/`；本报告不复制原始模型、纹理或原作资产。

## 实际覆盖和重复

| 子区域/模式 | 帧时间（秒） | 朝向与距离的有效证据 | 重复边界 |
| --- | --- | --- | --- |
| A 栈桥及泊船 | 0、5、134、135、137、140 | 同向纵向俯视，桥端、泊船、渔屋前平台至长桥的过渡 | 开头与结尾回到同一桥；没有桥下低机位或反向观察 |
| B 沙湾与岸上岩台 | 10–100，每 5 秒 | 雕像/岩台前沙地；岸边圆石；钓线朝向水面；水体占比变化 | 20–80 大量围绕同一圆石及珊瑚组合平移/拉开；不能算十余个岛屿或沙湾 |
| B 内角色特写 | 85 | 明显低角度角色和鱼的特写，背景失焦 | 是同湾的捕获展示，不提供平台底部、建筑侧背或完整岸线低角度证据 |
| B 内鱼篓交互 | 95 | 人物与鱼篓近乎顶视 | 相机模式变化不等于新区域；不能用于建筑正面或正常游戏观察距离比较 |
| C 沿岸沙地通路 | 105、110、115 | 水在左、沙地/植被在右，岸线纵向延伸 | 补一个相邻岸段的陆海分配；岸线转向不证明相机围绕环境旋转 |
| D 渔屋与断桥水道 | 120、122、124、125、126、128、130、132 | 屋顶接近 → 渔屋与窄水道、断桥并置 → 山墙正面与平台 | 只见同一渔屋的平移和构图变化，不是 8 座建筑；120/122 屋顶主导且有植被遮挡 |
| N 夜间沙岸 | 145、150、155、160 | 局部灯光和钓鱼动作，其余近黑 | 暗部不足以核实地点；全部排除固定白天材质、环境填充和落地对照 |

计数：**36 帧白天，其中 34 帧环境构图、2 帧角色/交互近景；4 帧夜晚。** 70 秒画面出现 `Noon → Afternoon` 提示，所以“都是白天”也不能当成太阳/曝光完全相同。跨时间取色、阴影深浅及明度变化需保留这一限制。

140 秒为白天，145 秒已为夜景；40 张抽样中没有抽到中间黑场/淡出帧，因此只能标记 **140–145 秒之间存在昼夜/镜头不连续**，不能推断它是自然实时昼夜过渡或确定某一种转场。85/95 秒是特殊镜头，应单列；不能和正常环境镜头混算角度覆盖。没有看到纯黑、无内容的转场专用抽样帧。

## 八个代表样本

这里的“代表”按证据用途选取，**不是八个独立场景**。原帧均已在五张索引中实际查看；下表 960 × 540 的单张 JPEG 是供后续按需打开的缩小副本，本轮没有额外查看。

| 样本/时间 | 区域 | 证据用途 | 与其他选样的区别及限制 |
| --- | --- | --- | --- |
| [representative_005s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_005s.jpg) / `frame_005s.png` / 5s | A 栈桥 | 泊船、纵向桥板、桥下投影、清水中海底物的并置 | 补水上构件组合；137/140 是重复桥段，不另计 |
| [representative_010s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_010s.jpg) / `frame_010s.png` / 10s | B 岸上岩台 | 岩台—沙地—植被、雕像基座落地 | 补岸上分层；仍是同一海岸，不是新地图 |
| [representative_020s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_020s.jpg) / `frame_020s.png` / 20s | B 沙湾 | 圆石、缓沙岸、浪沫与棕榈投影 | 与10相比聚焦硬石/柔沙/水边，不增加沙湾数量 |
| [representative_060s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_060s.jpg) / `frame_060s.png` / 60s | B 沙湾水面 | 水深渐变、海底物、岸线包围与稀疏构图 | 与20相比水体占比增加，提供水下关系；仍同湾 |
| [representative_085s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_085s.jpg) / `frame_085s.png` / 85s | B 角色特写 | 角色/道具低机位、景深、材质大类 | 唯一明显低角度特写模式；不补建筑/桥底低角度缺口，单独研究 |
| [representative_110s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_110s.jpg) / `frame_110s.png` / 110s | C 通路 | 纵向沙岸、人行留白、陆海与植被分配 | 新增相邻岸段组织；非已证实绕岛旋转机位 |
| [representative_124s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_124s.jpg) / `frame_124s.png` / 124s | D 渔屋/水道 | 屋、窄水道、两侧断桥残段及岸端关系 | 补建筑旁基础设施；与132只算同一房屋 |
| [representative_132s.jpg](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/representative_132s.jpg) / `frame_132s.png` / 132s | D 渔屋正面 | 山墙正面、完整屋前平台、入口与成组道具 | 比124更完整地呈现工作面；同建筑同朝向的用途补充，不是新角度全覆盖 |

## 确实还缺的证据

- **建筑侧背面：** 已阅画面主要是渔屋屋顶和山墙正面，缺清楚的背墙、侧檐、隐蔽连接及逆光面。斜俯视看到少量侧面不等于侧背专项检查。
- **环境低角度：** 85 秒只是角色特写；缺船侧正常观察高度、码头承托/桩/平台下方、岸上建筑从海面看的完整关系。不能据此证明现有修船厂低角度已经匹配参考。
- **城镇和连续铺装：** 当前 40 帧及本地 7433c905 图未出现城镇广场、道路、建筑群或铺装与路沿的可检验近景；不能用沙湾素材验证 `TownSquare.Field` 的实际显示效果。
- **工业铁皮和修船厂：** 没有足以核实压型铁皮、泛水/檐口、锈蚀分布、石坞承重外缘、坞底和沙地落差的同类对象。渔屋木作可供构件主次研究，不能直接充当工业材质实证。
- **同物体反向或不同方位：** 已有帧以连续跟随和平移为主，缺同一建筑环绕前/侧/后可配对证据；不能用岸线在屏幕中转向冒充相机绕物旋转。
- **严格同光照对照：** 缺相机参数、太阳方向/高度、曝光与游戏时间记录；本轮索引不能直接推出材质本色、粗糙度值、描边参数或运行时 Volume 开关。

以上缺口只描述本子任务已阅本地集合。主代理另外进行的官方截图审计可以补充或缩小这些缺口，需在它自己的来源记录中说明；本报告不预先把尚未查看的图片计入。

## 低负载索引与复查记录

- [索引 1：0–35s](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_01.jpg)
- [索引 2：40–75s](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_02.jpg)
- [索引 3：80–115s](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_03.jpg)
- [索引 4：120–132s](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_04.jpg)
- [索引 5：134–160s](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/index_05.jpg)
- [本地 Steam 图缩小副本](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/steam_candidate_7433c905.jpg)
- [逐帧 CSV 清单](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/frame_inventory.csv)、[区域/用途 JSON](../../demo/tropical_harbor_3d/captures/reference_review_20261113/reference_coverage/coverage_manifest.json)

本轮实际 `view_image` **6 次**：五张八格索引和一张 Steam 缩图，全部 JPEG；最大长边 1312 像素，总文件载荷 **677,563 字节（约 662 KiB）**。没有直接查看原始 2560 × 1440 PNG，没有额外裁剪复看。图像实际可读性已用于区域、重复和镜头模式判断；细小贴图/模型构件结论留给后续必要的受控局部取样。

交付只包含本报告和 `captures/reference_review_20261113/reference_coverage/` 下索引、缩小代表图及数据。未改共享汇总报告；没有运行游戏测试，因为本轮没有运行内容改动。

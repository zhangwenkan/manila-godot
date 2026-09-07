# 海面重做实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把当前“各归各的”海面效果改成与原画贴合的独立水层动画：静止时不违和，运行时主海域有明显流动，岸边次之。

**架构：** 把现有整张场景底图拆成“静态背景 + 独立水层 + 可选局部强调层”。动画不再采样 `screen_texture`，而是直接对水层纹理做低频位移，并用分区遮罩控制主海域和岸边的强弱。这样能保留原画笔触和色调，只让水面“活起来”。

**技术栈：** Godot 4、`Sprite2D`/`Polygon2D`、canvas_item shader、PNG 纹理资源。

---

## 文件结构

- 创建：`scene/image/scene_bg_base.png`
  - 只保留岸、码头、建筑等静态内容，不包含水面。

- 创建：`scene/image/water_main.png`
  - 独立海面纹理，保留原画里的水色、白沫和笔触。

- 创建：`scene/image/water_mask.png`
  - 灰度强度图，主海域亮、岸边暗，用来控制整体流动强度。

- 创建：`scene/image/water_flash_mask.png`
  - 局部闪动遮罩，只标出主海域中允许更明显流动的区域。

- 修改：`scene/scene_bg.tscn`
  - 把 `Background` 替换为静态底图。
  - 新增水层节点，把水层放在底图之上、船之下。
  - 删除当前依赖 `screen_texture` 的水面 Polygon2D 方案。

- 修改：`scene/shader/water_flow.gdshader`
  - 改成直接采样水层纹理。
  - 使用强度遮罩做分区位移。
  - 使用局部闪动遮罩控制主海域的高频细节。

---

### 任务 1：拆分场景图资源

**文件：**
- 创建：`scene/image/scene_bg_base.png`
- 创建：`scene/image/water_main.png`
- 创建：`scene/image/water_mask.png`
- 创建：`scene/image/water_flash_mask.png`

- [ ] **步骤 1：导出四张分层资源**

导出结果必须满足：
- `scene_bg_base.png` 中不包含任何海面像素。
- `water_main.png` 的透明区域只保留在海面以外。
- `water_mask.png` 为灰度图，主海域比岸边更亮。
- `water_flash_mask.png` 只覆盖主海域中希望更活跃的局部区域。

- [ ] **步骤 2：把四张资源放进项目并确认文件名**

检查以下文件存在：
```text
scene/image/scene_bg_base.png
scene/image/water_main.png
scene/image/water_mask.png
scene/image/water_flash_mask.png
```

- [ ] **步骤 3：人工确认切图边界**

打开 `scene/image/scene_bg_base.png` 和 `scene/image/water_main.png`，确认：
- 岸线没有被切进底图水层。
- 水层没有带进岸、船、建筑。
- 主海域遮罩范围足够大，岸边遮罩足够弱。

- [ ] **步骤 4：验证资源可用**

在 Godot 中刷新导入并确认四个资源都能正常加载，没有透明通道或尺寸异常。

---

### 任务 2：重建场景节点结构

**文件：**
- 修改：`scene/scene_bg.tscn`

- [ ] **步骤 1：编写新的场景结构**

把当前结构重排为：
```text
scene
├─ BackgroundBase (Sprite2D)
├─ WaterMain (Sprite2D or Polygon2D)
├─ boat (instance)
└─ CanvasLayer
```

其中：
- `BackgroundBase` 只显示 `scene_bg_base.png`
- `WaterMain` 显示 `water_main.png` 并挂新 shader
- `boat` 保持在水层之上

- [ ] **步骤 2：删除旧的 screen_texture 水面节点**

移除当前这两个节点：
- `WaterFlowBottom`
- `WaterFlowHarbor`

它们不再承担水面动画职责。

- [ ] **步骤 3：验证渲染顺序**

在场景树里确认：
- 底图在最底层
- 水层在底图之上
- 船在水层之上
- UI 仍然在最上层

- [ ] **步骤 4：运行场景确认静止态**

运行 `scene/scene_bg.tscn`，确认静止截图时：
- 画面像一张完整原画
- 没有额外“特效层”感
- 船没有被水层遮住

---

### 任务 3：改造水面 shader

**文件：**
- 修改：`scene/shader/water_flow.gdshader`
- 修改：`scene/scene_bg.tscn`

- [ ] **步骤 1：编写新的失败测试目标**

本项目没有现成自动化测试框架，因此把验证目标写死为可见行为：
- 水层必须随时间变化。
- 主海域位移必须强于岸边。
- 局部闪动只能在遮罩区域内出现。
- 不得再依赖 `screen_texture` 扭曲整屏。

- [ ] **步骤 2：实现最小 shader 改动**

shader 只做三件事：
1. 采样 `water_main.png`
2. 根据 `water_mask.png` 做低频整体位移
3. 根据 `water_flash_mask.png` 在局部增加轻微闪动

- [ ] **步骤 3：把参数回写到场景文件**

在 `scene_bg.tscn` 中设置 shader 参数，确保默认值偏保守：
```text
flow_speed
base_distortion
mask_strength
flash_strength
```

- [ ] **步骤 4：运行场景确认动态态**

运行场景并检查：
- 主海域有明显但不夸张的流动
- 岸边有较弱动感
- 局部闪动只出现在主海域
- 画面不会再像“另外贴了一层特效”

- [ ] **步骤 5：微调一次参数并复测**

如果动态太弱，优先只调：
- `base_distortion`
- `mask_strength`
- `flash_strength`

不要同时改多个结构性参数。

---

### 任务 4：最终视觉验收

**文件：**
- 无新增文件
- 复查：`scene/scene_bg.tscn`
- 复查：`scene/shader/water_flow.gdshader`

- [ ] **步骤 1：检查静止截图**

暂停或截帧，确认整体仍然像原画，不存在明显的分层断裂。

- [ ] **步骤 2：检查运行效果**

观察 10–15 秒，确认：
- 主海域持续有生命感
- 岸边是辅助动感
- 船周围没有喧宾夺主的闪烁

- [ ] **步骤 3：记录最终参数**

把最终可接受参数保留在 `scene_bg.tscn`，不再额外添加调试层。

---

## 自检

### 1. 规格覆盖度
- 原画拆分：覆盖于任务 1。
- 场景结构重排：覆盖于任务 2。
- shader 改造：覆盖于任务 3。
- 最终视觉确认：覆盖于任务 4。

### 2. 占位符扫描
- 未使用“待定”“TODO”“后续实现”等占位语。
- 所有步骤都包含明确文件和可执行检查。

### 3. 类型一致性
- 场景节点名统一为 `BackgroundBase`、`WaterMain`、`boat`。
- shader 参数名统一为 `flow_speed`、`base_distortion`、`mask_strength`、`flash_strength`。
- 任务间未引入未定义的函数或类型。

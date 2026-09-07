# worker_blue 上船实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 `worker_blue` 图片作为缩小的 `Sprite2D` 放入 `boat.tscn` 的船甲板区域。

**架构：** 只修改船本体场景 `boat/boat.tscn`。新增一个外部纹理资源 `res://worker/worker_blue.png`，并在船根节点下新增 `WorkerBlue` 子 `Sprite2D`；不修改脚本、不新增行为、不创建独立 worker 场景。

**技术栈：** Godot 4 `.tscn` 场景文件、`Sprite2D`、`Texture2D` 外部资源。

---

## 文件结构

- 修改：`boat/boat.tscn` — 船的可复用场景；新增 worker_blue 纹理资源和 `WorkerBlue` 精灵节点。

### 任务 1：把 worker_blue 加到 boat.tscn

**文件：**
- 修改：`boat/boat.tscn`

- [ ] **步骤 1：记录当前场景结构**

读取 `boat/boat.tscn`，确认当前内容包含船脚本资源、船贴图资源、根节点和船 `Sprite2D`：

```ini
[gd_scene format=3 uid="uid://cemyiwo12jg67"]

[ext_resource type="Script" uid="uid://bb6ibce41o4ui" path="res://boat/script/boat.gd" id="1_enlnh"]
[ext_resource type="Texture2D" path="res://boat/boat.png" id="2_f5k8p"]

[node name="boat" type="CharacterBody2D" unique_id=508499015]
script = ExtResource("1_enlnh")

[node name="Sprite2D" type="Sprite2D" parent="." unique_id=1978024710]
position = Vector2(131.7647, 69.99999)
scale = Vector2(0.26, 0.26)
texture = ExtResource("2_f5k8p")
```

- [ ] **步骤 2：添加 worker_blue 外部资源**

在 `boat/boat.tscn` 的现有 `ext_resource` 后添加：

```ini
[ext_resource type="Texture2D" path="res://worker/worker_blue.png" id="3_worker_blue"]
```

- [ ] **步骤 3：添加 WorkerBlue 子节点**

在船 `Sprite2D` 节点后添加：

```ini
[node name="WorkerBlue" type="Sprite2D" parent="."]
position = Vector2(128, 48)
scale = Vector2(0.12, 0.12)
texture = ExtResource("3_worker_blue")
```

位置选择说明：船主图当前位于 `Vector2(131.7647, 69.99999)` 且缩放 `0.26`；`WorkerBlue` 放在相近 X 坐标、略高的 Y 坐标，形成站在船上方/甲板区域的效果。`scale = Vector2(0.12, 0.12)` 用于明显缩小工人，避免覆盖船体。

- [ ] **步骤 4：用 Godot 可读性验证场景格式**

运行：

```bash
godot --headless --path "d:/自己做着玩的/马尼拉godot版/manila-godot" --quit
```

预期：Godot 无 `.tscn` 解析错误并正常退出。

如果本机没有 `godot` 命令，改用 VS Code/Godot 编辑器打开 `boat/boat.tscn` 验证：场景树中应出现 `WorkerBlue`，且 Inspector 中 texture 指向 `res://worker/worker_blue.png`。

- [ ] **步骤 5：视觉验证**

在 Godot 编辑器打开 `boat/boat.tscn`，确认：

```text
boat (CharacterBody2D)
├── Sprite2D      # 原船图
└── WorkerBlue    # 新增 worker_blue 图
```

预期视觉结果：`worker_blue` 已缩小并位于船的甲板区域；如果位置偏离船体，将 `WorkerBlue.position` 小幅调整，优先调整 Y 值，其次调整 X 值。

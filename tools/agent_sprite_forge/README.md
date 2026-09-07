# agent-sprite-forge 项目内工具包

这里是 `0x0funky/agent-sprite-forge` 的项目内副本，用来给当前 Godot 项目生成和后处理 2D 精灵、prop pack、分层地图预览等素材。

## 目录

- `skills/generate2dsprite/`：精灵表、动画帧、透明 PNG/GIF 后处理。
- `skills/generate2dmap/`：地图 prop pack 提取、分层预览合成等后处理。
- `requirements.txt`：Python 依赖，主要是 `numpy` 和 `Pillow`。
- `README.zh-CN.md`：上游中文说明。
- `run_processor.py`：当前项目的轻量入口，默认把输出写到 `generated/agent_sprite_forge/`。

## 安装依赖

建议使用本地虚拟环境，不要装进全局 Python：

```bash
python -m venv tools/agent_sprite_forge/.venv
./tools/agent_sprite_forge/.venv/Scripts/python -m pip install -r tools/agent_sprite_forge/requirements.txt
```

如果不用虚拟环境，也可以直接：

```bash
python -m pip install -r tools/agent_sprite_forge/requirements.txt
```

## 常用命令

生成布局参考图：

```bash
python tools/agent_sprite_forge/run_processor.py layout-guide --rows 2 --cols 2
```

生成精灵 prompt：

```bash
python tools/agent_sprite_forge/run_processor.py sprite build-prompt --target asset --mode idle --prompt "a small wooden boat sailing animation"
```

处理已经生成好的精灵表：

```bash
python tools/agent_sprite_forge/run_processor.py sprite process --input generated/agent_sprite_forge/raw/sheet.png --target asset --mode idle
```

提取 3x3 prop pack：

```bash
python tools/agent_sprite_forge/run_processor.py extract-props --input generated/agent_sprite_forge/raw/prop-pack.png --rows 3 --cols 3
```

合成分层地图预览：

```bash
python tools/agent_sprite_forge/run_processor.py compose-map --base generated/agent_sprite_forge/raw/base.png --placements generated/agent_sprite_forge/raw/placements.json
```

## 输出位置

默认输出到：

- `generated/agent_sprite_forge/sprites/`
- `generated/agent_sprite_forge/maps/`
- `generated/agent_sprite_forge/raw/`

这些输出目录在 Godot 项目内，生成出的 PNG/GIF/JSON 可以被 Godot 导入或继续整理到 `boat/`、`scene/` 等正式资源目录。

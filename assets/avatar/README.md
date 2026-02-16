# Live2D 形象

桌面置顶窗口，透明背景，可拖动。默认加载 hijiki 模型。

**语音：** 展开窗口后，点击右侧 ▶ 按钮开始录音，说完再点 ■ 结束，形象会复述你说的话。

**操作：** 小球常驻右侧，点击展开/收起 Live2D 窗口。

## Live2D 大小

收起和展开窗口均为 **2:3** 比例（80×120 / 400×600），Live2D 原比例缩放。在 `app.html` 可修改 `LIVE2D_SCALE`（默认 1，0.5=更小 1.2=更大）。

## 切换角色

在 `config/zhyx.yaml` 中修改 `avatar.model`：

```yaml
avatar:
  model: "hijiki"  # 可选: hijiki | shizuku | koharu | chitose | epsilon | tororo | izumi
```

首次使用需下载模型：

```bash
python scripts/download_models.py           # 下载全部
python scripts/download_models.py hijiki koharu   # 下载指定角色
```

## 添加自定义角色

### 1. 准备 Live2D 模型

需要 Cubism 2 格式的 Live2D 模型，包含：

- `xxx.model.json`：主配置
- `xxx.moc`：模型文件
- 贴图、动作 (.mtn)、表情 (.exp.json) 等

可从 [live2d-widget-models](https://github.com/xiazeyu/live2d-widget-models) 等获取免费模型。

### 2. 放入 models 目录

将模型文件夹放入 `assets/avatar/models/`，例如：

```
assets/avatar/models/
├── my_char/
│   ├── my_char.model.json
│   ├── my_char.moc
│   ├── moc/
│   │   └── my_char.2048/
│   │       └── texture_00.png
│   ├── mtn/
│   │   └── idle.mtn
│   └── ...
```

### 3. 注册到 registry.json

编辑 `assets/avatar/models/registry.json`，添加：

```json
{
  "my_char": {
    "path": "/models/my_char/my_char.model.json"
  }
}
```

- `path`：本地路径，以 `/models/` 开头
- 无需 `cdn`：仅本地模型可不填，有则作为加载失败时的回退

### 4. 使用

在 `config/zhyx.yaml` 中设置：

```yaml
avatar:
  model: "my_char"
```

重启形象窗口即可。

## 目录结构

```
assets/avatar/
├── app.html              # 主页面
├── models/
│   ├── registry.json     # 角色注册表
│   ├── shizuku/
│   ├── hijiki/
│   └── ...
├── tts/                  # TTS 生成的音频
└── README.md
```

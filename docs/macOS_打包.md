# 知式 Zhyx - macOS 应用打包

## 方式一：py2app（推荐）

### 1. 安装 py2app

```bash
pip install py2app
```

### 2. 开发模式（快速测试，依赖不打包）

```bash
python scripts/build_macos_app.py py2app -A
```

生成 `dist/Zhyx.app`，依赖从系统 Python 读取，体积小、构建快。

### 3. 发布模式（独立应用）

```bash
python scripts/build_macos_app.py py2app
```

打包所有依赖，生成独立 `.app`，可分发。**注意**：首次构建较慢，体积较大（含 PyTorch 等）。

### 4. 打包前准备

- 确保 `config/zhyx.yaml` 存在（或复制 `config/zhyx.yaml.example`）
- 确保 `assets/avatar/` 下有 Live2D 模型（运行 `python scripts/download_models.py`）
- 可选：准备 `assets/icon.icns` 作为应用图标，并在 `build_macos_app.py` 中取消注释 `iconfile`

### 5. 路径说明

- **开发模式 (-A)**：从源码运行，路径正常
- **发布模式**：数据在 `Zhyx.app/Contents/Resources/`，当前 `main` 通过 `__file__` 推导 ROOT，若遇问题可改为 `sys._MEIPASS`（py2app 会将 Resources 加入路径）

---

## 方式二：Platypus（脚本转 .app）

适合快速打包为「双击即运行」的 Mac 应用：

1. 安装 [Platypus](https://sveinbjorn.org/platypus)
2. 创建新应用：
   - Script: `./start.sh` 或 `python src/main.py`
   - 勾选 "Run in background"（API 服务）或留空（形象窗口）
   - 选择 "None" 作为界面类型（或 "Text Window" 看输出）

---

## 方式三：PyInstaller

```bash
pip install pyinstaller
pyinstaller --name Zhyx --windowed --onefile src/main.py
```

需额外配置 `--add-data` 包含 config、assets、skills 等目录。

---

## 注意事项

- **麦克风权限**：首次使用语音需授权，已在 plist 中声明
- **网络权限**：智谱 API、MCP、edge-tts 等需网络
- **签名与公证**：分发他人需 Apple 开发者账号做代码签名与公证，否则可能提示「来自未知开发者」

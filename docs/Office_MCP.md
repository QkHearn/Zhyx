# Office MCP 配置指南：让 AI 读写 Word / Excel / PowerPoint

## 方案一：不安装 Microsoft Office（推荐）

使用 `python-pptx`、`python-docx`、`openpyxl` 等库直接读写文件，**无需安装 Word/Excel/PowerPoint**，跨平台（Mac/Linux/Windows）。

### 前提
- **uv**（`brew install uv` 或 `pip install uv`）
- **Python 3.10+**

### 配置

在 `config/zhyx.yaml` 的 `mcp.servers` 下添加：

```yaml
    # PowerPoint（无需 Office）
    - name: ppt
      command: uvx
      args:
        - "--from"
        - office-powerpoint-mcp-server
        - ppt_mcp_server
    # Excel（无需 Office）
    - name: excel
      command: uvx
      args:
        - mcp-excel-server
    # Word（无需 Office）
    - name: word
      command: uvx
      args:
        - "--from"
        - office-word-mcp-uvx-server
        - word-mcp-server
        - stdio
```

### 能力说明
- **PowerPoint**：创建/编辑 .pptx、幻灯片、图表、表格、模板等
- **Excel**：读写 .xlsx/.csv、数据分析、透视表、图表
- **Word**：创建/编辑 .docx、段落、表格、格式、搜索替换等

---

## 方案二：需安装 Microsoft Office（仅 macOS）

通过 AppleScript 控制已安装的 Office 应用，适合需要「所见即所得」或复杂排版时使用。

### 前提条件

- **macOS** 10.15+
- **Microsoft Office for Mac**（Word、Excel、PowerPoint 至少安装一个）
- **Python 3.8+**

## 安装步骤（方案二）

### 1. 克隆并安装依赖

```bash
cd ~  # 或其他你想要的目录
git clone https://github.com/vAirpower/macos-office365-mcp-server.git
cd macos-office365-mcp-server
pip install -r requirements.txt
```

### 2. 配置 macOS 自动化权限

该服务器通过 AppleScript 控制 Office，需要授予权限：

1. 打开 **系统设置** → **隐私与安全性** → **自动化**
2. 在左侧列表找到你的终端应用（Terminal、iTerm、Cursor 等）
3. 勾选：
   - Microsoft PowerPoint
   - Microsoft Word
   - Microsoft Excel

首次运行如弹出授权提示，点击「好」允许。

### 3. 配置 Zhyx

编辑 `config/zhyx.yaml`，在 `mcp.servers` 下添加（替换为你的实际路径）：

```yaml
    - name: office365
      command: python
      args:
        - /Users/你的用户名/macos-office365-mcp-server/src/office365_mcp_server.py
```

或使用绝对路径，例如：
```yaml
    - name: office365
      command: /opt/anaconda3/bin/python
      args:
        - /Users/hearn/macos-office365-mcp-server/src/office365_mcp_server.py
```

### 4. 重启 Zhyx

重启形象或主程序后，语音对话即可调用 Office 工具。

## 可用能力

- **PowerPoint**：创建演示文稿、添加幻灯片、插入文字/图片/备注、保存
- **Word**：创建文档、添加标题/段落/列表/表格、格式化、保存
- **Excel**：创建工作簿、写入单元格/公式、创建图表、格式化、保存

## 常见问题

**提示 "Not authorized to send Apple events"**

- 检查终端应用是否有 Office 的自动化权限
- 至少手动打开过一次 Word/Excel/PPT
- 修改权限后重启终端或应用

**找不到 Office 应用**

- 确认 Microsoft Office 已安装在「应用程序」文件夹
- 使用 Finder 打开一次各 Office 应用

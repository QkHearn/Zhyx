# Skills 目录

符合 [Agent Skills 规范](https://agentskills.io/)，动态加载。

## 结构

- `skills/`：预置 skills，运行 `scripts/download_anthropic_skills.py` 从 anthropics/skills 下载
- `skills/agent_created/`：智能体运行时创建的新 skill，不会被下载脚本覆盖

## 配置

`config/zhyx.yaml`：

```yaml
skills:
  directory: skills
  writable_directory: null   # 默认 skills/agent_created/
  enabled: [skill-creator, docx, pptx, xlsx, pdf]
```

- `enabled`：加载完整 body 的 skill 名称；空则仅加载 metadata
- `writable_directory`：智能体可写目录，null 时使用 `skills/agent_created/`

## 动态加载

每次调用 `get_agent_skill_context()` 都会重新扫描目录，无需重启即可生效新增或删除的 skill。

# 复现说明

## 重新生成导出包

在源电脑执行：

```powershell
python "02_模型\export_codex_memory.py" `
  --output "04_输出结果" `
  --include-sessions
```

脚本会导出完整 `memories` 镜像、长期记忆压缩包、历史 sessions 证据包和 SHA-256 inventory。为避免误覆盖，若目标 memory mirror 已存在，脚本会停止；需要重导时应创建新的任务版本或新的空输出目录。

## 验证

1. 对照 `04_输出结果/memory_export_inventory.json` 检查归档 SHA-256。
2. 对两个 ZIP 执行完整性测试。
3. 确认长期记忆镜像文件数量与 inventory 一致。
4. 确认归档中不存在 `auth.json`、完整 `config.toml`、token 或桌面状态数据库。
5. 按 `新电脑首轮接管提示词.md` 完成新电脑只读验收。

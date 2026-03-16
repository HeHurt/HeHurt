# Workspace 减负工具

这个目录提供“先体检后清理”的最小工具集：

- `slim_hithium.ps1`：工作区减负扫描/可选执行脚本
- `gitignore.recommended`：推荐的根目录 `.gitignore` 模板

## 1) 仅体检（推荐先执行）

```powershell
Set-Location "d:\Users\hez\Desktop\hithium"
.\tools\workspace_health\slim_hithium.ps1 -Root .
```

运行后会生成报告目录：

- `tools/workspace_health/reports/<时间戳>/top_level_size.csv`
- `cache_dirs.csv`
- `copy_files.csv`
- `large_files_top.csv`
- `notebooks_top.csv`
- `git_size.csv`

## 2) 执行清理（谨慎）

仅删除缓存目录：

```powershell
.\tools\workspace_health\slim_hithium.ps1 -Root . -Apply
```

删除缓存 + copy 文件：

```powershell
.\tools\workspace_health\slim_hithium.ps1 -Root . -Apply -DeleteCopyFiles
```

删除缓存 + copy 文件 + 清空 notebook 输出：

```powershell
.\tools\workspace_health\slim_hithium.ps1 -Root . -Apply -DeleteCopyFiles -ClearNotebookOutputs
```

## 3) 更新 `.gitignore`

先手工比对再替换：

```powershell
Copy-Item .\tools\workspace_health\gitignore.recommended .\.gitignore.new
```

确认无误后再覆盖：

```powershell
Copy-Item .\.gitignore.new .\.gitignore -Force
```

## 4) 处理 `.git` 体积（建议顺序）

1. 先备份当前仓库
2. 压缩对象（非破坏）

```powershell
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

3. 若历史仍巨大，再考虑 `git filter-repo` 清理历史大文件（会重写历史）

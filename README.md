# Research Starter SDK

当前发布版本：**1.0.0-internal.5**（内部测试 1.0 便携运行时版）。

Windows 使用入口：下载 GitHub Release 中的完整 Windows ZIP，完整解压后双击 `Start Research Starter.cmd`。Launcher 固定调用包内 `runtime/python/python.exe` 与 `runtime/node/node.exe`，无需安装或选择系统 Python、Node/npm，也不会修改这些系统环境。页面只在 `127.0.0.1:8765` 启动。

三个入口：

- Paper Guide：上传或选择 iCloud Inbox PDF，生成导读后可在同一 thread 追问。
- Research Note：先生成和修订预览，再写入项目私有 Vault、用 Obsidian 打开检查，最后由代码把笔记与附件一次复制到 Settings 指定的云端笔记目录；Skill 不参与文件写入。
- Research Slides：上传或选择素材，生成本地可编辑 PPTX，验证后发布到 iCloud Output。

首次启动无需预先创建 `config.local.json`，应用会使用安全的发布默认值；用户从网页 Settings 保存后才生成本机配置。Python 3.12、Codex SDK、Docling、Web 依赖、Node 运行时和前端/PPT 依赖均随完整发布包提供，运行路径固定为项目相对位置且在 Settings 中只读显示。

iCloud 素材入口、iCloud 成品出口、云端 Obsidian 和 Obsidian 桌面程序均为可选项，留空时仍可使用本地上传、本地输出、Markdown 预览和项目私有 Vault。由于 Obsidian 不允许由本项目重新分发，用户只有在需要“用 Obsidian 打开”时才需自行安装并在 Settings 选择其程序。`runtime`、`node_modules`、`.runtime`、`config.local.json` 与个人任务不进入 Git 历史；完整运行时只随 GitHub Release ZIP 发布。

迁移依据见 `MIGRATION_BASELINE.md`，逐阶段证据见 `MIGRATION_LOG.md`。

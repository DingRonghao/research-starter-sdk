# Research Starter SDK

当前发布版本：**1.0.0-internal.4**（内部测试 1.0 启动修正版）。

Windows 使用入口：双击 `Start Research Starter.cmd`。Launcher 直接调用项目 `.venv`，无需激活环境，并只在 `127.0.0.1:8765` 启动本地页面。

三个入口：

- Paper Guide：上传或选择 iCloud Inbox PDF，生成导读后可在同一 thread 追问。
- Research Note：先生成和修订预览，再写入项目私有 Vault、用 Obsidian 打开检查，最后由代码把笔记与附件一次复制到 Settings 指定的云端笔记目录；Skill 不参与文件写入。
- Research Slides：上传或选择素材，生成本地可编辑 PPTX，验证后发布到 iCloud Output。

本地配置位于 `config.local.json`。首次启动配置器会先检查 Python 3.10–3.12、Node.js 18+ 与 npm；无法自动找到时直接弹出文件选择框，不要求用户手改 JSON。它不会下载新的基础 Python，也不会修改基础解释器；Python 包只安装到项目 `.venv`，Node 包只安装到项目 `node_modules`。项目运行始终使用相对位置 `.venv/Scripts/python.exe`。Docling、Skills 和 Node 包均从项目目录解析。

iCloud 素材入口、iCloud 成品出口和云端 Obsidian 均为可选项，留空时仍可使用本地上传、本地输出和项目私有 Obsidian Vault。`.venv`、`node_modules`、`.runtime`、`config.local.json` 与个人任务均不进入版本控制；`Inbox`、`Output` 的产品结构及每项功能的公开示例会进入版本控制。

迁移依据见 `MIGRATION_BASELINE.md`，逐阶段证据见 `MIGRATION_LOG.md`。

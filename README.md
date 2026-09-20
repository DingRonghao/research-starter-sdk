# Research Starter SDK

由CodeX主力开发，本人大约仅负责提供token，以引用CodeX SDK和预制skill为核心的的科研桌面端助手。现支持win x64版本，未来计划同步推出MacOS版本。

功能以本人科研需求为主，且业余精力有限，对于有些需求无法回应请谅解。

## 最新版本

当前发布版本：**1.3.0-internal.1**（内部测试版）。

- [下载 Windows 发行包](https://github.com/DingRonghao/research-starter-sdk/releases/latest)
- [查看本次更新说明](RELEASE_NOTES_1.3.0_INTERNAL.1.md)

三个入口：

- Paper Guide：上传或选择 iCloud Inbox PDF，生成导读后可在同一 thread 追问。
- Research Note：先生成和修订预览，再写入项目私有 Vault、用 Obsidian 打开检查，最后由代码把笔记与附件一次复制到 Settings 指定的云端笔记目录；Skill 不参与文件写入。
- Research Slides：上传或选择素材，生成本地可编辑 PPTX，验证后发布到 iCloud Output。

首次启动会在项目库中直接建立三个不消耗额度的完成示例；模型提供方可在 OpenAI Codex、DeepSeek API 与 Kimi API 之间选择。第三方 API Key 使用 Windows 当前用户加密，只写入本机私有目录，不会进入 Git 或发布包。

## 快速开始

1. 从 GitHub Releases 下载完整的 Windows ZIP。
2. 完整解压后，双击带应用图标的 `Research Starter.exe`。
3. 首次使用时进入 **Settings**，按需配置素材、成品与 Obsidian 路径，并登录 Codex，或配置 DeepSeek/Kimi API。

每个任务页面都可直接拖入 PDF 或素材文件夹。上传内容会自动进入项目 Inbox；发行包也附带三套公开合成素材，供用户自行运行完整流程。

Python 3.12、Codex SDK、Docling、Node.js 与所需项目依赖均已包含在发行包中，不需要安装或选择系统 Python/Node。iCloud 与 Obsidian 均为可选项，未配置时仍可使用本地上传、输出和预览功能。

## 内部测试版安全说明

当前 Windows 内部测试版尚未使用公开可信的 Authenticode 证书签名，因此 Windows 可能显示“未知发布者”。请只从本仓库的 [GitHub Releases](https://github.com/DingRonghao/research-starter-sdk/releases) 下载，并使用同一 Release 中的 `SHA256SUMS.txt` 核对文件。项目不会要求用户安装自签名根证书；同一版本发布后不会静默替换下载文件。

## 使用文档

- [完整使用指南](USER_GUIDE.md)
- [本版本更新说明](RELEASE_NOTES_1.3.0_INTERNAL.1.md)
- [Windows 启动器签名说明](CODE_SIGNING.md)
- [维护者发行流程](RELEASE_WORKFLOW.md)

## 本版本贡献

Ren Shuyue（[@SYID79](https://github.com/SYID79)）为 `1.3.0-internal.1` 提供了主要的 UI 交互与视觉设计建议。本版本三个功能输入页的布局、操作重点与视觉层级优化均受益于她的反馈。

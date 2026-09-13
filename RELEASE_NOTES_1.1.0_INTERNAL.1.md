# Research Starter 1.1.0-internal.1

本版本是面向内部测试的第二阶段发行版，重点增加模型选择能力并完善三类科研任务的完整使用体验。

## 主要更新

- 增加 DeepSeek API 支持。用户可以在 Settings 中使用 Windows 当前用户加密保存自己的 API Key，并单独测试连接；密钥不会进入项目配置、Git 或发布包。
- 支持 DeepSeek Flash（当前 V4.1 Flash）以及关闭、低、高、最大四档推理等级；无需 Codex 付费账户。
- 首次启动自动显示 Paper Guide、Research Note 和 Research Slides 三个已完成示例。
- Paper Guide 改为同一会话内的论文导读与持续问答；完整 Skill 只在首轮加载，后续问题复用 Docling 解析结果以降低遗忘和幻觉。
- Research Note 支持完整 Markdown 与图片预览、反复修订、本地 Obsidian 保存与检查，以及确认后机械复制到可选云端 Vault。
- Research Slides 支持反复生成修订版、不同版本预览切换和统一命名下载，并支持可选 PPTX 模板。
- 改进开发版与发行版实例隔离，避免浏览器打开错误副本。
- 修复 Windows 后台启动方式，避免主服务及 Codex/Node 子进程显示控制台窗口。
- 增加应用图标、浏览器图标和带图标的 Windows 启动快捷方式。
- Settings 中的 iCloud 与云端 Obsidian 路径保持可选；内置 Python、Node 和项目依赖无需用户配置。

## 隐私与本地数据

- 发布包不包含 Codex 登录状态、DeepSeek API Key、`config.local.json`、个人 Inbox/Output 项目或 `.runtime` 运行数据。
- 内置示例是专门选择的公开测试材料，不包含开发环境中的其他历史任务。
- Codex 账户状态继续使用每位用户自己的本机 Codex 用户目录。

## 平台说明

当前完整发行包面向 Windows。PPTX 模板追加功能需要本机 Microsoft PowerPoint；Obsidian 打开功能需要用户安装或配置 Obsidian。macOS 尚不是本版本的已验证目标。

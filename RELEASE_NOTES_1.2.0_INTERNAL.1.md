# Research Starter 1.2.0-internal.1

本版本继续面向内部测试，重点完善模型与用量适配、首次体验、PPT 模板工作流和 Research Slides 的交付质量。

## 主要贡献者

Yutong Tian（[@Feather-Forest](https://github.com/Feather-Forest)）是本次 Release 的主要想法、修复方案与 PPT 模板贡献者。他对模型选择、不同会员账户的用量显示、完整测试案例、Inbox 交互、模板使用方式及 PPT 预览问题提供了关键反馈、方案与素材贡献。

## 主要更新

- 模型列表支持 GPT-6 Astra，并改进不同 Codex 会员类型下五小时和一周用量的显示逻辑。
- 扩充三个公开合成案例。首次启动可查看已完成示例，也可从 Inbox 选择配套素材运行完整流程。
- 三个任务入口支持拖入文件或文件夹，并将材料统一收纳到对应 Inbox 目录。
- 增加独立 PPT 模板库与公开学术汇报模板，支持从模板库选择或手动上传 PPTX。
- Research Slides 将模板作为版式与视觉语言库，按需选用页面并清理未采用的示例页。
- 强化 Research Slides 的证据、计算、引用和输出语言复核，模板通用文案随用户选择的语言统一重写。
- 修复部分 Office 模板在网页预览中把白色主题背景显示成黑色的问题，同时保留真实深色页面。
- PPT 预览改为完整挂载页面与媒体，减少滚动时的缺页、闪烁和背景暴露。
- 完善未签名内部测试版的 SHA-256 校验文件、发行说明和构建检查。

## 隐私与发布边界

- Git 和发行 ZIP 不包含 `config.local.json`、`.runtime`、Codex 登录状态、DeepSeek API Key、个人任务或非公开 Inbox/Output 数据。
- DeepSeek API Key 继续使用 Windows 当前用户加密，并保存在项目外的本机用户状态目录。
- 发行包仅包含三套公开合成案例和明确允许发布的 PPT 模板。

## 已知说明

- 当前 Windows 启动器仍为未签名内部测试版本。请只从本项目 GitHub Releases 下载，并使用同页的 SHA-256 文件校验。
- 当前完整发行包面向 Windows x64；macOS 仍未进入正式验证范围。

# Research Starter 1.3.0-internal.2

本版本继续面向内部测试。在 `1.3.0-internal.1` 的功能基础上，统一发行信息，并改善使用指南页面的阅读体验。

## 主要贡献者

Ren Shuyue（[@SYID79](https://github.com/SYID79)）为 1.3.0 系列提供了主要的 UI 交互与视觉设计建议。三个功能输入页的布局、操作重点、视觉层级及多项细节优化均受益于她的反馈。

## 主要更新

- 新增 Kimi API 提供方。Kimi K3 已接入现有任务框架，支持独立 API Key、视觉输入、长上下文以及 Low、High、Max 三档推理等级，不要求 Codex 付费账户。
- 统一 OpenAI Codex、DeepSeek 与 Kimi 的模型提供方、模型和推理等级控件。
- 重构 Paper Guide、Research Note 与 Research Slides 的输入界面，强化素材、模板、输出语言和模型配置之间的视觉层级。
- 为 Research Slides 增加可复用的 PPT 模板载入流程。模板只需完成一次视觉分析、对象结构解析和适用场景归纳，后续生成可直接复用模板档案。
- 模板载入与 PPT 生成可以分别选择模型和推理等级；发行包内的公开模板已预先载入，可直接预览和使用。
- 完善 PPTX 网页预览兼容性，修复部分原生图表和 SVG 图表无法显示的问题。
- 扩宽并居中使用指南正文区域，使长篇说明在宽屏界面中更易阅读。
- 同步更新 About 页面版本信息，确保界面版本、Git 标签和发行包名称一致。

## 隐私与发行边界

- Git 和发行 ZIP 不包含个人配置、Codex 登录状态、第三方 API Key、个人任务或非公开素材。
- DeepSeek 与 Kimi API Key 使用 Windows 当前用户加密，并保存在本机私有运行状态中。
- 发行包仅包含公开合成案例、公开 PPT 模板及其预先生成的模板档案。

## 使用说明

- 当前 Windows 启动器为未签名内部测试版本。请只从本项目 GitHub Releases 页面下载，并使用同页的 SHA-256 文件校验。
- 当前完整发行包面向 Windows x64；macOS 尚未进入正式验证范围。
- PPTX 网页预览用于快速检查。正式演示前，建议使用 PowerPoint 再次确认字体和 Office 特效。

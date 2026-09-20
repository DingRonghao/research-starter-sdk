# Research Starter 1.3.0-internal.1

本版本继续面向内部测试，重点扩充模型提供方、重构三个任务的输入体验，并为 Research Slides 增加可复用的模板载入流程。

## 主要贡献者

Ren Shuyue（[@SYID79](https://github.com/SYID79)）为本次 Release 提供了主要的 UI 交互与视觉设计建议。三个功能输入页的布局、操作重点、视觉层级及多项细节优化均受益于她的反馈。

## 主要更新

- 新增 Kimi API 提供方。Kimi K3 通过 Responses API 接入现有任务框架，支持独立 API Key、视觉输入、长上下文及 Low、High、Max 三档推理等级，不要求 Codex 付费账户。
- 统一 OpenAI Codex、DeepSeek 与 Kimi 的模型提供方、模型和推理等级控件；所有任务入口均显示适用的账户用量或第三方平台提示。
- 大幅重构 Paper Guide 与 Research Note 输入页：素材和补充说明成为主要操作区域，输出语言与模型选择集中于右侧，支持拖入、Inbox 选择及更清晰的视觉层级。
- 大幅重构 Research Slides 输入页：模板、模板预览和模板载入模型集中于左侧；素材、输出语言和 PPT 生成模型集中于右侧；页面逻辑说明改为可选。
- 新增原创的 PPT 模板载入流程。系统对模板进行一次性的逐页视觉分析、对象结构解析和适用场景归纳，并保存为可复用模板档案；后续生成直接复用档案，减少重复分析，提高速度和模板匹配质量。
- 模板载入与 PPT 生成可以分别选择模型和推理等级；发行包内的公开模板已预先载入，可直接预览和使用。
- 完善 Research Slides 模板选择、版本预览和 PPTX 网页渲染兼容性，修复部分原生图表及 SVG 图表无法显示的问题。
- 统一三个任务的主要提交按钮和模型控件样式，调整卡片比例、对齐、高度与重点区域，使首次操作路径更清晰。

## 隐私与发布边界

- Git 和发行 ZIP 不包含 `config.local.json`、`.runtime`、Codex 登录状态、第三方 API Key、个人任务或非公开 Inbox/Output 数据。
- DeepSeek 与 Kimi API Key 分别使用 Windows 当前用户加密，并保存在本机私有运行状态中；界面、日志、Git 和发布包均不回显或携带密钥。
- 发行包仅包含三套公开合成案例、公开 PPT 模板及其预先生成的模板档案。

## 已知说明

- 当前 Windows 启动器仍为未签名内部测试版本。请只从项目 GitHub Releases 下载，并使用同页的 SHA-256 文件校验。
- 当前完整发行包面向 Windows x64；macOS 尚未进入正式验证范围。
- PPTX 网页预览用于快速检查，字体和部分 Office 特效仍可能与桌面 PowerPoint 有差异；正式演示前请使用 PowerPoint 复核。

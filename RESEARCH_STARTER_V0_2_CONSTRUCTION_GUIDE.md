# Research Starter v0.2 — SDK / iCloud / Local Web UI 施工指南

> 日期：2026-09-11  
> 用途：交给 Codex 作为本轮迁移施工的唯一执行规范。  
> 当前平台：先只在现有 Windows 电脑上实施和验证。  
> 后续目标：Windows 稳定后再迁移到 macOS；家庭服务器是否部署，另开任务决定。  
> **本轮不做 Git/GitHub 同步，不做服务器部署，不重写已经能工作的三个核心 Skill。**

---

# 0. 总体目标

当前已经存在一套**可以正常工作的 Desktop/Codex 版 Research Starter**，包含三个功能：

1. `paper-guide`
2. `research-note`
3. `research-slides`

这套旧系统已经在测试场景中达到可用水平。

本轮施工的目标不是重新设计三个功能，而是把它们从：

```text
用户手动打开文件夹
→ 把素材放进指定 inbox
→ 打开 Codex Desktop
→ 输入任务指令
→ Codex 调用既有 Skill
→ 产出结果
```

迁移成：

```text
本地 Web UI
→ Python Runner
→ OpenAI Codex Python SDK
→ 既有三个 Skill
→ 本地任务工作区 / Obsidian / iCloud output
```

核心思想：

> **只替换入口和执行控制层，不重做已经工作的科研功能。**

---

# 1. 强制施工顺序

本轮必须严格按三阶段施工。

```text
Phase 1
Desktop → Codex Python SDK

Phase 2
本地 input/output 保持主存储 → 增加可选 iCloud 发布/归档层

Phase 3
增加 Local Web UI + 双击 Launcher
```

## 禁止跨阶段施工

必须满足：

- Phase 1 三个功能全部通过验收，才允许进入 Phase 2；
- Phase 2 三个功能全部通过验收，才允许进入 Phase 3；
- 不允许为了“以后方便”提前做 UI、服务器、Git 同步或安装器；
- 不允许一次性大重构。

如果某一阶段失败，优先修复该阶段，不要通过重写整个架构绕过问题。

---

# 2. 最重要的保护规则：旧系统不能动

现有 Desktop 版本是**已知可工作 baseline**。

Codex 必须：

```text
只读参考旧目录
        ↓
在新的施工目录中重新搭建 SDK 版本
```

绝对禁止：

- 在旧项目原地升级；
- 修改旧 Skill；
- 删除旧环境；
- 替换旧 inbox/output；
- 把旧项目“整理”成新结构；
- 为了 SDK 迁移顺手重写三个功能。

如果新系统出现问题，旧系统必须仍然可以像现在一样继续运行。

---

# 3. 本轮固定技术选择

为了避免 Codex 重新选型，本轮技术栈固定如下。

## 3.1 Codex 执行层

**唯一使用：OpenAI 官方 Codex Python SDK**

Package:

```text
openai-codex
```

官方仓库：

https://github.com/openai/codex

官方 Python SDK Getting Started：

https://github.com/openai/codex/blob/main/sdk/python/docs/getting-started.md

官方 Python SDK API Reference：

https://github.com/openai/codex/blob/main/sdk/python/docs/api-reference.md

PyPI：

https://pypi.org/project/openai-codex/

### 本轮固定版本

截至 2026-09-11，公开稳定 Python SDK 最新版为：

```text
openai-codex==0.147.0
```

第一轮迁移**固定使用 0.147.0**。

不要因为 `openai-codex-cli-bin` 已存在更高 runtime 版本而手工替换 runtime。

`openai-codex==0.147.0` 会安装它自己匹配的 Codex runtime。

本轮的目标是先建立一个**已验证稳定组合**。

未来升级 Codex SDK 版本属于单独任务。

### 明确禁止

不要使用：

- Codex Desktop 自动化；
- 模拟键鼠控制 Codex Desktop；
- `subprocess` 包装 `codex exec` 作为正式 Runner；
- 第三方 Codex wrapper；
- OpenAI API 自己重新实现 Agent；
- LangChain / CrewAI。

CLI 可以保留为人工调试工具，但正式链路固定走 Python SDK。

---

## 3.2 SDK 调用模式

从一开始使用：

```text
AsyncCodex
```

而不是先用同步版、以后为了 Web UI 再重写异步结构。

基础思想：

```python
from openai_codex import AsyncCodex, Sandbox, ApprovalMode
```

Runner 长期运行时维护 SDK client。

默认：

```text
Sandbox.workspace_write
ApprovalMode.auto_review
```

正常运行禁止默认使用：

```text
Sandbox.full_access
```

---

## 3.3 Skill 调用方式

优先通过 SDK 官方的：

```text
SkillInput(name=..., path=...)
```

显式把现有 Skill 交给 Codex。

不要要求朋友或未来的其他电脑预先把 Skill 安装到全局 Codex 目录才能运行。

理想结构：

```text
Research Starter Project
└── skills/
    ├── paper-guide/
    │   └── SKILL.md
    ├── research-note/
    │   └── SKILL.md
    └── research-slides/
        └── SKILL.md
```

Python Runner 通过项目内相对路径找到 Skill。

这样未来：

```text
复制 / clone Research Starter
→ 安装依赖
→ Skill 自动可用
```

而不是：

```text
复制项目
→ 再手工安装三个 Skill
→ 再配全局 Codex
```

如果当前 Skill 的实际目录结构不同，**第一阶段优先保持现有可工作结构**；只有确认 SDK 能稳定显式调用后，才允许做最小目录调整。

---

## 3.4 Web UI 技术栈

Phase 3 固定：

```text
FastAPI
+ Jinja2
+ 原生 HTML/CSS/JavaScript
```

不要使用：

- React；
- Vue；
- Next.js；
- Electron；
- Tauri；
- Node 前端构建链；
- 独立前端项目；
- 数据库。

理由：

> UI 很简单，Python Runner 已经存在，没有必要再增加第二套应用技术栈。

`research-slides` 内部已有 Node/PptxGenJS 不代表前端也要使用 Node。

---

# 4. 推荐的新施工目录

建议新建：

```text
Research-Starter-SDK/
```

初始目标结构：

```text
Research-Starter-SDK/
│
├── skills/
│   ├── paper-guide/
│   ├── research-note/
│   └── research-slides/
│
├── runner/
│   ├── codex_client.py
│   ├── jobs.py
│   ├── tasks.py
│   └── config.py
│
├── web/
│   ├── app.py
│   ├── templates/
│   └── static/
│
├── .runtime/
│   └── jobs/
│
├── config.local.json
├── config.example.json
├── requirements.txt
├── MIGRATION_BASELINE.md
├── MIGRATION_LOG.md
├── README.md
└── Start Research Starter.cmd
```

注意：

- Phase 1 不需要提前把 `web/` 内容全部实现；
- Phase 3 再正式施工 `web/`；
- `.runtime/` 是本地状态，不属于用户长期科研数据；
- 将来做 Git 时 `.runtime/`、`config.local.json`、`.venv/` 都必须忽略。

---

# 5. Phase 0 — 冻结 Baseline

正式迁移前先完成一次“旧系统盘点”。

## 5.1 只读检查旧项目

记录：

- 三个 Skill 的真实路径；
- 三个 Skill 当前如何被调用；
- 当前 inbox / output 目录；
- paper-guide 依赖的 Docling 调用方式；
- research-note 依赖的 Obsidian / notesmd-cli 调用方式；
- research-slides 依赖的 Node/PptxGenJS 及脚本；
- 当前 Python / Node 版本；
- 当前测试样例；
- 当前输出结果。

写入：

```text
MIGRATION_BASELINE.md
```

## 5.2 建立三个最小回归测试

不要新造测试内容。

尽量使用旧版本已经成功跑过的素材。

至少固定：

```text
Test A — paper-guide
一个已验证 PDF
预期：能生成阅读导引，并能继续一次追问

Test B — research-note
一段已验证测试内容
预期：能正确创建或更新测试笔记

Test C — research-slides
一组已验证输入素材
预期：能生成可正常打开、可编辑的 PPTX
```

后面每一阶段都用同一组 baseline 测试。

这样才能判断问题来自“迁移”，还是来自测试条件变化。

---

# 6. Phase 1 — 用 Codex Python SDK 替代 Desktop

## 6.1 Phase 1 的唯一目标

把：

```text
Codex Desktop
```

替换为：

```text
Python Runner
→ OpenAI Codex Python SDK
```

此阶段：

- input 仍使用本地目录；
- output 仍使用本地目录；
- 不碰 iCloud；
- 不做 Web UI；
- 不做 Git；
- 不重写 Skill。

---

## 6.2 创建独立 Python 环境

在新项目目录下：

```text
.venv/
```

安装至少：

```text
openai-codex==0.147.0
```

以及旧系统实际需要的 Python 依赖。

不要复制旧 `.venv`。

不要要求正常用户每次：

```text
activate .venv
```

程序内部以后必须直接调用：

```text
.venv\Scripts\python.exe
```

环境激活只允许作为开发调试手段，不得成为最终正常入口。

---

## 6.3 先做 SDK Smoke Test

在碰三个 Skill 前先验证 SDK 本身。

需要完成：

### A. SDK 初始化

能够创建：

```python
AsyncCodex()
```

### B. 账号状态

调用：

```text
account()
```

如果当前电脑已有可复用 Codex 登录，则直接识别。

### C. ChatGPT 登录

若未登录：

```text
login_chatgpt()
```

取得官方登录 URL。

用 Python：

```text
webbrowser.open(...)
```

自动打开系统浏览器。

用户只在 OpenAI 官方网页完成登录。

**Research Starter 不允许提供 OpenAI 密码输入框。**

等待：

```text
login.wait()
```

确认登录成功。

### D. 模型查询

调用：

```text
models()
```

确保 SDK 与 Codex runtime 正常通信。

### E. 最小 turn

在一个测试工作目录执行：

```text
thread_start(...)
→ run("创建一个最简单的测试文件或返回一句固定文本")
```

确认：

- Codex 能运行；
- SDK 能拿到最终结果；
- sandbox 正常；
- runtime 正常。

完成后才允许接三个 Skill。

---

# 7. Phase 1 — Job Workspace 规范

即使 Phase 1 还没有 UI，也应从现在开始使用统一 Job。

每次执行建立：

```text
.runtime/jobs/<job-id>/
├── input/
├── temp/
├── output/
└── job.json
```

例如：

```text
.runtime/jobs/20260911-153012-a8f3/
```

`job.json` 最小字段：

```json
{
  "job_id": "20260911-153012-a8f3",
  "task": "paper-guide",
  "status": "running",
  "created_at": "...",
  "thread_id": null,
  "source_files": [],
  "outputs": [],
  "error": null
}
```

允许的状态：

```text
created
running
completed
failed
cancelled
```

不要引入数据库。

Job 文件夹本身就是任务状态。

---

# 8. Phase 1 — 三个功能如何通过 SDK 调用

## 8.1 `paper-guide`

### 工作目录

```text
job/
```

使用：

```text
cwd = 当前 job workspace
sandbox = workspace_write
```

PDF 复制到：

```text
job/input/
```

明确传入：

```text
SkillInput(name="paper-guide", path=<paper-guide skill path>)
```

同时传入用户任务说明。

目标：

```text
PDF
→ 既有 paper-guide Skill
→ Docling 等原有链路
→ 导读结果
```

### 多轮测试

必须验证同一 SDK thread：

```text
第一轮：做导读
第二轮：针对 Figure / Section 再追问一次
```

保存：

```text
thread_id
```

到 `job.json`。

这样 Phase 3 可以继续用 UI 追问，而不需要重新设计论文阅读逻辑。

---

## 8.2 `research-slides`

### 工作目录

```text
job/
```

素材复制到：

```text
job/input/
```

PPT 必须首先生成到：

```text
job/output/
```

调用现有：

```text
research-slides Skill
```

不要在 Phase 1 改它内部已经工作的 PPT 流程。

验收：

- `.pptx` 成功生成；
- 文件可正常打开；
- 文本 / 图片保持可编辑；
- 与旧 Desktop 版测试结果至少同等级；
- output 路径由 Runner 掌握，不靠模型猜。

---

## 8.3 `research-note`

这是三个模块中唯一特殊的一个。

因为真正需要写入的是：

```text
Obsidian Vault
```

而不是 Job output。

推荐：

```text
cwd = 已配置的 Obsidian Vault
sandbox = workspace_write
```

同时显式传入：

```text
SkillInput(name="research-note", path=<research-note skill path>)
```

这样写权限天然落在 Vault workspace 内，不必一开始设计复杂额外 writable roots。

Job 仍然可以用于保存：

- 本次输入；
- thread_id；
- 状态；
- 日志；
- 最终 Codex 回复。

但真正科研笔记直接写入 Vault。

如果现有 Skill 必须从项目目录访问只读脚本或配置，允许读取项目文件，但不要因此改成 `full_access`。

---

# 9. Phase 1 — 权限原则

默认：

```text
Sandbox.workspace_write
ApprovalMode.auto_review
```

不要默认：

```text
Sandbox.full_access
```

如果某个现有 Skill 因 SDK sandbox 与 Desktop 权限模型差异而失败：

1. 先明确失败路径；
2. 判断它实际需要写哪个目录；
3. 优先调整 `cwd` 或最小 writable scope；
4. 不要直接关闭 sandbox；
5. 如果必须增加权限，把原因记录进 `MIGRATION_LOG.md`。

---

# 10. Phase 1 — 验收门

只有同时满足以下条件才算 Phase 1 完成：

- [ ] 不打开 Codex Desktop，也能登录 Codex；
- [ ] Python SDK 能识别账号；
- [ ] `paper-guide` 完整跑通；
- [ ] `paper-guide` 至少完成一次同线程追问；
- [ ] `research-note` 能真实读写测试 Vault / 测试笔记；
- [ ] `research-slides` 能生成可编辑 `.pptx`；
- [ ] 三个功能都使用原有 Skill，而不是重新实现；
- [ ] 不需要人工打开终端输入 Codex 命令；
- [ ] 旧 Desktop 版本仍然完全可用。

完成后在：

```text
MIGRATION_LOG.md
```

记录 Phase 1 结果。

然后才能进入 Phase 2。

---

# 11. Phase 2 — iCloud 作为统一交换层，但所有高频处理留在本地

## 11.1 Phase 2 的真实目标

三个功能在未来落地版本中，仍然计划与 iCloud 中统一的：

```text
Inbox
Output
```

发生交互。

这样做的主要目的仍然是：

- Windows 与 Mac 可以看到同一批待处理素材；
- 用户不需要分别记住每台设备的本地输入目录；
- 最终产物可以自动出现在其他设备上；
- iCloud 继续承担跨设备“交换层”的角色。

**本轮并不取消这一设计。**

但是，已经从现有 `research-note` 与 iCloud/Obsidian 的实际使用中观察到：

> Windows 与 iCloud Drive 的刷新、同步和目录状态存在潜在不稳定性。

此前已经发生过文件位置异常、文件散落以及较高人工排查成本。

因此，本轮需要解决的不是：

> “要不要使用 iCloud？”

而是：

> **“怎样继续使用 iCloud，同时尽可能减少程序与 iCloud 的直接、高频交互？”**

最终原则固定为：

> **iCloud 负责跨设备交换；本地工作区负责实际执行。**

---

# 12. iCloud 仍然保留统一 Inbox / Output

推荐继续建立：

```text
iCloud/
└── Research-Starter-Data/
    ├── Inbox/
    │   ├── paper-guide/
    │   ├── research-note/
    │   └── research-slides/
    │
    └── Output/
        ├── paper-guide/
        ├── research-note/
        └── research-slides/
```

这两个目录仍然是用户层面看到的统一交换入口。

从用户角度：

```text
把素材放进 iCloud Inbox
        ↓
运行 Research Starter
        ↓
任务完成
        ↓
最终结果出现在 iCloud Output
```

这一体验不改变。

---

# 13. 关键风险抑制策略：Copy-In / Local Work / Copy-Out

程序主体不得直接把 iCloud 当成持续工作目录。

每一轮任务必须采用：

```text
iCloud Inbox
    ↓
一次性 Copy-In
    ↓
本地 .runtime/jobs/<job-id>/input
    ↓
全部高频处理在本地完成
    ↓
本地 .runtime/jobs/<job-id>/output
    ↓
一次性 Copy-Out
    ↓
iCloud Output
```

也就是说：

### 每轮任务与 iCloud 的理想直接交互只有 1–2 个关键阶段

1. **任务开始时：**
   从 iCloud Inbox 将所需输入一次性复制到本地 Job Workspace。

2. **任务结束时：**
   将已经完成并验证的最终产物一次性复制到 iCloud Output。

任务执行中间的所有过程：

- Codex 读写；
- Docling 解析；
- 临时 Markdown / JSON；
- Python 中间文件；
- Node / PptxGenJS 中间文件；
- 图片转换；
- 缓存；
- 日志；
- 草稿；
- 重试；
- 临时输出；

全部只能发生在本地。

**不得在任务执行过程中持续对 iCloud 文件反复读写。**

---

# 14. 本地 Job Workspace 是真正的执行区

每次执行仍建立：

```text
.runtime/jobs/<job-id>/
├── input/
├── temp/
├── output/
└── job.json
```

逻辑：

```text
iCloud = exchange layer
local job = execution layer
```

Codex SDK 的：

```text
cwd
sandbox
Skill execution
```

都必须围绕本地 Job Workspace 工作。

对于 `paper-guide` 和 `research-slides`：

> 一旦 Copy-In 完成，后续执行就不应该依赖原始 iCloud 文件继续存在或保持在线。

---

# 15. iCloud Inbox 的读取保护

iCloud 中一个“看得见”的文件，不一定意味着它的完整内容已经真正下载到 Windows 本机。

因此 Copy-In 前必须：

1. 检查路径存在；
2. 尝试实际打开并读取；
3. 确认文件不是不可用 placeholder；
4. 完整复制到本地 Job；
5. 必要时校验复制后的文件大小；
6. Copy-In 完成后才允许正式启动 Codex 任务。

如果 iCloud 文件当前不可读：

```text
任务不要启动
→ 明确提示用户等待 iCloud 下载完成或手动确保本地可用
```

不要让 Codex 在任务中途自己不断尝试读取同一个云文件。

---

# 16. iCloud Output 的写入保护

最终结果必须：

```text
先在本地生成
→ 在本地完成验证
→ 再一次性复制到 iCloud Output
```

禁止：

```text
在 iCloud Output 中创建最终 PPT
→ Codex / PptxGenJS 持续修改
```

推荐流程：

```text
local output/final.pptx
        ↓
确认文件存在、非空、可打开
        ↓
复制为：
iCloud Output/final.pptx.uploading
        ↓
复制完成
        ↓
rename
        ↓
iCloud Output/final.pptx
```

这样即使 iCloud 在同步过程中出现异常，也尽量不会让其他设备看到半成品。

---

# 17. iCloud 失败与任务状态必须解耦

例如：

```text
research-slides 已成功生成本地 PPT
但 iCloud Copy-Out 失败
```

不能把整个科研任务判定为失败。

应记录为类似：

```text
task_status: completed
cloud_sync_status: failed
local_output: available
```

用户至少仍能从本地 output 取回成果。

同理：

```text
iCloud Copy-In 失败
```

应在任务正式启动前终止，而不是进入 Codex 后再随机报错。

---

# 18. Phase 2 本地配置

`config.local.json` 推荐为：

```json
{
  "icloud_inbox_root": "本机实际可访问的 iCloud Inbox 路径",
  "icloud_output_root": "本机实际可访问的 iCloud Output 路径",
  "local_jobs": ".runtime/jobs",
  "local_fallback_output": ".runtime/local-output",
  "obsidian_vault": "当前真实 Obsidian Vault 路径"
}
```

禁止把 Windows 的 iCloud 默认绝对路径硬编码到业务逻辑。

以后迁移到 Mac 时，只修改：

```text
config.local.json
```

而不修改 Skill 或 Runner 核心逻辑。

---

# 19. Phase 2 对三个功能的统一规则

## `paper-guide`

```text
iCloud Inbox/paper-guide
→ Copy-In 到 local job/input
→ 本地 Docling + Codex 阅读
→ 本地生成需要保存的结果
→ Copy-Out 到 iCloud Output/paper-guide
```

多轮论文问答过程中不得反复读取原始 iCloud PDF。

---

## `research-slides`

```text
iCloud Inbox/research-slides
→ Copy-In 所有素材
→ 本地生成 PPTX
→ 本地验证
→ Copy-Out 最终 PPTX
→ iCloud Output/research-slides
```

PptxGenJS 不得直接对 iCloud 文件持续写入。

---

## `research-note`

`research-note` 需要区分两件事：

### A. 新版 Research Starter 的统一 Inbox / Output 逻辑

如果该任务存在需要从 Research Starter Inbox 获取的输入，仍采用：

```text
iCloud Inbox
→ Copy-In
→ 本地 Job
```

如果存在需要作为任务产物导出的文件，也仍采用：

```text
本地完成
→ Copy-Out
→ iCloud Output
```

### B. 现有 Obsidian Vault 的特殊问题

真正写入科研知识时，`research-note` 目前仍然需要直接操作：

```text
当前位于 iCloud 中的 Obsidian Vault
```

这一部分已知存在风险，但当前没有已经充分验证、可立即替代的跨设备同步方案。

因此本轮采取**姑息策略**：

- 维持现有 Vault 位置；
- 维持现有 interaction logic；
- 不迁移 Vault；
- 不新建同步体系；
- 不尝试用本轮 Research Starter 架构“顺手解决” Obsidian 同步问题。

也就是说：

> **Research Starter 新增的统一 iCloud Inbox/Output 要采用低频 Copy-In/Copy-Out 策略；现有 Obsidian Vault 的 iCloud 直接交互暂时保留，作为已知例外。**

未来再单独评估：

- Obsidian 官方 Sync；
- 家庭服务器；
- Syncthing；
- 其他成熟同步方案。

---

# 20. 对 Obsidian 当前姑息方案的保护要求

虽然暂时保持现状，但仍应避免扩大风险。

`research-note`：

1. 不移动 Vault 根目录；
2. 不修改 iCloud 同步方式；
3. 不批量移动笔记；
4. 不批量重命名现有目录；
5. 不让其他两个模块把文件写进 Vault；
6. 不把 Research Starter 的 Inbox/Output 建在 Vault 内；
7. 不把 `.runtime` 建在 Vault 内；
8. 若检测到 Vault 根目录结构明显异常或目标路径突然变化，停止写入并报错；
9. 不自动尝试“整理”散落文件。

这一部分的目标只是：

> **维持现在能工作的 research-note，不让本轮迁移进一步增加 Obsidian/iCloud 风险。**

---

# 21. Phase 2 验收门

继续使用 Phase 0 的同一组三个 baseline tests。

必须满足：

- [ ] iCloud Inbox 仍然是三个功能的用户输入交换层；
- [ ] 每次任务开始时，输入只 Copy-In 一次到本地 Job；
- [ ] 任务实际执行过程中不持续依赖 iCloud 原始输入；
- [ ] `paper-guide` 的 Docling / Codex 中间过程全部本地完成；
- [ ] `research-slides` 的 PPTX 全部本地生成后才 Copy-Out；
- [ ] 最终输出统一进入对应 iCloud Output；
- [ ] Copy-Out 之前先验证本地产物；
- [ ] iCloud Output 不出现持续写入的半成品；
- [ ] iCloud Copy-Out 失败时，本地结果仍完整保留；
- [ ] `.runtime` / cache / temp / `.venv` / node_modules 不进入 iCloud；
- [ ] `research-note` 对现有 iCloud Obsidian Vault 的交互暂时维持现状；
- [ ] 本轮不尝试迁移或重构 Obsidian Vault。

完成以上测试后才能进入 Phase 3。

---

# 22. Phase 3 — Local Web UI

## 16.1 目标

把原来的：

```text
找文件夹
→ 放素材
→ 记住怎么调用
→ 打开 Codex
→ 写 prompt
```

变成：

```text
双击 Research Starter
→ 浏览器自动打开
→ 选择功能
→ 上传 / 选择素材
→ 填写必要说明
→ 点击运行
→ 查看结果
```

用户不需要知道：

- Python 环境；
- SDK；
- Codex thread；
- inbox 真实路径；
- job workspace；
- shell command。

---

# 23. Phase 3 — Web 安全边界

FastAPI 默认只监听：

```text
127.0.0.1
```

不要监听：

```text
0.0.0.0
```

本轮不是服务器项目。

不要为了“以后家庭服务器也许会用”提前暴露 LAN 访问。

---

# 24. Phase 3 — UI 页面

主页只需要：

```text
Research Starter

[ Paper Guide ]
[ Research Note ]
[ Research Slides ]

Recent Jobs
Settings
```

不要增加：

- 用户系统；
- 登录系统；
- 插件商城；
- 多 Agent 管理；
- server dashboard；
- 模板商城；
- 数据库后台。

---

# 25. `paper-guide` UI

最小字段：

```text
PDF
[选择 / 上传]

阅读备注（可选）
[文本框]

特别关注的问题（可选）
[文本框]

[开始阅读]
```

任务完成后显示：

- 导读；
- 当前 PDF；
- thread 状态；
- 后续提问框。

后续提问必须：

```text
resume / reuse 同一个 thread
```

而不是每次新建论文会话。

---

# 26. `research-note` UI

最小字段：

```text
需要整理的内容
[大文本框]

备注（可选）
[文本框]

[预览]
[写入 Obsidian]
```

推荐保留两步：

```text
Preview
→ Save
```

因为该功能会修改长期知识库。

不要默认自动写入。

---

# 27. `research-slides` UI

最小字段：

```text
素材
[多文件上传区]

演讲时间（可选）
[输入]

内容 / 页面逻辑
[大文本框]

风格备注（可选）
[文本框]

额外要求（可选）
[文本框]

[生成 PPT]
```

任务完成后：

```text
[打开 PPT]
[打开输出文件夹]
```

如果以后需要“继续修改 PPT”，可复用当前 thread，但这不是 Phase 3 必须项。

---

# 28. Phase 3 — Job API

前端不要拼 shell command。

Web UI 只向 Runner 提交结构化任务，例如：

```json
{
  "task": "research-slides",
  "files": ["..."],
  "instructions": "...",
  "style": "...",
  "notes": "..."
}
```

Runner 负责：

- 建 job；
- copy input；
- 选择 Skill；
- 创建 / 恢复 Codex thread；
- 指定 cwd；
- 设 sandbox；
- 收集结果；
- 发布 output；
- 更新 `job.json`。

---

# 29. Phase 3 — 进度显示

第一版不需要复杂实时可视化。

只需要：

```text
Queued
Preparing
Running Codex
Publishing output
Completed / Failed
```

如果实现简单，可以利用 SDK：

```text
TurnHandle.stream()
```

获得结构化通知。

但不要为了漂亮进度条把 Phase 3 扩展成复杂事件系统。

---

# 30. Phase 3 — 双击 Launcher

正常使用必须满足：

> **不打开终端，不激活环境，不输入命令，不手动输入 localhost 地址。**

Windows 第一版提供：

```text
Start Research Starter.cmd
```

或配套桌面快捷方式。

Launcher 负责：

1. 找到项目目录；
2. 检查 `.venv`；
3. 若首次运行且环境不存在，自动 bootstrap；
4. 使用 `.venv\Scripts\python.exe` / `pythonw.exe`；
5. 启动 FastAPI；
6. 等待本地端口 ready；
7. 自动用系统默认浏览器打开 `http://127.0.0.1:<port>`；
8. 正常运行不要求用户执行任何环境激活。

### 重要

不要把：

```text
cd ...
activate ...
uvicorn ...
```

写进 README 后就认为“入口已经完成”。

**双击启动是 Phase 3 的硬验收项。**

---

# 31. First-run 体验

第一次启动允许多一个初始化步骤，但仍然不要求用户输入命令。

理想流程：

```text
双击 Research Starter
        ↓
检测环境
        ↓
如缺失则自动准备
        ↓
检测 Codex 登录
        ↓
未登录：
自动打开 OpenAI 官方登录页
        ↓
登录成功
        ↓
进入 Research Starter 首页
```

绝对不要自己创建：

```text
OpenAI Email
OpenAI Password
```

输入框。

账号认证必须由 OpenAI 官方登录页面完成。

---

# 32. 当前不做的事情

本轮明确不做：

- Git/GitHub 同步；
- Obsidian Vault 迁移；
- Obsidian 新同步方案；
- Git 自动更新；
- macOS 实施；
- 家庭服务器部署；
- 多用户；
- 公网访问；
- 自定义人工审批 UI；
- EXE installer；
- Windows code signing；
- 自动软件更新；
- 数据库；
- Docker；
- MCP；
- RAG；
- paper-find；
- Zotero；
- 新 Skill；
- 重写三个旧 Skill。

这些以后全部作为独立任务考虑。

---

# 33. 为以后 macOS 留下的约束

虽然本轮只施工 Windows，但代码不得无理由写死：

```text
C:\
反斜杠路径
Windows 用户目录
固定 iCloud 地址
固定 Python exe 位置
```

统一使用：

```python
pathlib.Path
```

外部路径全部来自：

```text
config.local.json
```

Windows 特有内容只允许集中在 Launcher / bootstrap 层。

核心：

```text
runner/
skills/
web/
```

应尽量保持跨平台。

---

# 34. 施工中的错误处理原则

任何任务失败都应该至少记录：

```text
job_id
task
stage
error
timestamp
```

到：

```text
job.json
```

以及简单文本日志。

不要让 UI 只显示：

```text
Something went wrong
```

至少告诉用户：

```text
Codex login failed
PDF could not be read
Skill execution failed
PPT was not created
iCloud source file is unavailable locally
Obsidian Vault path is invalid
```

但不要第一版建立复杂 logging framework。

---

# 35. 迁移成功的最终验收场景

## Scenario A — Paper Guide

用户：

```text
双击 Research Starter
→ Paper Guide
→ 从 iCloud Inbox 选择 PDF
→ 点击开始
```

系统：

```text
复制 PDF 到 local job
→ SDK 调用 paper-guide
→ 显示导读
```

用户继续提问。

系统复用 thread 给出回答。

全过程不打开 Codex Desktop，不打开终端。

---

## Scenario B — Research Note

用户：

```text
双击 Research Starter
→ Research Note
→ 粘贴一段自己的科研理解
→ Preview
→ Save
```

系统：

```text
SDK 调用 research-note
→ 在指定 Obsidian Vault 搜索
→ 创建 / 更新对应 Markdown
```

不要求用户知道 notesmd-cli。

---

## Scenario C — Research Slides

用户：

```text
双击 Research Starter
→ Research Slides
→ 从 iCloud Inbox 选择 / 上传素材
→ 输入 PPT 页面逻辑
→ Generate
```

系统：

```text
copy 素材到 local job
→ SDK 调用 research-slides
→ local job 生成 PPTX
→ 验证文件
→ 本地完成并验证
→ 一次性 Copy-Out 到 iCloud Output
```

UI 最后提供：

```text
打开 PPT
打开输出目录
```

全过程不打开 Codex Desktop，不打开终端。

---

# 36. 本轮最终架构

```text
                  用户
                   │
          双击 Research Starter
                   │
              Local Web UI
                   │
              FastAPI Runner
                   │
          OpenAI Codex Python SDK
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
 paper-guide  research-note  research-slides
        │          │          │
        │          │          │
 local job    Obsidian Vault  local job
        │                     │
        └───────┐       ┌─────┘
                ▼       ▼
              iCloud exchange
             Inbox / Output
```

iCloud 不承担：

```text
runtime
cache
temp
venv
Codex state
Node modules
Docling intermediate files
```

---

# 37. Codex 的施工行为要求

Codex 在执行这份指南时：

1. 先检查旧项目；
2. 先写 `MIGRATION_BASELINE.md`；
3. 再创建新施工目录；
4. 每个 Phase 完成后实际执行 baseline tests；
5. 只有通过验收门才进入下一 Phase；
6. 不擅自更换指定技术栈；
7. 不擅自增加大型框架；
8. 不因为“更优雅”而重写已经能工作的 Skill；
9. 出现缺口先报告，而不是静默引入新依赖；
10. 优先保持工程简单、可读、可撤销。

---

# 38. 官方参考资料

## OpenAI Codex Python SDK

Getting Started:

https://github.com/openai/codex/blob/main/sdk/python/docs/getting-started.md

API Reference:

https://github.com/openai/codex/blob/main/sdk/python/docs/api-reference.md

FAQ:

https://github.com/openai/codex/blob/main/sdk/python/docs/faq.md

PyPI:

https://pypi.org/project/openai-codex/

关键官方能力：

- Python >= 3.10；
- SDK 自动安装匹配 runtime；
- ChatGPT browser login；
- `account()`；
- `models()`；
- `thread_start()` / `thread_resume()`；
- `SkillInput`；
- `cwd`；
- `Sandbox.workspace_write`；
- `ApprovalMode.auto_review`；
- `Thread.run()`；
- `Thread.turn()`；
- `stream()`；
- `interrupt()`。

---

# 39. 本轮优先级

如果遇到“功能完整”和“入口简单”之间的选择：

> **优先入口简单。**

如果遇到“架构优雅”和“保留已经验证的旧 Skill”之间的选择：

> **优先保留旧 Skill。**

如果遇到“未来可能扩展”和“当前结构简单”之间的选择：

> **优先当前结构简单。**

Research Starter 的正常使用方式最终必须是：

```text
双击
→ 选择任务
→ 提供内容
→ 点击运行
→ 获得结果
```

而不是：

```text
打开终端
→ 激活环境
→ 切目录
→ 输入命令
→ 记住参数
```

这不是额外优化项，而是本项目的核心验收要求。

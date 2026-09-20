# Research Starter v0.2 Migration Log

## 2026-09-11 — Phase 0

- 以只读方式盘点旧项目 `D:\Research\research_agent`。
- 冻结三个既有 Skill、运行时、输入输出位置与 A/B/C 固定测试，详见 `MIGRATION_BASELINE.md`。
- 旧项目与旧运行时保持不动。

## 2026-09-11 — Phase 1（完成）

### 环境

- 基础解释器：`C:\mambaforge\envs\research-starter-paper-guide\python.exe`，Python 3.12.14，仅用于创建新项目 `.venv`。
- 项目私有环境：`D:\Research\research_starter_SDK\.venv`。
- 已安装到项目 `.venv`：`openai-codex==0.147.0`、匹配 runtime、`docling==2.117.0`。
- 项目 Node 依赖：PptxGenJS 4.0.1、JSZip 3.10.1，位于项目 `node_modules`。
- notesmd-cli 保持独立：`C:\Tools\notesmd-cli\0.3.7\notesmd-cli.exe`。
- 旧 Docling 环境中不含 `openai-codex` 或匹配 runtime；`pip check` 正常。
- npm 对固定依赖报告 2 个 high severity 上游审计项。由于版本由施工指南固定，未执行会改变依赖版本的 `npm audit fix --force`。
- Docling 安装时 `antlr4-python3-runtime==4.9.3` 的隔离构建进程异常长时间无进展。中止后确认无部分 Docling 安装；在项目 `.venv` 安装 setuptools 84.0.0，并仅对该 sdist 使用 `--no-build-isolation` 成功构建，之后完整安装 Docling。未修改旧环境。

### Codex SDK smoke test

- `AsyncCodex` 初始化通过。
- 复用现有 ChatGPT Plus 登录，未显示或收集 OpenAI 密码。
- `account()` 与 `models()` 通过。
- `Sandbox.workspace_write`、`ApprovalMode.auto_review` 的最小 thread 通过。
- Smoke thread：`01a08f0e-c43a-7062-8b64-124d512584e5`。
- 输出 `.runtime/jobs/sdk-smoke/sdk-smoke-ok.txt` 已验证精确内容 `CODEX_SDK_SMOKE_OK`。
- Windows runtime 需要显式向子进程传入 `HOME` 与 `CODEX_HOME`；未修改系统环境变量。受限执行环境运行测试时还需允许 runtime 初始化其既有 Codex 用户状态目录。

### Test A — paper-guide：通过

- Job：`20260911-152347-c0d3`。
- Thread：`01a08f22-f457-7011-872f-43e6ea259871`。
- 固定 PDF 已复制到 Job input；旧文件未修改。
- 项目 `.venv` 内 Docling 解析成功，中间产物位于 Job temp。
- 导读生成于 Job output，并核验到 PDF page 5、Figure 5。
- 同一 Job、同一 thread 完成 Figure 5 局部追问；回答定位到对应 Section、Equation 15、Figure 4 及 page 6 的最小上下文，没有重新总结全文。

### Test C — research-slides：通过

- Job：`20260911-152817-9caf`。
- Thread：`01a08f27-156a-7ca2-9a79-d79f842396d7`。
- 既有 6 页 smoke-test 目录一次性复制到 Job input。
- 通过显式 `research-slides` Skill、既有生成脚本和项目 Node 依赖生成 PPTX。
- 验证 6 页、有效 OOXML、3 张原始 PNG 作为独立媒体对象、可编辑文本。
- 使用 Codex 随附演示渲染器渲染全部 6 页；自动检查无画布溢出，逐页目视检查未见文本截断、重叠或图片变形。

### Test B — research-note：通过

- SDK Skill turn 使用 notesmd-cli 搜索真实 Vault，并创建唯一临时笔记 `Inoue_lab/__research-note-v0.2-sdk-test-20260911__.md`。
- notesmd-cli 回读确认“已确认理解”和“未决问题”语义分离正确。
- 首次 turn 在写入和回读后遭遇 Codex 用量限制，因此 Runner 记录为 failed；实际目标写入已经完成，没有重复运行写入步骤。
- 删除前将 312-byte 测试笔记备份到项目 `.runtime/research-note-backup` 并核验 SHA-256；随后只删除精确测试路径。
- 用量恢复后，另一个严格只读 SDK turn 返回 completed，确认测试笔记已不存在且未修改 Vault。
- iCloud 主目录测试前后均为 1,424 个条目；新增 0、删除 0、扫描错误 0。唯一元数据变化是 `Inoue_lab` 目录修改时间，符合创建后删除文件的预期；没有发现或删除其他同步副本。

### Phase 1 验收门

- SDK 登录、账号、模型和最小 turn：通过。
- paper-guide 完整导读与同线程追问：通过。
- research-note 真实 Vault 搜索、受控写入、回读和清理：通过。
- research-slides 可编辑 PPTX、OOXML、独立图片、渲染与视觉检查：通过。
- 三个功能均显式使用原有 Skill，副本哈希与旧项目一致。
- 旧 Docling 和 notesmd-cli 健康检查通过，旧系统未被修改。

Phase 1 完成，允许进入 Phase 2。

## 2026-09-11 — Phase 2（完成）

### iCloud 交换层

- 建立 `D:\iclould\iCloudDrive\Research-Starter-Data\Inbox` 与 `Output`，三个功能各自拥有子目录；该结构不在 Obsidian Vault 内。
- Copy-In 前递归实际读取源文件并核对大小；不可读或变化中的文件会在 Codex 启动前失败。
- Codex cwd 和全部高频处理围绕本地 `.runtime/jobs/<job-id>`。
- 本地产物存在、非空并通过类型检查后，先复制为 `.uploading`，核对大小，再原子重命名为最终文件。
- Job 将科研任务状态与 `cloud_sync_status` 分开；Copy-Out 失败不会删除或降级本地结果。

### Phase 2 baseline

- paper-guide Job `20260911-163203-fb94`：从 iCloud Inbox 一次性 Copy-In，完整本地解析和生成，导读原子 Copy-Out 成功。
- research-note Job `20260911-163506-6713`：从 iCloud Inbox 一次性 Copy-In 两份既有夹具，搜索真实 Vault 并产生预览；未写入 Vault，cloud sync 标记为 not applicable。
- research-slides Job `20260911-163648-2acf`：从 iCloud Inbox 一次性 Copy-In，PPTX 完全在本地生成并验证后原子 Copy-Out。
- paper-guide 本地/云端导读均为 7,662 bytes，SHA-256 一致：`CC025D57CC2995B00F3F1E32AEC8266313EFD1483343658F5C6099F001010364`。
- research-slides 本地/云端 PPTX 均为 128,573 bytes，SHA-256 一致：`2F853A4B7A5FD0C00F7A7548E4B1D37706A3E10ED501326D3647D3096E87827D`。
- iCloud Output 中无 `.uploading` 残留；交换目录中无 `.runtime`、`.venv`、`node_modules`、cache 或 temp。

Phase 2 验收门通过，允许进入 Phase 3。

## 2026-09-11 — Phase 3（完成）

### Local Web UI

- 使用固定技术栈 FastAPI 0.141.1、Jinja2 3.1.6、原生 HTML/CSS/JavaScript；Uvicorn 0.52.4 只监听 `127.0.0.1:8765`。
- 主页提供 Paper Guide、Research Note、Research Slides、Recent Jobs 与 Settings。
- Paper Guide 支持 PDF 上传/iCloud Inbox 选择、Job 状态、结果打开及同 thread 追问。
- Research Note 使用 Preview → Save 两步；保存成功后记录 `note_saved` 并隐藏保存按钮，避免重复追加。
- Research Slides 支持多文件上传或 iCloud 任务目录选择，完成后提供 PPTX 下载与打开输出目录。
- 前端只提交结构化表单/API；Job、Skill 选择、cwd、sandbox、输出收集与发布均由 Runner 负责。
- 状态字段覆盖 created、running_codex、publishing_output、completed/failed。
- iCloud 选择路径限制在对应 task Inbox；下载路径限制在当前 Job output。

### Launcher

- `Start Research Starter.cmd` 直接调用项目 `.venv`，不要求 activate 或手工输入 localhost。
- 缺少 `.venv` 时只使用已确认的现有 Python 3.12.14 创建 venv；bootstrap 先处理已验证的 antlr sdist，再安装固定 requirements。
- Node 缺失时使用项目本地 npm cache 安装项目 `node_modules`。
- Launcher 启动 UI 前通过官方 SDK 检查 ChatGPT 登录；未登录时调用官方 `login_chatgpt()` 并打开官方认证 URL，不提供密码输入框。
- Windows 下 `pythonw.exe` 与当前 Conda 基础解释器组合会产生异常高 CPU 重定向进程，因此改为 PowerShell `Start-Process -WindowStyle Hidden` 启动项目 `python.exe`。该方式已实际验证。
- 最终双击等价测试：服务 PID 16280 监听 `127.0.0.1:8765`，`/health` 返回 ok；重复启动后 PID 不变，只打开已有页面。

### 最终检查

- 首页、三个任务页、Settings 与 health 均返回 HTTP 200。
- 非法 task 返回 400；Paper Guide 缺少 PDF 返回 400；不存在 Job 返回 404。
- Python `pip check` 通过；Node 顶层依赖版本正确。
- FastAPI TestClient 发出上游 `httpx`/`httpx2` 弃用提示，仅影响测试工具，不影响 Uvicorn 正常运行；未为此引入额外依赖。
- iCloud 最终残留扫描：临时 research-note 测试文件副本 0、`.uploading` 0、runtime 泄漏 0；交换层根目录只有一个 `Research-Starter-Data`。

Phase 3 验收门通过。Windows 本地 Research Starter v0.2 的 SDK、iCloud 交换层、Local Web UI 与双击 Launcher 已完成。

## 2026-09-11 — Research Note / Slides 素材目录修正

- 核查确认 Runner 的 `create_job` 和 iCloud copy-in 原本就支持目录 source；缺陷位于 Web 上传适配层，并非 Codex SDK 或 Skill 接口。
- Research Note 改为“一个素材文件夹必选、补充说明可选”；文字说明不再伪装成素材文件写入 Job input。
- Research Slides 改为选择一个素材文件夹；保留“内容 / 页面逻辑”字段。
- 浏览器使用目录选择控件，并在 multipart 上传时显式携带 `webkitRelativePath`；服务端按安全相对路径重建完整目录树，不再拍平文件名。
- 服务端对本地上传和 iCloud 选择统一执行 source shape 校验：Note/Slides 只接受一个非空目录，Paper Guide 只接受一个 PDF。
- 新增目录层级保持、散落文件、多根目录、路径穿越、Note 无文字说明和 iCloud 单文件拒绝测试；6 项测试全部通过，`pip check` 通过。
- 重启后 `/health`、Research Note 与 Research Slides 页面均正常；浏览器实测只填写 Note 补充说明不能提交，并显示“请选择一个素材文件夹”。
- 本轮未提交真实任务，未向 Vault 或 iCloud 写入。复扫 iCloud 主目录得到 1,750 个条目、0 个扫描错误；相较先前最终快照，新显现隐藏 `.Trash` 树（内容混有 Python 包目录和既有个人笔记）及既有 `Research-Starter-Data`。由于无法证明 `.Trash` 全部由本轮操作产生，未执行删除。

## 2026-09-11 — 附件、任务结果页、Codex 设置与语言控制修正

### Research Note 附件

- 复现用户最近的 Job `20260911-172605-a91e`：输入含两个 GIF，但生成笔记明确写着“不复制图片”，Vault `attachment` 中也没有对应文件。
- 根因是新项目复制的 Research Note Skill 仍保留 v0.1 的“不自动复制二进制附件”限制；Obsidian 本身的附件目录配置正常，仍为 `attachment`。
- 保存确认后，Runner 现在把 GIF、PNG、JPEG、SVG、WebP、BMP、AVIF 和 PDF 原子复制到 `attachment/Research-Starter/<job-id>/`，保留输入相对目录，并把每个精确 Vault 路径以 `![[...]]` 嵌入指令交给同一 Codex thread。
- GIF 保持原格式；保存状态和附件路径写入 Job，重复保存请求返回冲突，避免重复追加。
- 旧项目全程只读，未修改。既有用户笔记未自动修补；本轮附件验收全部在临时 Vault 完成。

### 差异化结果页

- 修复 CSS 通用 `button` 显示规则覆盖 HTML `hidden` 的问题。
- Paper Guide 结果页仅提供导读结果、输出文件与同 thread 继续提问。
- Research Note 结果页仅提供预览、附件说明及“连同附件写入 Obsidian”。
- Research Slides 结果页仅提供 PPTX 结果与输出目录，不再出现提问或 Obsidian 按钮。
- 运行中界面改为明确的 Codex 状态卡、脉冲指示、阶段说明；完成与失败使用不同状态颜色。

### Codex 与语言设置

- 使用 SDK 模型目录动态显示当前可用模型、默认模型、各模型默认推理等级及支持的推理等级。
- 使用 `account/rateLimits/read` 显示真实 5 小时和一周窗口的剩余百分比及重置时间；设置页可手动刷新。
- 三个任务均可选择中文、日本語或 English；语言、模型和推理等级写入 Job 并实际传给 Codex turn，选择会在浏览器本地记忆。
- 实测当前默认模型 `gpt-5.6-sol`、默认推理等级 `low`；限额数据成功返回（百分比会随使用和窗口重置变化）。

### 验收

- 10 项隔离自动测试全部通过，包含附件复制、Obsidian 嵌入路径、重复/错误输入、模型/推理/语言记录及三任务按钮分流。
- `pip check` 通过；localhost health、模型目录和限额接口通过。
- 浏览器视觉核验通过：任务页显示语言滑块、模型、推理等级和限额；三个结果页只显示各自允许的操作。
- 测试后扫描：真实 Vault 中不存在 `attachment/Research-Starter` 测试目录，iCloud 中 `.uploading` 为 0，测试标识残留为 0；本轮没有真实 Vault 或 iCloud 写入。

## 2026-09-12 — Research Note 本地检查与机械式云端发布

- 按用户的新要求覆盖原施工指南中“维持现有 Obsidian 交互”的旧约束；旧 Desktop 项目、旧 Skill 与旧环境仍保持不动。
- 审计确认旧链路会先把附件直接复制到云端 Vault，再让同一 Codex thread 调用 notesmd-cli 决定并执行 Markdown 写入；云端目标定位与写入因此仍由 Agent 参与。
- 新建项目私有 Vault `.runtime/obsidian-local-vault`，只镜像云端的精确边界 `Inoue_lab/Record`。首次初始化仅从该目录 Copy-In；若存在尚未发布的本地笔记，新任务会停止，避免刷新覆盖本地工作。
- Research Note Skill 改为纯分析与预览：只返回受约束的目标路径、create/append 模式及一份完整 Markdown；禁止调用 notesmd-cli、写文件、复制附件或修改云端 Vault。
- 用户确认后，Runner 以代码把 Markdown 与附件写入本地 Vault，并保留相同的 Vault 相对路径；写入使用临时文件、回读/哈希校验与替换，不依赖 activate 或全局 Python。
- UI 现在强制执行“确认写入本地 → 用 `D:\Obsidian\Obsidian.exe` 打开精确本地笔记 → 确认发布云端”。没有实际打开本地笔记时，云端发布入口不会出现且接口拒绝请求。
- 云端发布只允许写入 `Inoue_lab/Record`：先在 Job 临时目录组装完整 bundle，再以一次 robocopy 调用复制笔记和附件；不使用 move、不在云端生成内容，完成后逐文件 SHA-256 校验。
- 本地保存时记录云端同名笔记哈希；发布前若云端文件发生变化，会停止而不是覆盖。
- 26 项自动测试全部通过，包括附件仅落本地、未打开本地笔记时禁止发布、Obsidian URI 精确启动、笔记和附件只复制进 Record、云端并发变化停止发布、路径与 UI 分流；Research Note Skill 验证通过，前端脚本语法检查通过。
- 真实本地 Vault 已从现有云端 Record 只读初始化，包含原有 1 个 Markdown（1,363 bytes）。本轮未向真实 iCloud 写入测试文件，也未处理用户已存在的 iCloud 污染。

## 2026-09-12 — 本地 Obsidian 笔记打开修正

- 复现记录确认原按钮传入的是正确绝对路径，但 Obsidian 弹出无法找到 Vault；本地 Vault 当时不在 `%APPDATA%\obsidian\obsidian.json` 的已知 Vault 清单中，清单仅包含云端 `research`。
- 根据 Obsidian URI 的实际规则，绝对 `path` 仍需先匹配一个已登记、且包含该文件的 Vault；因此旧实现不是文件路径错误，而是缺少本地 Vault 登记。
- 首次点击现在会先读取并校验 Obsidian Vault 清单，把原配置备份到项目 `.runtime/obsidian-config-backups`，再以原子替换方式仅增加项目本地 Vault 条目；现有云端 Vault 条目保持不变。
- 打开 URI 改为已登记的 `vault ID + Vault 内相对 file path`，不再依赖 Obsidian 从绝对文件路径反推 Vault。
- 使用失败任务 `20260912-000548-b845` 做真实接口验证：本地 Vault 已登记为 `56f8caee6e754fbd`，目标笔记 URI 指向 `Inoue_lab/Record/Research/26.09.10_测试项目0910.md`，接口成功返回；没有触发云端发布。
- 26 项自动测试全部通过，覆盖首次登记备份、保留既有 Vault、URI 编码、打开前禁止发布和云端复制边界。

## 2026-09-12 — Research Note 同名笔记隔离修正

- 复盘偏光案例确认英文任务返回 `note_mode=append`，目标与既有中文笔记完全相同；旧保存逻辑会读取中文全文并在末尾追加英文预览，造成预览与落盘内容不一致。
- Research Note Skill 现在把旧笔记检索限定为目录与知识组织参考；每个新任务固定创建独立版本，不得因主题、素材或名称相同而自主追加。
- Runner 不再信任模型返回的 append 决策：新任务统一强制为 create；若目标已存在，按语言生成 `-zh`、`-ja`、`-en` 后缀，后缀仍冲突时增加数字编号。
- 保存层再次执行同样的防冲突检查，覆盖旧任务或异常模型响应；既有文件绝不作为新任务内容前缀读取。
- 保存完成后，Job 的 `note_preview` 更新为实际落盘 Markdown，因此附件路径替换后的页面预览与本地/云端版本一致。
- 新增同名中英文测试，验证英文保存为 `polarization-en.md`、中文原文件逐字不变、英文文件不含中文旧内容。27 项自动测试通过，Skill 校验与 Python/JavaScript 语法检查通过。
- 未自动拆分或修改用户已经发布的中英混合笔记，避免未经确认改写现有科研数据。

## 2026-09-12 — Research Slides 多版本预览与统一下载命名

- 旧 UI 只读取 `latest_pptx`，虽然历史 PPTX 均保留在 output 中，但无法在预览器切换；底部下载直接暴露原始文件名，修订版会显示随机 `revision-<id>.pptx`。
- API 现在依据 `slides_revisions` 的真实顺序建立稳定版本序列：V1 为初始版本，V2 起依次对应每次修订，不再受文件系统枚举顺序或随机文件名影响。
- PPTX 预览器增加上一版、版本下拉和下一版控制；切换后复用同一个轻量预览器载入所选版本，并显示该版对应的修改要求。新修订出现时自动选择最新版本。
- 页面底部下载项统一显示 V1/V2/V3、初始版本/第 N 次修订及简短修改要求；下载响应使用 `<项目名称>-Vn-初始版.pptx` 或 `<项目名称>-Vn-修订版-N.pptx`，磁盘中的原始历史文件保持不变。
- 回归测试覆盖两次修订的历史排序、最新版本标记和下载文件名，全部 27 项测试通过；Python 与 JavaScript 语法检查通过。

### 版本控件细节调整

- 根据实测反馈移除与版本下拉框功能重复的“上一版 / 下一版”按钮，预览区仅保留一个版本选择入口。
- 底部不再为每个 PPTX 展开一个下载按钮，改为“下载版本”下拉框与单一“下载所选版本”按钮。
- 预览与下载共用同一个当前版本状态：任一处切换版本都会同步另一处，并刷新预览和下载目标。
- 静态资源版本更新为 0.2.1.5；27 项测试及 JavaScript/Python 语法检查通过。

## 2026-09-12 — 产品化路径与可选云端配置审计

- 扫描业务代码、Launcher、独立 Python/Node 脚本和三个项目 Skill；排除 `.venv`、`node_modules`、运行记录、文档示例及包锁定文件中的非运行路径。
- 唯一硬编码的主机运行路径是 Launcher 中的基础 Python，以及 Obsidian 可执行文件的代码默认值。Launcher 现在只在 `.venv` 缺失时从 `config.local.json` 的 `base_python` 读取解释器；正常入口始终直接调用项目相对的 `.venv/Scripts/python.exe`。Obsidian 可执行文件改为必须由配置提供，不再带 D 盘默认值。
- Docling 固定从项目相对的 `.venv/Scripts/docling.exe` 解析；Skills 从 `skills/`、前端与 PPT 依赖从项目 `node_modules/` 解析。PowerPoint 模板合并通过系统 COM 注册调用，不包含安装路径。未发现其他业务绝对路径。
- SDK smoke-test 原先隐式使用当前 Windows 用户的 `~/.codex`，已改为读取 Settings 的 `codex_home`。iCloud 审计脚本的扫描根和输出本就是显式命令参数，无隐藏路径。
- `notesmd-cli` 已不被任何运行逻辑调用，故从 Settings、配置模型和示例配置中移除，避免在新主机形成虚假必装依赖。
- iCloud Inbox、iCloud Output、云端 Obsidian Vault 与 Inoue_lab 路径现在可以留空。无 iCloud 时任务页保留本地上传；无 iCloud Output 时本地 PPT 成功不再判作云发布失败；无云端 Obsidian 时 Research Note 可完整执行本地预览、保存与打开，仅禁用云端发布。
- 云端 Obsidian 的 Vault 与写入根要求同时填写或同时留空；配置时仍强制写入根位于 Vault 内。未配置情况下接口也会拒绝伪造的云端请求并给出明确提示。
- Settings 保存会立即替换 Web 进程使用的 Settings；新增测试确认修改 `local_jobs` 后随即生效。项目内部的 `local_jobs`、备用输出和本地 Vault 保存回 JSON 时保持项目相对路径，外部工具与云端位置保留主机配置路径。
- 根目录重复的旧 `app.py` 已收敛为 `web.app` 的兼容导入，避免另一入口继续运行过时代码。
- 新增基础 Python 配置读取、可选路径留空/重新加载、Settings 即时生效、无云端本地笔记等测试。31 项自动测试、pip check、全部 Python 编译检查及前端 JavaScript 语法检查通过。

## 2026-09-15 — 通用模型提供方与 Kimi K3

- 将 DeepSeek 专用的模型、密钥、连接验证和 Codex override 逻辑收敛为统一 provider 注册表；保留原 DeepSeek 加密文件路径和旧 API 别名，现有配置无需迁移。
- 新增 Kimi K3：直接使用 `https://api.moonshot.ai/v1` 的原生 Responses API，独立读取 `KIMI_API_KEY`，不依赖 OpenAI/Codex 登录。
- Kimi 模型目录按官方能力声明 1M 上下文、文本/图片输入和工具调用，并显式传入 `model_context_window=1048576`。
- Kimi K3 始终启用思考；UI 仅提供 low、high、max，软件默认 high，不提供不受支持的 none。
- DeepSeek 与 Kimi API Key 分别使用 Windows 当前用户 DPAPI 加密为 `.runtime/secrets/<provider>-api-key.bin`；UI、Git、配置文件和日志均不回显密钥。
- Settings、三个任务入口及 Paper Guide 后续对话改为读取 provider 元数据，不再为每个第三方模型复制一套前端判断。
- 46 项自动测试、8 项 Markdown 数学解析测试、pip check、Python 编译与 JavaScript 语法检查通过；开发版实际页面确认 Settings 和任务入口均显示 Kimi API。

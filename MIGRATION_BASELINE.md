# Research Starter v0.2 Migration Baseline

记录日期：2026-09-11  
旧系统（只读 baseline）：`D:\Research\research_agent`  
新施工目录：`D:\Research\research_starter_SDK`

## 保护边界

- 旧项目只作读取和回归对照，不在原地升级。
- 不修改三个既有 Skill，不替换旧 inbox/output，不删除旧环境。
- 本轮不做 Git/GitHub、服务器、macOS、Obsidian Vault 迁移或新功能。
- 必须依次通过 Phase 1、Phase 2、Phase 3 验收门。

## 既有 Skill 与调用方式

| 功能 | 既有 Skill | Desktop 调用入口 | 固定运行链路 |
|---|---|---|---|
| `paper-guide` | `D:\Research\research_agent\.agents\skills\paper-guide` | 附加/指定 PDF 后自然语言唤起 | Docling CLI 导出 Markdown + JSON，Codex 提供导读与局部问答 |
| `research-note` | `D:\Research\research_agent\.agents\skills\research-note` | 明确要求保存到 Obsidian | notesmd-cli 搜索/读取后，在允许范围内创建或追加 Markdown，并回读验证 |
| `research-slides` | `D:\Research\research_agent\.agents\skills\research-slides` | 指定 `inbox/research-slides/<任务>/` 后自然语言唤起 | Skill 形成计划，Node/PptxGenJS 脚本生成可编辑 PPTX，再作 OOXML 与视觉检查 |

三个 Skill 的 `SKILL.md`、`agents/openai.yaml` 及 `research-slides/scripts/generate_slides.mjs` 均属于已知可工作实现；迁移时只复制到新项目并显式交给 SDK，不重写其行为。

## 既有输入与输出

- 论文 inbox：`D:\Research\research_agent\inbox\papers`
- Research Note inbox：`D:\Research\research_agent\inbox\research-note\<任务名称>`
- Research Slides inbox：`D:\Research\research_agent\inbox\research-slides\<任务名称>`
- Research Slides 本地输出：`D:\Research\research_agent\outputs\research-slides`
- Obsidian Vault：`D:\iclould\iCloudDrive\iCloud~md~obsidian\research`
- Research Note 唯一允许写入根：`D:\iclould\iCloudDrive\iCloud~md~obsidian\research\Inoue_lab`

## 固定依赖与本机状态

| 组件 | 版本/路径 | 已验证状态 |
|---|---|---|
| Docling | `C:\mambaforge\envs\research-starter-paper-guide\Scripts\docling.exe` | 2.117.0；Core 2.95.0；IBM Models 3.15.0；Parse 7.18.0 |
| Docling Python | `C:\mambaforge\envs\research-starter-paper-guide\python.exe` | CPython 3.12.14 |
| notesmd-cli | `C:\Tools\notesmd-cli\0.3.7\notesmd-cli.exe` | v0.3.7；Vault `research` 已注册且路径正确 |
| Node.js | PATH 中的 `node` | v24.18.0 |
| npm | PATH 中的 `npm` | 11.16.0 |
| PptxGenJS | 旧项目 `package.json` | 4.0.1 |
| JSZip | 旧项目 `package.json` | 3.10.1 |

风险：PATH 中的 `python.exe` 指向不可执行的 WindowsApps 别名，且 `py` launcher 不存在。Phase 1 使用已验证的 `C:\mambaforge\envs\research-starter-paper-guide\python.exe` 创建项目独立 `.venv`；Codex SDK 及匹配 runtime 只安装到该 `.venv`。最终入口直接调用 `.venv\Scripts\python.exe`，不能依赖环境激活或 PATH 中的 `python`。

## 固定回归测试

### Test A — paper-guide

- 输入：`D:\Research\research_agent\inbox\papers\2021-Inverse-Design-of-Plasmonic-Structures-with-FDTD.pdf`
- 文件大小：2,388,571 bytes
- SHA-256：`F4757B956A87F515525E347B08BD7F7D38C26B422D3E4FE3CD5BAEB773B6D668`
- 解析方式：`docling <pdf> --to md --to json --output <temp> --abort-on-error --no-ocr`
- 预期：Markdown 与 JSON 均存在且非空；生成六项阅读导引，至少包含一个可核验的 Section/Figure/Equation/Table 定位；保存 SDK `thread_id`。
- 同线程追问：针对导引中已定位的一个 Figure 或 Section 提问，必须复用同一 thread 并回到局部上下文，不能重新做全文总结。

### Test B — research-note

- 隔离测试 Vault 夹具：
  - `D:\Research\research_agent\tests\fixtures\research-note-vault\Theory\fdtd-notes.md`
  - `D:\Research\research_agent\tests\fixtures\research-note-vault\Lab\laser-stability.md`
- 已验证测试内容：FDTD 网格尺寸影响数值色散与计算成本；激光功率漂移需要与环境温度分开检查，并保留探测器响应变化这一未决问题。
- 预期：先搜索和读取，再正确追加匹配笔记或创建测试笔记；区分已确认理解与未决问题；写入后回读验证；无明确保存意图时不写入。
- Phase 1 默认先在隔离 Vault 完成回归；对真实 iCloud Vault 的任何测试必须继续限制在 `Inoue_lab`，不得重构、移动或批量修改既有内容。

### Test C — research-slides

- 输入目录：`D:\Research\research_agent\inbox\research-slides\__v0.1-smoke-test__`
- 固定计划：目录内 `brief.md` 与 `plan.json`；6 页，3 张本地 PNG，页面顺序固定。
- 既有输出：`D:\Research\research_agent\outputs\research-slides\research-slides-v0.1-smoke-test.pptx`
- 既有输出大小：128,516 bytes
- 既有输出 SHA-256：`919A824DE65FF28D7E1CC6286DAE91B255B1C4B04FCAD0355629C2E65791196B`
- 预期：新 Job 的 `output/` 中生成 6 页标准 16:9 PPTX；3 张图片为独立媒体对象，文本保持可编辑；OOXML 可读取；渲染后无明显截断、重叠或变形；不改变给定顺序或补造科研结论。

另有真实样例 `X射线物理组会_2026-09-11.pptx`（1,065,405 bytes，SHA-256 `0866028FEB24CAA72FC6DC3593BA88933D496E696C72FA5116C7F8F094289253`），可用于结果等级对照，但不替代固定 smoke test。

## 旧系统验收证据与已知限制

- `paper-guide`：三篇公开数字原生 PDF 的 Docling Markdown/JSON 解析通过；OCR 下载失败路径能准确暴露。当前固定 PDF 可用作 SDK 迁移回归。
- `research-note`：隔离 Vault 的搜索、读取、创建、追加、回读均通过；真实 iCloud Vault 的受控临时写入曾通过。只能确认本机写入，不能声称 iCloud 云同步完成。
- `research-slides`：6 页 smoke test 的生成、OOXML、独立图片对象和逐页视觉检查通过；PptxGenJS 4.0.1 的悬空母版内容类型已由既有脚本做最小清理。
- 旧目录当前不是可由 `git -C` 识别的工作树；本轮本来也禁止 Git 同步，因此不作修复或初始化。

## Phase 0 结论

三个功能均已有可复用的 Skill、运行时路径和成功样例。Phase 0 baseline 已冻结，可以开始 Phase 1：在新目录建立独立 Python 环境、复制既有 Skill、先做 Codex Python SDK smoke test，再依次执行同一组 A/B/C 回归测试。Phase 1 未全部通过前，不进入 iCloud Copy-In/Copy-Out 或 Web UI 施工。

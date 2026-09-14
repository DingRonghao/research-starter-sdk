import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(process.cwd());
const skillDir = process.env.SKILL_DIR;
const runtimePython = process.env.RUNTIME_PYTHON;
const runtimeNodeModules = process.env.RUNTIME_NODE_MODULES;
if (!path.isAbsolute(skillDir || "") || !path.isAbsolute(runtimePython || "") || !path.isAbsolute(runtimeNodeModules || "")) throw new Error("Missing runtime paths");
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtimeNodeModules, "@oai/artifact-tool/dist/artifact_tool.mjs")).href);
const { resolvePresentationFont, applyPresentationChartFont, finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href);
const family = resolvePresentationFont();
const build = path.join(root, "tmp", "public-sample-slides");
const staging = path.join(build, ".codex-finalizer");
const output = path.join(root, "Output", "research-slides", "public-sample", "temperature-scan-example.pptx");
await fs.mkdir(staging, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const colors = { ink: "#18322A", body: "#31443E", accent: "#276B59", pale: "#F3F6F3", orange: "#C56B32", muted: "#65756E" };

function baseSlide(titleText) {
  const slide = deck.slides.add();
  slide.background.fill = "#FBFCFA";
  const title = slide.shapes.add({ geometry: "textbox", position: { left: 74, top: 48, width: 1130, height: 62 }, fill: "none", line: { fill: "none", width: 0 } });
  title.text = titleText;
  title.text.style = { typeface: family, fontSize: 34, bold: true, color: colors.ink, autoFit: "none" };
  return slide;
}

function addText(slide, text, position, options = {}) {
  const box = slide.shapes.add({ geometry: "textbox", position, fill: "none", line: { fill: "none", width: 0 } });
  box.text = text;
  box.text.style = { typeface: family, fontSize: options.fontSize || 22, bold: Boolean(options.bold), color: options.color || colors.body, autoFit: "none" };
  return box;
}

let slide = deck.slides.add();
slide.background.fill = colors.pale;
addText(slide, "温度扫描与归一化峰宽", { left: 92, top: 160, width: 1090, height: 90 }, { fontSize: 46, bold: true, color: colors.ink });
addText(slide, "公开合成案例 | Research Slides 完整流程测试", { left: 96, top: 270, width: 1000, height: 52 }, { fontSize: 23, color: colors.accent });
addText(slide, "100-300 K · 9 个温度点 · 每点 10 s 积分", { left: 96, top: 480, width: 900, height: 45 }, { fontSize: 20, color: colors.muted });
slide.speakerNotes.textFrame.setText("All values are synthetic and intended only for testing Research Starter.");

slide = baseSlide("问题与测量定义");
addText(slide, "研究问题", { left: 82, top: 155, width: 300, height: 48 }, { fontSize: 22, bold: true, color: colors.accent });
addText(slide, "升温过程中，归一化峰宽是否呈稳定的单调变化？", { left: 82, top: 205, width: 1060, height: 72 }, { fontSize: 30, bold: true });
addText(slide, "定义\n峰宽以 100 K 的拟合结果归一化。每个温度点采用相同的 10 s 积分时间，并报告合成标准差。", { left: 82, top: 355, width: 500, height: 170 }, { fontSize: 21 });
addText(slide, "解释边界\n单调趋势是观察结果。散射、展宽机制或仪器漂移仍需额外测量区分。", { left: 665, top: 355, width: 500, height: 170 }, { fontSize: 21 });
slide.speakerNotes.textFrame.setText("The normalization and uncertainty values are synthetic.");

slide = baseSlide("峰宽随温度单调下降");
const chart = slide.charts.add("line", {
  position: { left: 92, top: 145, width: 1080, height: 430 },
  categories: ["100", "125", "150", "175", "200", "225", "250", "275", "300"],
  series: [{ name: "归一化峰宽", values: [1.00, 0.96, 0.91, 0.86, 0.80, 0.75, 0.70, 0.66, 0.62], line: { fill: colors.accent, width: 3 } }],
  hasLegend: false,
  dataLabels: { showValue: true, position: "above" },
});
applyPresentationChartFont(chart, { fontFamily: family });
addText(slide, "温度 (K)", { left: 555, top: 590, width: 180, height: 35 }, { fontSize: 18, color: colors.muted });
slide.speakerNotes.textFrame.setText("Editable chart. Source: bundled temperature_scan.csv. Values are synthetic.");

slide = baseSlide("变化幅度与不确定性");
addText(slide, "38%", { left: 90, top: 165, width: 350, height: 105 }, { fontSize: 68, bold: true, color: colors.accent });
addText(slide, "100 K 到 300 K 的总降幅", { left: 95, top: 276, width: 430, height: 50 }, { fontSize: 22 });
addText(slide, "相邻区间降幅", { left: 650, top: 165, width: 400, height: 48 }, { fontSize: 24, bold: true, color: colors.ink });
addText(slide, "3.9%-6.6%", { left: 650, top: 225, width: 430, height: 80 }, { fontSize: 48, bold: true, color: colors.orange });
addText(slide, "趋势连续，但当前数据不足以判定具体物理机制。估计标准差从 0.030 降至 0.019，误差模型仍需真实重复实验验证。", { left: 95, top: 415, width: 1060, height: 125 }, { fontSize: 24 });
slide.speakerNotes.textFrame.setText("Calculated from the synthetic CSV. No real experimental claim is made.");

slide = baseSlide("局限与下一步测量");
addText(slide, "当前局限", { left: 85, top: 155, width: 440, height: 48 }, { fontSize: 24, bold: true, color: colors.orange });
addText(slide, "单次合成扫描无法排除温度滞后、拟合模型偏差和仪器漂移。归一化还会传播 100 K 参考点的不确定性。", { left: 85, top: 220, width: 480, height: 205 }, { fontSize: 23 });
addText(slide, "建议验证", { left: 685, top: 155, width: 440, height: 48 }, { fontSize: 24, bold: true, color: colors.accent });
addText(slide, "执行升温与降温双向扫描，检验滞后。\n\n加入稳定参考样品，区分样品变化与仪器漂移。", { left: 685, top: 220, width: 480, height: 205 }, { fontSize: 23 });
addText(slide, "结论：合成数据支持“峰宽随温度下降”的描述，但不支持未经验证的机制归因。", { left: 85, top: 535, width: 1080, height: 70 }, { fontSize: 25, bold: true, color: colors.ink });
slide.speakerNotes.textFrame.setText("This conclusion deliberately separates observation from mechanism.");

const candidate = path.join(staging, "candidate-v2.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidate);
await finalizePresentation({
  workspaceDir: root, candidatePath: candidate, finalPath: output, pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  explicitTotalSlideCount: 5, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [3],
  materializeLiteralChartWorkbooks: true,
  fontPolicy: { basis: "design", families: [family] }, verifyArtifactToolImport: true,
  receiptPath: path.join(staging, "temperature-scan-example-v2.validation.json"),
});

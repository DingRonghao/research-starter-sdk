import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

const root = path.resolve(process.cwd());
const skillDir = process.env.SKILL_DIR;
const runtimePython = process.env.RUNTIME_PYTHON;
const runtimeNodeModules = process.env.RUNTIME_NODE_MODULES;
if (!path.isAbsolute(skillDir || "") || !path.isAbsolute(runtimePython || "") || !path.isAbsolute(runtimeNodeModules || "")) throw new Error("Missing runtime paths");
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtimeNodeModules, "@oai/artifact-tool/dist/artifact_tool.mjs")).href);
const { resolvePresentationFont, finalizePresentation } = await import(
  pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href,
);
const family = resolvePresentationFont();
const build = path.join(root, "tmp", "public-sample-slides");
const staging = path.join(build, ".codex-finalizer");
const output = path.join(root, "Output", "research-slides", "public-sample", "temperature-scan-example.pptx");
await fs.mkdir(staging, { recursive: true });
await fs.mkdir(path.dirname(output), { recursive: true });

const deck = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const slide = deck.slides.add();
slide.background.fill = "#F7F8F6";
const title = slide.shapes.add({ geometry: "textbox", position: { left: 80, top: 62, width: 1120, height: 72 }, fill: "none", line: { fill: "none", width: 0 } });
title.text = "温度扫描实验示例";
title.text.style = { typeface: family, fontSize: 42, bold: true, color: "#18322A", autoFit: "none" };
const body = slide.shapes.add({ geometry: "textbox", position: { left: 84, top: 190, width: 1080, height: 320 }, fill: "none", line: { fill: "none", width: 0 } });
body.text = "实验目标\n观察温度变化与归一化信号之间的关系\n\n示例数据\n20 °C：0.41    30 °C：0.57    40 °C：0.76    50 °C：0.88\n\n说明\n这是随软件发布的合成案例，不代表真实实验结论。";
body.text.style = { typeface: family, fontSize: 25, color: "#253B34", autoFit: "none" };
slide.speakerNotes.textFrame.setText("All values are synthetic and are included only to demonstrate the completed-project preview.");
const candidate = path.join(staging, "candidate.pptx");
await (await PresentationFile.exportPptx(deck)).save(candidate);
await finalizePresentation({
  workspaceDir: root, candidatePath: candidate, finalPath: output, pythonExecutable: runtimePython,
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
  explicitTotalSlideCount: 1, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [],
  fontPolicy: { basis: "design", families: [family] }, verifyArtifactToolImport: true,
  receiptPath: path.join(staging, "temperature-scan-example.validation.json"),
});

import fs from "node:fs";
import fsp from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

function loadPptxGenJS() {
  try {
    return require("pptxgenjs");
  } catch (firstError) {
    const modulesRoot = process.env.CODEX_NODE_MODULES;
    if (modulesRoot) {
      return require(path.join(modulesRoot, "pptxgenjs"));
    }
    throw new Error(`找不到 pptxgenjs。请由 Codex 配置项目依赖后重试。原始错误：${firstError.message}`);
  }
}

function loadJSZip() {
  try {
    return require("jszip");
  } catch (firstError) {
    const modulesRoot = process.env.CODEX_NODE_MODULES;
    if (modulesRoot) return require(path.join(modulesRoot, "jszip"));
    throw new Error(`找不到 PptxGenJS 使用的 jszip。原始错误：${firstError.message}`);
  }
}

async function removeDanglingMasterDeclarations(pptxPath) {
  const JSZip = loadJSZip();
  const zip = await JSZip.loadAsync(await fsp.readFile(pptxPath));
  const contentTypesFile = zip.file("[Content_Types].xml");
  if (!contentTypesFile) throw new Error("PPTX 缺少 [Content_Types].xml。 ");
  let contentTypes = await contentTypesFile.async("string");
  contentTypes = contentTypes.replace(
    /<Override PartName="\/ppt\/slideMasters\/(slideMaster\d+\.xml)" ContentType="application\/vnd\.openxmlformats-officedocument\.presentationml\.slideMaster\+xml"\/>/g,
    (entry, fileName) => (zip.file(`ppt/slideMasters/${fileName}`) ? entry : ""),
  );
  zip.file("[Content_Types].xml", contentTypes);
  const normalized = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  await fsp.writeFile(pptxPath, normalized);
}

function parseArgs(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--plan") result.plan = argv[++i];
    else if (argv[i] === "--output") result.output = argv[++i];
    else if (argv[i] === "--help") result.help = true;
    else throw new Error(`未知参数：${argv[i]}`);
  }
  return result;
}

const args = parseArgs(process.argv.slice(2));
if (args.help || !args.plan || !args.output) {
  console.log("用法：node generate_slides.mjs --plan <计划.json> --output <结果.pptx>");
  process.exit(args.help ? 0 : 2);
}

const planPath = path.resolve(args.plan);
const outputPath = path.resolve(args.output);
const planDir = path.dirname(planPath);
const plan = JSON.parse(await fsp.readFile(planPath, "utf8"));

if (!Array.isArray(plan.slides) || plan.slides.length === 0) {
  throw new Error("计划必须包含至少一页 slides。 ");
}
if (plan.slides.length > 60) throw new Error("页数超过 60；请拆分演示文稿。 ");

const allowedLayouts = new Set(["title", "body", "figure", "two-column", "comparison", "conclusion"]);
for (const [index, slide] of plan.slides.entries()) {
  if (!allowedLayouts.has(slide.layout)) throw new Error(`第 ${index + 1} 页布局不受支持：${slide.layout}`);
  if (!slide.title || typeof slide.title !== "string") throw new Error(`第 ${index + 1} 页缺少标题。`);
}

const PptxGenJS = loadPptxGenJS();
const pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = plan.meta?.author || "";
pptx.company = plan.meta?.organization || "";
pptx.subject = plan.meta?.subject || "Scientific presentation";
pptx.title = plan.meta?.title || plan.slides[0].title;
pptx.lang = plan.meta?.language || "zh-CN";
const C = {
  background: plan.theme?.background || "F7F8FA",
  text: plan.theme?.text || "172033",
  muted: plan.theme?.muted || "566176",
  accent: plan.theme?.accent || "2864DC",
  line: plan.theme?.line || "D9DEE8",
};
const fontFace = plan.theme?.fontFace || "Aptos";

function addBase(slide, index, title) {
  slide.background = { color: C.background };
  slide.addText(title, {
    x: 0.72, y: 0.42, w: 11.85, h: 0.55,
    fontFace, fontSize: 32, bold: true, color: C.text,
    margin: 0, breakLine: false, fit: "shrink",
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 0.72, y: 1.08, w: 11.85, h: 0,
    line: { color: C.line, width: 1 },
  });
  slide.addText(String(index + 1), {
    x: 12.15, y: 7.04, w: 0.42, h: 0.2,
    fontFace, fontSize: 9, color: C.muted, align: "right", margin: 0,
  });
}

function bulletText(items = []) {
  return items.map((item) => `• ${String(item)}`).join("\n");
}

function addBullets(slide, items, box) {
  if (!items?.length) return;
  slide.addText(bulletText(items), {
    ...box, fontFace, fontSize: 22, color: C.text,
    breakLine: false, breakLineOnOverflow: false,
    margin: 0.08, paraSpaceAfterPt: 12, valign: "mid", fit: "shrink",
  });
}

function resolveAsset(relativePath) {
  if (!relativePath) throw new Error("图片布局缺少 image 路径。 ");
  const resolved = path.resolve(planDir, relativePath);
  const relative = path.relative(planDir, resolved);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`图片必须位于计划文件所在的任务目录内：${relativePath}`);
  }
  if (!fs.existsSync(resolved)) throw new Error(`找不到图片：${resolved}`);
  return resolved;
}

function addImage(slide, relativePath, box) {
  slide.addImage({
    path: resolveAsset(relativePath),
    x: box.x, y: box.y, w: box.w, h: box.h,
    sizing: { type: "contain", w: box.w, h: box.h },
  });
}

function addColumn(slide, column, box) {
  if (column?.heading) {
    slide.addText(column.heading, {
      x: box.x, y: box.y, w: box.w, h: 0.42,
      fontFace, fontSize: 22, bold: true, color: C.accent, margin: 0, fit: "shrink",
    });
  }
  const top = box.y + (column?.heading ? 0.55 : 0);
  if (column?.image) {
    const imageHeight = column?.bullets?.length ? 3.25 : box.h - (top - box.y);
    addImage(slide, column.image, { x: box.x, y: top, w: box.w, h: imageHeight });
    if (column?.bullets?.length) addBullets(slide, column.bullets, { x: box.x, y: top + imageHeight + 0.18, w: box.w, h: 1.5 });
  } else {
    addBullets(slide, column?.bullets || [], { x: box.x, y: top, w: box.w, h: box.h - (top - box.y) });
  }
}

for (const [index, spec] of plan.slides.entries()) {
  const slide = pptx.addSlide();

  if (spec.layout === "title") {
    slide.background = { color: C.background };
    slide.addShape(pptx.ShapeType.line, { x: 0.9, y: 1.15, w: 1.1, h: 0, line: { color: C.accent, width: 4 } });
    slide.addText(spec.title, {
      x: 0.9, y: 1.55, w: 11.25, h: 1.7,
      fontFace, fontSize: 44, bold: true, color: C.text, margin: 0, valign: "mid", fit: "shrink",
    });
    if (spec.subtitle) slide.addText(spec.subtitle, { x: 0.92, y: 3.55, w: 10.8, h: 0.62, fontFace, fontSize: 23, color: C.muted, margin: 0, fit: "shrink" });
    if (spec.author || plan.meta?.author) slide.addText(spec.author || plan.meta.author, { x: 0.92, y: 6.4, w: 7.5, h: 0.38, fontFace, fontSize: 17, color: C.muted, margin: 0 });
  } else {
    addBase(slide, index, spec.title);
    if (spec.layout === "body" || spec.layout === "conclusion") {
      if (spec.body) slide.addText(spec.body, { x: 0.82, y: 1.48, w: 11.55, h: 1.0, fontFace, fontSize: 22, color: C.text, margin: 0, fit: "shrink" });
      addBullets(slide, spec.bullets || [], { x: 0.88, y: spec.body ? 2.7 : 1.45, w: 11.35, h: spec.body ? 3.7 : 4.95 });
    } else if (spec.layout === "figure") {
      addImage(slide, spec.image, { x: 0.82, y: 1.35, w: spec.bullets?.length ? 8.25 : 11.7, h: 5.35 });
      if (spec.bullets?.length) addBullets(slide, spec.bullets, { x: 9.35, y: 1.55, w: 3.0, h: 4.75 });
      if (spec.caption) slide.addText(spec.caption, { x: 0.92, y: 6.78, w: 10.8, h: 0.27, fontFace, fontSize: 11, color: C.muted, margin: 0, fit: "shrink" });
    } else if (spec.layout === "two-column" || spec.layout === "comparison") {
      addColumn(slide, spec.left || {}, { x: 0.82, y: 1.38, w: 5.55, h: 5.45 });
      slide.addShape(pptx.ShapeType.line, { x: 6.66, y: 1.45, w: 0, h: 5.15, line: { color: C.line, width: 1 } });
      addColumn(slide, spec.right || {}, { x: 6.96, y: 1.38, w: 5.55, h: 5.45 });
    }
  }

  if (Array.isArray(spec.notes) && typeof slide.addNotes === "function") slide.addNotes(spec.notes);
}

await fsp.mkdir(path.dirname(outputPath), { recursive: true });
await pptx.writeFile({ fileName: outputPath });
await removeDanglingMasterDeclarations(outputPath);
console.log(`已生成 ${plan.slides.length} 页：${outputPath}`);

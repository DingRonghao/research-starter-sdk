---
name: ppt-template-loader
description: 对一个可复用 PPTX 模板执行一次性的完整视觉与结构分析，生成供 Research Slides 后续任务直接检索和施工的持久化模板档案；不生成研究演示文稿。
---

# PPT Template Loader

## 任务边界

这是模板的一次性载入阶段。只理解模板，不制作研究演示文稿，不改写模板原件，也不分析未来任务的科研素材。模板必须同时经过视觉检查和结构检查，两者的结论要合并为一个可供后续 Agent 直接使用的模板档案。

## 分析流程

1. 确认输入目录中唯一的 PPTX，并保持模板原件只读。
2. 把全部模板页渲染为清晰截图，逐页查看。视觉分析覆盖构图、视觉重心、信息层级、留白、色彩、重复元素以及各区块在表达中的实际作用。
3. 解析 PPTX 的页面、母版、版式、主题和对象树。逐页记录对象 ID、类型、坐标、尺寸、占位符、文字容量、字体、图表、表格、图片、组合对象及其关系。
4. 将视觉观察与对象树对应起来。例如，不只记录“三个矩形”，还要说明它们在视觉上构成三项并列比较，并列出对应对象 ID。
5. 为每页给出：页面角色、适合场景、不适合承载的内容、合理信息容量、可替换区块、应保留元素、编辑风险、搜索关键词。描述应帮助后续 Agent 根据逐页内容计划快速匹配模板页。
6. 汇总模板的设计语言、页面家族、母版与主题约束、可复用原生图表或表格、页眉页脚和结束页规则。

## 输出

在 Runner 指定目录内只生成：

- `profile.json`：机器可检索的完整档案；
- `profile.md`：面向后续 Agent 的语义化使用指南。

`profile.json` 顶层至少包含：

下面的字段名是 Runner 读取的固定协议，不是示意命名。保持这些字段位于顶层并原样拼写；`schema_version` 使用整数 `1`。可以增加辅助字段，但不以 `profile_version`、`source`、`page_catalogue` 等替代固定字段，也不把固定字段移入嵌套对象。模板档案按模板文件名关联。

```json
{
  "schema_version": 1,
  "template_name": "原文件名",
  "slide_count": 1,
  "slide_size": {"width": 0, "height": 0, "unit": "in"},
  "design_system": {},
  "masters_and_layouts": [],
  "slide_families": [],
  "reusable_components": [],
  "slides": []
}
```

每个 `slides` 项至少包含：

```json
{
  "slide_number": 1,
  "visual_role": "封面",
  "suitable_for": ["论文题目与作者信息"],
  "not_suitable_for": ["密集正文"],
  "capacity": {"summary": "一个短标题和少量元信息"},
  "search_keywords": ["封面", "标题页"],
  "layout_and_visual_description": "页面视觉结构及区块关系",
  "objects": [{"shape_id": 1, "type": "text", "role": "主标题", "geometry": {}}],
  "preserve": [],
  "replace": [],
  "editing_cautions": []
}
```

对象清单需要足以支持后续定点编辑，但避免把原始 XML 全量复制进 JSON。`profile.md` 应以页面家族和使用场景组织，使 Agent 能先按表达目的缩小候选页，再查阅具体页面与对象。

## 验证

- 模板全部页面都同时完成视觉和结构检查；
- JSON 中页数与 PPTX 一致，页码无缺失和重复；
- 每页的视觉区块能够对应到具体对象或母版元素；
- 适用场景描述具有区分度，而非所有页面都使用相同泛化措辞；
- 输出档案不包含未来科研内容，也不包含对模板原件的修改。

/*
 * build_jiaodishu.js — 电池交底书 docx 构建脚本（海辰模板，正文楷体，A4）
 *
 * 用法：
 *   1) 复制到工作目录；把 5 张图存为 fig/f1.png … fig/f5.png（缺图会自动用占位段落代替）。
 *   2) 只改下方【CONTENT 区】：CONFIG / DEFECTS / SOLUTIONS / EFFECTS / IDEA_ROWS / 图的 img 调用与宽高比。
 *   3) node build_jiaodishu.js   （若无 docx 包：npm i docx）
 *   4) 用 docx validate.py 校验；soffice 转 PDF 预览；present_files 交付。
 * 联系人(何争/296133514@qq.com/13696988197)、楷体、A4、表格、图片/图题辅助已内置，无需改动下方【脚手架区】。
 */
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType, VerticalAlign
} = require("docx");

/* ============================== 【CONTENT 区：按发明填写】 ============================== */
const CONFIG = {
  subtitle: "（结构类）",                 // 或 "（软件 / 方法类）"
  title_name: "一种……的结构 / 方法 / 系统",   // 提案名称
  field: "……领域；特别涉及……，用于……。",     // 技术领域（一句话）
  note: "注：本提案为结构类发明，下文附图采用……（黑白线条图），各结构、步骤均附数字标号。",
  outfile: "交底书_XXX.docx",
};

// 现有技术（2 段散文）
const PRIOR_ART = [
  "（第1段：背景与现状，可用长时储能/厚涂层语境。）",
  "（第2段：现有做法虽可行但有结构性局限，为缺陷铺垫。）",
];

// 技术缺陷（分条，[加粗小标题, 说明]）
const DEFECTS = [
  ["（1）核心物理缺陷。", "……"],
  ["（2）直接后果之一。", "……"],
  ["（3）……。", "……"],
  ["（4）……。", "……"],
  ["（5）现有改善手段不解决根因。", "……"],
];

// 附图说明 + 标号
const FIG_LIST = [
  "图1  ……结构示意图；",
  "图2  ……对比曲线；",
  "图3  ……机理 / 映射；",
  "图4  ……制造流程图 / 系统架构图；",
  "图5  ……技术效果 / 外推曲线。",
];
const FIG_LABELS = "1—……；2—……；3—……；H—……；S1～S5—……。";

// 3.1 方案A：用 [类型, 内容] 段落序列；类型 'lead'=加粗引导段, 'p'=正文, 'fig'=插图([path,ratio,题])
const SOLUTION_A = [
  ["lead", "结构组成（参见图1）：", "极片包括……（引用数字标号）。"],
  ["fig", "fig/f1.png", 0.66, "图1  ……结构示意图"],
  ["lead", "关键参数范围（用于支撑权利要求）：", "……（示意区间）。"],
  ["lead", "功能性界定（权利要求核心）：", "……被配置成使……相对……更……。"],
  ["lead", "作用机理（参见图2）：", "……。"],
  ["fig", "fig/f2.png", 0.60, "图2  ……对比曲线"],
  ["lead", "设计判据（仿真驱动，受保护对象为结构）：", "剖面/参数由仿真求解；请求保护落入界定范围的结构本身及制造方法，而非仿真算法。"],
  ["lead", "制造方法（参见图4）：", "S1……；S2……；S3……；S4……；S5……。"],
  ["fig", "fig/f4.png", 1.18, "图4  ……制造流程图"],
];
// 3.2 / 3.3 拓展（段落序列同上）
const SOLUTION_B = [
  ["p", "在方案 A 的基础上，……（细化/优化/梯度化/概率化/迁移）。"],
];
const SOLUTION_C = [
  ["p", "在方案 A/B 的基础上，……（另一维度拓展 / 双功能 / 协同 / 系统与存储介质）。"],
  ["fig", "fig/f5.png", 0.60, "图5  ……技术效果 / 外推曲线"],
];
// 3.4 技术效果：A 为推理条目数组；B/C 各一段
const EFFECT_A = [
  "① 因……→因此……。",
  "② 因……→因此……。",
  "③ 因……→因此……。",
];
const EFFECT_B = "信息……（方案B效果）。";
const EFFECT_C = "在……（方案C效果）。";
const EFFECT_NOTE = "说明：图中数值为示意，具体需结合本体系仿真与实测标定确定。";

// 发明构思总结 改进点 1-5
const IDEA_ROWS = [
  ["改进点1", "……（核心结构特征，区别于现有）。"],
  ["改进点2", "……（功能判据 / 设计判据与受保护对象切分）。"],
  ["改进点3", "……（制造方法）。"],
  ["改进点4", "……（方案B 拓展）。"],
  ["改进点5", "……（方案C 拓展 / 下游动作 / 系统形态）。"],
];
/* ============================ 【CONTENT 区结束】 ============================ */


/* ================================ 【脚手架区：通常不改】 ================================ */
const CW = 9026;                                   // A4 正文宽 (DXA)
const BODY = { ascii: "Times New Roman", eastAsia: "楷体", hAnsi: "Times New Roman" };  // 正文楷体
const HEAD = { ascii: "Times New Roman", eastAsia: "楷体", hAnsi: "Times New Roman" };  // 标题也用楷体(加粗)
const CONTACT = { name: "何争", email: "296133514@qq.com", phone: "13696988197" };

const P = (text, o = {}) => new Paragraph({
  spacing: { line: 340, lineRule: "auto", after: o.after ?? 120, before: o.before ?? 0 },
  alignment: o.align, indent: o.indent,
  children: [new TextRun({ text, font: o.font || BODY, size: o.size || 21, bold: o.bold || false, italics: o.italics || false })],
});
const PR = (runs, o = {}) => new Paragraph({
  spacing: { line: 340, lineRule: "auto", after: o.after ?? 120, before: o.before ?? 0 },
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b || false, font: r.f || BODY, size: r.s || 21 })),
});
const H = (text, level) => new Paragraph({
  heading: level, spacing: { before: 220, after: 120 },
  children: [new TextRun({ text, font: HEAD, bold: true,
    size: level === HeadingLevel.HEADING_1 ? 28 : (level === HeadingLevel.HEADING_2 ? 25 : 23) })],
});
const border = { style: BorderStyle.SINGLE, size: 4, color: "888888" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 110, right: 110 };
const cell = (w, runs, o = {}) => new TableCell({
  borders, width: { size: w, type: WidthType.DXA }, margins: cellMargins,
  columnSpan: o.span, verticalAlign: VerticalAlign.CENTER,
  shading: o.shade ? { fill: o.shade, type: ShadingType.CLEAR } : undefined,
  children: (Array.isArray(runs) ? runs : [runs]).map(rr =>
    new Paragraph({ spacing: { line: 300, lineRule: "auto", after: 0 },
      children: [new TextRun({ text: rr, font: o.font || BODY, size: o.size || 20, bold: o.bold || false })] })),
});
const cap = (t) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
  children: [new TextRun({ text: t, font: BODY, size: 19, italics: true })] });
// 图片：缺文件则用占位段落，保证脚本可运行
function maybeImg(p, wpx, ratio, title) {
  if (p && fs.existsSync(p)) {
    return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 60 },
      children: [new ImageRun({ type: "png", data: fs.readFileSync(p),
        transformation: { width: wpx, height: Math.round(wpx * ratio) },
        altText: { title, description: title, name: title } })] });
  }
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 60 },
    children: [new TextRun({ text: `［图占位：${title}（请将 PNG 放到 ${p}）］`, font: BODY, size: 20, italics: true, color: "888888" })] });
}
// 段落序列渲染（用于方案 A/B/C）
function seq(arr) {
  const out = [];
  for (const item of arr) {
    if (item[0] === "lead") out.push(PR([{ t: item[1], b: true }, { t: item[2] }]));
    else if (item[0] === "p") out.push(P(item[1]));
    else if (item[0] === "fig") { out.push(maybeImg(item[1], 480, item[2], item[3])); out.push(cap(item[3])); }
  }
  return out;
}

const W = [1450, 1820, 900, 1806, 1250, 1800], spanW = CW - W[0];
const infoTable = new Table({
  width: { size: CW, type: WidthType.DXA }, columnWidths: W,
  rows: [
    new TableRow({ children: [
      cell(W[0], "技术联系人", { shade: "EFEFEF", bold: true }), cell(W[1], CONTACT.name),
      cell(W[2], "邮箱", { shade: "EFEFEF", bold: true }), cell(W[3], CONTACT.email),
      cell(W[4], "联系方式", { shade: "EFEFEF", bold: true }), cell(W[5], CONTACT.phone) ]}),
    new TableRow({ children: [
      cell(W[0], "专利工程师", { shade: "EFEFEF", bold: true }), cell(W[1], ""),
      cell(W[2], "邮箱", { shade: "EFEFEF", bold: true }), cell(W[3], ""),
      cell(W[4], "联系方式", { shade: "EFEFEF", bold: true }), cell(W[5], "") ]}),
    new TableRow({ children: [
      cell(W[0], "创新方式", { shade: "EFEFEF", bold: true }),
      cell(spanW, "☒ 自行研发      ☐ 合作研发（合作单位：________）      ☐ 委托研发（委托单位：________）", { span: 5 }) ]}),
    new TableRow({ children: [
      cell(W[0], "提案名称", { shade: "EFEFEF", bold: true }),
      cell(spanW, CONFIG.title_name, { span: 5, bold: true }) ]}),
    new TableRow({ children: [
      cell(W[0], "技术领域", { shade: "EFEFEF", bold: true }),
      cell(spanW, CONFIG.field, { span: 5 }) ]}),
  ],
});
const IW = [1800, 7226];
const ideaTable = new Table({
  width: { size: CW, type: WidthType.DXA }, columnWidths: IW,
  rows: [ new TableRow({ children: [ cell(CW, "发明构思总结（相对现有产品的重要改进点）", { span: 2, shade: "EFEFEF", bold: true }) ]}),
    ...IDEA_ROWS.map(([k, v]) => new TableRow({ children: [ cell(IW[0], k, { shade: "F7F7F7", bold: true }), cell(IW[1], v) ]})) ],
});

const children = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
    children: [new TextRun({ text: "专利技术交底书", font: HEAD, bold: true, size: 40 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: CONFIG.subtitle, font: HEAD, bold: true, size: 24 })] }),
  H("一、基本信息", HeadingLevel.HEADING_1), infoTable,
  P(CONFIG.note, { before: 40, after: 80, italics: true, size: 18 }),
  H("二、技术内容", HeadingLevel.HEADING_1),
  H("1、现有产品技术情况", HeadingLevel.HEADING_2), ...PRIOR_ART.map(t => P(t)),
  H("2、现有产品存在的技术缺陷或问题", HeadingLevel.HEADING_2),
  P("现有做法存在以下技术缺陷："),
  ...DEFECTS.map(([a, b]) => PR([{ t: a, b: true }, { t: b }])),
  H("3、详细介绍为了解决该缺陷或问题的技术方案", HeadingLevel.HEADING_2),
  P("本提案核心思路：……。下文给出最优方案 A 及两个拓展方案 B、C。"),
  PR([{ t: "【附图说明】", b: true, f: HEAD }], { after: 40 }),
  ...FIG_LIST.map(t => P(t, { after: 30 })),
  PR([{ t: "附图主要标号：", b: true }, { t: FIG_LABELS }]),
  H("3.1、技术方案 A【本方案为解决对应技术问题的最优方案】", HeadingLevel.HEADING_3), ...seq(SOLUTION_A),
  H("3.2、技术方案 B【本方案为以上最优方案的拓展方案】", HeadingLevel.HEADING_3), ...seq(SOLUTION_B),
  H("3.3、技术方案 C【本方案为以上最优方案的另一拓展方案】", HeadingLevel.HEADING_3), ...seq(SOLUTION_C),
  H("3.4、改进后的技术效果", HeadingLevel.HEADING_3),
  PR([{ t: "方案 A 的技术效果（以推理方式说明）：", b: true }], { after: 40 }),
  ...EFFECT_A.map(t => P(t, { after: 60 })),
  PR([{ t: "方案 B 的技术效果：", b: true }, { t: EFFECT_B }], { after: 80 }),
  PR([{ t: "方案 C 的技术效果：", b: true }, { t: EFFECT_C }], { after: 80 }),
  P(EFFECT_NOTE, { before: 40, after: 120, italics: true, size: 18 }),
  H("4、发明构思总结", HeadingLevel.HEADING_1), ideaTable,
];

const doc = new Document({
  styles: { default: { document: { run: { font: BODY, size: 21 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: HEAD }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, font: HEAD }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 23, bold: true, font: HEAD }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
    ] },
  sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children }],
});
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(CONFIG.outfile, buf); console.log("WROTE", CONFIG.outfile); });

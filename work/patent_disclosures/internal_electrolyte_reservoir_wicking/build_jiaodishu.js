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
  subtitle: "（结构类）",
  title_name: "一种用于长时储能电芯的内置电解液储库及芯吸补液结构",
  field: "属于锂离子储能电芯结构与电解液保持技术领域；特别涉及一种集成在大容量方壳储能电芯内、按长寿命电解液消耗量定容并通过芯吸路径被动补液的电解液储库结构。",
  note: "注：本提案为结构类发明，下文附图采用黑白线条图，各结构、工艺步骤和功能区域均附数字或步骤标号。",
  outfile: "交底书_内置电解液储库及芯吸补液结构.docx",
};

// 现有技术（2 段散文）
const PRIOR_ART = [
  "长时储能电芯通常采用大容量方壳结构和较厚的正负极涂层，在万次级慢循环、长期静置和高温运行过程中，电解液会因 SEI 持续生长、副反应消耗、气体带液、局部润湿网络退化和端部/角部传输路径不足而逐渐出现贫液或干涸。该问题在短期循环、出厂容量测试或常规数百周验证中不明显，但在长寿命储能应用中会逐渐表现为 DCR 后期增长、极化温升增加、容量 knee 提前和局部析锂风险上升。",
  "现有改善手段主要包括提高初始注液量、延长真空静置、优化化成脱气、在壳体或顶盖中设置储液腔、或者通过返修/二次注液补充电解液。公开技术中也可见储液空间、补充电解液腔以及吸液/芯吸材料的设计。上述方案虽能改善初期浸润或提供补液可能，但通常未针对长时储能电芯的万次循环电解液消耗量进行定容，也未将补液路径与端部、角部、厚度方向等后期干涸热点进行匹配，更缺乏使补液集中发生在循环后期的被动限流结构。",
];

// 技术缺陷（分条，[加粗小标题, 说明]）
const DEFECTS = [
  ["（1）初始过量注液不能准确覆盖长寿命消耗。", "单纯增加初始注液量会带来能量密度下降、游离液增加、化成带液和安全气隙压缩等问题，且不能保证电解液在循环后期仍位于贫液热点。"],
  ["（2）后期贫液具有空间非均匀性。", "大容量厚电芯的端部、角部、卷绕拐角或厚度方向中部容易形成低润湿区，常规均匀注液难以在长期循环后持续补偿这些局部区域。"],
  ["（3）现有储液结构多偏向初期浸润或被动存液。", "储液腔、流道或多孔件若未设置容量、路径和释放速率的匹配关系，可能在早期释放过快或长期留存在非反应区域，难以针对后期干涸发挥作用。"],
  ["（4）外部二次注液或返修工艺不适合在役储能电站。", "大规模储能系统在役阶段拆解、补液和重新封装成本高且风险大，难以作为常规寿命维护手段。"],
  ["（5）现有设计缺少可量化寿命判据。", "多数方案只描述储液或导液结构本身，未把储库容量与目标循环寿命、电解液消耗量、容量损失或 DCR 增长进行工程匹配。"],
];

// 附图说明 + 标号
const FIG_LIST = [
  "图1  内置电解液储库与芯吸补液结构示意图；",
  "图2  储库定容与循环后期补液效果示意图；",
  "图3  储库-芯吸路径的补液机理示意图；",
  "图4  储库与芯吸结构的设计制造流程图；",
  "图5  贫液均化与 DCR 增长抑制效果示意图。",
];
const FIG_LABELS = "1—方壳壳体；2—卷芯/叠芯主体；3—定容储库；4、4a、4b、4c—芯吸路径；5—限流膜；6a—端部贫液热点；6b—中段低润湿区；6c—角部贫液热点；7—储库固定/隔离支架；Vr—储库补偿电解液容量；S1～S5—消耗模型建立、热点确定、储库制备、路径布置、装配验证步骤。";

// 3.1 方案A：用 [类型, 内容] 段落序列；类型 'lead'=加粗引导段, 'p'=正文, 'fig'=插图([path,ratio,题])
const SOLUTION_A = [
  ["lead", "结构组成（参见图1）：", "本方案在方壳壳体 1 内设置卷芯/叠芯主体 2、定容储库 3、芯吸路径 4、限流膜 5 和储库固定/隔离支架 7。定容储库 3 布置在顶盖内侧、壳体侧壁、卷芯端面或角部非活性空间中的至少一种位置，内部容纳补偿电解液 Vr；芯吸路径 4 从储库出口延伸至端部贫液热点 6a、中段低润湿区 6b 或角部贫液热点 6c，且与焊接区、泄压通道和极耳根部保持绝缘隔离。"],
  ["fig", "fig/f1.png", 0.67, "图1  内置电解液储库与芯吸补液结构示意图"],
  ["lead", "关键参数范围（用于支撑权利要求）：", "定容储库 3 的补偿电解液容量 Vr 可为电芯初始注液量的 0.5%～8%，优选为目标寿命期净电解液消耗量的 60%～130%；芯吸路径 4 的等效孔径可为 0.1 μm～100 μm，毛细压力可为 0.5 kPa～80 kPa；限流膜 5 的液体渗透系数被配置为使 50% 以上补偿电解液在完成 20%～70% 目标循环寿命后释放；储库与活性电极区之间可设置 1～8 条芯吸路径，每条路径宽度为 0.2 mm～10 mm，厚度为 10 μm～2 mm。上述参数为示意范围，可按具体电芯容量、体系和寿命目标标定。"],
  ["lead", "功能性界定（权利要求核心）：", "定容储库 3、芯吸路径 4 和限流膜 5 被配置成使储库容量与目标寿命期电解液消耗量相匹配、芯吸路径的出口位置与循环后期贫液热点相匹配、补偿电解液释放速率与循环后期电解液消耗速率相匹配，从而相对于仅提高初始注液量的电芯，在万次级循环后保持更均匀的液相润湿状态。"],
  ["lead", "作用机理（参见图2和图3）：", "长时循环前期，限流膜和毛细阻抗限制储库中的补偿电解液过早释放；随着 SEI 消耗、气体带液和局部润湿网络退化，端部、角部或厚度方向低润湿区的毛细吸力上升，储库中的补偿电解液沿芯吸路径被动迁移至贫液热点，恢复局部液相通道并降低极化。"],
  ["fig", "fig/f2.png", 0.72, "图2  储库定容与循环后期补液效果示意图"],
  ["fig", "fig/f3.png", 0.67, "图3  储库-芯吸路径的补液机理示意图"],
  ["lead", "设计判据（仿真驱动，受保护对象为结构）：", "储库容量 Vr 可由长时循环副反应消耗量、化成带液量、气体夹带损失、拆解残液量和容量 knee 前后 DCR 增长速率综合确定；芯吸路径位置可由 CT、浸润实验、压力膜、电化学-热仿真或循环后拆解确定。请求保护的是落入上述容量匹配、路径匹配和释放速率匹配关系的电芯内部储库与芯吸结构本身及其制造方法，而非求解容量或路径的仿真算法。"],
  ["lead", "制造方法（参见图4）：", "S1，建立目标寿命下电解液消耗模型并确定补偿液量 Vr；S2，通过仿真、拆解或浸润测试确定端部、角部或厚度方向贫液热点；S3，制备带限流膜的定容储库并预填补偿电解液；S4，将芯吸路径布置至贫液热点并与焊接区、泄压区隔离；S5，完成装配、注液、化成和浸润验证，确认储库残液量、安全气隙和补液通道完整性。"],
  ["fig", "fig/f4.png", 1.20, "图4  储库与芯吸结构的设计制造流程图"],
];
// 3.2 / 3.3 拓展（段落序列同上）
const SOLUTION_B = [
  ["p", "在方案 A 的基础上，方案 B 将定容储库 3 设置为多腔分区结构。不同储液腔分别连接至卷芯端部、壳体角部、厚度方向中部或极耳附近低润湿区，各储液腔的限流膜孔径、芯吸路径长度和毛细压力不同，使不同区域按其贫液风险和补液需求获得不同释放速率。"],
  ["p", "方案 B 还可将储库材料设置为耐电解液的多孔陶瓷、氟聚合物、聚烯烃纤维毡、玻纤毡或复合隔膜边框，储库外表面设有电子绝缘层和离子可通透窗口，以避免储库与集流体或极耳形成短路风险。"],
];
const SOLUTION_C = [
  ["p", "在方案 A/B 的基础上，方案 C 将储库补液结构与电芯封装、安全泄压和化成工艺协同设计。储库可与顶盖下方气液分离迷宫、卷芯端面毛细边框或壳体内壁压力均化筋组合，使化成阶段带出的电解液回流至储库或芯吸路径，同时在热失控泄压路径上保留隔离间隙，避免储库阻塞安全阀通道。"],
  ["p", "方案 C 还可设置储库状态可检测标记，例如储库区域的超声反射特征、质量窗口、低残留示踪组分或顶盖外部定位标记，用于出厂抽检或寿命验证时确认储库剩余液量和补液通道完整性。"],
  ["fig", "fig/f5.png", 0.71, "图5  贫液均化与DCR增长抑制效果示意图"],
];
// 3.4 技术效果：A 为推理条目数组；B/C 各一段
const EFFECT_A = [
  "① 因定容储库 3 的补偿电解液容量 Vr 按目标寿命期电解液消耗量确定 → 因此相对于单纯增加初始注液量，可在不显著牺牲安全气隙和能量密度的情况下补偿循环后期贫液。",
  "② 因芯吸路径 4 的出口位置与端部、角部或厚度方向贫液热点相匹配 → 因此补偿电解液优先进入最易干涸区域，而不是长期滞留在壳体空腔或非反应区域。",
  "③ 因限流膜 5 和芯吸路径的毛细阻抗使补偿电解液在循环前期受限、在后期贫液吸力增大时持续释放 → 因此可延缓后期 DCR 快速上升和容量 knee 提前出现。",
  "④ 因储库固定/隔离支架 7 将储液结构与焊接区、泄压通道和极耳根部隔离 → 因此在引入补液结构的同时降低短路、堵塞泄压路径和装配干涉风险。",
  "⑤ 因本方案保护的是可拆解、可 CT 识别、可尺寸测量的内部储库和芯吸路径结构 → 因此相对于纯算法补液判据或外部维护方法，更适合作为结构类权利要求进行保护。",
];
const EFFECT_B = "方案 B 通过多腔分区和不同毛细阻抗路径，使端部、角部、极耳附近和厚度方向中部可获得差异化补液；因不同贫液热点的补液速率可独立设计，因此可提高大容量电芯长周期润湿一致性。";
const EFFECT_C = "方案 C 将储库与气液分离、壳体压力均化和状态检测结合，使补液结构既参与长期电解液保持，又不干扰化成脱气和安全泄压；因储库状态可抽检，因此便于量产质量控制和寿命验证。";
const EFFECT_NOTE = "说明：图中数值为示意，具体需结合本体系仿真与实测标定确定。";

// 发明构思总结 改进点 1-5
const IDEA_ROWS = [
  ["改进点1", "在长时储能电芯内部设置定容储库与芯吸路径，解决万次级循环后贫液/干涸，而非仅改善初期注液浸润。"],
  ["改进点2", "提出储库容量与寿命期电解液消耗量、芯吸路径与贫液热点、释放速率与后期消耗速率的三重匹配关系。"],
  ["改进点3", "采用限流膜和毛细阻抗路径控制补偿电解液在循环后期持续释放，避免早期释放过快。"],
  ["改进点4", "通过多腔储库和分区芯吸路径分别补偿端部、角部、极耳附近和厚度方向低润湿区。"],
  ["改进点5", "将储库结构与安全气隙、泄压路径、化成脱气和储库状态检测协同设计，提高量产和长期服役可行性。"],
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
  P("本提案核心思路：在长时储能电芯内部集成一个定容的被动电解液储库，并通过限流膜和芯吸路径将补偿电解液导向循环后期最易贫液的端部、角部或厚度方向低润湿区域；储库容量按目标循环寿命下的电解液消耗量确定，芯吸路径按贫液热点确定，释放速率按后期消耗速率确定。下文给出最优方案 A 及两个拓展方案 B、C。"),
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

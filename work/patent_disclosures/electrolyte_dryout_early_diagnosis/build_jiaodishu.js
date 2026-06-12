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
  subtitle: "（软件 / 方法类）",
  title_name: "一种储能电芯电解液干涸早期诊断及维护控制方法、系统和存储介质",
  field: "属于储能电池状态诊断与电池管理技术领域；特别涉及基于电化学-热模型残差、多源老化特征融合和风险分级的储能电芯电解液干涸早期诊断方法。",
  note: "注：本提案为软件 / 方法类发明，下文附图采用黑白线条图，各数据源、模块、步骤和信号特征均附数字或步骤标号。",
  outfile: "交底书_储能电芯电解液干涸早期诊断及维护控制方法.docx",
};

// 现有技术（2 段散文）
const PRIOR_ART = [
  "长时储能系统通常采用大容量磷酸铁锂/石墨体系电芯，电芯在长期循环、长期浮充或高温运行过程中，电解液会因 SEI 持续消耗、气体副反应、局部浸润不足、极片厚度方向传输受限等因素出现有效液相体积分数下降或局部干涸。该类干涸早期通常不会立即表现为容量断崖式下降，而是先表现为离子传输阻抗上升、脉冲极化增大、脉冲温升增加以及充放电曲线局部偏离。",
  "现有 BMS/EMS 或实验评价方法多依赖容量保持率、DCR 绝对值、温升阈值或人工 EIS/拆解分析来判断异常老化。上述方法虽可用于后期筛查，但往往难以在早期将电解液干涸与 SEI 增长、活性材料损失（LAM）或低温/高 SOC 锂析出区分开来；同时，电化学模型预测曲线与实测曲线之间的残差通常只作为拟合误差处理，未被结构化提取为干涸机理诊断特征。",
];

// 技术缺陷（分条，[加粗小标题, 说明]）
const DEFECTS = [
  ["（1）电解液干涸早期信号弱且易被运行工况掩盖。", "干涸早期的容量衰减幅度可能低于告警阈值，但电解液有效电导率、局部润湿面积和扩散通道已发生变化，相关信号会被温度、SOC、倍率和休止时间影响。"],
  ["（2）单一容量或 DCR 阈值具有明显滞后性。", "容量保持率和 DCR 绝对值通常在干涸已发展到中后期后才触发告警，不能提前指导降额、复测或均衡维护。"],
  ["（3）模型预测残差未被用于机理诊断。", "现有仿真对标多关注整体误差大小，未提取“模型预测电压 - 实测电压”在 SOC 分区、脉冲阶段和静置弛豫阶段的残差形状。"],
  ["（4）多种老化机理容易相互混淆。", "SEI 增长、LAM、锂析出和电解液干涸均可能导致容量下降或极化增加，仅凭单次容量测试、单点 DCR 或温升曲线难以区分。"],
  ["（5）诊断结果难以形成闭环维护动作。", "现有异常识别多停留在告警层面，未将干涸风险评分直接转化为功率降额、SOC 窗口调整、诊断脉冲复测、簇级均衡或隔离策略。"],
];

// 附图说明 + 标号
const FIG_LIST = [
  "图1  储能电芯电解液干涸早期诊断对象与信号采集示意图；",
  "图2  模型预测电压与实测电压残差形状对比图；",
  "图3  SEI、LAM、锂析出与电解液干涸的机理-特征映射表；",
  "图4  电解液干涸早期诊断系统架构图；",
  "图5  提前预警与维护控制技术效果示意图。",
];
const FIG_LABELS = "1—正极；2—隔膜；3—负极；4—被诊断储能电芯；5—电压采样；6—温度采样；7—诊断脉冲；8—BMS/测试设备；9—历史数据库；10—模型预测单元；11—残差诊断单元；12—维护策略；S1～S7—数据采集、片段筛选、模型预测、残差提取、机理区分、风险评分、维护控制步骤。";

// 3.1 方案A：用 [类型, 内容] 段落序列；类型 'lead'=加粗引导段, 'p'=正文, 'fig'=插图([path,ratio,题])
const SOLUTION_A = [
  ["lead", "方法组成（参见图1）：", "本方案包括被诊断储能电芯 4、BMS/测试设备 8、历史数据库 9、模型预测单元 10、残差诊断单元 11 和维护策略输出 12。BMS/测试设备采集电压 V(t)、电流 I(t)、温度 T(t)、SOC、容量测试片段、DCR 脉冲片段和静置弛豫片段，并在相同温度、SOC、倍率窗口下输入模型预测单元。"],
  ["fig", "fig/f1.png", 0.60, "图1  储能电芯电解液干涸早期诊断对象与信号采集示意图"],
  ["lead", "关键参数范围（用于支撑权利要求）：", "诊断脉冲持续时间可为 5 s～60 s，静置弛豫采样时间可为 60 s～1800 s；容量衰减特征采用当前容量相对初始容量或最近基准容量的变化率；DCR 特征采用欧姆分量、极化分量或指定脉冲宽度下的等效电阻；脉冲温升特征采用单位电流平方温升、单位 DCR 温升或温升残差；电压残差特征采用 eV(t,SOC)=V模型(t,SOC)-V实测(t,SOC) 的幅值、斜率、面积、SOC 分区峰值和静置长尾时间常数；干涸风险评分 Rdry 归一化为 0～100。上述范围为示意，可根据电芯容量、测试设备采样频率和运行工况标定。"],
  ["lead", "功能性界定（权利要求核心）：", "所述诊断方法被配置成在容量保持率或 DCR 绝对值尚未达到常规告警阈值前，通过容量衰减、DCR 增长、脉冲温升以及电压残差形状的组合特征，识别电解液有效液相体积分数下降或局部润湿不足导致的干涸早期趋势，并输出对应风险等级和维护动作。"],
  ["lead", "作用机理（参见图2）：", "当电解液干涸发生时，电解液电导率、孔隙内离子传输能力和局部反应面积下降，导致同一电流下实测电压相对模型预测电压产生具有 SOC 分区特征的极化残差；在脉冲结束后，浓差极化恢复时间延长，表现为弛豫残差长尾；同时极化热和欧姆热增加，表现为脉冲温升残差增加。"],
  ["fig", "fig/f2.png", 0.72, "图2  模型预测电压与实测电压残差形状对比图"],
  ["lead", "机理区分判据（参见图3）：", "将 SEI 增长、LAM、锂析出和电解液干涸分别映射到容量衰减、DCR 增长、脉冲温升、极化残差形状和弛豫长尾特征。若容量衰减为中等而 DCR 增长、脉冲温升、极化残差形状和弛豫长尾均为强特征，则优先判定为电解液干涸风险；若容量衰减强但 DCR 和温升较弱，则偏向 LAM；若低温高 SOC 充电段残差集中并伴随异常弛豫，则偏向锂析出；若容量衰减与轻中度 DCR 增长平滑同步，则偏向 SEI 增长。"],
  ["fig", "fig/f3.png", 0.63, "图3  老化机理与可观测特征映射表"],
  ["lead", "设计判据（仿真驱动，受保护对象为技术方法与系统）：", "模型预测单元可采用电化学模型、等效电路模型、电化学-热耦合模型或经实验标定的降阶模型，用于在同一工况下生成基准电压和温度曲线。本申请请求保护的是绑定电芯测试/BMS 数据采集、模型预测、残差特征提取、老化机理区分、风险评分和维护控制的技术方法、系统及存储介质，而非孤立的数学算法或人工判读规则。"],
  ["lead", "诊断步骤（参见图4）：", "S1，采集电芯运行或测试数据；S2，筛选容量、DCR、脉冲和静置片段并进行温度、SOC、倍率归一化；S3，在相同工况下由模型预测单元计算 V模型 和 T模型；S4，计算电压残差、温升残差、DCR 分量和容量变化率；S5，依据机理-特征映射区分 SEI、LAM、锂析出和电解液干涸；S6，输出 Rdry 风险评分和置信度；S7，将风险等级转化为功率降额、SOC 窗口调整、复测、均衡或隔离维护动作。"],
  ["fig", "fig/f4.png", 0.71, "图4  电解液干涸早期诊断系统架构图"],
];
// 3.2 / 3.3 拓展（段落序列同上）
const SOLUTION_B = [
  ["p", "在方案 A 的基础上，方案 B 将单体电芯诊断拓展为模组、簇或电站级自适应诊断。具体地，可按照电芯型号、制造批次、运行温度区间、SOC 使用窗口和循环工况建立基准模型库；对同一模组或同一簇内的多个电芯计算 Rdry 分布，并将相邻电芯、同批次电芯或同温区电芯作为对照组，从而降低单个传感器漂移、偶发采样噪声或短期工况变化导致的误判。"],
  ["p", "方案 B 还可采用在线标定权重或置信度更新机制，使容量衰减、DCR 增长、脉冲温升和残差形状的权重随电芯生命周期阶段变化。例如在循环早期提高温度和倍率归一化权重，在中后期提高 DCR 分量和弛豫长尾权重，在低温充电场景提高锂析出排除判据权重。"],
];
const SOLUTION_C = [
  ["p", "在方案 A/B 的基础上，方案 C 将诊断结果与维护控制闭环连接。系统可按照 Rdry 评分输出绿色、黄色、橙色和红色等级：绿色维持原功率策略；黄色安排低影响诊断脉冲或缩短复测周期；橙色执行充放电功率降额、SOC 上下限收窄、热管理加强或簇级均衡；红色触发离线复测、EIS 验证、绝缘/热异常排查或电芯/模组隔离。"],
  ["p", "方案 C 还包括计算机可读存储介质形态，即将上述 S1～S7 步骤固化为程序指令，由 BMS、EMS、测试柜服务器或云端诊断平台的处理器执行，以实现对储能电芯电解液干涸风险的周期性在线诊断和维护策略下发。"],
  ["fig", "fig/f5.png", 0.72, "图5  提前预警与维护控制技术效果示意图"],
];
// 3.4 技术效果：A 为推理条目数组；B/C 各一段
const EFFECT_A = [
  "① 因本方案同时采集容量、DCR、脉冲温升和充放电残差信号，并在相同温度、SOC、倍率窗口下与模型预测曲线对齐 → 因此可将工况扰动与电芯内部传输能力下降区分开，降低仅凭单一阈值判断造成的误报和漏报。",
  "② 因电解液干涸会同时引起离子传输受限、脉冲极化增加和弛豫恢复变慢，而 SEI、LAM、锂析出对应的特征组合不同 → 因此通过机理-特征映射可区分 SEI 增长、LAM、锂析出和电解液干涸，避免将不同老化机理简单归为容量衰减或内阻增大。",
  "③ 因本方案提取“模型预测电压 - 实测电压”的 SOC 分区峰值、面积、斜率和静置长尾时间常数 → 因此能够在容量保持率或 DCR 绝对值尚未越限前识别干涸趋势，实现早期预警。",
  "④ 因 Rdry 风险评分被转化为功率降额、SOC 窗口调整、复测、均衡或隔离等维护动作 → 因此诊断结果能够直接服务于储能系统运行控制，减少极化热积累和异常电芯继续高负荷运行的风险。",
  "⑤ 因模型预测单元可采用 DFN、SPM、等效电路或降阶电化学-热模型，并且诊断特征来自 BMS/测试柜常规采样数据 → 因此本方案可在研发实验、出厂筛选、在役电站运维和寿命预测中复用，工程部署成本较低。",
];
const EFFECT_B = "方案 B 通过批次、模组、簇级对照和在线权重更新，使诊断阈值随电芯型号、运行温区和生命周期阶段自适应变化；因同类电芯之间的相对偏离被纳入判断，因此可提升大规模储能系统中的一致性筛查能力。";
const EFFECT_C = "方案 C 将风险评分与维护动作绑定，使干涸诊断从离线分析扩展为 BMS/EMS 闭环控制；因橙色或红色等级可提前触发降额、复测和隔离，因此可延缓功率衰减并降低异常热积累风险。";
const EFFECT_NOTE = "说明：图中数值为示意，具体需结合本体系仿真与实测标定确定。";

// 发明构思总结 改进点 1-5
const IDEA_ROWS = [
  ["改进点1", "提出基于容量衰减、DCR 增长、脉冲温升和模型-实测电压残差形状的电解液干涸早期诊断方法，区别于单一容量或 DCR 阈值判断。"],
  ["改进点2", "将“模型预测电压 - 实测电压”的 SOC 分区残差、脉冲残差和静置长尾作为干涸判据，利用残差形状而非仅利用误差大小。"],
  ["改进点3", "建立 SEI、LAM、锂析出和电解液干涸的机理-特征映射，实现多老化机理区分和干涸风险置信度输出。"],
  ["改进点4", "将干涸风险评分拓展到模组、簇和电站级对照诊断，并通过在线权重更新适配不同电芯型号、温区和生命周期阶段。"],
  ["改进点5", "将 Rdry 风险等级闭环转化为功率降额、SOC 窗口调整、复测、均衡或隔离维护动作，并覆盖方法、系统和计算机可读存储介质形态。"],
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
  P("本提案核心思路：以储能电芯常规运行或测试数据为输入，在相同温度、SOC、倍率条件下生成模型预测电压和温度曲线，提取模型预测值与实测值之间的残差形状，并将容量衰减、DCR 增长、脉冲温升和残差长尾共同映射到 SEI、LAM、锂析出和电解液干涸等老化机理，最终输出电解液干涸风险评分和维护控制动作。下文给出最优方案 A 及两个拓展方案 B、C。"),
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

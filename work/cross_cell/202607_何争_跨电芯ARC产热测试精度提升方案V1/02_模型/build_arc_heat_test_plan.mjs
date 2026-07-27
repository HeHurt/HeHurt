import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const taskRoot = "C:/HithiumSSD/hithium/work/cross_cell/202607_何争_跨电芯ARC产热测试精度提升方案V1";
const outputDir = path.join(
  taskRoot,
  "04_输出结果",
  "outputs",
  "arc_heat_power_precision_20260723",
);
const qaDir = path.join(outputDir, "qa");
const outputPath = path.join(
  outputDir,
  "发热功率专项_ARC测试精度提升_SOH一致性与跨电芯迁移方案V1.xlsx",
);

await fs.mkdir(qaDir, { recursive: true });

const wb = Workbook.create();

const COLORS = {
  blue: "#1261D9",
  darkBlue: "#0B3E91",
  paleBlue: "#DCEBFA",
  lighterBlue: "#EEF5FC",
  text: "#1F2937",
  gray: "#64748B",
  lightGray: "#F3F4F6",
  line: "#CBD5E1",
  white: "#FFFFFF",
  yellow: "#FFF2CC",
  paleYellow: "#FFF8E1",
  red: "#C00000",
  paleRed: "#FCE8E6",
  green: "#16804A",
  paleGreen: "#E2F0D9",
};

function colName(index1Based) {
  let n = index1Based;
  let out = "";
  while (n > 0) {
    n -= 1;
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26);
  }
  return out;
}

function applyWidths(sheet, widths, maxRow = 200) {
  widths.forEach((width, idx) => {
    const col = colName(idx + 1);
    sheet.getRange(`${col}1:${col}${maxRow}`).format.columnWidth = width;
  });
}

function setupSheet(sheet, title, subtitle, columnCount, widths) {
  const lastCol = colName(columnCount);
  sheet.showGridLines = false;
  sheet.mergeCells(`A1:${lastCol}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: COLORS.blue,
    font: { bold: true, color: COLORS.white, size: 18 },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastCol}1`).format.rowHeight = 34;

  sheet.mergeCells(`A2:${lastCol}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${lastCol}2`).format = {
    fill: COLORS.lighterBlue,
    font: { color: COLORS.darkBlue, size: 10, italic: true },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange(`A2:${lastCol}2`).format.rowHeight = 32;
  applyWidths(sheet, widths);
  return lastCol;
}

function section(sheet, row, label, lastCol) {
  sheet.mergeCells(`A${row}:${lastCol}${row}`);
  sheet.getRange(`A${row}`).values = [[label]];
  sheet.getRange(`A${row}:${lastCol}${row}`).format = {
    fill: COLORS.darkBlue,
    font: { bold: true, color: COLORS.white, size: 12 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A${row}:${lastCol}${row}`).format.rowHeight = 25;
}

function writeTable(sheet, startRow, headers, rows, options = {}) {
  const startCol = options.startCol ?? 1;
  const endCol = startCol + headers.length - 1;
  const startColName = colName(startCol);
  const endColName = colName(endCol);
  const headerRange = sheet.getRange(
    `${startColName}${startRow}:${endColName}${startRow}`,
  );
  headerRange.values = [headers];
  headerRange.format = {
    fill: options.headerFill ?? COLORS.blue,
    font: { bold: true, color: COLORS.white, size: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.line },
  };
  headerRange.format.rowHeight = options.headerHeight ?? 32;

  if (rows.length) {
    const dataRange = sheet.getRange(
      `${startColName}${startRow + 1}:${endColName}${startRow + rows.length}`,
    );
    dataRange.values = rows;
    dataRange.format = {
      font: { color: COLORS.text, size: 9 },
      verticalAlignment: "center",
      wrapText: true,
      borders: { preset: "all", style: "thin", color: COLORS.line },
    };
    dataRange.format.rowHeight = options.rowHeight ?? 42;
    if (options.bandRows !== false) {
      for (let r = 0; r < rows.length; r += 1) {
        if (r % 2 === 1) {
          sheet
            .getRange(
              `${startColName}${startRow + 1 + r}:${endColName}${startRow + 1 + r}`,
            )
            .format.fill = COLORS.lighterBlue;
        }
      }
    }
  }
  return startRow + rows.length;
}

function noteBox(sheet, rowStart, rowEnd, lastCol, text, kind = "info") {
  const fill =
    kind === "warn"
      ? COLORS.paleYellow
      : kind === "risk"
        ? COLORS.paleRed
        : COLORS.paleBlue;
  const fontColor = kind === "risk" ? COLORS.red : COLORS.darkBlue;
  sheet.mergeCells(`A${rowStart}:${lastCol}${rowEnd}`);
  sheet.getRange(`A${rowStart}`).values = [[text]];
  sheet.getRange(`A${rowStart}:${lastCol}${rowEnd}`).format = {
    fill,
    font: { color: fontColor, bold: kind !== "info", size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: COLORS.line },
  };
}

function stylePriority(sheet, cell, value) {
  const range = sheet.getRange(cell);
  if (value === "P0") {
    range.format = {
      fill: COLORS.paleRed,
      font: { bold: true, color: COLORS.red },
      horizontalAlignment: "center",
    };
  } else if (value === "P1") {
    range.format = {
      fill: COLORS.yellow,
      font: { bold: true, color: "#7F6000" },
      horizontalAlignment: "center",
    };
  } else {
    range.format = {
      fill: COLORS.paleGreen,
      font: { bold: true, color: COLORS.green },
      horizontalAlignment: "center",
    };
  }
}

// 00 专项总览
{
  const sheet = wb.worksheets.add("00_专项总览");
  const lastCol = setupSheet(
    sheet,
    "发热功率专项｜ARC测试精度、SOH一致性与跨电芯迁移",
    "核心：先把容量爬坡后的稳定BOL状态统一，再拆分测量系统误差、样品状态误差和大电芯热惯性误差。",
    6,
    [14, 22, 30, 31, 31, 19],
  );

  section(sheet, 4, "一、这次专项真正要解决的问题", lastCol);
  const overviewRows = [
    [
      "1",
      "状态不一致",
      "很多ARC产热测试所用电芯仍处于容量爬坡阶段，或测试圈数、容量SOH和能量效率不同。",
      "同一工况下，不同活化程度和内阻状态会直接改变不可逆热及总产热。",
      "先通过容量爬坡试验确定统一正式测量圈数 N_ref，并以该圈的容量、能量效率、DCIR做样品状态闸门。",
      "P0",
    ],
    [
      "2",
      "ARC测量链偏差",
      "现有产热功率来源为 m·Cp·dT/dt，瞬时曲线会叠加温度量化、求导噪声、热漏和夹具附加热容。",
      "即使重复同一电芯，也可能得到不同瞬时热功率和平均热功率。",
      "先做电加热器标定、C_eff/UA识别、传感器与时间同步MSA，再进入电芯测试。",
      "P0",
    ],
    [
      "3",
      "过度筛选或直接取平均",
      "只挑一致性最好的电芯会低估量产离散性；直接把多只电芯取平均又会掩盖状态不同。",
      "无法区分测试系统误差与真实电芯一致性误差。",
      "建立精度标定组与量产代表组；前者做窄窗口配组，后者保留真实离散性。",
      "P0",
    ],
    [
      "4",
      "跨尺寸直接放大",
      "314Ah、587Ah、1175Ah的热容、厚度方向温差、时间常数和夹具热容不同。",
      "314Ah可用的方法在1175Ah上可能出现明显时滞和内部温度梯度。",
      "按314→587→1175逐级放大，每一级先用同几何假电芯/加热器重新标定，再做盲测。",
      "P1",
    ],
  ];
  writeTable(
    sheet,
    5,
    ["序号", "问题", "现状", "为什么影响精度", "专项动作", "优先级"],
    overviewRows,
    { rowHeight: 56 },
  );
  overviewRows.forEach((r, i) => stylePriority(sheet, `F${6 + i}`, r[5]));

  section(sheet, 11, "二、容量爬坡“定圈”的统一定义", lastCol);
  noteBox(
    sheet,
    12,
    14,
    lastCol,
    "容量爬坡最高点不是对每只电芯事后寻找单个最大容量点。专项先用样品组识别“稳定最高平台”，确定固定正式测量圈数 N_ref；后续所有正式ARC样品都在同一 N_ref 圈测试，并要求该圈容量、能量效率、DCIR同时落入预设状态窗口。这样才能真正减少因SOH和能效不同带来的电芯一致性误差。",
    "warn",
  );

  const stateRows = [
    [
      "容量参考",
      "以固定工况下的稳定放电容量作为BOL参考容量 Q_BOL,ref，而不是直接使用铭牌容量。",
      "容量SOH = Q_test / Q_BOL,ref",
      "建议容量状态偏差≤±0.5%（初始建议，需由试验能力确认）",
    ],
    [
      "能效参考",
      "记录同一循环的充入能量、放出能量和能量效率；容量一致但能效不同的样品不得视为同状态。",
      "Δη_E = η_E,test - η_E,ref",
      "建议偏差≤±0.3个百分点",
    ],
    [
      "电阻参考",
      "在统一温度、SOC和脉冲时长下测DCIR，防止仅靠容量SOH掩盖内阻差异。",
      "ΔR = R_test/R_ref - 1",
      "建议偏差≤±3%",
    ],
    [
      "历史参考",
      "记录循环数、累计Ah/Wh通量、储存时间/温度/SOC和测试间隔。",
      "状态向量而非单一SOH",
      "缺少历史字段的测试不进入高精度标定集",
    ],
  ];
  writeTable(
    sheet,
    16,
    ["状态维度", "统一方式", "判定量", "建议闸门"],
    stateRows,
    { startCol: 1, rowHeight: 48 },
  );
  sheet.mergeCells("E16:F16");
  sheet.getRange("E16").clear({ applyTo: "contents" });

  section(sheet, 22, "三、逐级放大路线与停止闸门", lastCol);
  const routeRows = [
    [
      "G0｜测量系统",
      "314Ah同几何假电芯/电加热器",
      "验证功率回收、C_eff、UA、时间常数、传感器和同步链",
      "已知功率回收误差≤3%；同装夹重复CV≤3%",
      "不通过不得测试真实电芯",
      "方法资格",
    ],
    [
      "G1｜314Ah",
      "容量爬坡定圈 + ARC精度标定",
      "建立 N_ref、样品配组窗口和完整SOC产热曲线",
      "状态闸门通过；产热重复CV≤3%；能量闭合可解释",
      "冻结V1 SOP后进入587Ah",
      "方法开发",
    ],
    [
      "G2｜587Ah",
      "冻结SOP迁移验证",
      "先不改数据算法，识别尺寸导致的新偏差；只重标定几何相关热参数",
      "同装夹CV≤3%；重装夹CV≤4%；温度梯度受控",
      "通过后冻结V2 SOP",
      "中尺度验证",
    ],
    [
      "G3｜1175Ah",
      "大热惯性/大温差最终验证",
      "增加多点温度与动态反演；验证集中参数法是否仍适用",
      "产热平均/积分误差≤5%；温升误差1–2°C；盲测通过",
      "形成全产品测试规范",
      "最终压力测试",
    ],
  ];
  writeTable(
    sheet,
    23,
    ["阶段", "对象", "目的", "通过标准", "下一步", "定位"],
    routeRows,
    { rowHeight: 49 },
  );

  section(sheet, 29, "四、建议专项验收指标", lastCol);
  const metricRows = [
    ["测量系统", "假负载功率回收误差", "≤3%", "同时报告U95，不只报告均值"],
    ["重复性", "同电芯同装夹产热CV", "≤3%", "至少3次，建议5次"],
    ["再现性", "拆装后产热CV", "≤4%", "传感器、导热胶和压紧力重新装配"],
    ["状态一致性", "容量SOH/能效/DCIR", "±0.5% / ±0.3pp / ±3%", "作为建议初值，314试验后冻结"],
    ["模型对标", "平均功率及积分热量误差", "≤5%", "完整SOC曲线另报NRMSE、Peak/P95"],
    ["温度预测", "最高温升误差", "≤1°C优先，最差≤2°C", "先确认产热源，再验证热边界"],
  ];
  writeTable(
    sheet,
    30,
    ["层级", "指标", "建议目标", "说明"],
    metricRows,
    { rowHeight: 39 },
  );
  sheet.mergeCells("E30:F30");
  sheet.getRange("E30").clear({ applyTo: "contents" });
  sheet.freezePanes.freezeRows(2);
}

// 01 容量爬坡定圈
{
  const sheet = wb.worksheets.add("01_容量爬坡定圈");
  const lastCol = setupSheet(
    sheet,
    "容量爬坡定圈｜先确定稳定BOL，再做正式ARC",
    "目标是确定可复现的固定测量圈数 N_ref，而不是事后为每只电芯挑最大容量圈。",
    10,
    [10, 18, 18, 17, 17, 17, 18, 18, 22, 30],
  );

  section(sheet, 4, "一、定圈术语和判定逻辑", lastCol);
  const definitionRows = [
    [
      "Q_peak,raw",
      "单只电芯原始容量序列中的最大值",
      "只用于诊断",
      "容易受测量噪声影响，禁止直接作为正式测量圈选择规则",
    ],
    [
      "Q_plateau",
      "容量爬坡完成后的稳定最高平台容量",
      "作为BOL容量参考",
      "建议采用3圈滚动中位数/均值，并结合斜率、能效和DCIR判断",
    ],
    [
      "N_plateau,start",
      "首次进入稳定最高平台的圈数",
      "每只试验样品均计算",
      "至少连续3圈满足容量和能效稳定条件",
    ],
    [
      "N_ref,product",
      "某型号正式ARC测量的固定圈数",
      "正式SOP的核心参数",
      "由试验组N_plateau,start分布确定，正式样品不得自行换圈",
    ],
    [
      "N_ref,common",
      "314/587/1175共用圈数",
      "优先目标，但不强求",
      "仅当三个型号在该圈均处于稳定平台时采用；否则按型号冻结N_ref",
    ],
  ];
  writeTable(
    sheet,
    5,
    ["符号", "定义", "用途", "注意事项"],
    definitionRows,
    { startCol: 1, rowHeight: 43 },
  );
  sheet.mergeCells("E5:J5");
  sheet.getRange("E5").clear({ applyTo: "contents" });

  section(sheet, 12, "二、建议初始判据（黄色单元格为待314试验确认参数）", lastCol);
  const criteriaHeaders = ["参数", "建议初值", "单位", "用途", "冻结原则"];
  const criteriaRows = [
    ["容量单圈变化限值", 0.002, "%/cycle", "判断容量斜率是否稳定", "至少连续3圈满足"],
    ["能量效率单圈变化限值", 0.002, "百分点", "避免容量已稳定但极化/能效仍变化", "至少连续3圈满足"],
    ["稳定平台带", 0.005, "%", "要求正式测量圈容量接近Q_plateau", "容量≥(1-带宽)×Q_plateau"],
    ["连续稳定圈数", 3, "cycle", "防止单圈偶然满足", "三个型号尽量统一"],
    ["定圈探索上限", 10, "cycle", "初始试验计划边界", "10圈仍不稳定则专项评审，不强行定圈"],
  ];
  writeTable(
    sheet,
    13,
    criteriaHeaders,
    criteriaRows,
    { startCol: 1, rowHeight: 38, bandRows: false },
  );
  sheet.getRange("B14:B18").format.fill = COLORS.yellow;
  sheet.getRange("B14").format.numberFormat = "0.0%";
  sheet.getRange("B15").format.numberFormat = "0.0%";
  sheet.getRange("B16").format.numberFormat = "0.0%";

  noteBox(
    sheet,
    20,
    21,
    lastCol,
    "建议决策：正式N_ref应在试验前冻结。若容量最高点在第4圈附近，正式测试也不能对每只样品分别挑第3/4/5圈；应统一在预先确定的N_ref圈测试，并用容量平台带、能效和DCIR做当圈有效性确认。",
    "warn",
  );

  section(sheet, 23, "三、单电芯容量爬坡记录模板", lastCol);
  const cycleHeaders = [
    "Cycle",
    "充电容量(Ah)",
    "放电容量(Ah)",
    "Q/Qmax",
    "ΔQ/Qprev",
    "库仑效率",
    "能量效率",
    "初始温度(°C)",
    "单圈稳定候选",
    "备注",
  ];
  const cycleRows = Array.from({ length: 15 }, (_, i) => [
    i + 1,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
    null,
  ]);
  writeTable(sheet, 24, cycleHeaders, cycleRows, {
    rowHeight: 28,
    bandRows: false,
  });
  for (let row = 25; row <= 39; row += 1) {
    sheet.getRange(`D${row}`).formulas = [
      [`=IF(C${row}="","",C${row}/MAX($C$25:$C$39))`],
    ];
    if (row > 25) {
      sheet.getRange(`E${row}`).formulas = [
        [`=IF(OR(C${row}="",C${row - 1}=""),"",C${row}/C${row - 1}-1)`],
      ];
    }
    sheet.getRange(`F${row}`).formulas = [
      [`=IF(OR(B${row}="",C${row}=""),"",C${row}/B${row})`],
    ];
    if (row > 25) {
      sheet.getRange(`I${row}`).formulas = [[
        `=IF(OR(D${row}="",E${row}="",G${row}="",G${row - 1}=""),"待录入",IF(AND(D${row}>=1-$B$16,ABS(E${row})<=$B$14,ABS(G${row}-G${row - 1})<=$B$15),"候选稳定","未稳定"))`,
      ]];
    } else {
      sheet.getRange(`I${row}`).values = [["基线圈"]];
    }
  }
  sheet.getRange("D25:G39").format.numberFormat = "0.00%";
  sheet.getRange("B25:H39").format.fill = COLORS.paleYellow;
  sheet.getRange("D25:G39").format.fill = COLORS.white;
  sheet.getRange("I25:I39").format.fill = COLORS.lighterBlue;

  section(sheet, 42, "四、跨样品定圈试验设计", lastCol);
  const pilotRows = [
    ["314Ah", 6, "同批为主，另保留1只跨批验证", "连续循环至稳定平台后至少3圈", "建立算法和初始N_ref", "最高优先级"],
    ["587Ah", 3, "同批", "先直接套用314冻结圈数，再继续到自身平台", "检验共同N_ref是否成立", "G1通过后"],
    ["1175Ah", 3, "同批", "先直接套用G2冻结圈数，再继续到自身平台", "检验大电芯活化与热历史差异", "G2通过后"],
  ];
  writeTable(
    sheet,
    43,
    ["型号", "建议样品数", "批次设计", "循环范围", "定圈目的", "启动条件"],
    pilotRows,
    { rowHeight: 44 },
  );

  const decisionRows = [
    [
      "各型号N_plateau,start接近",
      "取能覆盖绝大多数有效样品的最小共同圈数",
      "统一N_ref,common",
      "该圈三个型号容量均处平台带，且能效/DCIR状态通过",
    ],
    [
      "587或1175明显更晚稳定",
      "先判断是否由储存/形成历史或测试温度差异造成",
      "优先统一前处理；仍不同则型号化N_ref",
      "不为了形式统一而在未稳定状态测产热",
    ],
    [
      "个别样品峰值异常",
      "按预先声明的异常规则保留记录但不用于定圈",
      "不得删除原始数据",
      "异常包括测试中断、温度越界、容量突跳和明显通道故障",
    ],
  ];
  writeTable(
    sheet,
    49,
    ["情形", "处理方式", "输出", "底线"],
    decisionRows,
    { startCol: 1, rowHeight: 46 },
  );
  sheet.mergeCells("E49:J49");
  sheet.getRange("E49").clear({ applyTo: "contents" });
  sheet.freezePanes.freezeRows(2);
}

// 02 SOH与样品配组
{
  const sheet = wb.worksheets.add("02_SOH与样品配组");
  const lastCol = setupSheet(
    sheet,
    "SOH与能效配组｜把样品状态误差从测试误差中剥离",
    "容量SOH相同不代表产热相同；正式样品至少按容量、能量效率、DCIR和历史四个维度描述。",
    19,
    [12, 15, 14, 10, 12, 13, 13, 12, 13, 13, 12, 13, 13, 12, 11, 11, 11, 12, 15],
  );

  section(sheet, 4, "一、两类样品组必须同时存在", lastCol);
  const cohortRows = [
    [
      "精度标定组",
      "在固定N_ref圈，容量SOH、能量效率和DCIR均落入窄窗口",
      "隔离ARC测量链和模型误差",
      "可用于参数标定与方法重复性",
      "不得用来宣称量产一致性",
    ],
    [
      "量产代表组",
      "按生产批次随机抽样，不因偏离均值而删除",
      "评估真实电芯离散性和模型鲁棒性",
      "报告分布、P5/P50/P95及异常比例",
      "不得与精度组简单混合取平均",
    ],
  ];
  writeTable(
    sheet,
    5,
    ["样品组", "纳入规则", "目的", "输出", "限制"],
    cohortRows,
    { startCol: 1, rowHeight: 50 },
  );
  sheet.mergeCells("F5:S5");
  sheet.getRange("F5").clear({ applyTo: "contents" });

  section(sheet, 9, "二、建议状态窗口（黄色参数待314定圈试验后冻结）", lastCol);
  const thresholdRows = [
    ["容量SOH目标偏差", 0.005, "相对值", "ABS(SOH_Q - Target SOH)"],
    ["能量效率偏差", 0.3, "百分点", "η_test - η_ref"],
    ["DCIR偏差", 0.03, "相对值", "R_test/R_ref - 1"],
  ];
  writeTable(
    sheet,
    10,
    ["参数", "建议初值", "单位", "计算"],
    thresholdRows,
    { startCol: 1, rowHeight: 35, bandRows: false },
  );
  sheet.getRange("B11:B13").format.fill = COLORS.yellow;
  sheet.getRange("B11").format.numberFormat = "0.0%";
  sheet.getRange("B13").format.numberFormat = "0.0%";
  sheet.mergeCells("E10:S10");
  sheet.getRange("E10").clear({ applyTo: "contents" });

  section(sheet, 15, "三、样品状态与配组模板", lastCol);
  const matchHeaders = [
    "型号",
    "Cell_ID",
    "批次",
    "N_ref",
    "目标SOH",
    "Q_BOL,ref(Ah)",
    "Q_test(Ah)",
    "SOH_Q",
    "η_E,ref",
    "η_E,test",
    "Δη_E(pp)",
    "DCIR_ref(mΩ)",
    "DCIR_test(mΩ)",
    "ΔR",
    "容量判定",
    "能效判定",
    "DCIR判定",
    "总判定",
    "配组/备注",
  ];
  const matchRows = Array.from({ length: 24 }, () =>
    Array.from({ length: matchHeaders.length }, () => null),
  );
  writeTable(sheet, 16, matchHeaders, matchRows, {
    rowHeight: 30,
    bandRows: false,
  });
  for (let row = 17; row <= 40; row += 1) {
    sheet.getRange(`H${row}`).formulas = [
      [`=IF(OR(F${row}="",G${row}=""),"",G${row}/F${row})`],
    ];
    sheet.getRange(`K${row}`).formulas = [
      [`=IF(OR(I${row}="",J${row}=""),"",(J${row}-I${row})*100)`],
    ];
    sheet.getRange(`N${row}`).formulas = [
      [`=IF(OR(L${row}="",M${row}=""),"",M${row}/L${row}-1)`],
    ];
    sheet.getRange(`O${row}`).formulas = [[
      `=IF(OR(H${row}="",E${row}=""),"待录入",IF(ABS(H${row}-E${row})<=$B$11,"通过","不通过"))`,
    ]];
    sheet.getRange(`P${row}`).formulas = [[
      `=IF(K${row}="","待录入",IF(ABS(K${row})<=$B$12,"通过","不通过"))`,
    ]];
    sheet.getRange(`Q${row}`).formulas = [[
      `=IF(N${row}="","待录入",IF(ABS(N${row})<=$B$13,"通过","不通过"))`,
    ]];
    sheet.getRange(`R${row}`).formulas = [[
      `=IF(OR(O${row}="待录入",P${row}="待录入",Q${row}="待录入"),"待录入",IF(AND(O${row}="通过",P${row}="通过",Q${row}="通过"),"纳入精度组","转量产代表组/复核"))`,
    ]];
  }
  sheet.getRange("A17:G40").format.fill = COLORS.paleYellow;
  sheet.getRange("I17:M40").format.fill = COLORS.paleYellow;
  sheet.getRange("S17:S40").format.fill = COLORS.paleYellow;
  sheet.getRange("E17:E40").format.numberFormat = "0.0%";
  sheet.getRange("H17:J40").format.numberFormat = "0.00%";
  sheet.getRange("N17:N40").format.numberFormat = "0.00%";
  sheet.getRange("A17:A40").dataValidation = {
    rule: { type: "list", values: ["314Ah", "587Ah", "1175Ah"] },
  };
  sheet.getRange("S17:S40").dataValidation = {
    rule: {
      type: "list",
      values: ["精度组A", "精度组B", "量产代表组", "复核", "排除-保留记录"],
    },
  };

  noteBox(
    sheet,
    43,
    45,
    lastCol,
    "老化SOH测试：容量SOH必须相对同一只电芯或同一批次的稳定BOL容量定义；循环老化与日历老化即使容量SOH相同，也应分组，因为DCIR和能效可能不同。样品被排除时保留全部原始数据和原因，避免通过选择样品人为缩小一致性误差。",
    "warn",
  );
  sheet.freezePanes.freezeRows(16);
  sheet.freezePanes.freezeColumns(2);
}

// 03 ARC精度提升
{
  const sheet = wb.worksheets.add("03_ARC精度提升");
  const lastCol = setupSheet(
    sheet,
    "ARC精度提升清单｜从状态、装夹、测量到数据处理逐项控差",
    "每一项都明确误差机理、改进动作、固定参数和验收证据；P0未完成前不进入模型校准。",
    9,
    [9, 15, 24, 27, 34, 24, 24, 22, 10],
  );

  section(sheet, 4, "精度提升行动表", lastCol);
  const rows = [
    ["A01", "系统边界", "电芯本体热、极耳/引线/接触热混在一起", "不同装夹会改变外部焦耳热和导热损失", "书面冻结系统边界；四线采压；极耳与引线温度独立记录；必要时单独扣除I²R_contact", "测量端点、引线长度/截面、夹紧扭矩", "边界图、接触电阻、引线温度", "边界未冻结则数据仅作工程总热", "P0"],
    ["A02", "电加热标定", "只依赖仪器厂家标定或单点校验", "真实功率区间与电芯几何下回收率可能不同", "同几何假电芯/薄膜加热器覆盖预期产热的低/中/高三档；每档3次；测试前后各一次", "加热器位置、功率档、持续时间、温度", "P_meas/P_in、U95、漂移", "回收误差≤3%", "P0"],
    ["A03", "附加热容C_eff", "仅使用电芯质量×文献Cp", "夹具、传感器、胶带、引线和壳体均参与升温", "用已知电能阶跃识别整套C_eff(T)；电芯Cp另测并保留原始值", "装夹BOM、质量、温度范围", "C_eff(T)、cell Cp(T)", "不同装夹版本不得共用C_eff", "P0"],
    ["A04", "热漏UA", "默认完全绝热", "护套跟踪误差和引线导热会造成残余散热", "空载与加热器冷却/升温试验识别UA(T,ΔT)；计算Q=C_eff·dT/dt+UA·ΔT", "腔体状态、引线、环境温度", "UA曲线、残差", "热漏项与总热之比需报告", "P0"],
    ["A05", "温度传感器", "Can Temp、C1、C2位置和粘贴方式可能不固定", "位置/接触热阻变化会直接影响dT/dt", "定义坐标模板：大面中心、边缘/肩部、极耳侧；固定胶材、面积、厚度和压紧方式；传感器配对校准", "位置±、胶材、批次、贴附面积", "校准证书、位置照片、通道偏差", "通道偏差和位置偏差进入U95", "P0"],
    ["A06", "空间温差", "用单点温度代表整电芯", "587/1175Ah内部热滞后更明显，集中热容假设可能失效", "至少三点表面温度；先用假电芯评估加权平均；ΔT_space超限时启用逆热模型", "传感器数量、坐标、采样率", "T_center/T_edge/T_tab、ΔT_space", "314建议≤1°C；大电芯按模型能力冻结", "P0"],
    ["A07", "电流电压精度", "测试柜读数未与独立标准件交叉校验", "能量效率和I²R热对小误差敏感", "每季度或专项前用标准分流器/电压源核查；正式测试采用四线采压", "量程、采样率、校准日期", "I/V误差、能量闭合", "误差预算内分配", "P0"],
    ["A08", "时间同步", "ARC与测试柜事后最近邻对齐；当前代码容差与说明值不一致", "秒级错位会扭曲SOC分辨产热和瞬时峰值", "优先硬件公共触发；否则统一参数化对齐容差并输出每点残差；文档与代码共用同一配置", "共同时间源、采样周期、容差", "同步残差分布、丢点率", "同步误差≤0.5个采样周期", "P0"],
    ["A09", "容量爬坡圈数", "不同样品在不同循环圈测试", "活化程度、容量SOH和能效不同造成热源差异", "先完成定圈试验并冻结N_ref；正式ARC必须在N_ref圈执行", "循环工况、温度、SOC窗、休息时间", "Q_Nref、η_E、DCIR、累计Ah", "状态闸门全部通过", "P0"],
    ["A10", "储存与转运", "从预循环到ARC装机的等待时间和SOC不固定", "自放电、松弛和温度历史会改变初始状态", "固定预循环结束SOC、转运时间窗、储存温度和ARC前静置条件", "结束SOC、等待时长、温度", "OCV、T、dV/dt、dT/dt", "超窗则重新状态化", "P0"],
    ["A11", "装夹重复性", "不同人重新贴传感器和压紧", "接触热阻和传感器响应改变", "同电芯同装夹重复5次；拆装后重复3次；定义扭矩/压力和照片检查", "扭矩、压力、胶材、位置", "同装夹CV、重装夹CV", "≤3% / ≤4%", "P0"],
    ["A12", "初始恒温", "只按固定静置时间，不看真实稳定状态", "大电芯热惯性不同，固定时间不等于同温度状态", "时间+状态双判据：Tcell接近环境且dT/dt稳定；1175Ah按最慢通道判定", "T_env、各Tcell、最短时长", "ΔT0、dT/dt0", "建议|ΔT0|≤0.2°C且|dT/dt|≤0.01°C/min", "P0"],
    ["A13", "测试顺序", "同一电芯先0.25P再0.5P，顺序固定", "新增循环和热历史与倍率效应混淆", "优先使用状态匹配的独立样品；共用样品时采用AB/BA平衡顺序并限制在平台窗", "顺序、间隔、圈数", "order字段、容量漂移", "顺序效应单独检验", "P1"],
    ["A14", "原始数据保存", "仅保留源表计算后的Power(W)", "无法重算dT/dt和不确定度", "同步保存原始T/I/V/时间戳、仪器计算值和重算值；原始数据只读", "采样率、通道单位、时间源", "raw/processed版本和哈希", "任何修正可追溯", "P0"],
    ["A15", "dT/dt算法", "逐点差分放大温度量化噪声", "瞬时产热出现台阶和快速正负跳变", "统一时间网格；采用固定窗口局部线性拟合/SG滤波；窗口由加热器阶跃识别，不按结果调参", "重采样周期、窗口、阶数", "raw T、filtered T、dT/dt", "算法版本冻结；盲测不改参数", "P0"],
    ["A16", "动态时滞", "量热仪输出直接当作电芯瞬时热源", "大型电芯和量热腔存在相位滞后", "加热器脉冲识别传递函数；必要时进行正则化逆热传导；同时保留原始测量热流", "脉冲宽度、正则化参数", "冲激响应、时滞、重构误差", "加热器动态重构误差≤10%", "P1"],
    ["A17", "产热汇总", "只报告全程平均功率", "掩盖SOC区间偏差和正/负可逆热", "输出完整Q(SOC)曲线、分SOC能量、全程积分热量、平均、Peak/P95", "SOC映射、分箱宽度", "curve、E_heat、mean、P95", "不得只留平均值", "P0"],
    ["A18", "近零热功率", "对接近0W区间仍使用相对误差", "相对误差会无穷放大且符号不稳", "由空载和加热器标定确定绝对噪声门槛；门槛以下报告绝对误差", "噪声窗、检测限", "LOD/LOQ、绝对误差", "规则预先冻结", "P1"],
    ["A19", "能量闭合", "热量、充放电能效和电化学能量独立看", "无法发现符号、时间对齐或热漏错误", "按完整循环核对电能损失、积分热量和状态变化；偏差超限触发复核", "循环边界、符号约定", "能量闭合残差", "残差来源可解释", "P0"],
    ["A20", "日/人/设备漂移", "只在同一天、同一操作者重复", "低估长期再现性", "同一参考样品跨2天、2名操作者、必要时2台设备做嵌套MSA", "日期、操作者、设备", "方差分量", "测量系统贡献满足项目预算", "P1"],
    ["A21", "跨尺寸标定", "把314Ah标定系数直接用于587/1175Ah", "几何、时间常数和热容占比变化", "每种尺寸重做同几何加热器标定；只迁移算法和数据字典，不迁移C_eff/UA/时滞", "几何、装夹、功率范围", "size-specific校准包", "每一级通过后再测试电芯", "P0"],
  ];
  writeTable(
    sheet,
    5,
    ["ID", "环节", "现有风险", "误差机理", "具体提升动作", "必须固定/记录", "输出证据", "验收/处理", "优先级"],
    rows,
    { rowHeight: 60 },
  );
  rows.forEach((r, i) => stylePriority(sheet, `I${6 + i}`, r[8]));
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(2);
}

// 04 标准SOP
{
  const sheet = wb.worksheets.add("04_ARC标准SOP");
  const lastCol = setupSheet(
    sheet,
    "ARC标准SOP｜固定N_ref圈的完整执行流程",
    "SOP既固定圈数，也固定当圈状态；“到圈数”但容量/能效/DCIR不在窗口内的样品不得进入精度标定组。",
    9,
    [9, 15, 30, 27, 25, 23, 22, 23, 12],
  );

  section(sheet, 4, "一、正式测试前必须冻结的协议字段", lastCol);
  const freezeRows = [
    ["SOP版本", "ARC_HEAT_V1", "所有原始数据、图表和报告必须带版本号", "修改后需重新做最小MSA"],
    ["正式测量圈数", "N_ref（待定圈试验确认）", "区分314/587/1175或采用共同N_ref", "禁止按单只电芯事后挑圈"],
    ["容量爬坡工况", "温度、充放电倍率/功率、SOC/电压窗、CV截止、静置", "整个定圈和正式样品前处理一致", "任一字段变化视为新协议"],
    ["样品状态窗", "容量SOH、能量效率、DCIR", "精度组用窄窗口，量产组只记录不剔除", "阈值写入配置表"],
    ["ARC系统边界", "电芯本体或电芯+端子/连接件", "对应热量必须可解释", "报告首页声明"],
    ["数据算法", "同步、滤波、dT/dt、UA/C_eff修正、SOC映射", "盲测前冻结", "原始与修正结果同时保留"],
  ];
  writeTable(
    sheet,
    5,
    ["字段", "冻结值/形式", "要求", "变更控制"],
    freezeRows,
    { startCol: 1, rowHeight: 45 },
  );
  sheet.mergeCells("E5:I5");
  sheet.getRange("E5").clear({ applyTo: "contents" });

  section(sheet, 13, "二、逐步执行SOP", lastCol);
  const sopRows = [
    ["01", "样品接收", "记录型号、批次、生产/化成日期、储存SOC/温度/时长、质量和外观", "字段齐全", "样品主数据", "缺历史则仅进入代表组", "样品工程师", "测试前", "P0"],
    ["02", "初筛", "统一温度下测OCV、容量、能量效率、DCIR；排除通道故障和安全异常", "按筛选协议完成", "筛选表", "不得删除异常原始数据", "电性能测试", "N_ref前", "P0"],
    ["03", "容量爬坡前处理", "在冻结工况下完成Cycle 1至N_ref-1；每圈保留容量、能量效率和温度", "无中断/越界", "爬坡曲线", "中断后按偏差流程处理", "电性能测试", "ARC前", "P0"],
    ["04", "预转运状态", "第N_ref-1圈结束在统一SOC；固定转运/等待时间窗和储存温度", "状态满足SOP", "结束SOC、时间戳", "超时需重新状态化", "电性能测试", "ARC前", "P0"],
    ["05", "ARC前标定", "同几何加热器执行中档功率检查；核对传感器校准状态和空载漂移", "回收误差≤3%", "pre-check记录", "不通过停止", "ARC实验员", "每批/每日", "P0"],
    ["06", "装夹", "按照片模板布置传感器；固定胶材、面积、引线走向、夹紧扭矩/压力", "装夹检查表通过", "照片、扭矩", "重装必须新建Mount_ID", "ARC实验员", "正式测试前", "P0"],
    ["07", "电连接", "四线采压；记录端子接触电阻、引线规格和系统边界", "接触电阻在窗口内", "R_contact", "超限重装", "ARC实验员", "正式测试前", "P0"],
    ["08", "恒温与静置", "各温度通道满足Tcell≈Tenv且dT/dt稳定；采用时间+状态双判据", "建议|ΔT|≤0.2°C，|dT/dt|≤0.01°C/min", "稳定判定", "最慢通道不通过则继续等待", "ARC实验员", "正式测试前", "P0"],
    ["09", "N_ref圈ARC测试", "在冻结工况下完成第N_ref圈完整充/放电；同步采集T/I/V/容量/能量/ARC热功率", "协议、方向、截止一致", "原始时序", "按实际工步和截止判定，不依赖文件名", "ARC实验员", "正式测量", "P0"],
    ["10", "当圈状态确认", "计算Q_Nref、容量SOH、能量效率和DCIR；判定是否进入精度组", "全部状态闸门通过", "样品配组表", "未通过转代表组/复核，不换圈重挑", "数据工程师", "测试后", "P0"],
    ["11", "冷却段", "继续记录到温度恢复，供UA和积分热量修正；不得在主动段结束即截断", "尾部热量收敛", "完整热响应", "尾部不足则积分热量无效", "ARC实验员", "测试后", "P0"],
    ["12", "后标定", "重复中档加热器检查或参考样品检查", "漂移在预算内", "post-check记录", "超限则本批次复核", "ARC实验员", "每日/每批", "P1"],
    ["13", "同步与预处理", "统一时间源；输出对齐残差；原始数据只读；修正脚本记录版本", "丢点/残差合格", "raw/processed清单", "失败不进入曲线对标", "数据工程师", "数据处理", "P0"],
    ["14", "产热计算", "同时给出仪器Power、C_eff·dT/dt、UA修正、动态修正；保留正负号", "能量闭合可解释", "Q(SOC)、E_heat、mean、P95", "近零区间用绝对误差", "仿真/数据", "数据处理", "P0"],
    ["15", "重复性", "同装夹至少3次，方法开发建议5次；重装夹3次；采用相同N_ref状态或匹配样品", "CV达到目标", "MSA报告", "不通过先查测量链", "项目组", "阶段闸门", "P0"],
    ["16", "盲测", "冻结所有参数后，用未参与标定的样品/工况验证", "平均/积分热量误差≤5%", "盲测报告", "盲测前禁止再调算法", "项目组", "阶段闸门", "P0"],
  ];
  writeTable(
    sheet,
    14,
    ["Step", "阶段", "动作", "进入/完成判据", "输出", "异常处理", "责任角色", "时点", "优先级"],
    sopRows,
    { rowHeight: 55 },
  );
  sopRows.forEach((r, i) => stylePriority(sheet, `I${15 + i}`, r[8]));

  noteBox(
    sheet,
    33,
    35,
    lastCol,
    "多工况注意：同一电芯连续做多个倍率/温度会增加循环数并改变SOH。高精度标定优先使用状态匹配的独立样品；若必须复用同一电芯，采用AB/BA平衡顺序、记录每次累计Ah/Wh，并确认始终处于容量平台带内。",
    "risk",
  );
  sheet.freezePanes.freezeRows(14);
}

// 05 一致性MSA
{
  const sheet = wb.worksheets.add("05_一致性MSA");
  const lastCol = setupSheet(
    sheet,
    "一致性与MSA设计｜分开量化仪器、装夹、日期和电芯差异",
    "不把所有离散性笼统称为“电芯一致性”；每一种方差来源都需要独立试验设计。",
    8,
    [12, 21, 26, 18, 18, 18, 27, 24],
  );

  section(sheet, 4, "一、误差分层与试验安排", lastCol);
  const msaRows = [
    ["L0", "算法重复", "同一份原始数据重复处理", "1份数据×3次自动处理", "应完全一致", "代码非确定性/版本漂移", "0差异", "P0"],
    ["L1", "设备重复", "同几何加热器，不拆装", "3功率档×3次", "测量链本身重复性", "仪器噪声、基线漂移", "回收误差≤3%，CV≤2%", "P0"],
    ["L2", "同电芯同装夹", "同一状态匹配电芯，不拆传感器", "建议5次", "电芯+仪器短期重复性", "热历史、控制误差", "CV≤3%", "P0"],
    ["L3", "重装夹", "同一参考件/匹配电芯，完全拆装", "3次", "传感器和夹具再现性", "贴附、压紧、引线", "CV≤4%", "P0"],
    ["L4", "跨日/操作者", "参考样品跨2天、2名操作者", "每组合≥2次", "长期再现性", "环境、人员、设备漂移", "纳入U95预算", "P1"],
    ["L5", "同批电芯", "固定N_ref状态的多个样品", "314建议≥6；587/1175≥3", "真实同批离散性", "容量、能效、DCIR、制造差异", "分布报告，不与L1混合", "P0"],
    ["L6", "跨批电芯", "不同生产批次", "每批≥3", "批次可迁移性", "材料/工艺差异", "作为外部验证", "P2"],
  ];
  writeTable(
    sheet,
    5,
    ["层级", "名称", "对象", "建议设计", "测到什么", "主要来源", "建议目标", "优先级"],
    msaRows,
    { rowHeight: 48 },
  );
  msaRows.forEach((r, i) => stylePriority(sheet, `H${6 + i}`, r[7]));

  section(sheet, 14, "二、减少电芯状态误差的配组方法", lastCol);
  const groupingRows = [
    ["1", "先定N_ref", "所有候选样品完成相同容量爬坡工况，正式比较不允许不同圈数。", "消除活化程度差异"],
    ["2", "三指标筛选", "按容量SOH、能量效率、DCIR同时判定，不能只看容量。", "减少热源状态差异"],
    ["3", "区组配对", "按三指标接近程度分成匹配区组，再随机分配到温度/倍率/方向。", "避免某工况恰好分到高内阻样品"],
    ["4", "平衡顺序", "必须复用样品时采用AB/BA顺序，避免总是低倍率在前、高倍率在后。", "识别顺序和新增循环影响"],
    ["5", "代表组保留", "超出精度窗口的正常样品不删除，进入量产代表组。", "不掩盖真实制造离散性"],
    ["6", "盲样隔离", "至少保留1/3样品不参与定圈阈值和模型校准。", "防止过拟合"],
  ];
  writeTable(
    sheet,
    15,
    ["步骤", "方法", "具体做法", "价值"],
    groupingRows,
    { startCol: 1, rowHeight: 45 },
  );
  sheet.mergeCells("E15:H15");
  sheet.getRange("E15").clear({ applyTo: "contents" });

  section(sheet, 23, "三、容量爬坡圈数的统一原则", lastCol);
  const nrefRows = [
    [
      "先固定状态，后固定圈数",
      "先用探索试验找稳定平台，再冻结N_ref；不是先拍脑袋规定第3圈或第5圈。",
      "防止形式统一但实际SOH仍不一致",
    ],
    [
      "正式测试不再逐只选峰",
      "正式样品在预先规定N_ref圈测；当圈状态不合格就转代表组/复核。",
      "避免事后选择偏差",
    ],
    [
      "共同N_ref需跨型号验证",
      "314得到的N_ref先原样用于587、1175验证；若大电芯未稳定，优先查前处理差异，再决定型号化。",
      "兼顾统一性和物理真实性",
    ],
    [
      "过度循环也会引入误差",
      "共同N_ref应是所有型号稳定所需的最小圈数，不应远超平台后继续循环。",
      "避免初始老化和累计热历史差异",
    ],
  ];
  writeTable(
    sheet,
    24,
    ["原则", "执行方式", "原因"],
    nrefRows,
    { startCol: 1, rowHeight: 48 },
  );
  sheet.mergeCells("D24:H24");
  sheet.getRange("D24").clear({ applyTo: "contents" });
  sheet.freezePanes.freezeRows(5);
}

// 06 跨电芯迁移
{
  const sheet = wb.worksheets.add("06_314-587-1175迁移");
  const lastCol = setupSheet(
    sheet,
    "314Ah → 587Ah → 1175Ah｜测试方法逐级放大路线",
    "按容量从小到大测试是合理的，但每一级迁移的是SOP和判据，不是C_eff、UA、时滞等绝对参数。",
    9,
    [12, 15, 22, 27, 27, 26, 25, 23, 14],
  );

  section(sheet, 4, "一、逐级放大计划", lastCol);
  const migrationRows = [
    ["Stage 0", "314Ah假电芯", "低/中/高功率加热标定、空载、脉冲响应", "建立噪声下限、C_eff、UA和时滞", "无电化学干扰，快速迭代方法", "功率回收≤3%；CV≤2%", "测量链V1", "立即", "P0"],
    ["Stage 1", "314Ah真实电芯", "容量爬坡定圈、样品状态配组、0.25P/0.5P、充放电、完整SOC曲线", "确定N_ref和精度组阈值", "现有数据与模型基础最好，适合方法开发", "重复CV≤3%；盲测热量误差≤5%", "冻结SOP V1", "G0后", "P0"],
    ["Stage 2", "587Ah假电芯", "保持V1算法不变，重做几何/功率范围标定", "识别尺寸引起的C_eff/UA/时滞变化", "中尺度暴露热惯性问题", "动态重构误差≤10%", "587校准包", "G1后", "P0"],
    ["Stage 3", "587Ah真实电芯", "先按314的N_ref直接测，再继续容量爬坡判断自身平台", "验证共同N_ref和样品状态窗", "避免在看到结果后改圈数", "状态闸门与重复性通过", "冻结SOP V2", "Stage 2后", "P1"],
    ["Stage 4", "1175Ah假电芯", "多点加热/分布式加热、长时阶跃、冷却尾段", "验证集中参数法适用性", "最大尺寸、最大温差和最长时滞", "空间温差/重构残差受控", "1175校准包", "G2后", "P0"],
    ["Stage 5", "1175Ah真实电芯", "同样先套用冻结N_ref和算法，再做多点温度盲测", "完成全产品最终验证", "检验方法极限而非继续拟合", "产热≤5%；温升1–2°C", "全产品规范", "Stage 4后", "P1"],
  ];
  writeTable(
    sheet,
    5,
    ["阶段", "对象", "主要测试", "要回答的问题", "为什么按此顺序", "通过标准", "输出", "启动", "优先级"],
    migrationRows,
    { rowHeight: 57 },
  );
  migrationRows.forEach((r, i) => stylePriority(sheet, `I${6 + i}`, r[8]));

  section(sheet, 13, "二、哪些内容可以迁移，哪些必须重标定", lastCol);
  const transferRows = [
    ["可直接迁移", "数据字典、命名、原始/处理分层、同步质量字段、完整SOC产热输出、MSA结构、盲测原则", "保持全产品可比性"],
    ["需验证后迁移", "N_ref、样品状态窗口、滤波窗口、动态逆算法正则化、传感器加权方式", "可能随尺寸和时间常数改变"],
    ["必须重标定", "C_eff(T)、UA(T,ΔT)、夹具附加热容、绝对功率档、时滞/传递函数、传感器坐标", "几何与装夹强相关"],
    ["不得直接迁移", "314Ah平均产热功率、绝对热阻、单点温度代表性、按Ah线性放大的产热参数", "物理上不保证成立"],
  ];
  writeTable(
    sheet,
    14,
    ["类别", "内容", "原因"],
    transferRows,
    { startCol: 1, rowHeight: 48 },
  );
  sheet.mergeCells("D14:I14");
  sheet.getRange("D14").clear({ applyTo: "contents" });

  section(sheet, 21, "三、共同N_ref的最终决策规则", lastCol);
  const commonRows = [
    ["314、587、1175在同一圈均已进入容量平台", "采用共同N_ref", "统一前处理圈数；各型号仍保留独立Q_BOL,ref和DCIR/能效参考"],
    ["个别型号晚于共同圈稳定", "先复核生产/储存/测试历史", "若前处理可统一则修正前处理后重测"],
    ["复核后仍存在系统差异", "采用型号化N_ref", "统一的是“稳定BOL状态定义”，不是强制同一数字"],
    ["N_ref过晚导致容量开始下降", "缩短到共同稳定的最早圈或型号化", "避免为了统一圈数引入初始老化"],
  ];
  writeTable(
    sheet,
    22,
    ["观察", "决策", "说明"],
    commonRows,
    { startCol: 1, rowHeight: 44 },
  );
  sheet.mergeCells("D22:I22");
  sheet.getRange("D22").clear({ applyTo: "contents" });
  sheet.freezePanes.freezeRows(5);
}

// 07 首轮测试矩阵
{
  const sheet = wb.worksheets.add("07_首轮测试矩阵");
  const lastCol = setupSheet(
    sheet,
    "首轮测试矩阵｜先定圈、再MSA、后跨尺寸",
    "工况数按阶段闸门控制，上一阶段未通过时不启动下一阶段，避免直接铺开全矩阵。",
    15,
    [9, 15, 13, 24, 12, 12, 10, 10, 10, 10, 12, 13, 23, 22, 10],
  );

  section(sheet, 4, "测试矩阵及预计有效过程数", lastCol);
  const matrixHeaders = [
    "阶段",
    "Test_ID",
    "对象",
    "测试内容",
    "温度点数",
    "功率/倍率点数",
    "方向数",
    "样品数",
    "重复/圈数",
    "预计过程数",
    "测量圈",
    "样品组",
    "主要输出",
    "通过后动作",
    "优先级",
  ];
  const matrixRows = [
    ["G0", "HTR-314-01", "314同几何加热器", "低/中/高三档稳态功率回收", 3, 3, 1, 1, 3, null, "不适用", "设备", "回收率、U95、CV", "建立C_eff/UA", "P0"],
    ["G0", "HTR-314-02", "314同几何加热器", "功率阶跃与脉冲响应", 3, 3, 1, 1, 2, null, "不适用", "设备", "时间常数、传递函数", "冻结dT/dt窗口", "P0"],
    ["G0", "BLANK-314", "ARC空载/夹具", "空载漂移与热漏", 3, 1, 1, 1, 3, null, "不适用", "设备", "基线、UA", "通过G0", "P0"],
    ["G1", "RAMP-314", "314Ah", "容量爬坡定圈探索", 1, 1, 2, 6, 10, null, "Cycle 1–10上限", "定圈组", "Q/η/DCIR随圈数", "确定N_ref,314", "P0"],
    ["G1", "ARC-314-REP", "314Ah", "固定N_ref圈同装夹重复", 1, 1, 2, 1, 5, null, "N_ref", "精度组", "同装夹CV", "验证≤3%", "P0"],
    ["G1", "ARC-314-REMOUNT", "314Ah", "固定N_ref状态重装夹", 1, 1, 2, 1, 3, null, "N_ref", "精度组", "重装夹CV", "验证≤4%", "P0"],
    ["G1", "ARC-314-MAIN", "314Ah", "0.25P/0.5P充放电与完整SOC曲线", 3, 2, 2, 3, 1, null, "N_ref", "精度组", "Q(SOC)、E_heat、mean/P95", "冻结SOP V1", "P0"],
    ["G1", "ARC-314-PROD", "314Ah", "量产代表性抽样", 1, 2, 2, 6, 1, null, "N_ref", "代表组", "真实分布P5/P50/P95", "定义鲁棒性目标", "P1"],
    ["G2", "HTR-587", "587同几何加热器", "稳态+动态重新标定", 3, 3, 1, 1, 3, null, "不适用", "设备", "587 C_eff/UA/时滞", "启动真实电芯", "P0"],
    ["G2", "RAMP-587", "587Ah", "先套用314 N_ref，再继续到自身平台", 1, 1, 2, 3, 10, null, "先N_ref,314", "定圈组", "共同N_ref有效性", "冻结N_ref,587", "P0"],
    ["G2", "ARC-587-MAIN", "587Ah", "冻结算法的0.25P/0.5P盲测", 3, 2, 2, 3, 1, null, "N_ref,587", "精度/盲测组", "跨尺度误差", "冻结SOP V2", "P1"],
    ["G3", "HTR-1175", "1175同几何加热器", "分布式加热、长阶跃和多点温度", 3, 3, 1, 1, 3, null, "不适用", "设备", "空间温差与逆热模型", "启动真实电芯", "P0"],
    ["G3", "RAMP-1175", "1175Ah", "先套用冻结N_ref，再继续到自身平台", 1, 1, 2, 3, 10, null, "先N_ref,common", "定圈组", "最终共同N_ref验证", "冻结N_ref,1175", "P0"],
    ["G3", "ARC-1175-MAIN", "1175Ah", "冻结算法的0.25P/0.5P盲测", 3, 2, 2, 3, 1, null, "N_ref,1175", "精度/盲测组", "全产品误差与温升", "形成标准", "P1"],
  ];
  writeTable(sheet, 5, matrixHeaders, matrixRows, {
    rowHeight: 49,
    bandRows: false,
  });
  for (let row = 6; row <= 19; row += 1) {
    sheet.getRange(`J${row}`).formulas = [
      [`=E${row}*F${row}*G${row}*H${row}*I${row}`],
    ];
  }
  sheet.getRange("E6:I19").format.fill = COLORS.paleYellow;
  sheet.getRange("J6:J19").format.fill = COLORS.paleBlue;
  matrixRows.forEach((r, i) => stylePriority(sheet, `O${6 + i}`, r[14]));

  noteBox(
    sheet,
    22,
    24,
    lastCol,
    "过程数是上限估算，不代表一次性全部启动。容量爬坡定圈试验中的Cycle 1–10用于探索；正式ARC矩阵只在N_ref冻结、样品状态闸门和G0测量系统资格全部通过后启动。",
    "warn",
  );
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(2);
}

// 08 记录与判定
{
  const sheet = wb.worksheets.add("08_记录与判定模板");
  const lastCol = setupSheet(
    sheet,
    "ARC运行记录与有效性判定模板",
    "黄色为人工录入，蓝色为公式判定；正式使用时每个Run一行，原始时序另存并通过Run_ID关联。",
    21,
    [15, 12, 15, 14, 12, 13, 10, 13, 13, 13, 14, 14, 16, 16, 15, 13, 13, 13, 13, 13, 16],
  );

  section(sheet, 4, "一、判定阈值（与前述工作表保持一致，黄色可编辑）", lastCol);
  const qcRows = [
    ["容量SOH偏差", 0.005, "相对值", "正式圈容量相对目标SOH"],
    ["初温偏差", 0.2, "°C", "Tcell,start与Tenv"],
    ["初始dT/dt", 0.01, "°C/min", "最慢/最大绝对值通道"],
    ["加热标定误差", 0.03, "相对值", "测试前后回收率误差"],
    ["空间温差", 1, "°C", "多点表面温差建议初值"],
  ];
  writeTable(
    sheet,
    5,
    ["阈值", "值", "单位", "用途"],
    qcRows,
    { startCol: 1, rowHeight: 33, bandRows: false },
  );
  sheet.getRange("B6:B10").format.fill = COLORS.yellow;
  sheet.getRange("B6").format.numberFormat = "0.0%";
  sheet.getRange("B9").format.numberFormat = "0.0%";
  sheet.mergeCells("E5:U5");
  sheet.getRange("E5").clear({ applyTo: "contents" });

  section(sheet, 12, "二、Run级记录表", lastCol);
  const runHeaders = [
    "Run_ID",
    "型号",
    "Cell_ID",
    "SOP版本",
    "日期",
    "操作者",
    "N_ref",
    "目标SOH",
    "实测SOH_Q",
    "T_env(°C)",
    "Tcell,start(°C)",
    "|dT/dt|start",
    "标定误差",
    "ΔT_space(°C)",
    "平均产热(W)",
    "积分热量(Wh)",
    "容量判定",
    "初态判定",
    "标定判定",
    "空间判定",
    "总有效性",
  ];
  const runRows = Array.from({ length: 24 }, () =>
    Array.from({ length: runHeaders.length }, () => null),
  );
  writeTable(sheet, 13, runHeaders, runRows, {
    rowHeight: 29,
    bandRows: false,
  });
  for (let row = 14; row <= 37; row += 1) {
    sheet.getRange(`Q${row}`).formulas = [[
      `=IF(OR(H${row}="",I${row}=""),"待录入",IF(ABS(I${row}-H${row})<=$B$6,"通过","不通过"))`,
    ]];
    sheet.getRange(`R${row}`).formulas = [[
      `=IF(OR(J${row}="",K${row}="",L${row}=""),"待录入",IF(AND(ABS(K${row}-J${row})<=$B$7,ABS(L${row})<=$B$8),"通过","不通过"))`,
    ]];
    sheet.getRange(`S${row}`).formulas = [[
      `=IF(M${row}="","待录入",IF(ABS(M${row})<=$B$9,"通过","不通过"))`,
    ]];
    sheet.getRange(`T${row}`).formulas = [[
      `=IF(N${row}="","待录入",IF(ABS(N${row})<=$B$10,"通过","不通过"))`,
    ]];
    sheet.getRange(`U${row}`).formulas = [[
      `=IF(OR(Q${row}="待录入",R${row}="待录入",S${row}="待录入",T${row}="待录入"),"待录入",IF(AND(Q${row}="通过",R${row}="通过",S${row}="通过",T${row}="通过"),"有效","无效/复核"))`,
    ]];
  }
  sheet.getRange("A14:P37").format.fill = COLORS.paleYellow;
  sheet.getRange("Q14:U37").format.fill = COLORS.lighterBlue;
  sheet.getRange("H14:I37").format.numberFormat = "0.00%";
  sheet.getRange("M14:M37").format.numberFormat = "0.00%";
  sheet.getRange("B14:B37").dataValidation = {
    rule: { type: "list", values: ["314Ah", "587Ah", "1175Ah"] },
  };
  sheet.freezePanes.freezeRows(13);
  sheet.freezePanes.freezeColumns(3);
}

// 09 来源与说明
{
  const sheet = wb.worksheets.add("09_来源与说明");
  const lastCol = setupSheet(
    sheet,
    "来源、现有基线与使用说明",
    "内部文件用于核对现行数据链；外部资料用于方法学依据。最终SOP需结合设备手册和实验室能力冻结。",
    6,
    [14, 24, 33, 50, 23, 20],
  );

  section(sheet, 4, "一、现有项目证据", lastCol);
  const internalRows = [
    [
      "现有314 ARC时序提取",
      "extract_arc_complete_timeseries.py",
      "源表Power(W)来自dT/dt×Cp×mass/60；ARC与测试柜事后对齐。",
      "C:/HithiumSSD/hithium/work/314Ah/202607_何争_314初始产热实测对标V1/02_模型/extract_arc_complete_timeseries.py",
      "本专项要求原始T与重算热功率并存。",
      "内部",
    ],
    [
      "现有314 BOL对标",
      "run_314_bol_arc_benchmark.py",
      "当前覆盖25°C、0.25P/0.5P、充放电；平均实测热约4.2–12.6W。",
      "C:/HithiumSSD/hithium/work/314Ah/202607_何争_314初始产热实测对标V1/02_模型/run_314_bol_arc_benchmark.py",
      "314加热器初始标定范围应覆盖该区间并留余量。",
      "内部",
    ],
    [
      "现有完整ARC数据",
      "314Ah ARC完整时序",
      "约1s采样，包含Can Temp、C1、C2、I/V/功率和产热功率。",
      "C:/HithiumSSD/hithium/BatteryProject/output/runs/arc314_exp_processing/20260722_142927_314Ah_ARC完整时序/314Ah_0.25P_0.5P充放电完整实测产热数据.xlsx.inspect.ndjson",
      "后续需补传感器空间坐标与统一同步质量字段。",
      "内部",
    ],
    [
      "产热校准代码",
      "heat_calibration.py",
      "现有模型已区分欧姆、反应、混合、滞后、接触和可逆热。",
      "C:/HithiumSSD/hithium/BatteryProject/src/heat_calibration.py",
      "实测侧应输出SOC分辨曲线支持分项诊断。",
      "内部",
    ],
  ];
  writeTable(
    sheet,
    5,
    ["主题", "文件/对象", "提取的现状", "路径/URL", "本方案用途", "类型"],
    internalRows,
    { rowHeight: 55 },
  );

  section(sheet, 11, "二、方法学参考", lastCol);
  const externalRows = [
    ["一般电池能量平衡", "Bernardi/Newman能量平衡包含反应、混合、焦耳热等多项。", "https://www.osti.gov/biblio/5913742", "用于热源分项与能量闭合框架", "外部", "一次文献"],
    ["NREL等温量热", "量热可用于不同温度、倍率和工况下的产热与效率测试。", "https://www.nrel.gov/docs/fy24osti/89032.pdf", "用于测试矩阵和时滞认识", "外部", "国家实验室"],
    ["逆量热方法", "大型电芯外部热流存在时滞，逆热方法可改善时间分辨产热重构。", "https://research-hub.nrel.gov/en/publications/non-invasive-accurate-time-resolved-inverse-battery-calorimetry-a/", "用于587/1175动态修正路线", "外部", "研究论文"],
    ["整电芯Cp与产热测试", "通过均温过程减少大电芯温度不均匀造成的热参数离散。", "https://www.sciencedirect.com/science/article/pii/S0196890418312755", "用于C_eff/Cp和均温设计", "外部", "研究论文"],
    ["P2D参数可辨识性", "需组合OCV、倍率/EIS及敏感性分析，单一测试难以同时识别全部参数。", "https://www.sciencedirect.com/science/article/pii/S2405829721006279", "用于避免把测试误差反拟合进模型", "外部", "研究论文"],
  ];
  writeTable(
    sheet,
    12,
    ["主题", "关键结论", "URL", "本方案用途", "类型", "来源等级"],
    externalRows,
    { rowHeight: 53 },
  );

  section(sheet, 19, "三、使用说明", lastCol);
  const usageRows = [
    ["黄色单元格", "需由项目组录入或在314Ah定圈/MSA后冻结的参数。"],
    ["蓝色单元格", "公式或自动判定结果，不建议手工覆盖。"],
    ["建议阈值", "为立项初值，不等同于设备保证值；必须用假电芯和314Ah试验确认。"],
    ["正式变更", "N_ref、状态窗、同步/滤波、C_eff/UA或传感器布置任一变化，均需升级SOP版本。"],
    ["数据保留", "被排除或转代表组的样品数据不得删除；原始数据与处理数据分开存放。"],
  ];
  writeTable(
    sheet,
    20,
    ["项目", "说明"],
    usageRows,
    { startCol: 1, rowHeight: 42 },
  );
  sheet.mergeCells("C20:F20");
  sheet.getRange("C20").clear({ applyTo: "contents" });
  sheet.freezePanes.freezeRows(2);
}

// Compact inspections and visual renders.
const keyChecks = [
  ["00_专项总览", "A1:F35"],
  ["01_容量爬坡定圈", "A1:J52"],
  ["02_SOH与样品配组", "A1:S45"],
  ["03_ARC精度提升", "A1:I26"],
  ["04_ARC标准SOP", "A1:I35"],
  ["05_一致性MSA", "A1:H28"],
  ["06_314-587-1175迁移", "A1:I26"],
  ["07_首轮测试矩阵", "A1:O24"],
  ["08_记录与判定模板", "A1:U37"],
  ["09_来源与说明", "A1:F25"],
];

for (const [sheetName, range] of keyChecks) {
  const preview = await wb.render({
    sheetName,
    range,
    scale: sheetName === "02_SOH与样品配组" || sheetName === "08_记录与判定模板" ? 0.75 : 1,
    format: "png",
  });
  const safeName = sheetName.replaceAll("/", "_");
  await fs.writeFile(
    path.join(qaDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const overviewInspect = await wb.inspect({
  kind: "table",
  range: "00_专项总览!A1:F35",
  include: "values,formulas",
  tableMaxRows: 35,
  tableMaxCols: 6,
  maxChars: 12000,
});
await fs.writeFile(
  path.join(qaDir, "overview_inspect.ndjson"),
  overviewInspect.ndjson,
  "utf8",
);

const formulaErrorInspect = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(
  path.join(qaDir, "formula_errors.ndjson"),
  formulaErrorInspect.ndjson,
  "utf8",
);

const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(outputPath);
console.log(outputPath);

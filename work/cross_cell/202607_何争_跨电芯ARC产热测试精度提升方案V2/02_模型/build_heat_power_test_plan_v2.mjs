import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const taskRoot =
  "C:/HithiumSSD/hithium/work/cross_cell/202607_何争_跨电芯ARC产热测试精度提升方案V2";
const outputDir = path.join(
  taskRoot,
  "04_输出结果",
  "outputs",
  "heat_power_test_plan_v2_20260723",
);
const qaDir = path.join(outputDir, "qa");
const outputPath = path.join(
  outputDir,
  "发热功率专项_完整测试清单与精度提升方案V2.xlsx",
);
await fs.mkdir(qaDir, { recursive: true });

const wb = Workbook.create();
const C = {
  blue: "#1261D9",
  dark: "#0B3E91",
  pale: "#EAF2FB",
  pale2: "#F5F8FC",
  white: "#FFFFFF",
  text: "#243142",
  line: "#C9D6E5",
  yellow: "#FFF2CC",
  red: "#C00000",
  paleRed: "#FCE8E6",
  green: "#16804A",
  paleGreen: "#E2F0D9",
};

function colName(index1Based) {
  let n = index1Based;
  let s = "";
  while (n > 0) {
    n -= 1;
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26);
  }
  return s;
}

function setup(sheet, title, subtitle, widths) {
  const last = colName(widths.length);
  sheet.showGridLines = false;
  widths.forEach((w, i) => {
    const col = colName(i + 1);
    sheet.getRange(`${col}1:${col}120`).format.columnWidth = w;
  });
  sheet.mergeCells(`A1:${last}1`);
  sheet.getRange("A1").values = [[title]];
  sheet.getRange(`A1:${last}1`).format = {
    fill: C.blue,
    font: { bold: true, color: C.white, size: 18 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${last}1`).format.rowHeight = 34;
  sheet.mergeCells(`A2:${last}2`);
  sheet.getRange("A2").values = [[subtitle]];
  sheet.getRange(`A2:${last}2`).format = {
    fill: C.pale,
    font: { italic: true, color: C.dark, size: 10 },
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange(`A2:${last}2`).format.rowHeight = 30;
  return last;
}

function section(sheet, row, title, last) {
  sheet.mergeCells(`A${row}:${last}${row}`);
  sheet.getRange(`A${row}`).values = [[title]];
  sheet.getRange(`A${row}:${last}${row}`).format = {
    fill: C.dark,
    font: { bold: true, color: C.white, size: 12 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A${row}:${last}${row}`).format.rowHeight = 25;
}

function table(sheet, startRow, headers, rows, options = {}) {
  const startCol = options.startCol ?? 1;
  const endCol = startCol + headers.length - 1;
  const left = colName(startCol);
  const right = colName(endCol);
  const header = sheet.getRange(`${left}${startRow}:${right}${startRow}`);
  header.values = [headers];
  header.format = {
    fill: C.blue,
    font: { bold: true, color: C.white, size: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: C.line },
  };
  header.format.rowHeight = options.headerHeight ?? 32;
  if (rows.length) {
    const body = sheet.getRange(
      `${left}${startRow + 1}:${right}${startRow + rows.length}`,
    );
    body.values = rows;
    body.format = {
      font: { color: C.text, size: 9 },
      verticalAlignment: "center",
      wrapText: true,
      borders: { preset: "all", style: "thin", color: C.line },
    };
    body.format.rowHeight = options.rowHeight ?? 48;
    rows.forEach((_, i) => {
      if (i % 2 === 1) {
        sheet
          .getRange(
            `${left}${startRow + 1 + i}:${right}${startRow + 1 + i}`,
          )
          .format.fill = C.pale;
      }
    });
  }
  return startRow + rows.length;
}

function note(sheet, row1, row2, last, text, risk = false) {
  sheet.mergeCells(`A${row1}:${last}${row2}`);
  sheet.getRange(`A${row1}`).values = [[text]];
  sheet.getRange(`A${row1}:${last}${row2}`).format = {
    fill: risk ? C.paleRed : C.yellow,
    font: { bold: true, color: risk ? C.red : C.dark, size: 10 },
    wrapText: true,
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: C.line },
  };
}

function priority(sheet, cell, p) {
  const r = sheet.getRange(cell);
  if (p === "P0") {
    r.format = {
      fill: C.paleRed,
      font: { bold: true, color: C.red },
      horizontalAlignment: "center",
    };
  } else if (p === "P1") {
    r.format = {
      fill: C.yellow,
      font: { bold: true, color: "#7F6000" },
      horizontalAlignment: "center",
    };
  } else {
    r.format = {
      fill: C.paleGreen,
      font: { bold: true, color: C.green },
      horizontalAlignment: "center",
    };
  }
}

// 00 专项总览
{
  const s = wb.worksheets.add("00_专项总览");
  const last = setup(
    s,
    "发热功率专项｜完整测试体系与精度提升路线",
    "从电芯状态、热源参数、热物性、边界条件到温度场验证形成闭环；ARC只是其中的总产热基准。",
    [15, 22, 28, 31, 31, 24, 20, 12],
  );

  section(s, 4, "一、专项目标", last);
  const goalRows = [
    ["状态统一", "消除不同容量爬坡圈数、SOH、能量效率和DCIR带来的样品偏差", "固定N_ref圈；容量SOH+能效+DCIR联合筛选", "减少电芯一致性误差"],
    ["参数测准", "分别获得可逆热、欧姆/极化热、Cp、k和热边界参数", "独立测试优先，避免从同一温升曲线同时反演多个参数", "提高模型物理可信度"],
    ["产热验证", "用ARC/量热获得完整SOC产热曲线和积分热量", "设备标定、热漏/附加热容修正、时间同步和重复性MSA", "电芯级产热误差目标≤5%"],
    ["温升验证", "验证电芯—模组温度场而非只对一个测温点", "多点测温、边界条件实测、盲工况验证", "温升误差目标1–2°C"],
  ];
  table(s, 5, ["目标层", "要解决的问题", "核心手段", "预期结果"], goalRows, {
    rowHeight: 46,
  });
  s.mergeCells("E5:H5");
  s.getRange("E5").clear({ applyTo: "contents" });

  section(s, 11, "二、完整测试体系", last);
  const systemRows = [
    ["0｜状态基线", "容量爬坡定圈、容量/能效/DCIR筛选", "先保证不同电芯处在同一稳定BOL或目标SOH状态", "所有后续测试共同前提"],
    ["1｜电化学热源", "OCV与滞后、熵热系数、EIS、HPPC/DCIR、倍率/恒功率", "校准可逆热、欧姆热、反应/极化热及其SOC/T/SOH依赖", "P2D/Bernardi热源输入"],
    ["2｜热物性与边界", "比热Cp、各向异性导热系数k、换热系数h/接触热阻", "把热源与温升响应分开标定", "热方程输入"],
    ["3｜综合验证", "ARC产热功率、温度场、SOH产热、模组/系统验证", "检查完整曲线、积分热量、热点和跨产品迁移", "最终验收"],
  ];
  table(s, 12, ["层级", "测试项目", "主要作用", "输出去向"], systemRows, {
    rowHeight: 48,
  });
  s.mergeCells("E12:H12");
  s.getRange("E12").clear({ applyTo: "contents" });

  section(s, 18, "三、推荐实施顺序", last);
  const routeRows = [
    ["Step 1", "314Ah", "建立全部测试方法；确定N_ref；完成完整参数图谱和ARC重复性", "方法开发", "通过后冻结SOP V1"],
    ["Step 2", "587Ah", "按冻结方法先做锚点验证；Cp/k/h/EIS/HPPC等型号相关参数仍需实测", "中尺度迁移", "通过后冻结SOP V2"],
    ["Step 3", "1175Ah", "先做关键锚点和多点温度验证；重点检查大热惯性、温差和量热时滞", "最终压力验证", "通过后形成全产品规范"],
  ];
  table(s, 19, ["步骤", "电芯", "主要任务", "定位", "闸门"], routeRows, {
    rowHeight: 48,
  });
  s.mergeCells("F19:H19");
  s.getRange("F19").clear({ applyTo: "contents" });

  note(
    s,
    24,
    26,
    last,
    "关键判断：可以按314Ah→587Ah→1175Ah由小到大推进，但只能迁移测试方法、数据格式和验收逻辑；熵热系数、OCV滞后、EIS/HPPC、Cp、k及热边界参数不能简单按Ah比例放大。",
  );

  section(s, 28, "四、核心验收目标", last);
  const acceptRows = [
    ["样品状态", "容量SOH、能效、DCIR同时处于目标窗口", "建议初值：±0.5%、±0.3个百分点、±3%"],
    ["量热系统", "已知加热功率回收误差", "≤3%，并报告U95"],
    ["重复性", "同装夹/重装夹产热CV", "≤3% / ≤4%"],
    ["产热仿真", "平均功率和积分热量误差", "≤5%；完整SOC曲线另报NRMSE及Peak/P95"],
    ["温度场", "峰值温升和热点误差", "目标1°C，最差不超过2°C"],
    ["模组/系统", "综合热响应误差", "目标≤10%"],
  ];
  table(s, 29, ["层级", "指标", "建议目标"], acceptRows, { rowHeight: 38 });
  s.mergeCells("D29:H29");
  s.getRange("D29").clear({ applyTo: "contents" });

  section(s, 37, "五、方法学参考", last);
  const refRows = [
    ["电池能量平衡", "https://www.osti.gov/biblio/5913742"],
    ["NREL等温量热", "https://www.nrel.gov/docs/fy24osti/89032.pdf"],
    ["大型电芯逆量热", "https://research-hub.nrel.gov/en/publications/non-invasive-accurate-time-resolved-inverse-battery-calorimetry-a/"],
    ["P2D参数辨识", "https://www.sciencedirect.com/science/article/pii/S2405829721006279"],
  ];
  table(s, 38, ["主题", "URL"], refRows, { rowHeight: 32 });
  s.mergeCells("C38:H38");
  s.getRange("C38").clear({ applyTo: "contents" });
  s.freezePanes.freezeRows(2);
}

// 01 完整测试清单
{
  const s = wb.worksheets.add("01_完整测试清单");
  const last = setup(
    s,
    "发热功率专项｜完整测试清单",
    "主表：既包含ARC，也包含电化学热源参数、热物性、边界条件和温度场验证。",
    [8, 15, 19, 25, 27, 36, 24, 10],
  );
  section(s, 4, "测试项目、作用与精度提升重点", last);
  const rows = [
    ["T01", "状态基线", "容量爬坡定圈", "确定稳定BOL参考容量和正式测量圈数N_ref", "固定温度、倍率、SOC/电压窗和静置；连续循环至容量平台", "不用逐只事后挑最高容量圈；先用样品组确定N_ref，正式测试固定同一圈并校验能效/DCIR", "Q(cycle)、η_E、DCIR、N_ref", "P0"],
    ["T02", "状态基线", "容量/能效/DCIR筛选", "减少测试电芯SOH和能效不一致造成的产热偏差", "统一N_ref圈、温度、SOC和脉冲定义", "容量SOH、能量效率、DCIR联合配组；精度组与量产代表组分开", "样品状态表、配组结果", "P0"],
    ["T03", "电化学", "OCV与滞后测试", "提供平衡电压、SOC映射及充放电滞后热基础", "充/放电支路分别测试；低倍率或分段静置；多温度", "统一休息终止判据dV/dt；同一SOC网格；电压通道校准；禁止把单一放电OCV当平衡OCV", "OCV_charge/discharge(SOC,T)、滞后带", "P0"],
    ["T04", "电化学", "熵热系数测试", "得到dU/dT(SOC)，校准可逆热Qrev", "SOC 5%或10%步长；多个温度点；充放电支路分开", "每个SOC充分平衡后对U-T做回归；温度顺序交错以抵消漂移；高精度温度/电压校准；关键SOC重复", "dU/dT(SOC,T,branch)及置信区间", "P0"],
    ["T05", "电化学", "EIS", "约束欧姆、电荷转移、双电层和扩散响应", "典型SOC×温度×SOH；小信号频率扫描", "开短路/线缆补偿；激励幅值线性验证；测试前充分静置；重复谱与Kramers–Kronig一致性检查", "Nyquist/Bode、R0/Rct/扩散特征", "P0"],
    ["T06", "电化学", "HPPC/DCIR", "标定R(SOC,T,SOH,Δt)并支撑不可逆热", "SOC网格；充/放电脉冲；1/10/30/120s等多时间尺度", "SOC按稳定BOL容量计算；统一静置、采样率和脉冲边沿；分别输出瞬时与不同持续时间电阻", "DCIR map、极化与恢复曲线", "P0"],
    ["T07", "电化学", "倍率/恒功率充放电", "联合约束动力学、传质、能量效率和平均产热趋势", "多倍率/功率、温度、充放电方向", "固定N_ref与电压窗；使用配组样品；若复用同一电芯采用平衡顺序；同步记录电能和温度", "V/Q/E/η随SOC与倍率", "P0"],
    ["T08", "电化学", "GITT/松弛测试", "辅助识别扩散与准平衡电压，减少EIS/HPPC参数耦合", "SOC分段脉冲+充分松弛；代表温度", "统一脉冲量和松弛终止判据；温度稳定；用多段数据交叉验证", "扩散/松弛时间常数、准OCV", "P1"],
    ["T09", "产热基准", "ARC产热功率测试", "直接获得完整总产热曲线，作为模型总热基准", "固定N_ref圈；0.25P/0.5P等；充放电；多温度", "电加热器标定；C_eff与热漏修正；统一装夹/传感器位置；原始T保留；固定dT/dt算法；I/V/T硬件同步", "Qheat(SOC)、平均/P95、积分热量、U95", "P0"],
    ["T10", "热物性", "比热Cp测试", "决定单位热量对应的温升速度", "低/中/高SOC；多个温度；必要时SOH点", "整电芯已知加热功率法；扣除夹具附加热容；保证均温；同一装夹前后校准；Cp与C_eff分开报告", "Cp(T,SOC,SOH)、C_eff", "P0"],
    ["T11", "热物性", "导热系数k测试", "决定内部温差、热点位置和热扩散时间", "厚度/宽度/高度方向；温度与夹紧压力", "各向异性分别测试；校准参考材料；控制接触热阻和压力；多位置/重复测量", "kx/ky/kz(T,pressure)及不确定度", "P0"],
    ["T12", "热边界", "换热系数h与接触热阻", "建立空气、冷板、模组夹具的真实热边界", "不同风速/流量、方向、压紧力、界面材料", "使用同几何假电芯和分布式加热器；实测流量与入口温度；h和接触热阻分开标定，禁止同温升曲线同时自由反演", "h、Rth_contact、边界配置表", "P0"],
    ["T13", "综合验证", "温度场验证", "验证峰值温度、表面温差、热点和动态时滞", "多点温度+IR；恒功率、脉冲和真实工况", "固定测温坐标和粘贴方式；IR发射率校准；所有温度/电流同步；采用未参与标定的盲工况", "T(x,t)、热点位置、ΔTspace、温升误差", "P0"],
    ["T14", "综合验证", "SOH产热测试", "建立Qheat(SOC,T,I,SOH)并验证全寿命适用性", "BOL、95%、90%、80%SOH；循环/日历老化分开", "SOH相对稳定BOL容量定义；同时匹配能效和DCIR；相同SOH但不同老化路径不得混合", "产热随SOH/老化路径变化", "P1"],
    ["T15", "系统验证", "模组/系统热验证", "验证电芯迁移到模组后的附加热源和散热边界", "连接片、接触电阻、冷却边界、典型工况", "电芯本体热与连接件I²R热分开；测流量/压差/进出口温度；保留电芯级盲测参数", "模组热量、温度场、系统误差", "P1"],
  ];
  table(
    s,
    5,
    ["编号", "模块", "测试项目", "对仿真作用", "建议条件", "提高精度的核心措施", "主要输出", "优先级"],
    rows,
    { rowHeight: 66 },
  );
  rows.forEach((r, i) => priority(s, `H${6 + i}`, r[7]));
  note(
    s,
    22,
    24,
    last,
    "最小可执行集不是只做ARC：至少应包含T01–T07、T09–T13。ARC给出总热基准，熵热/OCV/EIS/HPPC负责解释热源，Cp/k/h负责把热量转换成温度场。",
  );
  s.freezePanes.freezeRows(5);
  s.freezePanes.freezeColumns(3);
}

// 02 各项目精度提升
{
  const s = wb.worksheets.add("02_各项目精度提升");
  const last = setup(
    s,
    "各测试项目如何提高精度",
    "按“常见偏差—改进动作—一致性控制—质量检查”组织，避免只有项目名称没有执行方法。",
    [20, 28, 36, 31, 24, 28, 22],
  );
  section(s, 4, "精度提升方法表", last);
  const rows = [
    ["容量爬坡定圈", "不同电芯在不同活化圈数测量；逐只挑最大容量圈", "先在314Ah样品组连续记录容量、能效和DCIR，识别稳定最高平台；冻结统一N_ref", "相同生产/储存历史、相同循环程序、相同测试间隔", "314Ah≥6只；587/1175Ah各≥3只验证", "容量斜率、能效漂移和DCIR同时稳定", "正式样品不得事后换圈"],
    ["OCV与滞后", "静置不足导致极化残留；充放电支路混用", "分支路测试；以dV/dt而不是固定时长作为平衡判据；校准电压通道", "同一SOC网格、温度、N_ref和容量基准", "关键SOC≥3只；其余点至少2只", "支路重复差、OCV闭合和温度稳定", "不使用单一文献OCV直接套用"],
    ["熵热系数", "温度未均匀、电压仍松弛；dU/dT信号小", "每个SOC在多个温度充分平衡；U-T线性回归；温度升降顺序交错；支路分开", "固定SOC制备方式、温度平台和测温位置", "全曲线≥2只，关键SOC≥3只", "回归R²、斜率置信区间、升降温差", "低倍率下不可忽略可逆热"],
    ["EIS", "夹具/线缆寄生、激励过大、SOC漂移", "开短路补偿；验证小信号线性；充分静置；频谱重复；做K-K一致性检查", "固定夹具、线缆、温度、SOC和激励幅值", "每个关键点≥3次重复", "重复谱差、K-K残差、漂移前后OCV", "不能仅凭单谱反演全部P2D参数"],
    ["HPPC/DCIR", "SOC定义不一致、脉冲边沿采样不足、静置时间不同", "统一容量基准和脉冲协议；高采样率记录边沿；输出多时间尺度电阻", "固定T/SOC/N_ref/脉冲幅值/静置判据", "每点≥3只或匹配样品", "电流精度、时间戳、恢复曲线一致性", "不能把单一30s电阻代表所有不可逆热"],
    ["倍率/恒功率", "工况顺序与新增循环混淆；电压窗不一致", "优先用匹配独立样品；复用时AB/BA平衡顺序；实际截止电压进入分析", "N_ref、SOH、温度、功率定义和静置统一", "关键工况≥3只", "容量/能量/效率闭合、顺序效应", "不要只按文件名判断工况"],
    ["ARC产热功率", "dT/dt噪声、热漏、夹具热容、传感器位置和时间错位", "已知加热器覆盖低/中/高功率；识别C_eff和UA；固定传感器位置；统一滤波/求导；同步I/V/T", "固定N_ref、装夹、系统边界、初始温度和冷却尾段", "同装夹≥3次，方法开发建议5次；重装≥3次", "功率回收、CV、同步残差、能量闭合、U95", "完整SOC曲线和积分热量优先于单点峰值"],
    ["比热Cp", "把夹具附加热容算进电芯；内部温度不均匀", "使用已知加热能量；空夹具/假电芯标定；温度均匀后计算；报告cell Cp与system C_eff", "固定SOC、温度、传感器和装夹BOM", "每个关键点≥3次", "加热能量闭合、升/降温一致性", "不能只用BOM加权值替代整电芯验证"],
    ["导热系数k", "未区分方向；接触热阻被当成材料导热", "厚/宽/高三方向分别测试；改变压力验证接触影响；使用参考材料校准", "固定样品尺寸、压力、界面材料和温度", "每方向≥3次", "稳态/瞬态拟合残差、重复性", "大方壳不能使用单一各向同性k"],
    ["h与接触热阻", "从电芯温升同时拟合h、Cp、k，参数互相补偿", "使用同几何分布式加热器；先独立Cp/k，再标定h和Rth_contact；实测风量/流量", "固定方向、流量、压力、界面材料和环境", "每个边界工况≥3次", "热平衡、流量稳定性、装夹重复性", "h不是跨夹具、跨产品的常数"],
    ["温度场验证", "单点温度代表整电芯；IR发射率和测点漂移", "三点以上接触温度+IR；位置模板；发射率校准；动态工况硬件同步；盲工况验收", "固定测点坐标、粘贴材料、相机角度和边界", "每个关键工况≥3只/次", "热点位置、空间温差、时滞和温升误差", "先验证产热源再调热边界"],
    ["SOH产热", "只按容量SOH分组；不同老化路径混在一起", "记录容量SOH、能效、DCIR、累计Ah/Wh和老化路线；循环/日历老化分开", "相同目标SOH、温度、倍率和静置", "每个SOH/路径≥3只", "状态窗口和热曲线重复性", "相同容量SOH不等于相同发热状态"],
    ["模组/系统", "连接件产热混入电芯；冷却边界不实测", "四线测接触电阻；连接片温度；测冷却流量/压差/进出口温度；电芯参数冻结盲测", "固定压紧、连接工艺、冷却条件和布点", "代表模组≥2套，关键工况重复", "系统能量平衡、温差和重复性", "系统误差不能反向全部修正到电芯产热"],
  ];
  table(
    s,
    5,
    ["测试项目", "常见偏差", "提高精度的具体动作", "一致性控制", "建议重复设计", "数据质量检查", "禁止/注意"],
    rows,
    { rowHeight: 72 },
  );
  s.freezePanes.freezeRows(5);
  s.freezePanes.freezeColumns(1);
}

// 03 跨电芯矩阵
{
  const s = wb.worksheets.add("03_跨电芯测试矩阵");
  const last = setup(
    s,
    "314Ah → 587Ah → 1175Ah｜测试矩阵",
    "314Ah做完整方法开发；587Ah和1175Ah先做锚点验证，再根据偏差决定是否扩展全图。",
    [19, 33, 33, 34, 20, 26],
  );
  note(
    s,
    4,
    5,
    last,
    "由小到大测试是合理的，但每个型号仍需测型号相关参数。可以减少587/1175的初始工况数量，不能直接把314Ah的熵热、OCV、EIS/HPPC、Cp、k和热边界按容量放大。",
  );

  section(s, 7, "分级实施矩阵", last);
  const rows = [
    ["容量爬坡/N_ref", "完整定圈：同批≥6只，形成算法和N_ref,314", "≥3只，先验证314的N_ref，再确认N_ref,587", "≥3只，先验证冻结N_ref，再确认N_ref,1175", "仅方法可迁移", "G0：先统一电芯状态"],
    ["容量/能效/DCIR配组", "建立精度组阈值与量产代表组规则", "沿用规则，参考值按587重新计算", "沿用规则，参考值按1175重新计算", "规则可迁移，数值不迁移", "所有测试共同前提"],
    ["OCV与滞后", "完整SOC×温度×充放电支路", "至少完整SOC支路；温度锚点后决定扩展", "完整SOC支路；优先代表温度", "不可直接迁移", "进入熵热/模型前"],
    ["熵热系数", "完整SOC曲线，关键SOC重复", "先测低/中/高SOC与温度锚点；偏差显著则全图", "先测关键SOC锚点；模型敏感区必须实测", "不可按Ah迁移", "Qrev标定闸门"],
    ["EIS", "SOC×温度完整设计", "至少10/50/90%SOC×关键温度", "关键SOC×温度锚点，重点检查大电芯寄生影响", "不可直接迁移", "电化学参数闸门"],
    ["HPPC/DCIR", "完整SOC×T×多脉冲时长", "完整SOC或10%步长关键图谱", "关键SOC×T，后续按敏感性扩展", "不可直接迁移", "不可逆热闸门"],
    ["倍率/恒功率", "0.1/0.25/0.5/1P等完整基线", "先0.25/0.5P充放电；通过后扩展", "先0.25/0.5P关键工况", "工况定义可迁移", "综合电化学验证"],
    ["GITT/松弛", "代表SOC/温度用于参数解耦", "按EIS/HPPC辨识结果决定", "仅在参数耦合明显时开展", "方法可迁移", "P1决策项"],
    ["ARC产热功率", "多温度×0.25/0.5P×充放电；完整SOC曲线", "先25°C与温度边界锚点；同装夹/重装MSA", "先25°C关键工况；重点做时滞与多点温度", "算法可迁移，校准不可迁移", "总热盲测闸门"],
    ["比热Cp", "低/中/高SOC×温度", "每个关键SOC/温度至少锚点测量", "必须做整电芯锚点，不能BOM外推", "不可按Ah迁移", "温升模型输入"],
    ["导热系数k", "三方向+压力/温度影响", "三方向至少代表点，压力条件与模组一致", "三方向必测，重点厚度方向", "不可直接迁移", "内部温差输入"],
    ["h/接触热阻", "314夹具和边界全标定", "587同几何假电芯重新标定", "1175分布式加热器重新标定", "不可跨夹具迁移", "温度场闸门"],
    ["温度场", "多点温度+IR；恒功率/脉冲/盲工况", "多点温度，检查热点和时间常数", "多点温度+IR，重点大热惯性与温差", "布点原则可迁移", "温升1–2°C目标"],
    ["SOH产热", "BOL方法通过后开展95/90/80%SOH", "先BOL与一个中间SOH锚点", "先BOL，确认资源后扩展SOH", "状态定义可迁移", "第二阶段"],
    ["模组/系统", "用于方法准备，不作为首轮主战场", "可先做小模组连接件热验证", "最终产品模组/系统验证", "不可从单体直接推断", "最终验收"],
  ];
  table(
    s,
    8,
    ["测试项目", "314Ah", "587Ah", "1175Ah", "迁移判断", "阶段闸门"],
    rows,
    { rowHeight: 62 },
  );

  section(s, 25, "推荐资源投入原则", last);
  const resourceRows = [
    ["314Ah", "投入最多", "用于把测试方法、数据处理、重复性和判据做扎实"],
    ["587Ah", "中等投入", "先做关键锚点，验证方法是否需要随尺寸修正"],
    ["1175Ah", "聚焦投入", "优先验证热惯性、内部温差、量热时滞和最终产品工况"],
  ];
  table(s, 26, ["对象", "投入级别", "理由"], resourceRows, { rowHeight: 42 });
  s.mergeCells("D26:F26");
  s.getRange("D26").clear({ applyTo: "contents" });
  s.freezePanes.freezeRows(8);
}

// 04 记录与验收
{
  const s = wb.worksheets.add("04_记录与验收");
  const last = setup(
    s,
    "统一记录与验收表",
    "上半部分是统一验收标准，下半部分用于项目组跟踪每个测试项目的实际完成情况。",
    [12, 19, 15, 16, 20, 21, 16, 21, 22, 14, 14, 14, 16, 25],
  );

  section(s, 4, "一、统一验收标准", last);
  const acceptRows = [
    ["样品状态", "固定N_ref；容量SOH、能效、DCIR在窗口内", "建议±0.5%、±0.3个百分点、±3%", "314首轮后冻结"],
    ["测试重复性", "同条件重复CV", "≤3%；重装夹≤4%", "分别报告仪器与电芯差异"],
    ["熵热系数", "关键SOC回归与重复", "报告斜率置信区间；升/降温结果一致", "不只给拟合曲线"],
    ["OCV/EIS/HPPC", "平衡、重复及一致性检查", "OCV满足dV/dt；EIS通过K-K；HPPC时间戳完整", "任一不通过不进入参数拟合"],
    ["Cp/k/h", "标准件/加热器校准与重复", "校准残差和U95满足模型精度预算", "三个参数不得同曲线自由反演"],
    ["ARC", "加热功率回收、同步与积分热量", "回收误差≤3%；同装夹CV≤3%", "保留原始T和修正结果"],
    ["产热仿真", "平均功率及积分热量误差", "≤5%；完整SOC曲线另评估", "使用盲样/盲工况"],
    ["温度场", "峰值温度、热点和空间温差", "温升误差1–2°C", "不得只看单点平均温度"],
    ["模组/系统", "热量及温度综合误差", "目标≤10%", "连接件热单独核算"],
  ];
  table(s, 5, ["层级", "验收内容", "建议目标", "说明"], acceptRows, {
    rowHeight: 42,
  });
  s.mergeCells("E5:N5");
  s.getRange("E5").clear({ applyTo: "contents" });

  section(s, 16, "二、测试项目执行记录", last);
  const headers = [
    "Test_ID",
    "测试项目",
    "型号",
    "样品组",
    "N_ref/SOH",
    "T/SOC/倍率",
    "样品数",
    "重复设计",
    "主要输出",
    "CV/U95",
    "是否通过",
    "状态",
    "负责人",
    "备注/偏差处理",
  ];
  const blank = Array.from({ length: 24 }, () =>
    Array.from({ length: headers.length }, () => null),
  );
  table(s, 17, headers, blank, { rowHeight: 29 });
  s.getRange("A18:J41").format.fill = C.yellow;
  s.getRange("K18:N41").format.fill = C.pale;
  s.getRange("C18:C41").dataValidation = {
    rule: { type: "list", values: ["314Ah", "587Ah", "1175Ah", "模组/系统"] },
  };
  s.getRange("K18:K41").dataValidation = {
    rule: { type: "list", values: ["通过", "不通过", "待判定"] },
  };
  s.getRange("L18:L41").dataValidation = {
    rule: { type: "list", values: ["未开始", "进行中", "已完成", "暂停", "复核"] },
  };
  note(
    s,
    44,
    46,
    last,
    "使用原则：原始数据、处理数据和报告通过Test_ID/Run_ID关联；任何被排除的样品或失败测试都保留记录和原因。黄色区域为人工录入，蓝色区域为结论与管理信息。",
  );
  s.freezePanes.freezeRows(17);
  s.freezePanes.freezeColumns(2);
}

const renders = [
  ["00_专项总览", "A1:H42", 1],
  ["01_完整测试清单", "A1:H24", 0.9],
  ["02_各项目精度提升", "A1:G18", 0.9],
  ["03_跨电芯测试矩阵", "A1:F29", 0.95],
  ["04_记录与验收", "A1:N46", 0.8],
];

for (const [sheetName, range, scale] of renders) {
  const image = await wb.render({ sheetName, range, scale, format: "png" });
  await fs.writeFile(
    path.join(qaDir, `${sheetName}.png`),
    new Uint8Array(await image.arrayBuffer()),
  );
}

const inspect = await wb.inspect({
  kind: "table",
  range: "01_完整测试清单!A1:H24",
  include: "values,formulas",
  tableMaxRows: 24,
  tableMaxCols: 8,
  maxChars: 16000,
});
await fs.writeFile(path.join(qaDir, "checklist_inspect.ndjson"), inspect.ndjson, "utf8");

const errors = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(path.join(qaDir, "formula_errors.ndjson"), errors.ndjson, "utf8");

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
console.log(outputPath);

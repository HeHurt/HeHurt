import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const ROOT = 'D:/Users/hez/Desktop/hithium/scratch/calendar_report_20260804';
const STARTER = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-report-20260804/template-starter.pptx';
const OUT = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-report-20260804/587Ah_calendar_report_final_plain.pptx';
const PLAIN_ROOT = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-report-20260804';
const ASSET = (name) => `${PLAIN_ROOT}/assets/${name}`;

async function imageBytes(name) {
  return new Uint8Array(await fs.readFile(ASSET(name)));
}

const TARGETS = {
  'sh/cz2pk3eh': [0, 'shape', '标题 1'], 'sh/ih0nah8r': [0, 'shape', '矩形 1'],
  'sh/c7ex8rut': [1, 'shape', '标题 1'],
  'sh/o7q5wbud': [2, 'shape', '标题 1'], 'sh/wfipcf2l': [2, 'shape', '灯片编号占位符 2'],
  'tb/info-card': [2, 'table', '表格 15'],
  'sh/tozmt876': [3, 'shape', '矩形 41'], 'sh/hg7a1wjm': [3, 'shape', '矩形 1'],
  'sh/0bep0ra1': [3, 'shape', '矩形 71'], 'sh/m58jmpc3': [3, 'shape', '标题 1'],
  'sh/6l8nid8f': [3, 'shape', '灯片编号占位符 2'],
  'sh/jadwja98': [4, 'shape', '文本框 41'], 'im/qt4by54v': [4, 'image', '图片 4'],
  'im/buxsralg': [4, 'image', '图片 6'], 'tb/43q5gfm9': [4, 'table', '表格 10'],
  'tb/h0zm50ni': [4, 'table', '表格 43'],
  'sh/xofqdcju': [5, 'shape', '矩形 27'], 'sh/o7i10zet': [5, 'shape', '文本框 13'],
  'sh/9kfq9cji': [5, 'shape', '矩形 23'], 'im/xo36hkbq': [5, 'image', '图片 3'],
  'im/cnup8ful': [5, 'image', '图片 4'], 'im/bmlofat0': [5, 'image', '图片 11'],
  'im/alc765cf': [5, 'image', '图片 12'], 'im/pk36dkbu': [5, 'image', '图片 15'],
  'tb/jmh8rmto': [5, 'table', '表格 31'],
  'sh/jex0f29c': [6, 'shape', '矩形 27'], 'sh/ud4j2hsv': [6, 'shape', '文本框 13'],
  'im/i9cnmto7': [6, 'image', '图片 15'], 'im/jal4vy5s': [6, 'image', '图片 12'],
  'tb/hwnql87q': [6, 'table', '表格 31'],
  'sh/ulknmtg7': [7, 'shape', '标题 1'], 'sh/h8ji1sfe': [7, 'shape', '日期占位符 1'],
  'sh/w7ah8nyt': [7, 'shape', '灯片编号占位符 2'], 'sh/4vahcnyp': [7, 'shape', '文本框 6'],
  'sh/jup876lg': [8, 'shape', '标题 3'], 'sh/mlg7ml47': [8, 'shape', '灯片编号占位符 2'],
};

function element(presentation, id) {
  const target = TARGETS[id];
  if (!target) throw new Error(`Missing target mapping for ${id}`);
  const [slideIndex, kind, name] = target;
  const slide = presentation.slides.getItem(slideIndex);
  const collection = kind === 'shape' ? slide.shapes.items : kind === 'image' ? slide.images.items : slide.tables.items;
  const found = collection.find((item) => item.name === name);
  if (!found) throw new Error(`Could not find ${kind} '${name}' on slide ${slideIndex + 1}`);
  return found;
}

function rewrite(presentation, id, oldText, newText) {
  element(presentation, id).text.set(newText);
}

async function replaceImage(presentation, id, assetName, alt) {
  const image = element(presentation, id);
  const old = {
    frame: image.frame,
    crop: image.crop,
    fit: image.fit,
    geometry: image.geometry,
    borderRadius: image.borderRadius,
    rotation: image.rotation,
    flipHorizontal: image.flipHorizontal,
    flipVertical: image.flipVertical,
    lockAspectRatio: image.lockAspectRatio,
  };
  image.replace({ blob: await imageBytes(assetName), contentType: 'image/png', alt, fit: 'contain' });
  image.frame = old.frame;
  image.crop = { left: 0, top: 0, right: 0, bottom: 0 };
  image.fit = 'contain';
  image.geometry = old.geometry;
  image.borderRadius = old.borderRadius;
  image.rotation = old.rotation;
  image.flipHorizontal = old.flipHorizontal;
  image.flipVertical = old.flipVertical;
  image.lockAspectRatio = old.lockAspectRatio;
}

function setTable(table, values) {
  values.forEach((row, r) => row.forEach((value, c) => table.cells.set(r, c, value)));
}

function notes(slide, lines) {
  slide.speakerNotes.textFrame.setText(['[Sources]', ...lines].join('\n'));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER));

// Slide 1: cover.
rewrite(
  presentation,
  'sh/cz2pk3eh',
  '欧盟新电池法MIC电芯100%SOC\n日历老化自放电率仿真报告',
  '587Ah电芯50%SOC无活化\n14个月多温度日历老化仿真报告',
);
rewrite(presentation, 'sh/ih0nah8r', 'RE_HC_314Ah_Cell_Base ', 'RE_HC_587Ah_Cell_Base ');
notes(presentation.slides.getItem(0), [
  '- Template: D:/Users/hez/Desktop/mic/RE_HCMICBase_E212_新电池法MIC日历老化自放电率性能仿真报告对外输出版.pptx',
  '- Task: C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1',
]);

// Slide 2 and 3: preserve agenda and blank information card.
rewrite(presentation, 'sh/c7ex8rut', '目录', '目录');
rewrite(presentation, 'sh/o7q5wbud', '1. 仿真概要', '1. 仿真概要');
rewrite(presentation, 'sh/wfipcf2l', '3', '3');
const infoCard = element(presentation, 'tb/info-card');
for (const [row, column] of [[1, 1], [1, 3], [2, 1], [2, 3], [3, 1], [4, 1], [5, 1], [6, 1]]) {
  infoCard.cells.set(row, column, '');
}

// Slide 4: protocol and assumptions.
rewrite(
  presentation,
  'sh/tozmt876',
  '仿真温度：25℃\n仿真工况：\n\n\n\n\n研究体系：MIC CW363冻结体系电芯',
  '存储温度：0～50℃，5℃间隔\n仿真工况：\n\n\n\n\n加速因子：1｜研究体系：587Ah电芯',
);
rewrite(
  presentation,
  'sh/hg7a1wjm',
  '0.25P 充放循环3圈\n0.25P 充电至3.65V\n100%SOC静置30天\n0.25P 放电至2.5V\n0.25P 充放循环1圈\n重复②~⑤工步300次',
  '25℃、0.5P充放1圈，获得C0\n充入0.5C0至50%SOC\n目标温度静置n×30天\n返回25℃静置1 h\n0.5P放电，获得保持容量\n0.5P充放，获得恢复容量',
);
rewrite(
  presentation,
  'sh/0bep0ra1',
  '1D电化学模型：\n模型内部过程仅考虑极片厚度方向\n将电极颗粒平均为粒径Dv50的球体\n不考虑产热温升，电池在充放电过程中为固定温度\n 老化机理模型：\t\n采用包含SEI生长、颗粒破碎、活性材料损失副反应的老化模型\n未考虑容量爬坡现象\n未考虑膨胀力影响',
  '1D电化学模型：\nDFN一维厚度方向\n热接口关闭，各阶段恒温\n温度切换重新初始化参数\n老化机理模型：\n包含SEI、裂纹/LAM分支\n标定EC扩散与SEI活化能/速率\n无独立可逆自放电支路',
);
rewrite(presentation, 'sh/m58jmpc3', '2. 模型概要', '2. 模型概要');
rewrite(presentation, 'sh/6l8nid8f', '4', '4');
notes(presentation.slides.getItem(3), [
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/03_输入数据/config.yaml',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/05_复现说明/README.md',
]);

// Slide 5: activated calibration benchmark.
rewrite(presentation, 'sh/jadwja98', '模型对标', '活化工况参数标定');
await replaceImage(presentation, 'im/qt4by54v', 'calibration_exp_vs_model.png', '25°C与45°C活化存储实测和模型恢复容量对比');
await replaceImage(presentation, 'im/buxsralg', 'sensitivity_rmse.png', '日历老化参数单因素敏感性RMSE排序');
setTable(element(presentation, 'tb/43q5gfm9'), [
  ['指标', '标定前 → 标定后'],
  ['整体RMSE', '5.89 → 0.52 pp'],
  ['25℃ RMSE', '3.38 → 0.19 pp'],
  ['45℃ RMSE', '7.61 → 0.71 pp'],
  ['EC扩散系数', '2.1×10⁻²² m²/s'],
  ['SEI活化能', '40 kJ/mol'],
  ['加速因子', '1'],
]);
setTable(element(presentation, 'tb/h0zm50ni'), [[
  '标定结论',
  '以25℃、45℃活化存储恢复容量为对标，整体RMSE由5.89 pp降至0.52 pp。\n敏感性结果显示EC扩散系数主导误差收敛，SEI活化能与反应速率用于修正温度和时间依赖；裂纹速率在本组数据中的一阶敏感性较低。',
]]);
notes(presentation.slides.getItem(4), [
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587_calendar_activated_calibration/calibration_comparison.csv',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587_calendar_activated_calibration/sensitivity_summary.csv',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587_calendar_activated_calibration/calibration_config.json',
]);

// Slide 6: full matrix.
rewrite(
  presentation,
  'sh/xofqdcju',
  '本次仿真基于自放电率测试工步，设置与实际实验一致的充放电及静置流程，完成了25年100%SOC储存全流程的电池行为模拟',
  '采用独立时长法构建11×14工况矩阵，共154个工况全部完成；所有诊断统一回到25℃、静置1 h后测试',
);
rewrite(presentation, 'sh/o7i10zet', '仿真过程说明', '容量保持与恢复趋势');
rewrite(
  presentation,
  'sh/9kfq9cji',
  '通过模型输出的电压-时间曲线，可以直观反映电池在长期循环及静置过程中的电压变化趋势',
  '温度升高使保持容量与恢复容量均下降，高温区随存储时间的衰减斜率明显增大',
);
await replaceImage(presentation, 'im/xo36hkbq', 'baseline_storage_target.png', 'C0与50%C0存储目标容量');
await replaceImage(presentation, 'im/cnup8ful', 'retention_selected.png', '代表温度容量保持率随存储月数变化');
await replaceImage(presentation, 'im/bmlofat0', 'recovery_selected.png', '代表温度容量恢复率随存储月数变化');
await replaceImage(presentation, 'im/alc765cf', 'retention_heatmap_report.png', '0至50°C容量保持率矩阵');
await replaceImage(presentation, 'im/pk36dkbu', 'recovery_heatmap_report.png', '0至50°C容量恢复率矩阵');
setTable(element(presentation, 'tb/jmh8rmto'), [[
  '仿真结论',
  '基准容量C0=606.98 Ah，50%SOC目标与实际充入量均为303.49 Ah；154/154工况完成且容量随月份、温度单调不增。\n14个月恢复容量由0℃的99.23%降至50℃的90.42%，高温存储是矩阵内的主导风险变量。',
]]);
notes(presentation.slides.getItem(5), [
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/calendar_aging_587Ah_50SOC_matrix.csv',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/validation_summary.json',
]);

// Slide 7: loss split.
rewrite(
  presentation,
  'sh/jex0f29c',
  '通过提取各类容量损失（SEI、裂纹SEI、锂枝晶、LAM等）及负极孔隙率随循环变化的曲线，进一步分析存储容量衰减成因',
  '14个月末恢复容量率随存储温度单调下降；温度升高同时放大静置后可恢复损失与不可逆容量损失',
);
rewrite(presentation, 'sh/ud4j2hsv', '内部老化参数分析', '14个月温度效应与损失拆分');
await replaceImage(presentation, 'im/i9cnmto7', 'month14_temperature_summary.png', '14个月容量保持率与恢复率随存储温度变化');
await replaceImage(presentation, 'im/jal4vy5s', 'loss_split_month14.png', '14个月各温度可恢复与不可逆容量损失拆分');
setTable(element(presentation, 'tb/hwnql87q'), [[
  '温度效应',
  '14个月恢复容量：0℃ 99.23%、25℃ 96.31%、45℃ 91.83%、50℃ 90.42%；不可逆损失由0℃ 0.77%增至50℃ 9.58%，与高温加速SEI副反应的模型路径一致。\n保持容量与恢复容量的差值同时包含电压截止和极化影响；当前无活化流程及25℃/45℃之外温度属于模型外推。',
]]);
notes(presentation.slides.getItem(6), [
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/calendar_aging_587Ah_50SOC_matrix.csv',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/summary_month_14.csv',
]);

// Slide 8: synthesis and boundaries.
rewrite(presentation, 'sh/ulknmtg7', '4. 仿真结论', '4. 仿真结论');
rewrite(presentation, 'sh/h8ji1sfe', '2025/6/14', '2026/8/4');
rewrite(presentation, 'sh/w7ah8nyt', '9', '8');
element(presentation, 'sh/4vahcnyp').text.set([
  { runs: [{ run: '1. 工况：', textStyle: { bold: true } }, '50%SOC无活化，0～50℃/5℃，月龄1～14独立计算；25℃静置1 h后0.5P测试。'] },
  { runs: [{ run: '2. 标定：', textStyle: { bold: true } }, '25℃/45℃活化数据，整体RMSE 5.89→0.52 pp；加速因子为1。'] },
  { runs: [{ run: '3. 结果：', textStyle: { bold: true } }, '14月恢复容量：0℃ 99.23%、25℃ 96.31%、45℃ 91.83%、50℃ 90.42%。'] },
  { runs: [{ run: '4. 机理：', textStyle: { bold: true } }, '高温加速SEI副反应；不可逆损失由0.77%升至9.58%。'] },
  { runs: [{ run: '5. 边界：', textStyle: { bold: true } }, '无活化及非25℃/45℃结果均为外推；模型无独立可逆自放电支路，绝对寿命需实测复核。'] },
]);
notes(presentation.slides.getItem(7), [
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587_calendar_activated_calibration/calibration_config.json',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/summary_month_14.csv',
  '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/validation_summary.json',
]);

// Slide 9: preserve closing slide while satisfying placeholder handling.
rewrite(presentation, 'sh/jup876lg', 'Thanks', 'Thanks');
rewrite(presentation, 'sh/mlg7ml47', '10', '9');

const snapshot = await presentation.inspect({
  kind: 'slide,textbox,image,table,notes,layout',
  maxChars: 200000,
});
await fs.writeFile(`${PLAIN_ROOT}/final-inspect-v2.ndjson`, snapshot.ndjson, 'utf8');

await fs.mkdir(`${PLAIN_ROOT}/final-render-v2`, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, '0')}`;
  const png = await presentation.export({ slide, format: 'png', scale: 1.5 });
  await fs.writeFile(`${PLAIN_ROOT}/final-render-v2/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: 'layout' });
  await fs.writeFile(`${PLAIN_ROOT}/final-render-v2/${stem}.layout.json`, await layout.text(), 'utf8');
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(OUT);
console.log(OUT);

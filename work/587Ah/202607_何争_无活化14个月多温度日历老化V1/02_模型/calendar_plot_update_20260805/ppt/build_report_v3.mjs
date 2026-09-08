import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const ROOT = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-plot-update-20260805';
const STARTER = `${ROOT}/template-starter.pptx`;
const OUT = `${ROOT}/calendar-report-v3.pptx`;
const RENDER_DIR = `${ROOT}/report-v3-render`;

function byName(items, name) {
  const found = items.find((item) => item.name === name);
  if (!found) throw new Error(`Missing inherited element: ${name}`);
  return found;
}

async function replaceImage(image, path, alt) {
  const frame = image.frame;
  const bytes = new Uint8Array(await fs.readFile(path));
  image.replace({ blob: bytes, contentType: 'image/png', alt, fit: 'contain' });
  image.frame = frame;
  image.crop = { left: 0, top: 0, right: 0, bottom: 0 };
  image.fit = 'contain';
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(STARTER));
const curveSlide = presentation.slides.getItem(6);

byName(curveSlide.shapes.items, '文本框 13').text.set('1～14个月保持/恢复容量趋势');
byName(curveSlide.shapes.items, '矩形 27').text.set(
  '温度越高，保持容量与恢复容量随存储月龄下降越快；50℃工况在14个月末降至80.90%/90.42%'
);
await replaceImage(
  byName(curveSlide.images.items, '图片 15'),
  `${ROOT}/capacity_retention_vs_month.png`,
  '0至50摄氏度、1至14个月的容量保持率曲线'
);
await replaceImage(
  byName(curveSlide.images.items, '图片 12'),
  `${ROOT}/recovered_capacity_vs_month.png`,
  '0至50摄氏度、1至14个月的恢复容量率曲线'
);

const conclusion = byName(curveSlide.tables.items, '表格 31');
conclusion.cells.set(0, 0, '月龄趋势');
conclusion.cells.set(
  0,
  1,
  '低温区曲线缓慢下降，0℃在14个月末保持/恢复容量为98.48%/99.23%。\n' +
    '高温加速SEI副反应，50℃对应值降至80.90%/90.42%；保持—恢复差值还包含截止电压与极化影响。'
);
curveSlide.speakerNotes.textFrame.setText(
  '[Sources]\n' +
    '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/calendar_aging_587Ah_50SOC_matrix.csv\n' +
    '- C:/HithiumSSD/hithium/work/587Ah/202607_何争_无活化14个月多温度日历老化V1/04_输出结果/20260727_587calander_50SOC_full_v1/artifacts/capacity_retention_recovery_vs_month.png'
);

byName(presentation.slides.getItem(8).shapes.items, '灯片编号占位符 2').text.set('9');
byName(presentation.slides.getItem(9).shapes.items, '灯片编号占位符 2').text.set('10');

await fs.mkdir(RENDER_DIR, { recursive: true });
const inspect = await presentation.inspect({ kind: 'slide,textbox,shape,image,table,notes,layout', maxChars: 200000 });
await fs.writeFile(`${ROOT}/report-v3-inspect.ndjson`, inspect.ndjson, 'utf8');
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, '0')}`;
  const png = await presentation.export({ slide, format: 'png', scale: 1.5 });
  await fs.writeFile(`${RENDER_DIR}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: 'layout' });
  await fs.writeFile(`${RENDER_DIR}/${stem}.layout.json`, await layout.text(), 'utf8');
}

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(OUT);
console.log(OUT);

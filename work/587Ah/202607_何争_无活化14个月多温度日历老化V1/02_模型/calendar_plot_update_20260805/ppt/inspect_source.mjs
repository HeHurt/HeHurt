import fs from 'node:fs/promises';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

const source = 'C:/Users/hez/AppData/Local/Temp/codex-hithium/calendar-plot-update-20260805/report-v2-source.pptx';
const out = 'C:/HithiumSSD/hithium/scratch/calendar_plot_update_20260805/ppt/manual-inspect';
const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
await fs.mkdir(out, { recursive: true });
const inspect = await presentation.inspect({ kind: 'slide,textbox,shape,image,table,notes,layout', maxChars: 200000 });
await fs.writeFile(`${out}/source-inspect.ndjson`, inspect.ndjson, 'utf8');
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, '0')}`;
  const png = await presentation.export({ slide, format: 'png', scale: 1.5 });
  await fs.writeFile(`${out}/${stem}.png`, new Uint8Array(await png.arrayBuffer()));
  const layout = await slide.export({ format: 'layout' });
  await fs.writeFile(`${out}/${stem}.layout.json`, await layout.text(), 'utf8');
}
console.log(`slides=${presentation.slides.items.length}`);

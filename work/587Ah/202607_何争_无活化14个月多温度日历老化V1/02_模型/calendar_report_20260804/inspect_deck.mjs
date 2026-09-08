import fs from 'node:fs/promises';
import path from 'node:path';
import { FileBlob, PresentationFile } from '@oai/artifact-tool';

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

const [inputPptx, outputDir] = process.argv.slice(2);
if (!inputPptx || !outputDir) throw new Error('Usage: inspect_deck.mjs <pptx> <output-dir>');
await fs.mkdir(outputDir, { recursive: true });
const presentation = await PresentationFile.importPptx(await FileBlob.load(inputPptx));
const snapshot = await presentation.inspect({
  kind: 'deck,slide,textbox,shape,image,table,chart,notes,thread,layout',
  maxChars: 2_000_000,
});
await fs.writeFile(path.join(outputDir, 'template-inspect.ndjson'), snapshot.ndjson, 'utf8');

for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, '0')}`;
  await writeBlob(path.join(outputDir, `${stem}.png`), await presentation.export({ slide, format: 'png', scale: 1.5 }));
  const layout = await slide.export({ format: 'layout' });
  await fs.writeFile(path.join(outputDir, `${stem}.layout.json`), await layout.text(), 'utf8');
}
await writeBlob(path.join(outputDir, 'montage.webp'), await presentation.export({ format: 'webp', montage: true, scale: 1 }));
await fs.writeFile(path.join(outputDir, 'manifest.json'), JSON.stringify({
  inputPptx,
  slideCount: presentation.slides.items.length,
  masterCount: presentation.masters.items.length,
  layoutCount: presentation.layouts.items.length,
}, null, 2), 'utf8');

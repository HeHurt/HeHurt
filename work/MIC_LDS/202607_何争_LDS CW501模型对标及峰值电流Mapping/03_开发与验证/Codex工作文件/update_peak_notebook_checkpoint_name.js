const fs = require("fs");

const notebookPath = process.argv[2];
const notebook = JSON.parse(fs.readFileSync(notebookPath, "utf8"));
for (const cell of notebook.cells) {
  if (!Array.isArray(cell.source)) continue;
  const text = cell.source.join("").replaceAll(
    "peak_current_map.csv",
    "peak_current_map_v3_checkpoint.txt",
  );
  cell.source = text.split(/(?<=\n)/);
}
fs.writeFileSync(notebookPath, JSON.stringify(notebook, null, 1), "utf8");

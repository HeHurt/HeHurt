const fs = require("fs");
const notebook = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
notebook.cells.forEach((cell, index) => {
  const source = Array.isArray(cell.source) ? cell.source.join("") : cell.source;
  process.stdout.write(`\n--- CELL ${index} ${cell.cell_type} ---\n${source}\n`);
});

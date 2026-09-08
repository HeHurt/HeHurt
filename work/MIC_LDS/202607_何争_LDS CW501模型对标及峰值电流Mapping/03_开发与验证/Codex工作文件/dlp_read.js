const fs = require("fs");
const filePath = process.argv[2];
const start = Number(process.argv[3] || 1);
const count = Number(process.argv[4] || Number.MAX_SAFE_INTEGER);
const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
process.stdout.write(lines.slice(start - 1, start - 1 + count).join("\n"));

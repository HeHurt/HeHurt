const fs = require("fs");
const path = require("path");

const sourceDir = process.argv[2];
const targetDir = process.argv[3];
fs.mkdirSync(targetDir, { recursive: true });
for (const fileName of fs.readdirSync(sourceDir)) {
  if (!fileName.endsWith("_完整时序.csv")) continue;
  const text = fs.readFileSync(path.join(sourceDir, fileName), "utf8");
  const targetName = fileName.replace(/\.csv$/, ".txt");
  fs.writeFileSync(path.join(targetDir, targetName), text, "utf8");
}

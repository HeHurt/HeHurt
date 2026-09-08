const fs = require("fs");
const sourcePath = process.argv[2];
const targetPath = process.argv[3];
const content = fs.readFileSync(sourcePath, "utf8");
fs.writeFileSync(targetPath, content, "utf8");

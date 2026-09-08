const fs = require("fs");

const sourcePath = process.argv[2];
const targetPath = process.argv[3];
fs.copyFileSync(sourcePath, targetPath);

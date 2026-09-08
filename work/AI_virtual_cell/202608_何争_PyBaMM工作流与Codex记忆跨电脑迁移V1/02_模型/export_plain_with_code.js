const fs = require("fs");

const source = process.argv[2];
const destination = process.argv[3];

if (!source || !destination) {
  throw new Error("usage: export_plain_with_code.js <source> <destination>");
}

const data = fs.readFileSync(source);
fs.writeFileSync(destination, data);

const fs = require('fs');

if (process.argv.length !== 4) {
  throw new Error('Usage: dlp_copy.cjs <source> <destination>');
}

const source = process.argv[2];
const destination = process.argv[3];
fs.writeFileSync(destination, fs.readFileSync(source));
console.log(`${source} -> ${destination} (${fs.statSync(destination).size} bytes)`);

import sharp from "sharp";

for (const [source, target] of [
  ["work/cw368_voltage_source.bin", "work/cw368_voltage_benchmark_small.bin"],
  ["work/cw368_heat_source.bin", "work/cw368_heat_power_small.bin"],
]) {
  await sharp(source).resize({ width: 1400, withoutEnlargement: true }).png().toFile(target);
}

import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from extract_arc_values import MAIN_NS, NS, decode_cell, shared_strings, sheet_targets


ROOT = Path(__file__).resolve().parent
TARGET_TITLES = {
    "充电@25ºC测试柜原始数据",
    "放电@25ºC测试柜原始数据",
}
KEEP_COLUMNS = {"F", "I", "J", "K", "L", "M", "N", "Q"}


def column_name(reference):
    return re.match(r"[A-Z]+", reference).group(0)


def summarize_sheet(archive, target, strings):
    modes = set()
    voltages = []
    currents = []
    powers = []
    active_voltages = []
    active_currents = []
    active_powers = []
    charge_capacities = []
    discharge_capacities = []
    charge_energies = []
    discharge_energies = []
    row_count = 0
    with archive.open(target) as stream:
        for _, node in ET.iterparse(stream, events=("end",)):
            if node.tag != f"{{{MAIN_NS}}}row":
                continue
            row_count += 1
            row_values = {}
            for cell in node.findall("x:c", NS):
                column = column_name(cell.attrib["r"])
                if column not in KEEP_COLUMNS:
                    continue
                value = decode_cell(cell, strings)["value"]
                row_values[column] = value
                if column == "F" and isinstance(value, str):
                    modes.add(value)
                elif isinstance(value, (int, float)):
                    if column == "I":
                        voltages.append(float(value))
                    elif column == "J":
                        currents.append(float(value))
                    elif column == "K":
                        charge_capacities.append(float(value))
                    elif column == "L":
                        charge_energies.append(float(value))
                    elif column == "M":
                        discharge_capacities.append(float(value))
                    elif column == "N":
                        discharge_energies.append(float(value))
                    elif column == "Q":
                        powers.append(float(value))
            if isinstance(row_values.get("Q"), (int, float)) and abs(float(row_values["Q"])) > 10.0:
                active_voltages.append(float(row_values["I"]))
                active_currents.append(abs(float(row_values["J"])))
                active_powers.append(abs(float(row_values["Q"])))
            node.clear()
    return {
        "rows": row_count,
        "modes": sorted(modes),
        "voltage_min_v": min(voltages),
        "voltage_max_v": max(voltages),
        "voltage_first_v": voltages[0],
        "voltage_last_v": voltages[-1],
        "current_min_a": min(currents),
        "current_max_a": max(currents),
        "power_min_w": min(powers),
        "power_max_w": max(powers),
        "active_mean_voltage_v": sum(active_voltages) / len(active_voltages),
        "active_mean_abs_current_a": sum(active_currents) / len(active_currents),
        "active_mean_abs_power_w": sum(active_powers) / len(active_powers),
        "charge_capacity_max_ah": max(charge_capacities),
        "discharge_capacity_max_ah": max(discharge_capacities),
        "charge_energy_max_wh": max(charge_energies),
        "discharge_energy_max_wh": max(discharge_energies),
    }


def main():
    results = []
    for path in sorted(ROOT.glob("*.xlsx")):
        with zipfile.ZipFile(path) as archive:
            strings = shared_strings(archive)
            sheets = []
            for title, target in sheet_targets(archive):
                if title in TARGET_TITLES:
                    sheets.append(
                        {
                            "title": title,
                            **summarize_sheet(archive, target, strings),
                        }
                    )
            results.append({"source": path.name, "sheets": sheets})
    output = ROOT / "raw_protocol_summary.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

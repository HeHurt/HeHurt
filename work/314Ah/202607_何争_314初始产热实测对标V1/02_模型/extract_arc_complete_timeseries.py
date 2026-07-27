"""Extract and align complete 314 Ah ARC heat and electrical time series."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"x": MAIN_NS, "r": REL_NS, "p": PKG_REL_NS}

SOURCE_DIR = Path(r"D:\Users\hez\Desktop\hithium\data_raw\314Ah\Exp")
SOURCE_FILES = {
    0.25: SOURCE_DIR / "T3-20260627-0035-0.25PARC发热功率测试报告.xlsx",
    0.50: SOURCE_DIR / "T3-20260627-0035-0.5PARC发热功率测试报告.xlsx",
}
SHEET_NAMES = {
    "charge": {
        "electrical": "充电@25ºC测试柜原始数据",
        "arc": "充电@25ºC 绝热温升数据",
    },
    "discharge": {
        "electrical": "放电@25ºC测试柜原始数据",
        "arc": "放电@25ºC 绝热温升数据",
    },
}
ARC_TARGETS = {
    (0.25, "charge"): {"duration_min": 261.25, "capacity_ah": 327.352783},
    (0.25, "discharge"): {"duration_min": 256.65, "capacity_ah": 331.575958},
    (0.50, "charge"): {"duration_min": 133.10, "capacity_ah": 330.894104},
    (0.50, "discharge"): {"duration_min": 126.68333333333334, "capacity_ah": 331.129486},
}


def _text_content(node):
    return "".join(part.text or "" for part in node.findall(".//x:t", NS))


def _shared_strings(archive):
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [_text_content(item) for item in root.findall("x:si", NS)]


def _sheet_targets(archive):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target_by_id = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("p:Relationship", NS)
    }
    targets = {}
    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = target_by_id[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        targets[sheet.attrib["name"]] = target
    return targets


def _decode_cell(cell, strings):
    data_type = cell.attrib.get("t")
    value = cell.find("x:v", NS)
    inline = cell.find("x:is", NS)
    raw = value.text if value is not None else None
    if data_type == "s" and raw is not None:
        return strings[int(raw)]
    if data_type == "inlineStr" and inline is not None:
        return _text_content(inline)
    if data_type == "b" and raw is not None:
        return raw == "1"
    if data_type in {"str", "e"}:
        return raw
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return raw


def _column(reference):
    return re.match(r"[A-Z]+", reference).group(0)


def _stream_sheet(archive, target, strings, columns):
    records = []
    with archive.open(target) as stream:
        for _, node in ET.iterparse(stream, events=("end",)):
            if node.tag != f"{{{MAIN_NS}}}row":
                continue
            row = {}
            for cell in node.findall("x:c", NS):
                column = _column(cell.attrib["r"])
                if column in columns:
                    row[column] = _decode_cell(cell, strings)
            if row:
                records.append(row)
            node.clear()
    return pd.DataFrame(records)


def _extract_electrical(archive, target, strings, p_rate, direction):
    table = _stream_sheet(
        archive,
        target,
        strings,
        {"D", "F", "I", "J", "K", "M", "P", "Q"},
    )
    for column in ("D", "I", "J", "K", "M", "P", "Q"):
        table[column] = pd.to_numeric(table[column], errors="coerce")
    capacity_column = "K" if direction == "charge" else "M"
    active = table["Q"].abs().gt(10.0) & table["D"].notna()
    reset = table["D"].diff().lt(-0.1)
    new_segment = active & (~active.shift(fill_value=False) | reset)
    table["segment"] = new_segment.cumsum()
    target_values = ARC_TARGETS[(p_rate, direction)]
    candidates = []
    for segment, group in table.loc[active].groupby("segment", sort=False):
        duration_min = float(group["D"].iloc[-1] - group["D"].iloc[0])
        capacity_ah = float(group[capacity_column].max() - group[capacity_column].min())
        score = (
            abs(duration_min - target_values["duration_min"]) / target_values["duration_min"]
            + abs(capacity_ah - target_values["capacity_ah"]) / target_values["capacity_ah"]
        )
        candidates.append((score, segment))
    if not candidates:
        raise ValueError(f"No active electrical segment found for {p_rate:g}P {direction}")
    selected_segment = min(candidates)[1]
    table = table.loc[active & table["segment"].eq(selected_segment)].copy()
    table = table.dropna(subset=["D", "I", "J", "Q"])
    table["时间(s)"] = (table["D"] - table["D"].iloc[0]) * 60.0
    table["容量(Ah)"] = table[capacity_column] - table[capacity_column].iloc[0]
    table["电能(Wh)"] = table["P"].abs() - abs(table["P"].iloc[0])
    table["电流(A)"] = table["J"]
    table["电压(V)"] = table["I"]
    table["电功率(W)"] = table["Q"]
    return table[["时间(s)", "容量(Ah)", "电能(Wh)", "电流(A)", "电压(V)", "电功率(W)"]].sort_values("时间(s)")


def _extract_arc(archive, target, strings, duration_min):
    table = _stream_sheet(archive, target, strings, {"B", "P", "Q", "AA", "AC"})
    for column in ("B", "P", "Q", "AA", "AC"):
        table[column] = pd.to_numeric(table[column], errors="coerce")
    table = table.dropna(subset=["AA", "AC"]).copy()
    table["时间(s)"] = (table["AA"] - table["AA"].iloc[0]) * 60.0
    table = table.loc[table["时间(s)"].le(duration_min * 60.0 + 0.6)].copy()
    table["电芯温度(°C)"] = table["B"]
    table["热电偶C1温度(°C)"] = table["P"]
    table["热电偶C2温度(°C)"] = table["Q"]
    table["产热功率(W)"] = table["AC"]
    return table[["时间(s)", "电芯温度(°C)", "热电偶C1温度(°C)", "热电偶C2温度(°C)", "产热功率(W)"]].sort_values("时间(s)")


def _align_complete(electrical, arc):
    aligned = pd.merge_asof(
        arc,
        electrical,
        on="时间(s)",
        direction="nearest",
        tolerance=1.1,
    )
    aligned = aligned.dropna(subset=["容量(Ah)", "电能(Wh)", "电流(A)", "电压(V)"])
    aligned.insert(1, "时间(min)", aligned["时间(s)"] / 60.0)
    columns = [
        "时间(s)",
        "时间(min)",
        "容量(Ah)",
        "电能(Wh)",
        "电流(A)",
        "电压(V)",
        "电功率(W)",
        "产热功率(W)",
        "电芯温度(°C)",
        "热电偶C1温度(°C)",
        "热电偶C2温度(°C)",
    ]
    return aligned[columns]


def extract_all(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for p_rate, source_path in SOURCE_FILES.items():
        with zipfile.ZipFile(source_path) as archive:
            strings = _shared_strings(archive)
            targets = _sheet_targets(archive)
            for direction in ("charge", "discharge"):
                electrical = _extract_electrical(
                    archive,
                    targets[SHEET_NAMES[direction]["electrical"]],
                    strings,
                    p_rate,
                    direction,
                )
                arc = _extract_arc(
                    archive,
                    targets[SHEET_NAMES[direction]["arc"]],
                    strings,
                    ARC_TARGETS[(p_rate, direction)]["duration_min"],
                )
                complete = _align_complete(electrical, arc)
                label = f"{p_rate:g}P_{'充电' if direction == 'charge' else '放电'}"
                complete.to_csv(output_dir / f"{label}_完整时序.csv", index=False, encoding="utf-8-sig")
                electrical.to_csv(output_dir / f"{label}_电性能原始.csv", index=False, encoding="utf-8-sig")
                arc.to_csv(output_dir / f"{label}_ARC原始.csv", index=False, encoding="utf-8-sig")
                matched = len(complete)
                summary.append(
                    {
                        "工况": label,
                        "倍率(P)": p_rate,
                        "方向": direction,
                        "完整时序行数": len(complete),
                        "电性能有效行数": len(electrical),
                        "成功对齐行数": matched,
                        "对齐率(%)": matched / len(complete) * 100.0,
                        "最大时间(s)": float(complete["时间(s)"].max()),
                        "最终容量(Ah)": float(complete["容量(Ah)"].dropna().iloc[-1]),
                        "最终电能(Wh)": float(complete["电能(Wh)"].dropna().iloc[-1]),
                        "平均产热功率(W)_仅QA": float(np.trapz(complete["产热功率(W)"], complete["时间(s)"]) / complete["时间(s)"].max()),
                        "最高电芯温度(°C)_仅QA": float(complete["电芯温度(°C)"].max()),
                        "源文件": str(source_path),
                    }
                )
    summary_table = pd.DataFrame(summary)
    summary_table.to_csv(output_dir / "提取质量检查.csv", index=False, encoding="utf-8-sig")
    (output_dir / "提取说明.json").write_text(
        json.dumps(
            {
                "time_alignment": "ARC Step Time and cabinet STEP TIME, nearest neighbor, tolerance 0.75 s; no interpolation",
                "electrical_filter": "abs(cabinet power) > 10 W",
                "heat_power": "ARC worksheet Power(W), computed in source workbook from dT/dt * Cp * mass / 60",
                "cell_temperature": "ARC Can Temp (degC); C1 and C2 retained separately",
                "electric_energy": "absolute cabinet cumulative energy difference column P, zeroed at active-step start",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary_table


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = extract_all(args.output_dir)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()

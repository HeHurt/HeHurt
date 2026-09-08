import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from extract_arc_values import MAIN_NS, NS, decode_cell, shared_strings, sheet_targets


ROOT = Path(__file__).resolve().parent
TARGET_TITLES = {
    "充电@25ºC 绝热温升数据",
    "放电@25ºC 绝热温升数据",
}


def first_rows(archive, target, strings, limit=6):
    rows = []
    with archive.open(target) as stream:
        for _, node in ET.iterparse(stream, events=("end",)):
            if node.tag != f"{{{MAIN_NS}}}row":
                continue
            values = [decode_cell(cell, strings) for cell in node.findall("x:c", NS)]
            rows.append({"row": node.attrib.get("r"), "cells": values})
            node.clear()
            if len(rows) >= limit:
                break
    return rows


def main():
    all_results = []
    for path in sorted(ROOT.glob("*.xlsx")):
        with zipfile.ZipFile(path) as archive:
            strings = shared_strings(archive)
            sheets = []
            for title, target in sheet_targets(archive):
                if title in TARGET_TITLES:
                    sheets.append(
                        {
                            "title": title,
                            "target": target,
                            "rows": first_rows(archive, target, strings),
                        }
                    )
            all_results.append({"source": path.name, "sheets": sheets})
    print(json.dumps(all_results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

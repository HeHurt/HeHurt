import json
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parent
TARGET_SHEETS = {"ARC发热功率测试报告"}
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"x": MAIN_NS, "r": REL_NS, "p": PKG_REL_NS}


def text_content(node):
    return "".join(part.text or "" for part in node.findall(".//x:t", NS))


def shared_strings(archive):
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [text_content(item) for item in root.findall("x:si", NS)]


def sheet_targets(archive):
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target_by_id = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("p:Relationship", NS)
    }
    result = []
    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        target = target_by_id[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        result.append((sheet.attrib["name"], target))
    return result


def decode_cell(cell, strings):
    data_type = cell.attrib.get("t")
    formula = cell.find("x:f", NS)
    value = cell.find("x:v", NS)
    inline = cell.find("x:is", NS)
    raw = value.text if value is not None else None
    if data_type == "s" and raw is not None:
        parsed = strings[int(raw)]
    elif data_type == "inlineStr" and inline is not None:
        parsed = text_content(inline)
    elif data_type == "b" and raw is not None:
        parsed = raw == "1"
    elif data_type in {"str", "e"}:
        parsed = raw
    elif raw is None:
        parsed = None
    else:
        try:
            parsed = float(raw)
            if parsed.is_integer():
                parsed = int(parsed)
        except ValueError:
            parsed = raw
    return {
        "cell": cell.attrib["r"],
        "value": parsed,
        "formula": formula.text if formula is not None else None,
    }


def extract_workbook(path):
    payload = path.read_bytes()
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        strings = shared_strings(archive)
        sheets = []
        for title, target in sheet_targets(archive):
            if title not in TARGET_SHEETS:
                continue
            root = ET.fromstring(archive.read(target))
            dimension = root.find("x:dimension", NS)
            cells = [
                decode_cell(cell, strings)
                for cell in root.findall("x:sheetData/x:row/x:c", NS)
                if cell.find("x:v", NS) is not None or cell.find("x:is", NS) is not None
            ]
            sheets.append(
                {
                    "title": title,
                    "dimension": dimension.attrib.get("ref") if dimension is not None else None,
                    "cells": cells,
                }
            )
    return {"source": path.name, "sheets": sheets}


def main():
    outputs = []
    for path in sorted(ROOT.glob("*.xlsx")):
        result = extract_workbook(path)
        output_path = path.with_suffix(".cells.json")
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(
            {
                "source": result["source"],
                "output": output_path.name,
                "sheets": [
                    {"title": sheet["title"], "dimension": sheet["dimension"], "nonempty_cells": len(sheet["cells"])}
                    for sheet in result["sheets"]
                ],
            }
        )
    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

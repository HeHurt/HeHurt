import io
import json
from pathlib import Path

from openpyxl import load_workbook


source = Path(
    r"C:\Users\hez\Documents\Codex\2026-07-29"
    r"\cw369-paramldscw369-py\work\reference_314ah_pulse_map.bin"
)
workbook = load_workbook(io.BytesIO(source.read_bytes()), data_only=False)
result = {}
for worksheet in workbook.worksheets:
    cells = {}
    for coordinate in ["A3", "A4", "B4", "A5", "B5", "S3", "AK3", "A27", "B29"]:
        cell = worksheet[coordinate]
        cells[coordinate] = {
            "value": cell.value,
            "style_id": cell.style_id,
            "font": {
                "name": cell.font.name,
                "size": cell.font.sz,
                "bold": cell.font.bold,
                "color_type": cell.font.color.type if cell.font.color else None,
                "color": (
                    cell.font.color.rgb
                    if cell.font.color and cell.font.color.type == "rgb"
                    else None
                ),
            },
            "fill": {
                "type": cell.fill.fill_type,
                "fg": cell.fill.fgColor.rgb,
            },
            "alignment": {
                "horizontal": cell.alignment.horizontal,
                "vertical": cell.alignment.vertical,
            },
            "number_format": cell.number_format,
            "border": {
                "left": cell.border.left.style,
                "right": cell.border.right.style,
                "top": cell.border.top.style,
                "bottom": cell.border.bottom.style,
            },
        }
    result[worksheet.title] = {
        "dimensions": worksheet.calculate_dimension(),
        "merged_cells": [str(item) for item in worksheet.merged_cells.ranges],
        "row_heights": {
            str(index): worksheet.row_dimensions[index].height
            for index in [3, 4, 5, 26, 27, 28, 29]
        },
        "column_widths": {
            column: worksheet.column_dimensions[column].width
            for column in ["A", "B", "P", "Q", "R", "S", "AH", "AI", "AJ", "AK", "AZ"]
        },
        "freeze_panes": str(worksheet.freeze_panes) if worksheet.freeze_panes else None,
        "sheet_view": {"show_grid_lines": worksheet.sheet_view.showGridLines},
        "conditional_formatting_ranges": [
            str(item.sqref) for item in worksheet.conditional_formatting
        ],
        "cells": cells,
    }
print(json.dumps(result, ensure_ascii=False, indent=2))

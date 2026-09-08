import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient


os.environ["CW501_SKIP_FULL_MAPPING"] = "1"
path = Path(
    r"C:\Users\hez\Documents\Codex\2026-07-29"
    r"\cw369-paramldscw369-py\work\CW501_peak_v2_validation.json"
)
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(
    notebook,
    timeout=300,
    kernel_name="python3",
    resources={"metadata": {"path": str(path.parent)}},
    allow_errors=False,
)
client.execute()
nbformat.write(notebook, path)
print("executed", path)

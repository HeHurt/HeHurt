from pathlib import Path

import nbformat
from nbclient import NotebookClient


path = Path(
    r"D:\Users\hez\Desktop\hithium\work\MIC_LDS"
    r"\202607_何争_LDS CW501模型对标及峰值电流Mapping"
    r"\02_模型\CW501_DFN模型对标.ipynb"
)
notebook = nbformat.read(path, as_version=4)
client = NotebookClient(
    notebook,
    timeout=600,
    kernel_name="python3",
    resources={"metadata": {"path": str(path.parent.parent)}},
    allow_errors=False,
)
client.execute()
nbformat.write(notebook, path)
print(path)

"""Execute each notebook in a fresh kernel and save results outside source files."""
import os
from pathlib import Path
import sys
import tempfile

import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
output = root / "outputs/notebooks"
output.mkdir(parents=True, exist_ok=True)

# Select this interpreter rather than an unrelated globally registered kernel.
with tempfile.TemporaryDirectory() as temporary:
    import json
    kernel = Path(temporary) / "kernels/aiaa-execution"
    kernel.mkdir(parents=True)
    (kernel / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "AIAA execution", "language": "python",
    }))
    os.environ["JUPYTER_PATH"] = temporary + os.pathsep + os.environ.get("JUPYTER_PATH", "")
    for path in sorted((root / "notebooks").glob("*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(notebook, timeout=300, kernel_name="aiaa-execution",
                       resources={"metadata": {"path": str(root / "notebooks")}}).execute()
        nbformat.write(notebook, output / path.name)
        print(f"Executed {path.name}")

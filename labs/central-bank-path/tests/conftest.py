import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
os.environ["PYTHONPATH"] = str(SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")
sys.path.insert(0, str(SRC))

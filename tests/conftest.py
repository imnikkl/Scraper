import sys
from pathlib import Path

# Make src/ importable in tests without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

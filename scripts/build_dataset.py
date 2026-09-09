from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from automotive_analytics import build_dataset


if __name__ == "__main__":
    tables = build_dataset(ROOT / "data", ROOT / "output" / "warehouse")
    for name, frame in tables.items():
        print(f"{name}: {len(frame):,} rows")
    print("Warehouse: output/warehouse")

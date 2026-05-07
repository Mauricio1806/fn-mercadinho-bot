# Patch: override catalog path para Railway
import os
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "catalog_full.yaml"

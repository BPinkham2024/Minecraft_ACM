import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    ITEM_TAGS_PATH,
    LOOT_TABLE_PATH,
    RAW_DIR,
    RECIPE_PATH,
    TREE_CACHE_DIR,
)


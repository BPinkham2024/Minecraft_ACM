import json
import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (
    ITEM_TAGS_PATH,
    LOOT_TABLE_PATH,
    MCMETA_RAW_BASE,
    MCMETA_TREE_API,
    MC_VERSION,
    RAW_DIR,
    RECIPE_PATH,
    TREE_CACHE_DIR,
)

_MISSING = "__404__" #cache missing files as this string to avoid repeated requests for the same missing file


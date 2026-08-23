# Basic settings for project, i don't want any hardcoded values in the code, so all the values are in this file.

from pathlib import Path


# ----- mcmeta data (recipes, loot tables, item tags) -----
MC_VERSION = "1.21.1-data"

MCMETA_REPO = "misode/mcmeta"
MCMETA_RAW_BASE = f"https://raw.githubusercontent.com/{MCMETA_REPO}/{MC_VERSION}/"
MCMETA_TREE_API = (f"https://api.github.com/repos/{MCMETA_REPO}/git/trees/{MC_VERSION}?recursive=1")

# mcmeta file paths
RECIPE_PATH = "data/minecraft/recipe"
LOOT_TABLE_PATH = "data/minecraft/loot_table"
ITEM_TAGS_PATH = "data/minecraft/tags/item"


# ----- local layout -----
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# cached tree
TREE_CACHE_DIR = RAW_DIR / "tree.json"


# ----- simulation settings -----
# monte carlo trials
N_TRIALS = 10000

# setting random seed to a fixed value for now for testing
RANDOM_SEED = 510

# assuming player does not have looting ability
LOOTING_LEVEL = 0



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


# testing items
TEST_ITEMS = [
    # pure deterministic cheap items
    "oak_planks",
    "stick",
    "crafting_table",
    "torch",
    "furnace",
    "iron_pickaxe",
    "iron_sword",
    "bucket",
    "clock",
    "golden_apple",
    # mixed deterministic recipe with random loot table
    "blaze_powder",
    "fire_charge",
    "brewing_stand",
    "ender_eye",
    "beacon",
    # pure random loot table items
    "ender_pearl",
    "blaze_rod",
    "totem_of_undying",
    "trident",
    "nether_star",
]

# test tiers (will get rid of this later, but for now just to test the simulation)
TEST_TIERS = {
    "oak_planks": "trivial",
    "stick": "trivial",
    "crafting_table": "trivial",
    "torch": "trivial",
    "furnace": "trivial",
    "iron_pickaxe": "common",
    "iron_sword": "common",
    "bucket": "common",
    "clock": "common",
    "golden_apple": "common",
    "blaze_powder": "rare",
    "fire_charge": "rare",
    "brewing_stand": "rare",
    "ender_eye": "rare",
    "beacon": "rare",
    "ender_pearl": "legendary",
    "blaze_rod": "legendary",
    "totem_of_undying": "legendary",
    "trident": "legendary",
    "nether_star": "legendary",
}

# recipe types
SUPPORTED_RECIPE_TYPES = (
    "minecraft:crafting_shaped",
    "minecraft:crafting_shapeless",
    "minecraft:smelting",
)

# if an item has more than one recipe, we will only consider the first suported one for now
RECIPE_PRIORITY = {
    "minecraft:smelting": 0,
    "minecraft:crafting_shaped": 1,
    "minecraft:crafting_shapeless": 2,
}

# loot table types (also used to break ties when several tables can get the same item)
LOOT_TABLE_PRIORITY = ("entities", "blocks", "gameplay", "chests", "archaeology")

KMEANS_CLUSTERS = 4
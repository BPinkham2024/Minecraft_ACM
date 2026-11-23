import json
from pathlib import Path
import pandas as pd

from phase1_data import read_data
from phase2_montecarlo import run_simulation
from phase3_routes import build_table, derive_progression



if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parents[1]
    raw_dir, curated_dir = ROOT / 'data/raw', ROOT / 'data/curated'
    print('Phase 1: parsing recipes, tags, loot tables')
    recipes, tags, loot, items = read_data(raw_dir)

    print('Phase 2: simulating loot with 10000 trials')
    scenario = json.loads((curated_dir / 'scenario.json').read_text())
    sources, assumptions = run_simulation(recipes, tags, loot, scenario, trials=10000, seed=69)

    print('Phase 3: costs and progression')
    tier_lables = pd.read_csv(curated_dir / 'progression_labels.csv', usecols=['item', 'tier'])
    table = build_table(items, recipes, sources, tier_lables)
    progression_policy = json.loads((curated_dir / 'progression_rules.json').read_text())
    table = table.merge(derive_progression(items, recipes, sources, progression_policy, raw_dir), on='item')
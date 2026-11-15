import json
from pathlib import Path
import pandas as pd

from phase1_data import read_data
from phase2_montecarlo import run_simulation



if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parents[1]
    raw_dir, curated_dir = ROOT / 'data/raw', ROOT / 'data/curated'
    print('Phase 1: parsing recipes, tags, loot tables')
    recipes, tags, loot, items = read_data(raw_dir)

    print('Phase 2: simulating loot with 10000 trials')
    scenario = json.loads((curated_dir / 'scenario.json').read_text())
    sources, assumptions = run_simulation(recipes, tags, loot, scenario, trials=10000, seed=69)

    
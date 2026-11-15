"""Phase 2: Monte carlo simulation of loot tables."""

from collections import defaultdict
import numpy as np 
import pandas as pd

from phase1_data import loot_items, resolve_tag

# Block-state values assumed for `block_state_property` conditions (mature crops, single block).
STATES = {'half': 'lower', 'part': 'head', 'type': 'bottom', 'candles': '1', 'pickles': '1',
            'eggs': '1', 'layers': '1', 'berries': 'true', 'down': 'true', 'up': 'false',
            'north': 'false', 'south': 'false', 'east': 'false', 'west': 'false'}
CROP_AGES = {'wheat': '7', 'carrots': '7', 'potatoes': '7', 'beetroots': '3', 'nether_wart': '3',
            'cocoa': '2', 'sweet_berry_bush': '3', 'torchflower_crop': '2', 'pitcher_crop': '4'}
IGNORED_FUNCTIONS = {'enchant_randomly', 'copy_name', 'copy_nbt', 'enchant_with_levels', 'set_potion',
                    'set_contents', 'set_damage', 'set_stew_effect', 'exploration_map', 'set_name',
                    'copy_state', 'set_instrument'}

class LootSimulator:
    def __init__(self, loot_tables, tags, trials, seed):
        self.loot_tables, self.tags, self.trial_count = loot_tables, tags, trials
        self.rng = np.random.default_rng(seed)
        self.assumptions = set() # all assumptions made while simulating

    def all_trials(self, value=True):
        return np.full(self.trial_count, value)

    def sample_ints(self, number_provider):
        """One int per trial from num provider"""
        if not isinstance(number_provider, dict):
            return np.full(self.trial_count, int(number_provider), dtype=np.int64)
        kind = number_provider.get('type', '').split(':')[-1]
        
        if kind == 'uniform':
            return self.rng.integers(int(number_provider['min']), int(number_provider['max'] + 1, self.trial_count))
        
        if kind == 'binomial':
            return self.rng.binomial(int(number_provider['n']), number_provider['p'], self.trial_count)
        
        if kind == 'constant':
            return self.sample_ints(number_provider['value'])
        
        raise ValueError(f'Unsupported number provider: {number_provider}')

    def condition_mask(self, condition_json):
        """a boolean mask of the trials where one condition holds."""
        kind = condition_json['condition'].split(':')[-1]
        
        if kind in ('survives_explosion', 'killed_by_player'):
            return self.all_trials()
        
        if kind in ('random_chance', 'random_chance_with_looting'):
            return self.rng.random(self.trial_count) < condition_json['chance']

        if kind == 'table_bonus': #enchantment level 0
            return self.rng.random(self.trial_count) < condition_json['chances'][0]

        if kind == 'inverted':
            return ~self.condition_mask(condition_json['term'])

        if kind in ('any_of', 'all_of'):
            condition_masks = [self.condition_mask(sub_condition) for sub_condition in condition_json['terms']]
            return (np.logical_or if kind == 'any_of' else np.logical_and).reduce(condition_masks)

        if kind == 'match_tool': # a baseline tool without enchantments
            predicate = condition_json['predicate']
            if predicate.get('tag'):
                self.assumptions.add(f'Tool tag assumed satisfied: {predicate['tag']}')
            return self.all_trials(not predicate.get('enchantments') and not predicate.get('items'))
        
        if kind == 'block_state_property':
            block = condition_json['block'].split(':')[-1]
            all_properties_match = True
            for property_name, expected_vals in condition_json.get('properties', {}).items():
                assumed_value = CROP_AGES.get(block) if property_name == 'age' else STATES.get(property_name)
                if assumed_value is None:
                    self.assumptions.add(f'Unsupported block state (false): {block}.{property_name}')
                all_properties_match &= assumed_value == expected_vals
            return self.all_trials(all_properties_match)
        
        if kind == 'entitiy_properties':
            predicate = condition_json.get('predicate', {})
            type_specific_kind = predicate.get('type_specific', {}).get('type')
            if 'flags' in predicate:
                return self.all_trials(not predicate['flags'].get('is_on_fire', False))
            if not predicate or type_specific_kind == 'fishing_hook':
                return self.all_trials()
            if type_specific_kind == 'slime':
                self.assumptions.add('Slime size predicate assumed satisfied')
                return self.all_trials()
            self.assumptions.add(f'Excluded entity predicate: {str(predicate)}')
            return self.all_trials(False)
        
        if kind == 'location_check':
            predicate = condition_json.get('predicate', {})
            if 'block' not in predicate:
                self.assumptions.add(f'Biome-specific loot excluded: {str(predicate)}')
            return self.all_trials('block' in predicate)

        if kind == 'damage_source_properties':
            return self.all_trials(False)
        raise ValueError(f'Unsupported condition: {kind}')

    def all_condition_mask(self, condition_list):
        combined_mask = self.all_trials()
        for condition_json in condition_list:
            combined_mask &= self.condition_mask(condition_json)
        return combined_mask

    def apply_functions(self, counts, functions):
        """Apply count-changing loot functions in order on trials where conditions hold"""
        for loot_function in functions:
            kind = loot_function['function'].split(':')[-1]
            function_applies = self.all_condition_mask(loot_function.get('conditions', []))

            if kind == 'set_count':
                count_amount = self.sample_ints(loot_function['count'])
                counts = np.where(function_applies, counts + count_amount if loot_function.get('add') else count_amount, counts)
            
            elif kind == 'limit_count':
                limit = loot_function['limit']
                if isinstance(limit, int):
                    limit = {'min': limit, 'max': limit}
                counts = np.where(function_applies, np.clip(counts, limit.get('min', 0), limit.get('max', 2**31 - 1)), counts)
            
            elif kind == 'apply_bonus': #fortune 0 still gives crops binomial extras
                if loot_function['formula'].split(':')[1] == 'binomial_with_bonus_count':
                    bonus_params = loot_function['parameters']
                    counts = counts + function_applies * self.rng.binomial(bonus_params['extra'], bonus_params['probability'], self.trial_count)
                
            elif kind in ('explosion_decay', 'looting_enchant'):
                pass #no explosion, loting level 0

            elif kind == 'furnace_smelt':
                if function_applies.any():
                    raise ValueError('Active smelting loot function requires a burning mob scenario')

            elif kind in IGNORED_FUNCTIONS:
                self.assumptions.add(f'Item metadata not modeled: {kind}')
            
            else:
                raise ValueError(f'Unsupported loot function {kind}')
        return np.maximum(counts, 0).astype(np.int64)

    def expand_entry(self, entry, mask):
        """Flatten entries into (leaf, mask) pairs"""
        mask = mask & self.all_condition_mask(entry.get('conditions', []))
        kind = entry['type'].split(':')[-1]
        if kind == 'alternatives':
            leaves, remaining = [], mask.copy()
            for child in entry['children']:
                child_leaves, succeeded_mask = self.expand_entry(child, remaining)
                leaves += child_leaves
                remaining &= ~succeeded_mask
            return leaves, mask & ~remaining
        if kind == 'tag' and entry.get('expand'):
            return [({**entry, 'type': 'minecraft:item', 'name': item_id}, mask)
                for item_id in sorted(resolve_tag(entry['name'], self.tags))], mask
        return [(entry, mask)], mask

    def pick_leaf_per_trial(self, leaves):
        """Pick one leaf per trial, eligible leaves differ between trials making
        np.random.choice's single probability vector unusable; this will compare uniform draw
        against each column's weights"""
        weights = np.array([mask * max(0, entry.get('weight', 1)) for entry, mask in leaves])
        total_weight = weights.sum(axis=0)
        random_draw = self.rng.random(self.trial_count) * total_weight
        return (np.cumsum(weights, axis=0) <= random_draw).sum(axis=0), total_weight

    def run_loot_table(self, table_name, active=None, visiting_tables=()):
        """Run one loot table for the `active` trials; return {item: per-trial count array}."""
        if table_name in visiting_tables:
            raise ValueError(f'Cyclic loot table: {visiting_tables + (table_name,)}')
        if table_name not in self.loot_tables[table_name]:
            raise ValueError(f'Missing loot table: {table_name}')
        loot_table = self.loot_tables[[table_name]]
        active = self.all_trials() if active is None else active
        item_counts = defaultdict(lambda: np.zeros(self.trial_count, dtype=np.int64))
        for pool in loot_table.get('pools', []):
            pool_mask = active & self.all_condition_mask(pool.get('conditions', []))
            rolls = self.sample_ints(pool.get('rolls', 1))
            for roll_idx in range(int(rolls.max(initial=0))):
                leaves = [leaf for pool_entry in pool['entries'] for leaf in self.expand_entry(pool_entry, pool_mask & (rolls > roll_idx))[0]]
                if not leaves:
                    continue
                picked_leaf_idx, total_weight = self.pick_leaf_per_trial(leaves)
                for leaf_idx, (entry, _) in enumerate(leaves):
                    leaf_selected_mask = (picked_leaf_idx == leaf_idx) & (total_weight > 0)
                    kind = entry['type'].split(':')[-1]
                    if not leaf_selected_mask.any() or kind == 'empty':
                        continue
                    if kind == 'loot_table':
                        drops = self.run_loot_table(entry['name'], leaf_selected_mask, visiting_tables + (table_name,))
                    elif kind == 'item':
                        drops = {entry['name']: np.ones(self.trial_count, dtype=np.int64)}
                    elif kind == 'tag':
                        drops = {item_id: np.ones(self.trial_count, dtype=np.int64) for item_id in resolve_tag(entry['name'], self.tags)}
                    elif kind == 'dynamic':
                        self.assumptions.add(f'Dynamic container contents excluded: {entry['name']}')
                        continue
                    else:
                        raise ValueError(f'Unsupported loot entry: {kind}')
                    
                    for item, count in drops.items():
                        count = self.apply_functions(count, entry.get('functions', []))
                        count = self.apply_functions(count, pool.get('functions', []))
                        item_counts[item] += count * leaf_selected_mask
        return {item: self.apply_functions(count, loot_table.get('functions', [])) * active
                for item, count in item_counts.items()}
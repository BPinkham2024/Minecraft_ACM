"""Phase 2: Monte carlo simulation of loot tables."""

from collections import defaultdict
import numpy as np 
import pandas as pd

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

    def all_condition_ask(self, condition_list):
        combined_mask = self.all_trials()
        for condition_json in condition_list:
            combined_mask &= self.condition_mask(condition_json)
        return combined_mask

# standardize data

from pathlib import Path
import json
from dataclasses import dataclass

def identifier(path, root):
    """Vanilla files use paths relative to each data category as resource IDs.
    A file beneath loot_tables/chests becomes an ID beginning minecraft:chests/"""

    return 'minecraft: ' + path.relative_to(root).with_suffix('').as_posix()

def load_category(root):
    """Loads entire category of data"""
    return {identifier(p, root): json.loads(p.read_text(encoding='utf-8'))
            for p in sorted(root.rglob('*.json'))}



class Tags:
    """Tags are generics put in place to be able to use multiple different items as the same material.
    Resolve nested item tags, rejecting cycles and missing required references."""

    def __init__(self, values):
        self.values = values
        self.cache = {}

    def resolve(self, name, stack=()):
        if name in stack:
            raise ValueError(f'Cyclic item tag: {stack + (name,)}')
        if name in self.cache:
            return self.cache[name]
        if name not in self.values:
            raise ValueError(f'Missing required item tag: {name}')
        
        items = set()
        for value in self.values[name]['values']:
            required = True
            if isinstance(value, dict):
                required = value.get('required', True)
                value = value['id']
            if value.startswith('#'):
                if not required and value[1:] not in self.values:
                    continue
                items.update(self.resolve(value[1:], stack + (name,)))
            else:
                items.add(value)
        self.cache[name] = tuple(sorted(items))
        return self.cache[name]

    def ingredients(self, value):
        if isinstance(value, list):
            return tuple(sorted({i for v in value for i in self.ingredients(v)}))
        if 'item' in value:
            return (value['item'],)
        return self.resolve(value['tag'])

@dataclass(frozen=True)
class Recipe:
    id: str
    kind: str
    output: str
    count: int
    slots: tuple
    requires_table: bool = False

def parse_recipe(name, data, tags):
    """Read a single recipe; return None for dynamic item/NBT transformations."""

    kind = data['type'].split(':')[-1]
    if kind == 'crafting_shaped':
        # walking data as opposed to keying to get multiple of a symbol
        slots = [data['key'][symbol] for row in data['pattern']
                for symbol in row if symbol != ' ']
    elif kind == 'crafting_shapeless':
        slots = data['ingredients']
    elif kind in ('smelting', 'blasting', 'smoking', 'capfire_cooking', 'stonecutting'):
        slots = [data['ingredients']]
    elif kind == 'smithing_transform':
        slots = [data[key] for key in ('template', 'base', 'addition')]
    else:
        return None

    # cookking and stonecutting have string results; crafting has objects
    result = data['result']
    if isinstance(result, str):
        output, count = result, data.get('count', 1)
    else:
        output, count = result['item'], result.get('count', 1)
    options = tuple(tags.ingredient(slot) for slot in slots)
    if count < 1 or any(not slot for slot in options):
        raise ValueError(f'Invalid recipe: {name}')

    # all three wide patterns need crafting table
    requires_table = False
    if kind == 'crafting_shaped':
        requires_table = len(data['pattern']) > 2 or max(map(len, data['pattern'])) > 2
    elif kind == 'crafting_shapeless':
        requires_table = len(slots) > 4
    return Recipe(name, kind, output, count, options, requires_table)

def collect_loot_items(value, inventory):
    """Traverse JSON and add referenced item IDs to the inventory."""
    
    if isinstance(value, dict):
        if value.get('type') == 'minecraft:item':
            inventory.add(value['name'])
        for child in value.values():
            collect_loot_items(child, inventory)
    elif isinstance(value, list):
        for child in value:
            collect_loot_items(child, value)
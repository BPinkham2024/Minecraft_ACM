"""Phase 1: read the raw JSON (recipes, item tags, loot tables) into plain structures."""

import json
from typing import NamedTuple

def load_dir(root):
    """Map resource id ('minecraft:path/name') -> parsed JSON for every file under root."""
    return {'minecraft:' + path.relative_to(root).with_suffix('').as_posis(): json.loads(path.read_text())
            for path in sorted(root.rglob('*.json'))}

def resolve_tag(tag_name, tags, visiting_tags=()):
    """All item ids in a tag, following nested '#tag' references."""
    if tag_name in visiting_tags:
        raise ValueError(f'Cyclic tag: {visiting_tags + (tag_name,)}')
    if tag_name not in tags:
        raise ValueError(f'Missing tag: {tag_name}')
    item_ids = set()
    for value in tags[tag_name]['values']:
        required = True
        if isinstance(value, dict):
            required, value = value.get('required', True), value['id']
        if not value.startswith('#'):
            item_ids.add(value)
        elif required or value[1:] in tags:
            item_ids |= resolve_tag(value[1:], tags, visiting_tags + (tag_name,))
    return item_ids

class Recipe(NamedTuple):
    id: str
    kind: str
    output: str
    count: int
    slots: tuple # one tuple of alternative item ids per ingredient slot (OR within, AND across)
    needs_table: bool


def ingredient(ingredient_json, tags):
    if isinstance(ingredient_json, list):
        return tuple(sorted({item_id for sub_ingredient in ingredient_json for item_id in ingredient(sub_ingredient, tags)}))
    return (ingredient_json['item'],) if 'item' in ingredient_json else tuple(sorted(resolve_tag(ingredient_json['tag'], tags)))


def parse_recipe(recipe_id, recipe_json, tags):
    """Return a recipe, or None for dynamic recipes that can't be modeled here"""
    kind = recipe_json['type'].split(':')[-1]
    if kind == 'crafting_shaped':
        slots = [recipe_json['key'][cell] for row in recipe_json['pattern'] for cell in row if cell != ' ']
        needs_crafting_table = len(recipe_json['pattern']) > 2 or max(map(len, recipe_json['pattern'])) > 2
    elif kind == 'crafting_shapeless':
        slots = recipe_json['ingredients']
        needs_crafting_table = len(slots) > 4
    elif kind in ('smelting', 'blasting', 'smoking', 'campfire_cooking', 'stonecutting'):
        slots, needs_crafting_table = [recipe_json['ingredient']], False
    elif kind == 'smithing_transform':
        slots, needs_crafting_table = [recipe_json[part_name] for part_name in ('template', 'base', 'addition')], False
    else:
        return None
    result = recipe_json['result'] #will be either string or object, cooking/stonecutting: str, crafting: obj
    output, count = (result, recipe_json.get('count', 1)) if isinstance(result, str) \
        else(result['item'], result.get('count', 1))
    return Recipe(recipe_id, kind, output, count, tuple(ingredient(slot, tags) for slot in slots), needs_crafting_table)


def loot_items(loot_node, item_ids_found):
    """Collect every item id named anywhere in a loot table"""
    if isinstance(loot_node, dict):
        if loot_node.get('type') == 'minecraft:item':
            item_ids_found.add(loot_node['name'])
        loot_node = list(loot_node.values())
    if isinstance(loot_node, list):
        for child_node in loot_node:
            loot_items(child_node, item_ids_found)


def read_data(raw_dir):
    """Return (recipes, item tags, loot tables, sorted list of every item id)"""
    tags = load_dir(raw_dir / 'tags/items')
    loot = load_dir(raw_dir / 'loot_tables')
    recipes = [recipe for recipe_id, recipe_json in load_dir(raw_dir / 'recipes').items() if (recipe := parse_recipe(recipe_id, recipe_json, tags))]
    items = set()
    for tag in tags:
        items |= resolve_tag(tag, tags)
    for recipe in recipes:
        items.add(recipe.output)
        items.update(item_id for slot in recipe.slots for item_id in slot)
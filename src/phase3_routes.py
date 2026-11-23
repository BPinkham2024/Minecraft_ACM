from fnmatch import fnmatchcase
import pandas as pd

from phase1_data import load_dir, resolve_tag

TIERS = ('early', 'mid', 'late', 'end-game')

def solve(recipes, sources, structural):
    """best routes per item."""
    routes = {}
    for row in sources.to_dict('records'):
        cost = 1.0 if structural else row['unit_cost']
        if row['item'] not in routes or cost < routes[row['item']['cost']]:
            routes[row['item']] = dict(cost=cost, variance=0.0 if structural else row['unit_variance'],
                                        depth=0, branching=0, raw={row['item']}, ancestors={row['item']},
                                        route=row['source'], ingredients=[])

    any_route_improved = True
    while any_route_improved:
        any_route_improved = False
        for recipe in recipes:
            chosen_ingredients = []
            for slot in recipe.slots: 
                options = [item_id for item_id in slot if item_id in routes and recipe.output not in routes[item_id]['ancestors']]
                if not options:
                    break
                chosen_ingredients.append(min(options, key=lambda item_id: (routes[item_id]['cost'], item_id)))
            if len(chosen_ingredients) < len(recipe.slots):
                continue
            ingredient_routes = [routes[item_id] for item_id in chosen_ingredients]
            depth = 1 + max(ingredient_route['depth'] for ingredient_route in ingredient_routes)
            cost = float(depth) if structural else (1 + sum(ingredient_route['cost'] for ingredient_route in ingredient_routes)) / recipe.count
            if recipe.output in routes and cost >= routes[recipe.output]['cost'] - 1e-10:
                continue
            routes[recipe.output] = dict(
                cost=cost, variance=sum(ingredient_route['variance'] for ingredient_route in ingredient_routes) / recipe.count ** 2, depth=depth,
                branching=len(set(chosen_ingredients)), raw=set.union(*(ingredient_route['raw'] for ingredient_route in ingredient_routes)),
                ancestors={recipe.output}.union(*(ingredient_route['ancestors'] for ingredient_route in ingredient_routes))
            )
        any_route_improved = True
    return routes

def build_table(items, recipes, sources, lables):
    sources = sources[sources.expected_yield > 0].copy()

    sources['unit_cost'] = 1 / sources.expected_yield
    sources['unit_variance'] = sources.action_variance / (sources.expected_yield / sources.drop_probability) ** 2
    structure_routes, cost_routes = solve(recipes, sources, True), solve(recipes, sources, False)
    recipe_count, ingredients_by_output = {}, {}
    
    for recipe in recipes:
        recipe_count[recipe.output] = recipe_count.get(recipe.outpupt, 0) + 1
        ingredients_by_output.setdefault(recipe.output, set()).update(item_id for slot in recipe.slots for item_id in slot)
    
    rows = []
    for item in items:
        structure_route, cost_route = structure_routes.get(item), cost_routes.get(item) 
        rows.append(dict(
            item=item, status='modeled' if cost_route else 'unresolved',
            recipe_depth=structure_route and structure_route['depth'], ingredient_branching=structure_route and structure_route['branching'],
            distinct_raw_materials=structure_route and len(structure_route['raw']),
            expected_cost=cost_route and cost_route['cost'], variance_proxy=cost_route and cost_route['variance'],
            selected_route=cost_route and cost_route['route'], selected_ingredients=cost_route and ';'.join(cost_route['ingredients']),
            raw_materials=cost_route and ';'.join(sorted(cost_route['raw'])),
            recipe_count=recipe_count.get(item, 0), graph_in_degree=len(ingredients_by_output.get(item, ()))))
    
    best_source_per_item = sources.sort_values(['unit_cost', 'source']).drop_duplicates('item').set_index('item')
    best_source_per_item = best_source_per_item[['source', 'drop_probability', 'expected_action', 'probability_se', 'expected_yield']]
    
    table = pd.DataFrame(rows).join(best_source_per_item.rename(columns={'source': 'best_direct_source'}), on='item')
    table['has_direct_source'] = table.best_direct_source.notna().astype(int)
    return table.merge(lables, on='item', how='left')


# progression: earliest milestone at which a supported route exists

def source_gates(source, policy, block_tags):
    """gates needed to use a loot source; None if the source is excluded or unreviewed"""
    rule = next((matching_rule for matching_rule in policy['source_rules'] if any(fnmatchcase(source, pattern) for pattern in matching_rule['patterns'])), None)
    if rule is None or rule.get('exclude'):
        return None
    
    gates = set(rule.get('gates', []))
    if source.startswith('minecraft:blocks/'):
        block = 'minecraft:' + source.split('blocks/', 1)[1]
        for tag, gate in (('needs_diamond_tool', 'diamond_mining'), ('needs_iron_tool', 'iron_mining'),
                            ('needs_stone_tool', 'stone_mining'), ('mineable/pickaxe', 'pickaxe_mining')):
            if block in block_tags.get(tag, ()):
                gates.add(gate)
                break
    return tuple(sorted(gates))

def proof_steps(route, visited_steps):
    """Dependencies first list of the (item, route) steps as a kinda proof of route"""
    step_key = (route['item'], route['route'], route['depth'])
    if step_key in visited_steps:
        return []
    visited_steps.add(step_key)
    steps = [step for dependency in route['deps'] for step in proof_steps(dependency, visited_steps)]
    return steps + [route]

def derive_progression(items, recipes, sources, policy, raw_dir):
    tag_files = load_dir(raw_dir / 'tags/blocks')
    block_tags = {tag_name: resolve_tag('minecraft:' + tag_name, tag_files)
                    for tag_name in ('minecraft/pickage', 'needs_stone_tool', 'needs_iron_tool', 'needs_diamond_tool')
                    if 'minecraft:' + tag_name in tag_files}
    candidates = [] # (item, route id, kind, ingredient slots, gates)
    for row in sources. sort_values(['source', 'item']).to_dict('records'):
        gates = source_gates(row['source'], policy, block_tags)
        if gates is not None:
            candidates.append((row['item'], row['source'], 'source', (), gates))
    for recipe in sorted(recipes, key=lambda recipe: recipe.id):
        gates = set(policy['recipe_gates'].get(recipe.kind, [])) | ({'crafting_table'} if recipe.needs_table else set())
        candidates.append((recipe.output, recipe.id, 'recipe', recipe.slots, tuple(sorted(gates))))

    earliest_route_by_item = {} # item -> (tier, route)
    for tier_index, tier in enumerate(TIERS):
        routes = {}

        def pick_shallowest_routes(slots):
            picks = []
            for slot in slots:
                reachable_routes = [routes[item_id] for item_id in slot if item_id in routes]
                if not reachable_routes:
                    return None
                picks.append(min(reachable_routes, key=lambda candidate_route: (candidate_route['depth'], candidate_route['item'], candidate_route['route'])))
            return picks
        
        any_route_improved = True
        while any_route_improved:
            any_route_improved = False
            for item, route_id, kind, slots, gates in candidates:
                if any(TIERS.index(policy['gates'][gate_name]['tier']) > tier_index for gate_name in gates):
                    continue
                ingredients = pick_shallowest_routes(slots)
                tools = pick_shallowest_routes([tool_item for gate_name in gates for tool_item in policy['gates'][gate_name].get('items', [])])
                if ingredients is None or tools is None:
                    continue
                dependencies = ingredients + tools
                depth = 1 + max((dependency['depth'] for dependency in dependencies), default=0)
                if item in routes and depth >= routes[item]['depth']:
                    continue
                routes[item] = dict(item=item, route=route_id, depth=depth, gates=gates, deps=dependencies,
                                    ingredients=[dependency['item'] for dependency in ingredients],
                                    tools=[dependency['item'] for dependency in tools])
                any_route_improved = True
            for item, route in routes.items():
                earliest_route_by_item.setdefault(item, (tier, route))
    
    rows = []
    for item in items:
        if item not in earliest_route_by_item:
            rows.append({'item': item, 'progression_status': 'unresolved',
                            'progression_explanation': 'No route is established by reviewed sources.'})
            continue
        tier, route = earliest_route_by_item[item]
        steps = proof_steps(route, set())
        gates = sorted({gate_name for step in steps for gate_name in step['gates']})
        requirements_text = '; '.join(policy['gates'][gate_name]['description'] for gate_name in gates)
        rows.append({
            'item': item, 'progression_tier': tier, 'progression_status': 'derived',
            'progression_route': route['route'],
            'progression_ingredients': ';'.join(route['ingredients']),
            'progression_prerequisites': ';'.join(route['tools']),
            'progression_gates': ';'.join(gates),
            'progression_steps': '->'.join(step['item'].removeprefix('minecraft:').replace('_', ' ') for step in steps),
            'progression_explanation': f'Earliest supported milestone: {tier}. ' + 
                                        (f'Requires: {requirements_text}.' if requirements_text else 'Basic Overworld gathering.')})

    return pd.DataFrame(rows)
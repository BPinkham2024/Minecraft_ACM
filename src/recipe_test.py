import json
from pathlib import Path


def load_json(item_name: str) -> dict:
	"""Load and parse data/raw/(item_name).json."""
	base_dir = Path(__file__).resolve().parent.parent
	json_path = base_dir / "data" / "raw" / "recipes" / f"{item_name}.json"
	with json_path.open("r", encoding="utf-8") as f:
		return json.load(f)

# parsed_acacia_boat_json = load_acacia_boat_json()
# parsed_arrow_json = load_arrow_json()
# loaded_item_json = load_json("rabbit_stew_from_brown_mushroom")
item_name = input("enter item: ")
loaded_item_json = load_json(item_name)
# print(loaded_item_json)

def get_ingredients_list_shaped(item_json) -> list:
	ingredients = item_json.get("key", [])
	keys = ingredients.keys() # Get the keys from the ingredients dictionary
	ingredient_list = [
		ingredients[ingredient].get("item") or ingredients[ingredient].get("tag")
		for ingredient in keys
	]
	return ingredient_list

def get_ingredients_list_shapeless(item_json) -> list:
	ingredients = item_json.get("ingredients", [])
	ingredient_list = [
		ingredient.get("item") or ingredient.get("tag")
		for ingredient in ingredients
		]
	return ingredient_list

def get_recursive_items(item_json):
	if "shapeless" in str(loaded_item_json.get("type")):
		ingredient_list = get_ingredients_list_shapeless(loaded_item_json)
	elif "shaped" in str(loaded_item_json.get("type")):
		ingredient_list = get_ingredients_list_shaped(loaded_item_json)
	else:
		print(f"{item_name} is {loaded_item_json.get("type")}")
		ingredient_list = []

	
	
	
	return ingredient_list

# # Extract ingredients needed to craft acacia_boat
# ingredients = loaded_item_json.get("key", [])
# key = ingredients.keys()  # Get the keys from the ingredients dictionary
# print(ingredients)  # Output te ingredients for acacia_boat
# print(key)  # Output the key for acacia_boat

# for ingredient in key:
# 	ingredient_data = ingredients[ingredient]
# 	item_id = ingredient_data.get("item")
# 	print(f"Ingredient: {ingredient}, Item ID: {item_id}")



ingredient_list = get_recursive_items(loaded_item_json)

print("Items:\n{")
for ing in ingredient_list:
	print("\t"+ing[ing.find(":") + 1:])
print("}")
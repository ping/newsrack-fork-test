from typing import List

from _recipe_utils import Recipe, CoverOptions, onlyon_weekdays

# Define the categories display order, optional
categories_sort: List[str] = ["Examples", "Example Magazines"]

# Define your custom recipes list here
# Example: https://github.com/ping/newsrack-fork-test/blob/custom/_recipes_custom.py

recipes: List[Recipe] = [
    # Custom recipe example (recipes_custom/example.recipe.py)
    Recipe(
        recipe="example",
        slug="example-01",
        src_ext="epub",
        category="Examples",
        target_ext=["pdf"],
        cover_options=CoverOptions(
            text_colour="white",
            background_colour="black",
        ),  # generate black cover with white text
        tags=["example"]
    ),
    # Builtin Calibre recipe example
    Recipe(
        recipe="Macrobusiness",
        name="Macrobusiness",
        slug="macrobusiness",
        src_ext="epub",
        category="Examples",
        enable_on=onlyon_weekdays([1, 3, 5], 10),  # tues, thurs, sat
        tags=["business"]
    ),
    # newsrack builtin recipe
    Recipe(
        recipe="vox",
        slug="vox",
        src_ext="mobi",
        target_ext=["epub"],
        category="Example Magazines",
        tags=["news"]
    ),
]

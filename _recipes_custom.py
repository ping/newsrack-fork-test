from dataclasses import dataclass
from typing import List

from _recipe_utils import Recipe, CoverOptions, onlyon_weekdays

# Define the categories display order, optional
categories_sort: List[str] = ["Examples", "Examples 2"]

# Define your custom recipes list here
# Example: https://github.com/ping/newsrack-fork-test/blob/custom/_recipes_custom.py


@dataclass
class CustomTitleDateFormatRecipe(Recipe):
    # Use a different title date format from default
    def __post_init__(self):
        self.title_date_format = "%Y-%m-%d"


recipes: List[Recipe] = [
    # Custom recipe example (recipes_custom/example.recipe.py)
    Recipe(
        recipe="example",
        slug="example-01",
        src_ext="epub",
        category="Examples",
        target_ext=["pdf"],
        cover_options=CoverOptions(
            logo_path_or_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Logo.png",
            text_colour="white",
            background_colour="black",
        ),  # generate black cover with white text
        tags=["custom-recipe"]
    ),
    # Builtin Calibre recipe example
    Recipe(
        recipe="The Asian Review of Books",
        name="The Asian Review of Books",
        slug="asian-review-books",
        src_ext="epub",
        category="Examples",
        enable_on=onlyon_weekdays([1, 3, 5], 10),  # tues, thurs, sat
        tags=["calibre-builtin"]
    ),
    # newsrack builtin recipe
    Recipe(
        recipe="vox",
        slug="vox",
        src_ext="mobi",
        target_ext=["epub"],
        category="Examples 2",
        tags=["newsrack-builtin"]
    ),
    # newsrack builtin recipe with different default title_date_format
    CustomTitleDateFormatRecipe(
        recipe="mit-tech-review",
        slug="mit-tech-review-feed",
        src_ext="epub",
        category="Examples 2",
        enable_on=onlyon_weekdays([0, 1, 2, 3, 4, 5], -4),
        tags=["newsrack-builtin"],
    ),

]

# newsrack

Generate a "newsrack" of periodicals for your ereader.

Uses [calibre](https://calibre-ebook.com/), [GitHub Actions](.github/workflows/build.yml) and hosted
on [GitHub Pages](https://pages.github.com/).

## Running Your Own Instance

Enable Pages in your forked repository settings to deploy from `GitHub Actions`. If you wish to, from a different
branch, customise [_recipes_custom.py](_recipes_custom.py) and add your own recipes to the [`recipes_custom/`](recipes_custom) folder. Remember to set the
new branch as default so that GitHub Actions will build/deploy from the correct branch.

### What Can Be Customised

- The formats generated (`src_ext`, `target_ext`)
- When periodical recipes are enabled (`enable_on`)
- Remove/add recipes
- cron schedule and job timeout interval in [.github/workflows/build.yml](.github/workflows/build.yml)

[Example fork repo](https://github.com/ping/newsrack-fork-test/) / [Example customisations](https://github.com/ping/newsrack-fork-test/compare/main...custom)

#### Periodical Recipe Definition

```python
# Defined in _recipes.py
Recipe(
    recipe="example",  # actual recipe name
    slug="example",  # file name slug
    src_ext="mobi",  # recipe output format
    category="news",  # category
    name="An Example Publication",
    # display name, taken from recipe source by default. Must be defined for built-in recipes.
    target_ext=[],  # alt formats that src_ext will be converted to
    timeout=300,  # max interval (seconds) for executing the recipe, default 180 seconds
    overwrite_cover=False,  # generate a plain cover to overwrite Calibre's
    enable_on=True,  # determines when to run the recipe
    retry_attempts=1,  # retry attempts on TimeoutExpired, ReadTimeout
    cover_options=CoverOptions(),  # cover options
),
```

#### Examples

Run a built-in Calibre periodical recipe:

```python
Recipe(
    recipe="Associated Press",
    name="Associated Press",  # Required for built-in recipes
    slug="ap",
    src_ext="mobi",
    category="news",
),
```

Only generate epubs:

```python
Recipe(
    recipe="example",  # example.recipe.py
    slug="example",
    src_ext="epub",  # generate epub
    target_ext=[],  # don't generate alt formats
    category="example",
),
```

Use `enable_on` to conditionally enable a recipe:

```python
# instead of using the available functions, you can define your own custom functions for enable_on
from _recipe_utils import Recipe, onlyon_days, onlyat_hours, onlyon_weekdays

Recipe(
    recipe="example1",
    slug="example1",
    src_ext="epub",
    category="example",
    enable_on=onlyon_weekdays([0]),  # only on Mondays
),
Recipe(
    recipe="example2",
    slug="example2",
    src_ext="epub",
    category="example",
    enable_on=onlyon_days([1, 14]),  # only on days 1, 14 of each month
),
Recipe(
    recipe="example3",
    slug="example3",
    src_ext="epub",
    category="example",
    enable_on=onlyat_hours(list(range(6, 12)), -5),  # from 6am-11.59am daily, for the timezone UTC-5
),
```

Use calibre-generated cover:

```python
Recipe(
    recipe="example",
    slug="example",
    src_ext="epub",
    category="example",
    overwrite_cover=False,
),
```

Customise the generated cover:

```python
from _recipe_utils import CoverOptions

Recipe(
    recipe="example",
    slug="example",
    src_ext="epub",
    category="example",
    cover_options=CoverOptions(
        text_colour="white",
        background_colour="black",
        title_font_path="path/to/example.ttf",
        datestamp_font_path="path/to/example.ttf"
    ),
),
```

## Available Recipes

In addition to built-in Calibre [recipes](https://github.com/kovidgoyal/calibre/tree/master/recipes), [customised
recipes (`recipes/*.recipe.py`)](recipes) are included in this repository.

Recipes customised here have a modified `publication_date` which is set to the latest article date. This allows the
outputs to be sorted by recency. The recipe `title` is also modified to include the latest article date or issue date/number.

In alphabetical order:

<details>
<summary><b>News</b></summary>

1. [Asahi Shimbun](https://www.asahi.com/ajw/)
2. [Channel News Asia](https://www.channelnewsasia.com/)
3. [The Financial Times](https://www.ft.com/)
4. [The Guardian](https://www.theguardian.com/international)
5. [The JoongAng Daily](https://koreajoongangdaily.joins.com/)
6. [The Korea Herald](https://koreaherald.com/)
7. [The New York Times](https://www.nytimes.com/)
8. [The New York Times (Print)](https://www.nytimes.com/section/todayspaper)
9. [South China Morning Post](https://www.scmp.com/)
10. [Sydney Morning Herald](https://www.smh.com.au/)
11. [Taipei Times](https://www.taipeitimes.com/)
12. [The Washington Post](https://www.washingtonpost.com/)
13. ~~[The Japan Times](https://www.japantimes.co.jp/)~~

</details>

<details>
<summary><b>Magazines</b></summary>

1. [The Atlantic](https://www.theatlantic.com/)
2. [The Atlantic Magazine](https://www.theatlantic.com/magazine/)
3. [The Diplomat](https://thediplomat.com/)
4. [The Economist](https://www.economist.com/printedition)
5. [Harvard Business Review](https://hbr.org/magazine)
6. [MIT Press Reader](https://thereader.mitpress.mit.edu/)
7. [MIT Technology Review](https://www.technologyreview.com/)
8. [MIT Technology Review Magazine](https://www.technologyreview.com/magazine/)
9. [Nature](https://www.nature.com/nature/current-issue/)
10. [Nautilus](https://nautil.us/)
11. [The New Yorker](https://www.newyorker.com/)
12. [Poetry](https://www.poetryfoundation.org/poetrymagazine)
13. [Politico](https://www.politico.com/)
14. [ProPublica](https://www.propublica.org/)
15. [Rest of World](https://restofworld.org)
16. [Scientific American](https://www.scientificamerican.com/)
17. [The Third Pole](https://www.thethirdpole.net/)
18. [Time Magazine](https://time.com/magazine/)
19. [Vox](https://www.vox.com/)
20. [Wired](https://www.wired.com/magazine/)

</details>

<details>
<summary><b>Books</b></summary>

1. [Asian Review of Books](https://asianreviewofbooks.com)
2. [Five Books](https://fivebooks.com/)
3. [London Review of Books](https://www.lrb.co.uk/)
4. [The New Yorks Times - Books](https://www.nytimes.com/section/books)

</details>


# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

import argparse
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from collections import namedtuple
from datetime import datetime, timezone, timedelta
from functools import cmp_to_key
from timeit import default_timer as timer
from typing import List, Dict
from urllib.parse import urljoin, urlparse
from xml.dom import minidom

import humanize  # type: ignore
import requests  # type: ignore

from _opds import init_feed, simple_tag, extension_contenttype_map
from _recipe_utils import sort_category, Recipe
from _recipes import (
    recipes as default_recipes,
    categories_sort as default_categories_sort,
)
from _recipes_custom import (
    recipes as custom_recipes,
    categories_sort as custom_categories_sort,
)
from _utils import generate_cover, slugify

logger = logging.getLogger(__file__)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("publish_site", type=str, help="Deployment site url")
parser.add_argument(
    "-v",
    "--verbose",
    dest="verbose",
    action="store_true",
    help="Enable more verbose messages for debugging",
)
args = parser.parse_args()

verbose_mode = False
try:
    verbose_mode = str(os.environ["verbose"]).strip().lower() == "true"
except (KeyError, ValueError):
    pass

verbose_mode = verbose_mode or args.verbose
if verbose_mode:
    logger.setLevel(logging.DEBUG)

start_time = timer()
publish_folder = "public"
cache_folder = "cache"
job_log_filename = "job_log.json"
publish_site = args.publish_site
if not publish_site.endswith("/"):
    publish_site += "/"

catalog_path = "catalog.xml"
parsed_site = urlparse(publish_site)
username, domain, _ = parsed_site.netloc.split(".")
source_url = f"https://{domain}.com/{username}{parsed_site.path}"


RecipeOutput = namedtuple(
    "RecipeOutput",
    ["slug", "title", "file", "rename_to", "published_dt", "category", "description"],
)

# default style
with open("static/site.css", "r", encoding="utf-8") as f:
    site_css = f.read()

# non kindle style
with open("static/nonkindle.css", "r", encoding="utf-8") as f:
    nonkindle_css = f.read()

# default js
with open("static/site.js", "r", encoding="utf-8") as f:
    site_js = f.read().replace('"{nonkindle}"', json.dumps(nonkindle_css.strip()))


# use environment variables to skip specified recipes in CI
skip_recipes_slugs: List[str] = []
try:
    skip_recipes_slugs = [
        r.strip() for r in str(os.environ["skip"]).split(",") if r.strip()
    ]
except (KeyError, ValueError):
    pass

# use environment variables to run specified recipes in CI
regenerate_recipes_slugs: List[str] = []
try:
    regenerate_recipes_slugs = [
        r.strip() for r in str(os.environ["regenerate"]).split(",") if r.strip()
    ]
except (KeyError, ValueError):
    pass

commit_hash = None
for k in ["CI_COMMIT_SHA", "GITHUB_SHA"]:
    try:
        commit_hash = str(os.environ[k])
        break
    except (KeyError, ValueError):
        continue


# fetch index.json from published site
def fetch_cache():
    res = requests.get(urljoin(publish_site, "index.json"), timeout=15)
    try:
        res.raise_for_status()
        return res.json()
    except Exception as err:  # noqa
        logger.exception("[!] Error fetching index.json")
        return {}


curr_job_log = {}
job_log = {}
try:
    with open(os.path.join(cache_folder, job_log_filename), "r", encoding="utf-8") as f:
        job_log = json.load(f)
except:  # noqa
    pass

generated: Dict[str, Dict[str, List[RecipeOutput]]] = {}
today = datetime.utcnow().replace(tzinfo=timezone.utc)
index = {}  # type: ignore
cached = fetch_cache()
cache_sess = requests.Session()

# for GitHub
job_summary = """| Recipe | Status | Duration |
| ------ | ------ | -------- |
"""


def _add_recipe_summary(rec, status, duration=None):
    if duration:
        duration = humanize.precisedelta(duration)
    return f"| {rec.name} | {status} | {duration or 0} |\n"


# sort categories for display
sort_category_key = cmp_to_key(
    lambda a, b: sort_category(a, b, custom_categories_sort or default_categories_sort)
)

recipes: List[Recipe] = custom_recipes or default_recipes
for recipe in recipes:
    if not recipe.name:
        try:
            with open(f"{recipe.recipe}.recipe") as f:
                recipe_source = f.read()
                mobj = re.search(
                    r"\n_name\s=\s['\"](?P<name>.+)['\"]\n", recipe_source
                ) or re.search(
                    r"\btitle\s+=\s+u?['\"](?P<name>.+)['\"]\n", recipe_source
                )
                if mobj:
                    recipe.name = mobj.group("name")
                else:
                    logger.warning(f"Unable to extract recipe name for {recipe}.")
                    recipe.name = (
                        f"{recipe.recipe}.recipe"  # set name to recipe file name
                    )
        except FileNotFoundError:
            logger.warning(
                f"Built-in recipes should be configured with a recipe name: {recipe.recipe}"
            )
            recipe.name = f"{recipe.recipe}.recipe"
        except Exception as err:  # noqa
            logger.exception("Error getting recipe name")
            continue

    recipe.job_log = job_log
    job_status = ""

    if recipe.slug in skip_recipes_slugs:
        logger.info(f'[!] SKIPPED recipe: "{recipe.slug}"')
        job_summary += _add_recipe_summary(recipe, ":arrow_right_hook: Skipped")
        continue

    logger.info(f'{"-" * 20} Executing "{recipe.name}" recipe... {"-" * 30}')
    recipe_start_time = timer()

    if recipe.category not in generated:
        generated[recipe.category] = {}
    generated[recipe.category][recipe.name] = []
    index[recipe.name] = []

    source_file_name = f"{recipe.slug}.{recipe.src_ext}"
    source_file_path = os.path.join(publish_folder, source_file_name)
    cmd = [
        "ebook-convert",
        f"{recipe.recipe}.recipe",
        source_file_path,
    ]
    if recipe.conv_options and recipe.conv_options.get(recipe.src_ext):
        cmd.extend(recipe.conv_options[recipe.src_ext])
    if verbose_mode:
        cmd.append("-vv")

    exit_code = 0

    # set recipe debug output folder
    if verbose_mode:
        os.environ["recipe_debug_folder"] = os.path.abspath(publish_folder)

    # use glob for re-run cases in local dev
    if not glob.glob(publish_folder + f"/{recipe.slug}*.{recipe.src_ext}"):
        # existing file does not exist
        try:
            # regenerate restriction is not in place and recipe is enabled
            if (recipe.is_enabled() and not regenerate_recipes_slugs) or (
                # regenerate restriction is in place and recipe is included
                regenerate_recipes_slugs
                and recipe.slug in regenerate_recipes_slugs
            ):
                for attempt in range(recipe.retry_attempts + 1):
                    try:
                        # run recipe
                        exit_code = subprocess.call(
                            cmd,
                            timeout=recipe.timeout,
                            stdout=sys.stdout,
                            stderr=sys.stderr,
                        )
                        break
                    except subprocess.TimeoutExpired:
                        if attempt < recipe.retry_attempts:
                            recipe_elapsed_time = timedelta(
                                seconds=timer() - recipe_start_time
                            )
                            logger.warning(
                                f"TimeoutExpired fetching '{recipe.name}' "
                                f"after {humanize.precisedelta(recipe_elapsed_time)}. Retrying..."
                            )
                            time.sleep(2)
                            continue
                        raise
                curr_job_log[recipe.name] = int(time.time())
            else:
                # use cache
                logger.warning(f'Using cached copy for "{recipe.name}".')
                if cached.get(recipe.name):
                    abort_recipe = False
                    for cached_item in cached[recipe.name]:
                        _, ext = os.path.splitext(cached_item["filename"])
                        if ext != f".{recipe.src_ext}" and ext not in [
                            f".{x}" for x in recipe.target_ext
                        ]:
                            continue
                        ebook_url = urljoin(publish_site, cached_item["filename"])
                        timeout = 120
                        for attempt in range(1 + recipe.retry_attempts):
                            try:
                                ebook_res = cache_sess.get(
                                    ebook_url, timeout=timeout, stream=True
                                )
                                ebook_res.raise_for_status()
                                with open(  # type: ignore
                                    os.path.join(
                                        publish_folder, os.path.basename(ebook_url)
                                    ),
                                    "wb",
                                ) as f:
                                    shutil.copyfileobj(ebook_res.raw, f)
                                job_status = ":outbox_tray: From cache"
                                break
                            except requests.exceptions.ReadTimeout as err:
                                if attempt < recipe.retry_attempts:
                                    logger.warning(f"ReadTimeout for {ebook_url}")
                                    timeout += 30
                                    time.sleep(2)
                                    continue
                                logger.error(f"[!] ReadTimeout for {ebook_url}")
                                abort_recipe = True

                    if abort_recipe:
                        recipe_elapsed_time = timedelta(
                            seconds=timer() - recipe_start_time
                        )
                        logger.info(
                            f'{"=" * 10} "{recipe.name}" recipe took {humanize.precisedelta(recipe_elapsed_time)} {"=" * 20}'
                        )
                        job_summary += _add_recipe_summary(
                            recipe, ":x: Cache Timeout", recipe_elapsed_time
                        )
                        continue
                else:
                    # not cached, so run it anyway to ensure that we try to have a copy
                    logger.warning(f'"{recipe.name}" is not cached.')
                    for attempt in range(recipe.retry_attempts + 1):
                        try:
                            # run recipe
                            exit_code = subprocess.call(
                                cmd,
                                timeout=recipe.timeout,
                                stdout=sys.stdout,
                                stderr=sys.stderr,
                            )
                            break
                        except subprocess.TimeoutExpired:
                            if attempt < recipe.retry_attempts:
                                recipe_elapsed_time = timedelta(
                                    seconds=timer() - recipe_start_time
                                )
                                logger.warning(
                                    f"TimeoutExpired fetching '{recipe.name}' "
                                    f"after {humanize.precisedelta(recipe_elapsed_time)}. Retrying..."
                                )
                                time.sleep(2)
                                continue
                            raise
                    curr_job_log[recipe.name] = int(time.time())

        except subprocess.TimeoutExpired:
            logger.exception(f"[!] TimeoutExpired fetching '{recipe.name}'")
            recipe_elapsed_time = timedelta(seconds=timer() - recipe_start_time)
            logger.info(
                f'{"=" * 10} "{recipe.name}" recipe took {humanize.precisedelta(recipe_elapsed_time)} {"=" * 20}'
            )
            job_summary += _add_recipe_summary(
                recipe, ":x: Convert Timeout", recipe_elapsed_time
            )
            continue
    else:
        job_status = ":file_folder: From local"

    # unset debug folder
    if os.environ.get("recipe_debug_folder", ""):
        del os.environ["recipe_debug_folder"]

    source_file_paths = sorted(
        glob.glob(publish_folder + f"/{recipe.slug}*.{recipe.src_ext}")
    )
    if not source_file_paths:
        logger.error(
            f"Unable to find source generated: '/{recipe.slug}*.{recipe.src_ext}'"
        )
        recipe_elapsed_time = timedelta(seconds=timer() - recipe_start_time)
        logger.info(
            f'{"=" * 20} "{recipe.name}" recipe took {humanize.precisedelta(recipe_elapsed_time)} {"=" * 20}'
        )
        job_summary += _add_recipe_summary(recipe, ":x: No output", recipe_elapsed_time)
        continue

    source_file_path = source_file_paths[-1]
    source_file_name = os.path.basename(source_file_path)

    if not exit_code:
        logger.debug(f'Get book meta info for "{source_file_path}"')
        proc = subprocess.Popen(
            ["ebook-meta", source_file_path], stdout=subprocess.PIPE
        )
        meta_out = proc.stdout.read().decode("utf-8")  # type: ignore
        mobj = re.search(
            r"Published\s+:\s(?P<pub_date>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",
            meta_out,
        )
        pub_date = today
        if mobj:
            pub_date = datetime.strptime(
                mobj.group("pub_date"), "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        title = ""
        mobj = re.search(r"Title\s+:\s(?P<title>.+)", meta_out)
        if mobj:
            title = mobj.group("title")
        rename_file_name = f"{recipe.slug}-{pub_date:%Y-%m-%d}.{recipe.src_ext}"

        comments = []
        description = ""
        mobj = re.search(r"Comments\s+:\s(?P<comments>.+)", meta_out, re.DOTALL)
        if mobj:
            try:
                comments = [
                    c.strip() for c in mobj.group("comments").split("\n") if c.strip()
                ]
                description = f"""{comments[0]}
                <ul><li>{"</li><li>".join(comments[1:-1])}</li></ul>
                {comments[-1]}
                """
            except:  # noqa
                pass

        generated[recipe.category][recipe.name].append(
            RecipeOutput(
                slug=recipe.slug,
                title=title,
                file=source_file_name,
                rename_to=rename_file_name,
                published_dt=pub_date,
                category=recipe.category,
                description=description,
            )
        )

        pseudo_series_index = pub_date.year * 1000 + pub_date.timetuple().tm_yday
        # (rename_file_name != source_file_name) checks that it is a newly generated file
        # so that we don't regenerate the cover needlessly
        if recipe.overwrite_cover and title and rename_file_name != source_file_name:
            # customise cover
            logger.debug(f'Setting cover for "{source_file_path}"')
            try:
                cover_file_path = f"{source_file_path}.png"
                generate_cover(cover_file_path, title, recipe.cover_options)
                cover_cmd = [
                    "ebook-meta",
                    source_file_path,
                    f"--cover={cover_file_path}",
                    f"--series={recipe.name}",
                    f"--index={pseudo_series_index}",
                    f"--publisher={publish_site}",
                ]
                _ = subprocess.call(cover_cmd, stdout=subprocess.PIPE)
                os.remove(cover_file_path)
            except Exception:  # noqa
                logger.exception("Error generating cover")
        elif rename_file_name != source_file_name:
            # just set series name
            series_cmd = [
                "ebook-meta",
                source_file_path,
                f"--series={recipe.name}",
                f"--index={pseudo_series_index}",
                f"--publisher={publish_site}",
            ]
            _ = subprocess.call(series_cmd, stdout=subprocess.PIPE)

        index[recipe.name].append(
            {
                "filename": f"{recipe.slug}-{pub_date:%Y-%m-%d}.{recipe.src_ext}",
                "published": pub_date.timestamp(),
            }
        )

        # convert generate book into alternative formats
        for ext in recipe.target_ext:
            target_file_name = f"{recipe.slug}.{ext}"
            target_file_path = os.path.join(publish_folder, target_file_name)

            cmd = [
                "ebook-convert",
                source_file_path,
                target_file_path,
                f"--series={recipe.name}",
                f"--series-index={pseudo_series_index}",
                f"--publisher={publish_site}",
            ]
            if recipe.conv_options and recipe.conv_options.get(ext):
                cmd.extend(recipe.conv_options[ext])

            customised_css_filename = os.path.join("static", f"{ext}.css")
            if os.path.exists(customised_css_filename):
                cmd.append(f"--extra-css={customised_css_filename}")
            if ext == "pdf":
                cmd.extend(["--pdf-page-numbers"])
            if verbose_mode:
                cmd.append("-vv")
            if not glob.glob(publish_folder + f"/{recipe.slug}*.{ext}"):
                exit_code = subprocess.call(
                    cmd,
                    timeout=recipe.timeout,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                )
            target_file_path = sorted(
                glob.glob(publish_folder + f"/{recipe.slug}*.{ext}")
            )[-1]
            target_file_name = os.path.basename(target_file_path)

            if not exit_code:
                generated[recipe.category][recipe.name].append(
                    RecipeOutput(
                        slug=recipe.slug,
                        title=title,
                        file=target_file_name,
                        rename_to=f"{recipe.slug}-{pub_date:%Y-%m-%d}.{ext}",
                        published_dt=pub_date,
                        category=recipe.category,
                        description=comments,
                    )
                )
                index[recipe.name].append(
                    {
                        "filename": f"{recipe.slug}-{pub_date:%Y-%m-%d}.{ext}",
                        "published": pub_date.timestamp(),
                    }
                )

        recipe_elapsed_time = timedelta(seconds=timer() - recipe_start_time)
        logger.info(
            f'{"=" * 20} "{recipe.name}" recipe took {humanize.precisedelta(recipe_elapsed_time)} {"=" * 20}'
        )
        job_summary += _add_recipe_summary(
            recipe,
            job_status or ":white_check_mark: Completed",
            recipe_elapsed_time,
        )

listing = ""
for i, (category, publications) in enumerate(
    sorted(generated.items(), key=sort_category_key)
):
    generated_items = [(k, v) for k, v in publications.items() if v]
    publication_listing = []
    for recipe_name, books in sorted(
        generated_items, key=lambda item: item[1][0].published_dt, reverse=True
    ):
        book_links = []
        for book in books:
            # change filename to datestamped name
            if book.file != book.rename_to:
                os.rename(
                    os.path.join(publish_folder, book.file),
                    os.path.join(publish_folder, book.rename_to),
                )
            file_size = os.path.getsize(os.path.join(publish_folder, book.rename_to))
            book_links.append(
                f'<div class="book"><a href="{book.rename_to}">{os.path.splitext(book.file)[1]}<span class="file-size">{humanize.naturalsize(file_size).replace(" ", "")}</span></a></div>'
            )
        publication_listing.append(
            f"""<li id="{books[0].slug}"><span class="title">{books[0].title or recipe_name}</span>{" ".join(book_links)}
            <span class="pub-date" data-pub-date="{int(books[0].published_dt.timestamp() * 1000)}">
                Published at {books[0].published_dt:%Y-%m-%d %-I:%M%p %z}
            </span>
            <div class="contents hide">{books[0].description}</div>
            </li>"""
        )
    category_recipes = [r for r in recipes if r.category == category]
    for r in category_recipes:
        if not r.name:
            continue
        success = False
        for recipe_name, _ in generated_items:
            if recipe_name == r.name:
                success = True
                break
        if not success:
            publication_listing.append(
                f"""<li class="not-available">{r.name}
                <span class="pub-date">Not available</span></li>"""
            )

    listing += f"""<h2 id="{slugify(category, True)}" class="category is-open">{category}
    <a class="opds" title="OPDS for {category.title()}" href="{slugify(category, True)}.xml">OPDS</a></h2>
    <ol class="books">{"".join(publication_listing)}
    <div class="close-cat-container"><a class="close-cat-shortcut" href="#" data-click-target="{category}"></a></div>
    </ol>
    """

with open(os.path.join(publish_folder, "index.json"), "w", encoding="utf-8") as f_in:
    index["_generated"] = int(time.time())
    json.dump(index, f_in, indent=0)

elapsed_time = timedelta(seconds=timer() - start_time)

job_log.update(curr_job_log)
with open(os.path.join(cache_folder, job_log_filename), "w", encoding="utf-8") as f:
    json.dump(job_log, f)

with open("static/index.html", "r", encoding="utf-8") as f_in:
    html_output = f_in.read().format(
        listing=listing,
        css=site_css,
        refreshed_ts=int(time.time() * 1000),
        refreshed_dt=datetime.now(tz=timezone.utc),
        js=site_js,
        publish_site=publish_site,
        elapsed=humanize.naturaldelta(elapsed_time, minimum_unit="seconds"),
        catalog=catalog_path,
        source_link=f'<a class="git" href="{source_url}"><img src="git.svg" alt="Git icon"> {commit_hash[0:7] if commit_hash else "Source"}.</a>',
    )
    index_html_file = os.path.join(publish_folder, "index.html")
    with open(index_html_file, "w", encoding="utf-8") as f:
        f.write(html_output)


# Generate minimal OPDS
main_doc = minidom.Document()
main_feed = init_feed(main_doc, publish_site, "newsrack", "News Rack")

for category, publications in sorted(generated.items(), key=sort_category_key):

    cat_doc = minidom.Document()
    cat_feed = init_feed(
        cat_doc, publish_site, "newsrack", f"News Rack - {category.title()}"
    )

    generated_items = [(k, v) for k, v in publications.items() if v]
    publication_listing = []
    for recipe_name, books in sorted(
        generated_items, key=lambda item: item[1][0].published_dt, reverse=True
    ):
        book_links = []
        for doc, feed in [(main_doc, main_feed), (cat_doc, cat_feed)]:
            entry = doc.createElement("entry")
            entry.appendChild(simple_tag(doc, "id", recipe_name))
            entry.appendChild(
                simple_tag(
                    doc,
                    "title",
                    f"{books[0].title or recipe_name}",
                )
            )
            entry.appendChild(
                simple_tag(
                    doc,
                    "summary",
                    f"{books[0].title or recipe_name} published at {books[0].published_dt:%Y-%m-%d %H:%M%p}.",
                )
            )
            entry.appendChild(
                simple_tag(
                    doc,
                    "content",
                    f"{books[0].description or recipe_name}",
                    attributes={"type": "text/html"},
                )
            )
            entry.appendChild(
                simple_tag(
                    doc,
                    "updated",
                    f"{books[0].published_dt:%Y-%m-%dT%H:%M:%SZ}",
                )
            )
            entry.appendChild(
                simple_tag(
                    doc,
                    "category",
                    attributes={"label": category.title()},
                )
            )
            author_tag = simple_tag(doc, "author")
            author_tag.appendChild(simple_tag(doc, "name", category.title()))
            entry.appendChild(author_tag)

            for book in books:
                book_ext = os.path.splitext(book.file)[1]
                link_type = (
                    extension_contenttype_map.get(book_ext)
                    or "application/octet-stream"
                )

                entry.appendChild(
                    simple_tag(
                        doc,
                        "link",
                        attributes={
                            "rel": "http://opds-spec.org/acquisition",
                            "type": link_type,
                            "href": f"{os.path.basename(book.rename_to)}",
                        },
                    )
                )

            feed.appendChild(entry)

    opds_xml_path = os.path.join(publish_folder, f"{slugify(category, True)}.xml")
    with open(opds_xml_path, "wb") as f:  # type: ignore
        f.write(cat_doc.toprettyxml(encoding="utf-8", indent=""))

opds_xml_path = os.path.join(publish_folder, catalog_path)
with open(opds_xml_path, "wb") as f:  # type: ignore
    f.write(main_doc.toprettyxml(encoding="utf-8", indent=""))

with open("job_summary.md", "w", encoding="utf-8") as f:
    f.write(job_summary)

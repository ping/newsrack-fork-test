#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Original at https://github.com/kovidgoyal/calibre/blob/4a01a799f19c4d0711d826ec7c79821b4ea690b6/recipes/japan_times.recipe
#
# [!] Ad-blocked, requires login
#
"""
japantimes.co.jp
"""

__license__ = "GPL v3"
__copyright__ = (
    "2008-2013, Darko Miletic <darko.miletic at gmail.com>. "
    "2022, Albert Aparicio Isarn <aaparicio at posteo.net>"
)

import os
import sys
from datetime import datetime

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title, get_datetime_format

from calibre.web.feeds.news import BasicNewsRecipe

_name = "Japan Times"


class JapanTimes(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    __author__ = "Albert Aparicio Isarn (original recipe by Darko Miletic)"
    description = "The latest news from Japan Times, Japan's leading English-language daily newspaper"
    language = "en_JP"
    category = "news, politics, japan"
    publisher = "The Japan Times"
    oldest_article = 1
    max_articles_per_feed = 60
    publication_type = "newspaper"
    masthead_url = "https://cdn-japantimes.com/wp-content/themes/jt_theme/library/img/japantimes-logo-tagline.png"

    auto_cleanup = False

    conversion_options = {
        "comment": description,
        "tags": category,
        "publisher": publisher,
        "language": language,
    }

    remove_attributes = ["style"]
    remove_tags_before = [dict(name="main")]
    remove_tags_after = [dict(name="main")]

    remove_tags = [
        dict(name=["script", "style"]),
        dict(
            id=[
                "tpModal",
                "site_header",
                "nav_anchor_container",
                "nav",
                "no_js_blocker",
                "menu",
                "taboola-below-article-thumbnails",
                "disqus_thread",
                "piano-recommend",
            ]
        ),
        dict(
            class_=[
                "clearfix",
                "nav_search",
                "sub_menu_container",
                "sidebar",
                "ad",
                "site_footer",
                "post-attachments",
                "post-keywords",
                "newsletter-signup",
                "DisplayAd",
                "jt-subscribe-box",
                "single-sns-area",
                "single-upper-meta",
                "article_footer_ad",
                "note-to-commenters",
                "note-to-non-commenters",
                "pagetop-wrap",
                "jt-related-stories",
            ]
        ),
    ]

    extra_css = """
    .article-meta {  margin-top: 1rem; margin-bottom: 1rem; }
    .article-meta .author { font-weight: bold; color: #444; margin-right: 0.5rem; }
    ul.slides { list-style: none; }
    .slide_image img { max-width: 100%; height: auto; }
    .slide_image div, .inline_image div { font-size: 0.8rem; margin-top: 0.2rem; }
    """

    feeds = [
        ("Top Stories", "https://www.japantimes.co.jp/feed/topstories/"),
        ("News", "https://www.japantimes.co.jp/news/feed/"),
        ("Opinion", "https://www.japantimes.co.jp/opinion/feed/"),
        ("Life", "https://www.japantimes.co.jp/life/feed/"),
        ("Community", "https://www.japantimes.co.jp/community/feed/"),
        ("Culture", "https://www.japantimes.co.jp/culture/feed/"),
        # ("Sports", "https://www.japantimes.co.jp/sports/feed/"),
    ]

    def preprocess_html(self, soup):
        # "unbullet" the images
        slides = soup.find(name="ul", attrs={"class": "slides"})
        if slides:
            for img_div in slides.find_all(attrs={"class": "slide_image"}):
                slides.insert_after(img_div.extract())
            slides.decompose()

        # embed the lazy loaded images
        lazy_loaded_images = soup.find_all(name="img", attrs={"data-src": True})
        for img in lazy_loaded_images:
            img["src"] = img["data-src"]

        # reformat the article meta
        meta = soup.new_tag("div", attrs={"class": "article-meta"})
        credit = soup.find(name="meta", attrs={"name": "cXenseParse:jat-credit"})
        if credit:
            sep = credit.get("data-separator", ",")
            authors = credit["content"].split(sep)
            author_ele = soup.new_tag("span", attrs={"class": "author"})
            author_ele.append(",".join(authors))
            meta.append(author_ele)
        pub_date = soup.find(name="meta", attrs={"property": "article:published_time"})
        if pub_date:
            pub_date = datetime.fromisoformat(pub_date["content"])
            pub_date_ele = soup.new_tag("span", attrs={"class": "published-date"})
            pub_date_ele.append(f"{pub_date:{get_datetime_format()}}")
            meta.append(pub_date_ele)
            if (not self.pub_date) or pub_date > self.pub_date:
                self.pub_date = pub_date
                self.title = format_title(_name, pub_date)
        soup.body.h1.insert_after(meta)
        return soup

    def parse_feeds(self):
        # because feed is not sorted by date
        parsed_feeds = super().parse_feeds()
        for feed in parsed_feeds:
            articles = feed.articles
            articles = sorted(articles, key=lambda a: a.utctime, reverse=True)
            feed.articles = articles
        return parsed_feeds

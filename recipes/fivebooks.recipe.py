# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

"""
fivebooks.com
"""
import json
import os
import re
from datetime import datetime
from datetime import timezone

from calibre.ebooks.BeautifulSoup import BeautifulSoup
from calibre.web.feeds.news import BasicNewsRecipe

_name = "Five Books"


class FiveBooks(BasicNewsRecipe):
    title = _name
    __author__ = "ping"
    description = "Expert book recommendations https://fivebooks.com/"
    language = "en"
    category = "books"
    publication_type = "blog"
    max_articles_per_feed = 15
    use_embedded_content = False
    encoding = "utf-8"
    remove_javascript = True
    no_stylesheets = True
    compress_news_images = True
    masthead_url = "https://fivebooks.com/app/themes/five-books/assets/images/logo.png"
    scale_news_images = (400, 400)
    scale_news_images_to_device = False  # force img to be resized to scale_news_images
    auto_cleanup = False
    timeout = 20
    timefmt = ""  # suppress date output
    pub_date = None  # custom publication date

    ignore_duplicate_articles = {"url"}

    remove_attributes = ["style", "font"]
    remove_tags = [
        dict(id=["interview-related", "buyfive"]),
        dict(
            class_=[
                "listen-button",
                "buy-button",
                "book-ad",
                "-newsletter",
                "read-later-and-social",
                "further-reading",
                "show-for-medium-up",
                "hide-for-small",
                "book-list-mobile",
                "-donate",
                "update",
                "social-buttons",
                "ebook-button",
                "book-links",
                "bio-component",
            ]
        ),
        dict(name=["script", "noscript", "style"]),
    ]
    remove_tags_before = [dict(class_=["main-content"])]
    remove_tags_after = [dict(class_=["main-content"])]

    extra_css = """
    p.book-number { font-weight: bold; font-size: 1.2rem; }
    ul.book-covers { list-style: none; list-style-type: none; padding-left: 0; }
    ul.book-covers li { display: block; margin-bottom: 1rem; }
    ul.book-covers li .cover-wrap { display: inline-block; vertical-align: top; }
    ul.book-covers li p.book-number { display: none; }
    ul.book-covers li h2 { display: inline-block; font-size: 0.8rem; margin-left: 1rem; }
    p.pullquote { margin-left: 3pt; font-size: 0.85rem; color: #333333; font-style: italic; }
    """
    feeds = [
        ("Newest", "https://fivebooks.com/interviews/?order=newest"),
        ("Popular", "https://fivebooks.com/interviews/?order=popular"),
    ]

    def _format_title(self, feed_name, post_date):
        """
        Format title
        :return:
        """
        try:
            var_value = os.environ["newsrack_title_dt_format"]
            return f"{feed_name}: {post_date:{var_value}}"
        except:  # noqa
            return f"{feed_name}: {post_date:%-d %b, %Y}"

    def publication_date(self):
        return self.pub_date

    def populate_article_metadata(self, article, soup, first):
        post_date = None
        dt = soup.find(class_="date")
        if not dt:
            dated_tag = soup.find(attrs={"data-post-modified-date": True})
            if dated_tag:
                post_date = datetime.fromisoformat(dated_tag["data-post-modified-date"])
        else:
            post_date = datetime.strptime(dt.text, "%B %d, %Y").replace(
                tzinfo=timezone.utc
            )
        if post_date:
            if not self.pub_date or post_date > self.pub_date:
                self.pub_date = post_date
                self.title = self._format_title(_name, post_date)
            article.utctime = post_date

        description_tag = soup.find(attrs={"data-post-description": True})
        if description_tag:
            article.text_summary = description_tag["data-post-description"]

    def preprocess_raw_html(self, raw_html, url):
        soup = BeautifulSoup(raw_html)
        content = soup.find(class_="main-content")
        script = soup.find("script", attrs={"type": "application/ld+json"})
        if not (script and script.get_text()):
            return raw_html
        graph = json.loads(script.get_text()).get("@graph", [])
        if not graph:
            return raw_html
        for g in graph:
            if g.get("@type") != "WebPage":
                continue
            content["data-post-modified-date"] = (
                g.get("dateModified") or g["datePublished"]
            )
            content["data-post-description"] = g.get("description", "")
            break
        return str(soup)

    def parse_index(self):
        br = self.get_browser()
        articles = {}
        for feed_name, feed_url in self.feeds:
            articles[feed_name] = []
            raw_html = br.open_novisit(feed_url).read().decode("utf-8")
            soup = BeautifulSoup(raw_html)
            interviews = soup.find_all(class_="library-page")
            if self.max_articles_per_feed < len(interviews):
                interviews = interviews[: self.max_articles_per_feed]
            for interview in interviews:
                heading = interview.find("h2")
                title = re.sub(r"\s{2,}", " ", heading.text)
                link = heading.find("a")
                articles[feed_name].append(
                    {
                        "title": title,
                        "url": link["href"],
                        "date": "",
                        "description": "",
                    }
                )
        return articles.items()

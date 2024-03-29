# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0
import os
import sys

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title, get_datetime_format

from calibre.web.feeds.news import BasicNewsRecipe

_name = "Vox"


class Vox(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    language = "en"
    description = "General interest news site https://www.vox.com/"
    __author__ = "ping"
    publication_type = "magazine"
    masthead_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Vox_logo.svg/300px-Vox_logo.svg.png"
    oldest_article = 7  # days

    max_articles_per_feed = 25
    use_embedded_content = True
    scale_news_images = (600, 600)

    remove_attributes = ["style", "font"]

    feeds = [
        ("Font Page", "https://www.vox.com/rss/front-page/index.xml"),
        ("All", "https://www.vox.com/rss/index.xml"),
    ]
    # e-image
    extra_css = """
    h2 { font-size: 1.8rem; margin-bottom: 0.4rem; }
    .article-meta { padding-bottom: 0.5rem; }
    .article-meta .author { font-weight: bold; color: #444; margin-right: 0.5rem; }
    .e-image cite { display: block; }
    .e-image div, .e-image cite { font-size: 0.8rem; }
    """

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = format_title(_name, article.utctime)

    def parse_feeds(self):
        parsed_feeds = super().parse_feeds()
        for feed in parsed_feeds:
            for article in feed.articles:
                article.content = (
                    f"""
                <div class="article-meta">
                    <span class="author">{article.author}</span>
                    <span class="published-dt">{article.utctime:{get_datetime_format()}}</span>
                </div>
                """
                    + article.content
                )
        return parsed_feeds

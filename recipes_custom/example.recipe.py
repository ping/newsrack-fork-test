# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

"""
github.blog
"""
import os
import sys

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title

from calibre.web.feeds.news import BasicNewsRecipe

_name = "GitHub Blog"


class GitHubBlog(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    description = (
        "Updates, ideas, and inspiration from GitHub to help "
        "developers build and design software. https://github.blog/"
    )
    language = "en"
    __author__ = "ping"
    publication_type = "blog"
    oldest_article = 7  # days
    max_articles_per_feed = 7
    use_embedded_content = True
    encoding = "utf-8"
    auto_cleanup = False

    feeds = [
        (_name, "https://github.blog/feed/"),
    ]

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = format_title(_name, article.utctime)

    def parse_feeds(self):
        return self.group_feeds_by_date()

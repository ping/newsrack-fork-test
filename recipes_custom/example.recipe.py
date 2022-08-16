# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

"""
github.blog
"""
from datetime import timezone, timedelta
from calibre.web.feeds.news import BasicNewsRecipe
from calibre.web.feeds import Feed

_name = "GitHub Blog"


class GitHubBlog(BasicNewsRecipe):
    title = _name
    description = "Updates, ideas, and inspiration from GitHub to help developers build and design software."
    language = "en"
    __author__ = "ping"
    publication_type = "blog"
    oldest_article = 7  # days
    max_articles_per_feed = 7
    use_embedded_content = True
    no_stylesheets = True
    remove_javascript = True
    encoding = "utf-8"
    auto_cleanup = False
    timefmt = ""
    pub_date = None  # custom publication date

    feeds = [
        ("GitHub Blog", "https://github.blog/feed/"),
    ]

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = f"{_name}: {article.utctime:%-d %b, %Y}"

    def publication_date(self):
        return self.pub_date

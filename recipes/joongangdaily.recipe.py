# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

"""
koreajoongangdaily.joins.com
"""
import os
from datetime import timezone, timedelta

from calibre.web.feeds import Feed
from calibre.web.feeds.news import BasicNewsRecipe

_name = "JoongAng Daily"


class KoreaJoongAngDaily(BasicNewsRecipe):
    title = _name
    description = "The Korea JoongAng Daily is an English-language daily published by the JoongAng Group, Korea’s leading media group, in association with The New York Times. https://koreajoongangdaily.joins.com/"
    language = "en"
    __author__ = "ping"
    publication_type = "newspaper"
    oldest_article = 1  # days
    max_articles_per_feed = 60
    use_embedded_content = True
    no_stylesheets = True
    remove_javascript = True
    encoding = "utf-8"
    compress_news_images = True
    masthead_url = (
        "https://koreajoongangdaily.joins.com/resources/images/common/logo.png"
    )
    scale_news_images = (800, 800)
    scale_news_images_to_device = False  # force img to be resized to scale_news_images
    auto_cleanup = True
    timeout = 60
    timefmt = ""
    pub_date = None  # custom publication date

    feeds = [
        ("Korea JoongAng Daily", "https://koreajoongangdaily.joins.com/xmls/joins"),
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

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = self._format_title(_name, article.utctime)

    def publication_date(self):
        return self.pub_date

    def parse_feeds(self):
        # convert single parsed feed into date-sectioned feed
        # use this only if there is just 1 feed
        parsed_feeds = super().parse_feeds()
        if len(parsed_feeds or []) != 1:
            return parsed_feeds

        articles = []
        for feed in parsed_feeds:
            articles.extend(feed.articles)
        articles = sorted(articles, key=lambda a: a.utctime, reverse=True)
        new_feeds = []
        curr_feed = None
        parsed_feed = parsed_feeds[0]
        for i, a in enumerate(articles, start=1):
            date_published = a.utctime.replace(tzinfo=timezone.utc)
            date_published_loc = date_published.astimezone(
                timezone(offset=timedelta(hours=9))  # Seoul time
            )
            article_index = f"{date_published_loc:%-d %B, %Y}"
            if i == 1:
                curr_feed = Feed(log=parsed_feed.logger)
                curr_feed.title = article_index
                curr_feed.description = parsed_feed.description
                curr_feed.image_url = parsed_feed.image_url
                curr_feed.image_height = parsed_feed.image_height
                curr_feed.image_alt = parsed_feed.image_alt
                curr_feed.oldest_article = parsed_feed.oldest_article
                curr_feed.articles = []
                curr_feed.articles.append(a)
                continue
            if curr_feed.title == article_index:
                curr_feed.articles.append(a)
            else:
                new_feeds.append(curr_feed)
                curr_feed = Feed(log=parsed_feed.logger)
                curr_feed.title = article_index
                curr_feed.description = parsed_feed.description
                curr_feed.image_url = parsed_feed.image_url
                curr_feed.image_height = parsed_feed.image_height
                curr_feed.image_alt = parsed_feed.image_alt
                curr_feed.oldest_article = parsed_feed.oldest_article
                curr_feed.articles = []
                curr_feed.articles.append(a)
            if i == len(articles):
                # last article
                new_feeds.append(curr_feed)

        return new_feeds

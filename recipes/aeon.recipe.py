import json
import os
import sys
from datetime import datetime, timezone

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title

from calibre.web.feeds import Feed
from calibre.web.feeds.news import BasicNewsRecipe, prefixed_classes
from calibre.ebooks.BeautifulSoup import BeautifulSoup

_name = "Aeon"


class Aeon(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    __author__ = "ping"
    language = "en"
    description = (
        "A unique digital magazine, publishing some of the most profound and "
        "provocative thinking on the web. We ask the big questions and find "
        "the freshest, most original answers, provided by leading thinkers on "
        "science, philosophy, society and the arts. https://aeon.co/"
    )
    use_embedded_content = False
    encoding = "utf-8"
    publication_type = "blog"
    masthead_url = "https://aeon.co/logo.png"
    auto_cleanup = False
    oldest_article = 30
    max_articles_per_feed = 30
    compress_news_images_auto_size = 10
    remove_empty_feeds = True

    keep_only_tags = [prefixed_classes("styled__MainColumn-sc-")]
    remove_tags = [
        prefixed_classes(
            "SupportBar__Wrapper-sc- article__HideOnPrint-sc- article__AppendixContainer-sc- "
            "ArticleInfo__Wrapper-sc- SyndicationButton__SyndicationButtonWrapper-sc- "
            "article__SocialShareBar-sc- styled__MobileAttributionWrapper-sc- "
            "article__CurioPlayer-sc- article__EditorCredit-sc- article__Sidebar-sc-"
        )
    ]
    remove_attributes = ["align", "style"]

    extra_css = """
    h2 { font-size: 1.8rem; margin-bottom: 0.4rem; }
    h1 { font-size: 1.2rem; font-style: italic; margin-bottom: 1rem; }
    div.custom-date-published { font-weight: bold; color: #444; }
    .ld-image-block img { display: block; max-width: 100%; height: auto; }
    .ld-image-caption p { margin-top: 0.4rem; font-size: 0.8rem; }
    """
    feeds = [(_name, "https://aeon.co/feed.rss")]

    def preprocess_raw_html_(self, raw_html, url):
        soup = BeautifulSoup(raw_html)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if not script.contents:
                continue
            article = json.loads(script.contents[0])
            if not (article.get("@type") and article["@type"] == "Article"):
                continue
            break
        if not (article and article.get("articleBody")):
            err_msg = f"Unable to find article: {url}"
            self.log.warn(err_msg)
            self.abort_article(err_msg)

        published_date = datetime.strptime(
            article["datePublished"], "%Y-%m-%d"
        ).replace(tzinfo=timezone.utc)
        if (not self.pub_date) or published_date > self.pub_date:
            self.pub_date = published_date
            self.title = format_title(_name, published_date)

        # display article date
        header = soup.find("h1") or soup.find("h2")
        if header:
            date_ele = soup.new_tag("div", attrs={"class": "custom-date-published"})
            date_ele.append(f"{published_date:%-d %B, %Y}")
            header.insert_after(date_ele)
        return str(soup)

    def parse_feeds(self):
        return self.group_feeds_by_date(
            filter_article=lambda a: "/videos/" not in a.url
        )

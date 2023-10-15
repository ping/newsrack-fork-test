"""
newsletter.mollywhite.net
"""
import os
import sys

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title

from calibre.web.feeds.news import BasicNewsRecipe

_name = "Molly White"


class MollyWhiteNewsletter(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    description = "Keep up with the happenings in the tech world without all the boosterism. Cryptocurrency critic, technology researcher, and software engineer Molly White publishes a weekly explainer of the latest news and developments in the cryptocurrency industry, with summaries of the latest disasters featured on her well-known project Web3 is Going Just Great. https://newsletter.mollywhite.net/"
    language = "en"
    __author__ = "ping"
    publication_type = "blog"
    use_embedded_content = True
    auto_cleanup = False

    oldest_article = 30  # days
    max_articles_per_feed = 30

    remove_tags = [dict(class_=["subscription-widget-wrap", "image-link-expand"])]
    remove_attributes = ["width"]

    extra_css = """
    .captioned-image-container img {
        display: block;
        max-width: 100%;
        height: auto;
        box-sizing: border-box;
    }
    .captioned-image-container .image-caption { font-size: 0.8rem; margin-top: 0.2rem; }
    blockquote { font-size: 1.25rem; margin-left: 0; text-align: center; }
    blockquote p { margin: 0.4rem 0; }
    
    .footnote { color: dimgray; }
    .footnote .footnote-content p { margin-top: 0; }
    """

    feeds = [
        (_name, "https://newsletter.mollywhite.net/feed"),
    ]

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = format_title(_name, article.utctime)

    def parse_feeds(self):
        return self.group_feeds_by_date(timezone_offset_hours=6)

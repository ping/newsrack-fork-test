"""
natesilver.net
"""
import os
import sys

# custom include to share code between recipes
sys.path.append(os.environ["recipes_includes"])
from recipes_shared import BasicNewsrackRecipe, format_title

from calibre.web.feeds.news import BasicNewsRecipe

_name = "Nate Silver"


class NateSilver(BasicNewsrackRecipe, BasicNewsRecipe):
    title = _name
    description = "Nate Silver is the founder and editor in chief of FiveThirtyEight. https://www.natesilver.net/"
    language = "en"
    __author__ = "ping"
    publication_type = "blog"
    masthead_url = "https://substackcdn.com/image/fetch/w_256,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9798f361-e880-406c-9ed4-29229df02c27_256x256.png"
    use_embedded_content = True
    auto_cleanup = False

    oldest_article = 30  # days
    max_articles_per_feed = 30

    remove_tags = [
        dict(class_=["subscription-widget-wrap", "image-link-expand", "button-wrapper"])
    ]
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
        (_name, "https://www.natesilver.net/feed"),
    ]

    def preprocess_html(self, soup):
        paywall_ele = soup.find(attrs={"data-component-name": "Paywall"})
        if paywall_ele:
            err_msg = f'Article is paywalled: "{self.tag_to_string(soup.find("h1"))}"'
            self.log.warning(err_msg)
            self.abort_article(err_msg)
        return soup

    def populate_article_metadata(self, article, __, _):
        if (not self.pub_date) or article.utctime > self.pub_date:
            self.pub_date = article.utctime
            self.title = format_title(_name, article.utctime)

    def parse_feeds(self):
        return self.group_feeds_by_date(timezone_offset_hours=6)

# Copyright (c) 2022 https://github.com/ping/
#
# This software is released under the GNU General Public License v3.0
# https://opensource.org/licenses/GPL-3.0

# This is a vanilla calibre recipe, not recommended for newsrack use because
# Bloomberg blocks non-residential IPs

import json
import re
from urllib.parse import urljoin, urlparse

from calibre import browser, iswindows
from calibre.ebooks.BeautifulSoup import BeautifulSoup
from calibre.utils.date import parse_date
from calibre.web.feeds.news import BasicNewsRecipe

issue_url = ""  # ex: https://www.bloomberg.com/magazine/businessweek/22_44

blocked_path_re = re.compile(r"/tosv.*.html")


class BloombergBusinessweek(BasicNewsRecipe):
    title = "Bloomberg Businessweek"
    __author__ = "ping"
    description = (
        "Bloomberg delivers business and markets news, data, analysis, and video "
        "to the world, featuring stories from Businessweek. https://www.bloomberg.com/businessweek"
    )
    language = "en"
    masthead_url = "https://assets.bwbx.io/s3/javelin/public/hub/images/BW-Logo-Black-cc9035fbb3.svg"
    ignore_duplicate_articles = {"url"}
    auto_cleanup = False
    remove_javascript = True
    no_stylesheets = True
    compress_news_images = True
    timeout = 20
    date_format = "%I:%M%p, %-d %b, %Y" if iswindows else "%-I:%M%p, %-d %b, %Y"

    # NOTES: Bot detection kicks in really easily so either:
    # - limit the number of feeds
    # - or max_articles_per_feed
    # - or increase delay
    delay = 2
    oldest_article = 7
    max_articles_per_feed = 25

    compress_news_images_auto_size = 8
    bot_blocked = False
    download_count = 0

    remove_attributes = ["style", "height", "width", "align"]
    keep_only_tags = [dict(id="article-container")]
    remove_tags = [
        dict(
            class_=[
                "terminal-news-story",
                "inline-newsletter-top",
                "inline-newsletter-middle",
                "inline-newsletter-bottom",
                "for-you__wrapper",
                "video-player__overlay",
                "css--social-wrapper-outer",
                "css--recirc-wrapper",
            ]
        ),
        dict(name=["aside"], class_=["postr-recirc"]),
        dict(attrs={"data-tout-type": True}),
        dict(attrs={"data-ad-placeholder": True}),
    ]

    extra_css = """
    .headline, h1.css--lede-hed { font-size: 1.8rem; margin-bottom: 0.4rem; }
    .sub-headline, .css--lede-dek p { font-size: 1.2rem; font-style: italic; margin-bottom: 1rem; }
    .article-meta { padding-bottom: 0.5rem; }
    .article-meta .author { font-weight: bold; color: #444; margin-right: 0.5rem; }
    .article-section { display: block; font-weight: bold; color: #444; }
    .image img, .css--multi-image-wrapper img, .css--image-wrapper img { display: block; max-width: 100%; height: auto; }
    .news-figure-caption-text, .news-figure-credit, .caption, .credit,
    .css--caption-outer-wrapper, .css--multi-caption-outer-wrapper
     {
        display: block; font-size: 0.8rem; margin-top: 0.2rem;
    }
    .trashline { font-style: italic; }
    """

    # We send no cookies to avoid triggering bot detection
    def get_browser(self, *args, **kwargs):
        return self

    def clone_browser(self, *args, **kwargs):
        return self.get_browser()

    def open_novisit(self, *args, **kwargs):
        if self.bot_blocked:
            self.log.warn(f"Block detected. Skipping {args[0]}")
            # Abort article without making actual request
            self.abort_article(f"Block detected. Skipped {args[0]}")
        br = browser()
        br.set_handle_redirect(False)
        try:
            res = br.open_novisit(*args, **kwargs)
            self.download_count += 1
            return res
        except Exception as e:
            is_redirected_to_challenge = False
            if hasattr(e, "hdrs"):
                is_redirected_to_challenge = blocked_path_re.match(
                    urlparse(e.hdrs.get("location") or "").path
                )
            if is_redirected_to_challenge or (hasattr(e, "code") and e.code == 307):
                self.bot_blocked = True
                err_msg = f"Blocked by bot detection: {args[0]}"
                self.log.warn(err_msg)
                self.abort_recipe_processing(err_msg)
                self.abort_article(err_msg)
            raise

    open = open_novisit

    def cleanup(self):
        if self.download_count <= 1 + (1 if self.masthead_url else 0):
            err_msg = "No articles downloaded."
            self.log.warn(err_msg)
            self.abort_recipe_processing(err_msg)

    def image_url_processor(self, base_url, img_url):
        # downsize image
        for frag in ("/-1x-1.", "/-999x-999.", "/1200x-1."):
            img_url = img_url.replace(frag, "/800x-1.")
        return img_url

    def render_content(self, content, soup, parent):
        content_type = content.get("type", "")
        content_subtype = content.get("subType", "")
        if content_type in ("inline-newsletter", "inline-recirc", "ad", "list"):
            return None
        if content_type == "text":
            parent.append(content["value"])
            return
        if content_type == "heading" and content.get("data", {}).get("level"):
            return soup.new_tag(f'h{content["data"]["level"]}')
        if content_type == "paragraph":
            p = soup.new_tag("p")
            return p
        if content_type == "br":
            br = soup.new_tag("br")
            return br
        if content_type == "aside":
            return soup.new_tag("blockquote")
        if content_type == "embed" and content.get("iframeData", {}).get("html"):
            return BeautifulSoup(content["iframeData"]["html"], features="html.parser")
        if content_type == "link" and content.get("data", {}).get(
            "destination", {}
        ).get("web"):
            a = soup.new_tag("a")
            a["href"] = content["data"]["destination"]["web"]
            return a
        if content_type == "link" and content.get("data", {}).get("href"):
            a = soup.new_tag("a")
            a["href"] = content["data"]["href"]
            return a
        if content_type == "link":
            return soup.new_tag("span", attrs={"class": "link"})
        if content_type == "entity" and content_subtype == "story":
            link = (
                content.get("data", {})
                .get("link", {})
                .get("destination", {})
                .get("web", "")
            )
            if link:
                a = soup.new_tag("a")
                a["href"] = link
                return a
        if content_type == "entity" and content_subtype in (
            "person",
            "security",
            "story",
        ):
            return soup.new_tag("span", attrs={"class": content_subtype})
        if content_type == "media" and content_subtype == "chart":
            chart = content.get("data", {}).get("chart", {})
            if chart.get("fallback"):
                div = soup.new_tag("div", attrs={"class": "image"})
                img = soup.new_tag(
                    "img",
                    attrs={
                        "src": content.get("data", {}).get("chart", {}).get("fallback")
                    },
                )
                div.append(img)
                return div
        if content_type == "media" and content_subtype == "photo":
            photo = content.get("data", {}).get("photo", {})
            if photo.get("src"):
                div = soup.new_tag("div", attrs={"class": "image"})
                img = soup.new_tag(
                    "img",
                    attrs={"src": photo["src"]},
                )
                div.append(img)
                if photo.get("caption"):
                    caption = soup.new_tag("div", attrs={"class": "caption"})
                    caption.append(photo["caption"])
                    div.append(caption)
                if photo.get("credit"):
                    credit = soup.new_tag("div", attrs={"class": "credit"})
                    credit.append(photo["credit"])
                    div.append(credit)
                return div
        if content_type == "media" and content_subtype == "video":
            attachment = content.get("data", {}).get("attachment")
            if attachment.get("thumbnail", {}).get("url"):
                div = soup.new_tag("div", attrs={"class": "image"})
                img = soup.new_tag(
                    "img",
                    attrs={"src": attachment["thumbnail"]["url"]},
                )
                div.append(img)
                if attachment.get("title"):
                    caption = soup.new_tag("div", attrs={"class": "caption"})
                    caption.append(attachment["title"])
                    div.append(caption)
                return div

        self.log.warning(f"Unknown content type: {content_type}: {json.dumps(content)}")
        return None

    def nested_render(self, content, soup, parent):
        for cc in content.get("content", []):
            content_ele = self.render_content(cc, soup, parent)
            if content_ele:
                if cc.get("content"):
                    self.nested_render(cc, soup, content_ele)
                parent.append(content_ele)

    def preprocess_raw_html(self, raw_html, url):
        article = None
        soup = BeautifulSoup(raw_html)
        for script in soup.find_all(
            "script",
            attrs={
                "type": "application/json",
                "data-component-props": ["ArticleBody", "FeatureBody"],
            },
        ):
            j = json.loads(script.contents[0])
            if not j.get("story"):
                continue
            article = j
            break
        if not article:
            script = soup.find(
                "script", id="__NEXT_DATA__", attrs={"type": "application/json"}
            )
            if script:
                article = json.loads(script.contents[0])

        if not article:
            err_msg = f"Unable to find json: {url}"
            self.log.warn(err_msg)
            # self.abort_article(err_msg)
            return raw_html

        article = article.get("story") or article.get("props", {}).get(
            "pageProps", {}
        ).get("story")
        if not article:
            err_msg = f"Unable to find article json: {url}"
            self.log.warn(err_msg)
            self.abort_article(err_msg)

        date_published = parse_date(article["publishedAt"], assume_utc=True)
        soup = BeautifulSoup(
            """<html>
        <head><title></title></head>
        <body>
            <article id="article-container">
            <h1 class="headline"></h1>
            <div class="article-meta">
                <span class="published-dt"></span>
            </div>
            </article>
        </body></html>"""
        )
        published_at = soup.find(class_="published-dt")
        published_at.append(f"{date_published:{self.date_format}}")
        if article.get("updatedAt"):
            date_updated = parse_date(article["updatedAt"], assume_utc=True)
            published_at.append(f", Updated {date_updated:{self.date_format}}")

        soup.head.title.append(article.get("headlineText") or article["headline"])
        h1_title = soup.find("h1")
        h1_title.append(
            BeautifulSoup(
                article.get("headlineText") or article["headline"],
                features="html.parser",
            )
        )
        if article.get("summaryText") or article.get("abstract"):
            sub_headline = soup.new_tag("div", attrs={"class": "sub-headline"})
            if article.get("summaryText"):
                sub_headline.append(article["summaryText"])
            elif article.get("abstract"):
                for i, abstract in enumerate(article["abstract"]):
                    if i > 0:
                        sub_headline.append(soup.new_tag("br"))
                    sub_headline.append(f"• {abstract}")
            h1_title.insert_after(sub_headline)
        # inject authors
        if article.get("byline"):
            soup.find(class_="article-meta").insert(
                0,
                BeautifulSoup(f'<span class="author">{article["byline"]}</span>'),
            )
        else:
            try:
                post_authors = [a["name"] for a in article.get("authors", [])]
                if post_authors:
                    soup.find(class_="article-meta").insert(
                        0,
                        BeautifulSoup(
                            f'<span class="author">{", ".join(post_authors)}</span>'
                        ),
                    )
            except (KeyError, TypeError):
                pass
        # inject categories
        categories = [cat.title() for cat in article.get("categories", [])]
        if categories:
            soup.body.article.insert(
                0,
                BeautifulSoup(
                    f'<span class="article-section">{" / ".join(categories)}</span>'
                ),
            )
        # inject lede image
        if article.get("ledeImageUrl"):
            lede_img_url = article["ledeImageUrl"]
            lede_img_caption_html = article.get("ledeCaption", "")
            img_container = soup.new_tag("div", attrs={"class": "image"})
            img_ele = soup.new_tag("img", attrs={"src": lede_img_url})
            img_container.append(img_ele)
            if lede_img_caption_html:
                caption_ele = soup.new_tag(
                    "div", attrs={"class": "news-figure-caption-text"}
                )
                caption_ele.append(BeautifulSoup(lede_img_caption_html))
                img_container.append(caption_ele)
            soup.body.article.append(img_container)

        if type(article["body"]) == str:
            body_soup = BeautifulSoup(article["body"], features="html.parser")
            for img_div in body_soup.find_all(
                name="figure", attrs={"data-type": "image"}
            ):
                for img in img_div.find_all("img", attrs={"data-native-src": True}):
                    img["src"] = img["data-native-src"]
            for img in body_soup.find_all(name="img", attrs={"src": True}):
                img["src"] = img["src"]
            soup.body.article.append(body_soup)
        else:
            body_soup = BeautifulSoup(features="html.parser")
            self.nested_render(article["body"], body_soup, body_soup)
            soup.body.article.append(body_soup)
        return str(soup)

    def parse_index(self):
        if not issue_url:
            soup = self.index_to_soup("https://www.bloomberg.com/businessweek")
            latest_issue_article = soup.select(
                "#magazines_carousel article div[data-component='headline']"
            )[0]
            edition_url = urljoin(
                "https://www.bloomberg.com", latest_issue_article.a["href"]
            )
        else:
            edition_url = issue_url
        soup = self.index_to_soup(edition_url)
        edition = self.tag_to_string(soup.find("h1")).replace(" Issue", "")
        self.timefmt = f": {edition}"
        cover_img = soup.find("img", class_="story-list-module__image")
        self.cover_url = cover_img["src"].replace("/280x-1.jpg", "/800x-1.jpg")
        feeds = []
        for section in soup.find_all("div", class_="story-list-module__info"):
            section_name = self.tag_to_string(section.find("h3"))
            section_articles = []
            for article in section.find_all(
                class_="story-list-story__info__headline-link"
            ):
                section_articles.append(
                    {
                        "title": self.tag_to_string(article),
                        "url": urljoin("https://www.bloomberg.com", article["href"]),
                    }
                )
            if section_articles:
                feeds.append((section_name, section_articles))
        return feeds

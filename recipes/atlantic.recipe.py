#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2015, Kovid Goyal <kovid at kovidgoyal.net>
from __future__ import unicode_literals

import json
import os
import re
from datetime import datetime, timezone

from calibre.ebooks.BeautifulSoup import BeautifulSoup
from calibre.web.feeds.news import BasicNewsRecipe


def embed_image(soup, block):
    caption = block.get("captionText", "")
    if caption and block.get("attributionText", "").strip():
        caption += " (" + block["attributionText"].strip() + ")"

    container = soup.new_tag("div", attrs={"class": "article-img"})
    img = soup.new_tag("img", src=block["url"])
    container.append(img)
    cap = soup.new_tag("div", attrs={"class": "caption"})
    cap.append(BeautifulSoup(caption))
    container.append(cap)
    return container


def json_to_html(raw):
    data = json.loads(raw)

    # open('/t/p.json', 'w').write(json.dumps(data, indent=2))
    data = sorted(
        (v["data"] for v in data["props"]["pageProps"]["urqlState"].values()), key=len
    )[-1]
    article = json.loads(data)["article"]

    new_soup = BeautifulSoup(
        """<html><head></head><body><main id="from-json-by-calibre"></main></body></html>"""
    )
    if article.get("issue"):
        issue_ele = new_soup.new_tag("div", attrs={"class": "issue"})
        issue_ele.append(article["issue"]["issueName"])
        new_soup.main.append(issue_ele)

    headline = new_soup.new_tag("h1", attrs={"class": "headline"})
    headline.append(BeautifulSoup(article["title"]))
    new_soup.main.append(headline)

    subheadline = new_soup.new_tag("h2", attrs={"class": "sub-headline"})
    subheadline.append(BeautifulSoup(article["dek"]))
    new_soup.main.append(subheadline)

    meta = new_soup.new_tag("div", attrs={"class": "article-meta"})
    authors = [x["displayName"] for x in article["authors"]]
    author_ele = new_soup.new_tag("span", attrs={"class": "author"})
    author_ele.append(", ".join(authors))
    meta.append(author_ele)

    # Example: 2022-04-04T10:00:00Z
    published_date = datetime.strptime(
        article["datePublished"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    pub_ele = new_soup.new_tag("span", attrs={"class": "published-dt"})
    pub_ele["data-published"] = f"{published_date:%Y-%m-%dT%H:%M:%SZ}"
    pub_ele.append(f"{published_date:%-I:%M%p, %-d %B, %Y}")
    meta.append(pub_ele)
    if article.get("dateModified"):
        modified_date = datetime.strptime(
            article["dateModified"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        upd_ele = new_soup.new_tag("span", attrs={"class": "modified-dt"})
        upd_ele["data-modified"] = f"{modified_date:%Y-%m-%dT%H:%M:%SZ}"
        upd_ele.append(f"Updated {modified_date:%-I.%M%p, %-d %B, %Y}")
        meta.append(upd_ele)

    new_soup.main.append(meta)

    if article.get("leadArt") and "image" in article["leadArt"]:
        new_soup.main.append(embed_image(new_soup, article["leadArt"]["image"]))
    for item in article["content"]:
        tn = item.get("__typename", "")
        if tn.endswith("Image"):
            new_soup.main.append(embed_image(new_soup, item))
            continue
        content_html = item.get("innerHtml")
        if (not content_html) or "</iframe>" in content_html:
            continue
        if tn == "ArticleHeading":
            tag_name = "h2"
            mobj = re.match(r"HED(?P<level>\d)", item.get("headingSubtype", ""))
            if mobj:
                tag_name = f'h{mobj.group("level")}'
            header_ele = new_soup.new_tag(tag_name)
            header_ele.append(BeautifulSoup(content_html))
            new_soup.main.append(header_ele)
            continue
        if tn == "ArticlePullquote":
            container_ele = new_soup.new_tag("blockquote")
            container_ele.append(BeautifulSoup(content_html))
            new_soup.main.append(container_ele)
            continue
        if tn == "ArticleRelatedContentLink":
            container_ele = new_soup.new_tag("div", attrs={"class": "related-content"})
            container_ele.append(BeautifulSoup(content_html))
            new_soup.main.append(container_ele)
            continue
        content_ele = new_soup.new_tag(item.get("tagName", "p").lower())
        content_ele.append(BeautifulSoup(content_html))
        new_soup.main.append(content_ele)
    return str(new_soup)


class NoJSON(ValueError):
    pass


def extract_html(soup):
    script = soup.findAll("script", id="__NEXT_DATA__")
    if not script:
        raise NoJSON("No script tag with JSON data found")
    raw = script[0].contents[0]
    return json_to_html(raw)


_name = "The Atlantic"


class TheAtlantic(BasicNewsRecipe):

    title = _name
    description = "News and editorial about politics, culture, entertainment, tech, etc. Contains many articles not seen in The Atlantic magazine https://www.theatlantic.com/"

    __author__ = "Kovid Goyal"
    language = "en"
    encoding = "utf-8"
    use_embedded_content = False
    masthead_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/The_Atlantic_Logo_11.2019.svg/1200px-The_Atlantic_Logo_11.2019.svg.png"

    no_stylesheets = True
    remove_javascript = True
    remove_empty_feeds = True
    compress_news_images = True
    scale_news_images = (800, 800)
    scale_news_images_to_device = False  # force img to be resized to scale_news_images
    timeout = 20
    timefmt = ""
    pub_date = None  # custom publication date

    remove_attributes = ["style", "width", "height"]
    remove_tags_before = [dict(name=["main"])]
    remove_tags_after = [dict(name=["main"])]
    remove_tags = [
        dict(id=["interview-related", "buyfive"]),
        dict(
            class_=[
                "hints",
                "social-icons",
                "read-more",
            ]
        ),
        dict(name=["script", "noscript", "style"]),
    ]

    extra_css = """
    .issue { font-weight: bold; margin-bottom: 0.2rem; }
    .headline { font-size: 1.8rem; margin-bottom: 0.4rem; }
    .sub-headline { font-size: 1.2rem; font-style: italic; font-weight: normal; margin-bottom: 0.5rem; }
    .article-meta {  margin-top: 0.5rem; margin-bottom: 1rem; }
    .article-meta .author { font-weight: bold; color: #444; display: inline-block; }
    .article-meta .published-dt { display: inline-block; margin-left: 0.5rem; }
    .article-meta .modified-dt { display: block; margin-top: 0.2rem; font-style: italic; }
    .caption, .credit { font-size: 0.8rem; margin-top: 0.2rem; margin-bottom: 0.5rem; }
    .article-img img { display: block; max-width: 100%; height: auto; }
    h3 span.smallcaps { font-weight: bold; }
    p span.smallcaps { text-transform: uppercase; }
    blockquote { font-size: 1.25rem; margin-left: 0; text-align: center; }
    div.related-content { margin-left: 0.5rem; color: #444; font-style: italic; }
    /* for raw_html in Photo */
    div.img img { display: block; max-width: 100%; height: auto; }
    """

    feeds = [
        ("All", "https://www.theatlantic.com/feed/all/"),
        ("Best Of", "https://www.theatlantic.com/feed/best-of/"),
        ("Politics", "https://www.theatlantic.com/feed/channel/politics/"),
        ("Business", "https://www.theatlantic.com/feed/channel/business/"),
        ("Culture", "https://www.theatlantic.com/feed/channel/entertainment/"),
        ("Global", "https://www.theatlantic.com/feed/channel/international/"),
        ("Technology", "https://www.theatlantic.com/feed/channel/technology/"),
        ("U.S.", "https://www.theatlantic.com/feed/channel/national/"),
        ("Healthc", "https://www.theatlantic.com/feed/channel/health/"),
        ("Video", "https://www.theatlantic.com/feed/channel/video/"),
        ("Sexes", "https://www.theatlantic.com/feed/channel/sexes/"),
        ("Education", "https://www.theatlantic.com/feed/channel/education/"),
        ("Science", "https://www.theatlantic.com/feed/channel/science/"),
        ("News", "https://www.theatlantic.com/feed/channel/news/"),
        # ("Press Releases", "https://www.theatlantic.com/feed/channel/press-releases/"),
        ("Newsletters", "https://www.theatlantic.com/feed/channel/newsletters/"),
        # ("The Atlantic Photo", "https://feeds.feedburner.com/theatlantic/infocus"),
        ("Notes", "https://feeds.feedburner.com/TheAtlanticNotes"),
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

    def get_browser(self):
        br = BasicNewsRecipe.get_browser(self)
        br.set_cookie("inEuropeanUnion", "0", ".theatlantic.com")
        return br

    def preprocess_raw_html(self, raw_html, url):
        try:
            return extract_html(self.index_to_soup(raw_html))
        except NoJSON:
            self.log.warn("No JSON found in: {} falling back to HTML".format(url))
        except Exception:
            self.log.exception(
                "Failed to extract JSON data from: {} falling back to HTML".format(url)
            )
        return raw_html

    def preprocess_html(self, soup):
        for img in soup.findAll("img", attrs={"data-srcset": True}):
            data_srcset = img["data-srcset"]
            if "," in data_srcset:
                img["src"] = data_srcset.split(",")[0]
            else:
                img["src"] = data_srcset.split()[0]
        for img in soup.findAll("img", attrs={"data-src": True}):
            img["src"] = img["data-src"]

        ul = soup.find("ul", attrs={"class": "photos"})
        if ul:
            for li in ul.find_all("li"):
                li.name = "div"
                li["class"] = "article-img"
                permalink = li.find("a", attrs={"class": "permalink"})
                if permalink:
                    permalink.decompose()
                ul.insert_after(li.extract())
            ul.decompose()
        return soup

    def publication_date(self):
        return self.pub_date

    def populate_article_metadata(self, article, soup, _):
        headline = soup.find("h1", attrs={"class": "headline"})
        if headline:
            # reset the title because the title in the rss feed can contain tags, e.g. <em>
            article.title = headline.text

        modified = soup.find(attrs={"data-modified": True})
        if modified:
            modified_date = datetime.strptime(
                modified["data-modified"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            if (not self.pub_date) or modified_date > self.pub_date:
                self.pub_date = modified_date
                self.title = self._format_title(_name, modified_date)

        published = soup.find(attrs={"data-published": True})
        if published:
            published_date = datetime.strptime(
                published["data-published"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            article.utctime = published_date
            if (not self.pub_date) or published_date > self.pub_date:
                self.pub_date = published_date
                self.title = self._format_title(_name, published_date)

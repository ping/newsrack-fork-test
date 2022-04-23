#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2015, Kovid Goyal <kovid at kovidgoyal.net>
from __future__ import unicode_literals
from datetime import datetime, timezone
import json
import re

from calibre.web.feeds.news import BasicNewsRecipe
from calibre.ebooks.BeautifulSoup import BeautifulSoup


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
    pub_ele.append(f"{published_date:%H:%M%p, %-d %B, %Y}")
    meta.append(pub_ele)
    if article.get("dateModified"):
        modified_date = datetime.strptime(
            article["dateModified"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        upd_ele = new_soup.new_tag("span", attrs={"class": "modified-dt"})
        upd_ele["data-modified"] = f"{modified_date:%Y-%m-%dT%H:%M:%SZ}"
        upd_ele.append(f"Updated {modified_date:%H.%M%p, %-d %B, %Y}")
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
            mobj = re.match("HED(?P<level>\d)", item.get("headingSubtype", ""))
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


class TheAtlanticMagazine(BasicNewsRecipe):

    title = "The Atlantic Magazine"
    description = "Current affairs and politics focussed on the US"
    INDEX = "https://www.theatlantic.com/magazine/"

    __author__ = "Kovid Goyal"
    language = "en"
    encoding = "utf-8"

    masthead_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/The_Atlantic_magazine_logo.svg/1200px-The_Atlantic_magazine_logo.svg.png"

    no_stylesheets = True
    remove_javascript = True
    remove_empty_feeds = True
    compress_news_images = True
    scale_news_images = (800, 800)
    scale_news_images_to_device = False  # force img to be resized to scale_news_images
    timeout = 20
    timefmt = "%-d, %b %Y"
    pub_date = None  # custom publication date

    remove_attributes = ["style"]
    extra_css = """
    .issue { font-weight: bold; margin-bottom: 0.2rem; }
    .headline { font-size: 1.8rem; margin-bottom: 0.5rem; }
    .sub-headline { font-size: 1.4rem; margin-top: 0; margin-bottom: 0.5rem; }
    .article-meta {  margin-top: 1rem; margin-bottom: 1rem; }
    .article-meta .author { font-weight: bold; color: #444; display: inline-block; }
    .article-meta .published-dt { display: inline-block; margin-left: 0.5rem; }
    .article-meta .modified-dt { display: block; margin-top: 0.2rem; font-style: italic; }
    .caption { font-size: 0.8rem; margin-top: 0.2rem; margin-bottom: 0.5rem; }
    .article-img { display: block; max-width: 100%; height: auto; }
    h3 span.smallcaps { font-weight: bold; }
    p span.smallcaps { text-transform: uppercase; }
    blockquote { font-size: 1.25rem; margin-left: 0; text-align: center; }
    div.related-content { margin-left: 0.5rem; color: #444; font-style: italic; }
    """

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
        return soup

    def publication_date(self):
        return self.pub_date

    def populate_article_metadata(self, article, soup, _):
        # modified = soup.find(attrs={"data-modified": True})
        # if modified:
        #     modified_date = datetime.strptime(
        #         modified["data-modified"], "%Y-%m-%dT%H:%M:%SZ"
        #     ).replace(tzinfo=timezone.utc)
        #     if (not self.pub_date) or modified_date > self.pub_date:
        #         self.pub_date = modified_date

        published = soup.find(attrs={"data-published": True})
        if published:
            published_date = datetime.strptime(
                published["data-published"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            article.utctime = published_date
            if (not self.pub_date) or published_date > self.pub_date:
                self.pub_date = published_date

    def parse_index(self):
        soup = self.index_to_soup(self.INDEX)
        figure = soup.find("figure", id="cover-image")
        if figure is not None:
            img = figure.find("img", src=True)
            if img:
                self.cover_url = img["src"]
        issue_ele = soup.find("h1", attrs={"class": "c-section-header__title"})
        self.title = f"The Atlantic Magazine: {issue_ele.text.title()}"
        current_section, current_articles = "Cover Story", []
        feeds = []
        for div in soup.findAll(
            "div",
            attrs={
                "class": lambda x: x
                and set(x.split()).intersection({"top-sections", "bottom-sections"})
            },
        ):
            for h2 in div.findAll("h2", attrs={"class": True}):
                cls = h2["class"]
                if hasattr(cls, "split"):
                    cls = cls.split()
                if "section-name" in cls:
                    if current_articles:
                        feeds.append((current_section, current_articles))
                    current_articles = []
                    current_section = self.tag_to_string(h2)
                    self.log("\nFound section:", current_section)
                elif "hed" in cls:
                    title = self.tag_to_string(h2)
                    a = h2.findParent("a", href=True)
                    if a is None:
                        continue
                    url = a["href"]
                    if url.startswith("/"):
                        url = "https://www.theatlantic.com" + url
                    li = a.findParent(
                        "li",
                        attrs={"class": lambda x: x and "article" in x.split()},
                    )
                    desc = ""
                    dek = li.find(attrs={"class": lambda x: x and "dek" in x.split()})
                    if dek is not None:
                        desc += self.tag_to_string(dek)
                    byline = li.find(
                        attrs={"class": lambda x: x and "byline" in x.split()}
                    )
                    if byline is not None:
                        desc += " -- " + self.tag_to_string(byline)
                    self.log("\t", title, "at", url)
                    if desc:
                        self.log("\t\t", desc)
                    current_articles.append(
                        {"title": title, "url": url, "description": desc}
                    )
        if current_articles:
            feeds.append((current_section, current_articles))
        return feeds

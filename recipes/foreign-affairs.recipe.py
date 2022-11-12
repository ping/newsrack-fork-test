# Original at https://github.com/kovidgoyal/calibre/blob/962fc18be18cccb6fc70d29a086f16a7e0a36519/recipes/foreignaffairs.recipe
import json
import re
from datetime import datetime

import mechanize

from calibre.web.feeds.news import BasicNewsRecipe, classes
from calibre.ebooks.BeautifulSoup import BeautifulSoup

_name = "Foreign Affairs"


def get_issue_data(br, log, node_id="1126213", year="2020", volnum="99", issue_vol="5"):
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.foreignaffairs.com",
        "Referer": "https://www.foreignaffairs.com",
    }

    def make_query(**kwds):
        size = kwds.pop("size", 1)
        is_filter = kwds.pop("filter", None)
        if is_filter:
            q = {"filter": [{"terms": {k: v}} for k, v in kwds.items()]}
        else:
            q = {"must": [{"term": {k: v}} for k, v in kwds.items()]}
        return {
            "from": 0,
            "post_filter": {"bool": q},
            "_source": {
                "includes": [
                    "nid",
                    "path",
                    "title",
                    "field_subtitle",
                    "field_display_authors",
                    "fa_node_type_or_subtype",
                    "field_issue_sspecial_articles__nid",
                    "field_issue_sspecial_header",
                ]
            },
            "query": {"match_all": {}},
            "sort": [{"field_sequence": "asc"}, {"fa_normalized_date": "desc"}],
            "size": size,
        }

    def get_data(data):
        search_url = "https://www.foreignaffairs.com/fa-search.php"
        req = mechanize.Request(
            url=search_url, data=json.dumps(data), headers=headers, method="POST"
        )
        res = br.open(req)
        data = json.loads(res.read())
        return data["hits"]["hits"]

    feeds = []

    def as_article(source):
        title = BeautifulSoup(source["title"][0]).get_text()
        desc = ""
        fs = source.get("field_subtitle")
        if fs:
            desc = fs[0]
        aus = source.get("field_display_authors")
        if aus:
            desc += " By " + aus[0]
        url = "https://www.foreignaffairs.com" + source["path"][0]
        return {"title": title, "description": desc, "url": url}

    issue_data = get_data(
        make_query(
            fa_node_type_or_subtype="Issue",
            field_issue_volume=issue_vol,
            field_issue_year=year,
            field_issue_volume_number=volnum,
        )
    )[0]["_source"]

    if "field_issue_sspecial_articles__nid" in issue_data:
        main_sec_title = issue_data["title"][0]
        main_sec_nids = issue_data["field_issue_sspecial_articles__nid"]
        articles_data = get_data(
            make_query(nid=main_sec_nids, filter=True, size=len(main_sec_nids))
        )
        articles = []
        log(main_sec_title)
        for entry in articles_data:
            source = entry["_source"]
            articles.append(as_article(source))
            log("\t", articles[-1]["title"], articles[-1]["url"])
        feeds.append((main_sec_title, articles))

    articles_data = get_data(make_query(field_issue__nid=node_id, size=50))
    ans = {}
    for entry in articles_data:
        source = entry["_source"]
        section = source["fa_node_type_or_subtype"][0]
        ans.setdefault(section, []).append(as_article(source))
    for sectitle in sorted(ans):
        articles = ans[sectitle]
        log(sectitle)
        if articles:
            for art in articles:
                log("\t", art["title"], art["url"])
            feeds.append((sectitle, articles))

    return feeds


class ForeignAffairsRecipe(BasicNewsRecipe):
    title = _name
    __author__ = "Kovid Goyal"
    language = "en"
    publisher = "Council on Foreign Relations https://www.foreignaffairs.com/magazine"
    category = "USA, Foreign Affairs"
    description = "The leading forum for serious discussion of American foreign policy and international affairs. https://www.foreignaffairs.com/magazine"
    masthead_url = (
        "https://www.foreignaffairs.com/themes/fa/assets/images/icon__FA-logotype.png"
    )
    encoding = "utf-8"
    publication_type = "magazine"
    INDEX = "https://www.foreignaffairs.com/magazine"

    no_stylesheets = True
    remove_javascript = True
    needs_subscription = "optional"
    ignore_duplicate_articles = {"title", "url"}
    remove_empty_feeds = True
    remove_attributes = ["style"]

    timefmt = ""
    pub_date = None

    keep_only_tags = [
        classes("article-header article-body article-lead-image article-body-text"),
    ]
    remove_tags = [
        classes("loading-indicator paywall article-footer article-tools"),
        dict(name=["svg"]),
    ]

    extra_css = """
    h1.article-title { font-size: 1.8rem; margin-bottom: 0.4rem; }
    h2.article-subtitle { font-size: 1.2rem; font-style: italic; margin-bottom: 1rem; }
    .article-byline { margin-bottom: 1rem; color: #444; }
    .article-inline-img-block img {
        display: block; margin-bottom: 0.3rem; max-width: 100%; height: auto;
        box-sizing: border-box;
    }
    .article-inline-img-block--figcaption { font-size: 0.8rem; }
    blockquote.internal-blockquote { font-size: 1.25rem; margin-left: 0; text-align: center; }
    """

    def publication_date(self):
        return self.pub_date

    def parse_index(self):
        soup = self.index_to_soup(self.INDEX)
        # get dates
        date = re.split(r"\s\|\s", self.tag_to_string(soup.head.title.string))[0]
        self.title = "{}: {}".format(_name, date)
        # self.timefmt = " [%s]" % date
        link = soup.find("link", rel="canonical", href=True)["href"]
        year, vol_num, issue_vol = link.split("/")[-3:]
        self.cover_url = soup.find(**classes("subscribe-callout-image"))[
            "data-src"
        ].split("|")[-1]
        self.cover_url = self.cover_url.split("?")[0].replace(
            "_webp_issue_small_2x", "_webp_issue_large_2x"
        )
        cls = soup.find("body")["class"]
        if isinstance(cls, (list, tuple)):
            cls = " ".join(cls)
        node_id = re.search(r"\bpage-node-(\d+)\b", cls).group(1)
        br = self.cloned_browser
        feeds = get_issue_data(br, self.log, node_id, year, vol_num, issue_vol)
        return feeds

    def preprocess_html(self, soup):
        modified_meta = soup.find("meta", attrs={"property": "article:modified_time"})
        if modified_meta:
            # Example: 2022-09-06T07:34:24-04:00
            modified_dt = datetime.fromisoformat(modified_meta["content"])
            if not self.pub_date or modified_dt > self.pub_date:
                self.pub_date = modified_dt
        for attr in ("ng-src", "data-blazy", "data-src"):
            for img in soup.findAll("img", attrs={attr: True}):
                img["src"] = img[attr]
        author_info = soup.find(id="author-info")
        if author_info:
            author_info.name = "div"
            for li in author_info.find_all("li"):
                li.name = "p"
        return soup

    def get_browser(self):
        def select_form(form):
            return form.attrs.get("id", None) == "fa-user-login-form"

        br = BasicNewsRecipe.get_browser(self)
        if self.username is not None and self.password is not None:
            br.open("https://www.foreignaffairs.com/user/login")
            br.select_form(predicate=select_form)
            br.form["name"] = self.username
            br.form["pass"] = self.password
            br.submit()
        return br

/*
Copyright (c) 2022 https://github.com/ping/

This software is released under the GNU General Public License v3.0
https://opensource.org/licenses/GPL-3.0
*/


/*
    To maintain compat with the Kindle browser:
    - no `let`, `const`
    - no `Intl`
    - no `Object.keys`, `Object.values`
*/
(function () {

    var searchInfo = document.getElementById("search-info");
    var searchTextField = document.getElementById("search-text");
    var searchButton = document.getElementById("search-button");
    searchTextField.disabled = true;
    searchButton.disabled = true;

    // in miliseconds
    var units = {
        year: 24 * 60 * 60 * 1000 * 365,
        month: 24 * 60 * 60 * 1000 * 365 / 12,
        day: 24 * 60 * 60 * 1000,
        hour: 60 * 60 * 1000,
        minute: 60 * 1000,
        second: 1000
    };

    var rtf = null;
    if (typeof (Intl) !== "undefined") {
        rtf = new Intl.RelativeTimeFormat("en", {numeric: "auto"});
    }

    function getRelativeTime(d1, d2) {
        d2 = (typeof d2 !== "undefined") ? d2 : new Date();
        var elapsed = d1 - d2;
        // "Math.abs" accounts for both "past" & "future" scenarios
        for (var u in units) {
            if (Math.abs(elapsed) > units[u] || u === "second") {
                var diff = Math.round(elapsed / units[u]);
                if (typeof (Intl) !== "undefined") {
                    return rtf.format(diff, u);
                }
                // manually construct format
                var unit = u;
                if (Math.abs(diff) > 1) {
                    unit = u + "s";
                }
                if (diff < 0) {
                    return Math.abs(diff) + " " + unit + " ago"
                } else {
                    return "in " + diff + " " + unit;
                }
            }
        }
    }

    function toggleDateDisplay(target, isRelative) {
        var publishedDate = new Date(parseInt(target.attributes["data-pub-date"].value));
        var tags = "";
        if (typeof(target.parentElement.dataset["tags"]) !== "undefined"
            && target.parentElement.dataset["tags"].trim().length > 0) {
            tags = " " + '<span class="tags">' + target.parentElement.dataset["tags"] + "</span>";
        }
        target.title = publishedDate.toLocaleString();
        if (isRelative) {
            target.innerHTML = "Published " + getRelativeTime(publishedDate) + tags;
        } else {
            target.innerHTML = "Published " + publishedDate.toLocaleString() + tags;
        }
    }

    var refreshedDateEle = document.getElementById("refreshed_dt");
    var refreshedDate = new Date(parseInt(refreshedDateEle.attributes["data-refreshed-date"].value));
    refreshedDateEle.title = refreshedDate.toLocaleString();
    refreshedDateEle.innerHTML = getRelativeTime(refreshedDate);

    // toggle pub date display
    var pudDateElements = document.querySelectorAll("[data-pub-date]");
    for (var i = 0; i < pudDateElements.length; i++) {
        var pubDateEle = pudDateElements[i];
        toggleDateDisplay(pubDateEle, true);

        pubDateEle.addEventListener("pointerenter", function (event) {
            toggleDateDisplay(event.target, false);
        }, false);

        pubDateEle.addEventListener("pointerleave", function (event) {
            toggleDateDisplay(event.target, true);
        }, false);
    }

    // toggle collapsible toc for publication
    var accordionBtns = document.querySelectorAll(".pub-date");
    for (var i = 0; i < accordionBtns.length; i++) {
        var accordion = accordionBtns[i];
        accordion.onclick = function () {
            this.classList.toggle("is-open");
            this.nextElementSibling.classList.toggle("hide");   // content
            var slug = this.parentElement.id;
            if (this.nextElementSibling.childElementCount <= 0 && RECIPE_DESCRIPTIONS[slug] !== undefined) {
                if (RECIPE_COVERS[slug] !== undefined) {
                    this.nextElementSibling.innerHTML = '<p class="cover">'
                        + '<a href="' + RECIPE_COVERS[slug] + '">'
                        + '<img alt="Cover" src="'
                        + RECIPE_COVERS[slug] + '"></a></p>';
                }
                this.nextElementSibling.innerHTML += RECIPE_DESCRIPTIONS[slug];
            }
        };
    }

    // toggle publications listing for category
    var categoryButtons = document.querySelectorAll("h2.category");
    for (var i = 0; i < categoryButtons.length; i++) {
        var category = categoryButtons[i];
        category.onclick = function (e) {
            if (e.target.nodeName.toLowerCase() === "a") {
                // don't do toggle action if it's a link
                return;
            }
            this.parentElement.classList.toggle("is-open");
            this.nextElementSibling.classList.toggle("hide");   // content
        };
    }

    var catCloseShortcuts = document.querySelectorAll("[data-click-target]");
    for (var i = 0; i < catCloseShortcuts.length; i++) {
        var shortcut = catCloseShortcuts[i];
        shortcut.onclick = function (e) {
            e.preventDefault();
            var cat = document.getElementById(e.target.dataset["clickTarget"]);
            cat.parentElement.classList.toggle("is-open");
            cat.nextElementSibling.classList.toggle("hide");    // content
            if (!cat.parentElement.classList.contains("is-open")) {
                cat.parentElement.scrollIntoView();
           }
        };
    }

    window.addEventListener("DOMContentLoaded", function() {
        if (typeof(lunr) !== "undefined") {
            var ogPlaceholderText = searchTextField.placeholder;
            searchTextField.placeholder = "Indexing search...";
            var periodicalsEles = document.querySelectorAll("ol.books > li");

            function resetSearch() {
                for (var i = 0; i < periodicalsEles.length; i++) {
                    var periodical = periodicalsEles[i];
                    periodical.classList.remove("hide");
                    var pubDate = periodical.querySelector(".pub-date");
                    if (pubDate) {
                        pubDate.classList.remove("is-open");
                    }
                    var contents = periodical.querySelector(".contents");
                    if (contents) {
                        contents.classList.add("hide");
                    }
                }
            }

            var idx = lunr(function () {
                this.field("title");
                this.field("articles");
                this.field("tags");
                this.field("category");

                for (var i = 0; i < periodicalsEles.length; i++) {
                    var periodical = periodicalsEles[i];
                    var id = periodical["id"];
                    var catName = periodical.dataset["catName"]
                    var title = periodical.querySelector(".title").textContent;
                    var articlesEles = periodical.querySelectorAll(".contents > ul > li");
                    var articles = [];
                    for (var j = 0; j < articlesEles.length; j++) {
                        var articleEle = articlesEles[j];
                        articles.push(articleEle.textContent);
                    }
                    this.add({
                        "id": id,
                        "title": title,
                        "articles": articles.join(" "),
                        "tags": periodical.dataset["tags"],
                        "category": catName
                    });
                }
                searchTextField.placeholder = ogPlaceholderText;
                searchTextField.disabled = false;
                searchButton.disabled = false;
            });

            // unhide everything when search field is cleared
            document.getElementById("search-text").onchange = function(e) {
                if (this.value.trim().length > 0) {
                    return;
                }
                searchInfo.innerText = "";
                resetSearch();
            };

            // search form submitted
            document.getElementById("search-form").onsubmit = function (e) {
                e.preventDefault();
                searchInfo.innerText = "";
                var searchText = document.getElementById("search-text").value.trim();
                if (searchText.length < 3) {
                    searchInfo.innerText = "Search text must be at least 3 characters long.";
                    return;
                }

                var results = idx.search(searchText);
                if (results.length <= 0) {
                    searchInfo.innerText = "No results.";
                    resetSearch();
                    return;
                }

                var bookIds = []
                var resultsSumm = {}
                for (var i = 0; i < results.length; i++) {
                    bookIds.push(results[i].ref);
                    var fields = []
                    var metadata = results[i].matchData.metadata;
                    for (var key in metadata) {
                        for (var kkey in metadata[key]) {
                            fields.push(kkey);
                        }
                    }
                    resultsSumm[results[i].ref] = fields;

                }
                for (var i = 0; i < periodicalsEles.length; i++) {
                    var periodical = periodicalsEles[i];
                    var id = periodical["id"];

                    if (bookIds.indexOf(id) < 0) {
                        periodical.classList.add("hide");
                        continue;
                    }
                    periodical.classList.remove("hide");
                    var cat = document.getElementById(periodical.dataset["catId"]);
                    if (cat) {
                        if (!cat.classList.contains("is-open")) {
                            cat.classList.add("is-open");
                        }
                        if (cat.nextElementSibling.classList.contains("hide")) {
                            cat.nextElementSibling.classList.remove("hide");
                        }
                    }
                    var pubDateEle = periodical.querySelector(".pub-date");
                    var contentsEle = periodical.querySelector(".contents");
                    if (resultsSumm[id].indexOf("articles") >= 0) {
                        pubDateEle.classList.add("is-open");
                        if (contentsEle) {
                            contentsEle.classList.remove("hide");
                        }
                        periodical.querySelector(".contents").classList.remove("hide");
                    } else {
                        pubDateEle.classList.remove("is-open");
                        if (contentsEle) {
                            contentsEle.classList.add("hide");
                        }
                    }

                }
            };
        }
    });

})();
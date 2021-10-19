from fastapi import FastAPI, Header
import requests
import secrets
from bs4 import BeautifulSoup
import re
import os
from starlette.requests import Request
from starlette.responses import PlainTextResponse

app = FastAPI()

@app.middleware("http")
async def check_rapidAPI_proxy_header(request: Request, call_next):
    # Check if server knows about valid "secret"
    secret_header = os.environ.get("PROXY_SECRET", None)
    if secret_header:
        headers = request.headers
        # If the header is missing, or does not match expected value
        # Reject the request altogether
        if (
            "X-RapidAPI-Proxy-Secret" not in headers
            or secrets.compare_digest(headers["X-RapidAPI-Proxy-Secret"], secret_header)
        ):
            return PlainTextResponse(
                "Direct access to the API not allowed", status_code=403
            )

    response = await call_next(request)
    return response


def get_archive_url(search_url, timestamp):
    timestamp = timestamp.replace("-", "").replace(" ", "").replace(":", "")
    url = (
        f"https://archive.org/wayback/available?url={search_url}&timestamp={timestamp}"
    )
    response = requests.get(url)
    arch_url = response.json()["archived_snapshots"]
    if arch_url:
        return arch_url["closest"]["url"]
    else:
        return None


def get_regexp_pattern(keywords, include):
    keywords_ext = [k.lower().replace(".", "\.") for k in keywords]
    if include == "all":
        regexp_pattern = "".join([f"(?=.*{k})" for k in keywords_ext])
    elif include == "one":
        regexp_pattern = "|".join(keywords_ext)
    else:
        raise ValueError(f"Unknown include option {include}")
    return regexp_pattern


def get_historical_articles(
    source_urls_map, timestamp, keywords, include, sources=None
):

    if sources is None:
        sources = source_urls_map.keys()

    # get regexp pattern
    regexp_pattern = get_regexp_pattern(keywords, include)

    output = dict()
    for source in sources:

        source_regexp = re.compile(source_urls_map[source.lower()]["regexp"])

        # get archive url
        source_url = source_urls_map[source.lower()]["link"]
        archive_url = get_archive_url(source_url, timestamp)

        # get archive response
        output[source] = dict()
        if archive_url is None:
            continue

        # take exact timestep
        timestep = archive_url.split("http://web.archive.org/web/")[1].split("/")[0]
        output[source]["timestep"] = timestep
        output[source]["articles"] = []

        # request and parse
        archive_response = requests.get(archive_url)
        soup = BeautifulSoup(archive_response.text, "html.parser")
        titles = set()
        for anchor in soup.find_all(
            "a",
            text=re.compile(regexp_pattern, re.IGNORECASE),
            href=re.compile(timestep + "/"),
        ):

            link = anchor.get("href").split(timestep + "/")[1]
            title = anchor.get_text()
            if title in titles or not source_regexp.search(link):
                continue
            v = {
                "link": link,
                "title": title,
            }
            output[source]["articles"].append(v)
            titles.add(title)
    return output


def main(timestamp, keywords, include, sources):
    # to do: remove hardcoded stuff
    source_urls_map = {
        "guardian": {  # time-indexed
            "link": "theguardian.com/international",
            "regexp": "theguardian.com/(.*)/(.*)/(.*)/(.*)/(.*)$",
        },
        "time": {
            "link": "time.com",
            "regexp": "time.com/([0-9]*)/(.*)/$",
        },
        "economist": {  # time-indexed
            "link": "economist.com",
            "regexp": "economist.com/(.*)/(.*)/(.*)/(.*)/(.*)$",
        },
        "reuters": {
            "link": "reuters.com",
            "regexp": "reuters.com/article/(.*)/(.*)",
        },
        # "bbc": "bbc.com",
        # "cnn": "edition.cnn.com",
        # "bloomberg": "bloomberg.com/europe",
    }
    out = get_historical_articles(
        source_urls_map, timestamp, keywords, include, sources
    )
    return out


@app.get("/{source}/{timestamp}/")
async def root(source, timestamp, keywords: str = "", include: str = "all"):

    keywords = keywords.split(",")
    out = main(timestamp, keywords, include, [source])
    return out

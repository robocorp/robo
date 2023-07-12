from urllib.parse import urljoin


def url_join(*parts: str) -> str:
    url = ""
    for part in parts:
        url = urljoin(url, part.strip("/") + "/")
    return url

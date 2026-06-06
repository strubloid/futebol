from urllib.parse import urlparse


class UrlValidator:
    def is_valid(self, url: str) -> bool:
        parsed = urlparse(url.strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

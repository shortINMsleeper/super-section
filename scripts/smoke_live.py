from __future__ import annotations

import re
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ASSETS = [f"assets/ashikaga-{i:02d}.jpg" for i in range(1, 5)]
FORBIDDEN_SECTION_LABELS = {"music", "pv", "video"}


class HeadingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._heading: str | None = None
        self._parts: list[str] = []
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading = tag
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._heading:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._heading:
            text = " ".join("".join(self._parts).split()).strip().lower()
            if text:
                self.headings.append(text)
            self._heading = None
            self._parts = []


def fetch(url: str, *, attempts: int = 8) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(url, headers={"User-Agent": "super-section-live-smoke/1.0"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}: {url}")
                return response.read(), response.headers.get_content_type()
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(min(2 ** (attempt - 1), 12))
    raise RuntimeError(f"取得に失敗しました: {url}: {last_error}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python scripts/smoke_live.py <base-url>", file=sys.stderr)
        return 2

    base_url = sys.argv[1].rstrip("/") + "/"
    errors: list[str] = []

    try:
        body, content_type = fetch(base_url)
    except RuntimeError as exc:
        print(f"LIVE E2E: FAIL\n- {exc}")
        return 1

    if content_type not in {"text/html", "application/xhtml+xml"}:
        errors.append(f"トップページのContent-TypeがHTMLではありません: {content_type}")

    text = body.decode("utf-8", errors="replace")
    lowered = text.lower()
    if "アシカガ" not in text or "ashikaga" not in lowered:
        errors.append("公開ページで『アシカガ / ASHIKAGA』を確認できません")

    parser = HeadingParser()
    parser.feed(text)
    for heading in parser.headings:
        tokens = re.sub(r"[^a-z0-9]+", " ", heading).strip().split()
        if any(token in FORBIDDEN_SECTION_LABELS for token in tokens):
            errors.append(f"禁止セクション見出しを公開ページで検出しました: {heading}")

    for asset in ASSETS:
        url = urljoin(base_url, asset)
        try:
            data, asset_type = fetch(url)
            if not data:
                errors.append(f"公開画像が空です: {asset}")
            if not asset_type.startswith("image/"):
                errors.append(f"公開画像のContent-Typeが不正です: {asset}: {asset_type}")
        except RuntimeError as exc:
            errors.append(str(exc))

    if errors:
        print("LIVE E2E: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"LIVE E2E: PASS — {base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

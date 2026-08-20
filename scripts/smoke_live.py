from __future__ import annotations

import re
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

IMAGE_ASSETS = [f"assets/ashikaga-{i:02d}.avif" for i in range(1, 5)]
SCRIPT_ASSET = "assets/site.js"
FORBIDDEN_SECTION_LABELS = {"music", "pv", "video"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._heading: str | None = None
        self._parts: list[str] = []
        self.headings: list[str] = []
        self.csp: str | None = None
        self.referrer: str | None = None
        self.scripts: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "meta":
            if data.get("http-equiv", "").lower() == "content-security-policy":
                self.csp = data.get("content")
            if data.get("name", "").lower() == "referrer":
                self.referrer = data.get("content")
        if tag == "script":
            self.scripts.append(data.get("src"))
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

    parser = PageParser()
    parser.feed(text)
    if not parser.csp:
        errors.append("公開ページにContent-Security-Policy metaがありません")
    else:
        lowered_csp = parser.csp.lower()
        for required in ("default-src 'none'", "script-src 'self'", "connect-src 'none'", "object-src 'none'"):
            if required not in lowered_csp:
                errors.append(f"公開ページのCSPが不足しています: {required}")
    if parser.referrer != "no-referrer":
        errors.append("公開ページのReferrer Policyがno-referrerではありません")
    if parser.scripts != [SCRIPT_ASSET]:
        errors.append(f"公開ページのscript参照が想定外です: {parser.scripts}")

    for heading in parser.headings:
        tokens = re.sub(r"[^a-z0-9]+", " ", heading).strip().split()
        if any(token in FORBIDDEN_SECTION_LABELS for token in tokens):
            errors.append(f"禁止セクション見出しを公開ページで検出しました: {heading}")

    for asset in IMAGE_ASSETS:
        url = urljoin(base_url, asset)
        try:
            data, asset_type = fetch(url)
            if not data:
                errors.append(f"公開画像が空です: {asset}")
            if not asset_type.startswith("image/"):
                errors.append(f"公開画像のContent-Typeが不正です: {asset}: {asset_type}")
        except RuntimeError as exc:
            errors.append(str(exc))

    try:
        script_data, script_type = fetch(urljoin(base_url, SCRIPT_ASSET))
        if not script_data:
            errors.append("公開JavaScriptが空です")
        if script_type not in {"text/javascript", "application/javascript"}:
            errors.append(f"公開JavaScriptのContent-Typeが不正です: {script_type}")
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

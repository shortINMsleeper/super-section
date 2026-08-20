from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
REQUIRED_ASSETS = [ROOT / "assets" / f"ashikaga-{i:02d}.avif" for i in range(1, 5)]
REQUIRED_ASSETS.append(ROOT / "assets" / "site.js")
FORBIDDEN_PATTERNS = {
    "eval(": r"\beval\s*\(",
    "innerHTML": r"\.innerHTML\b",
    "document.write": r"\bdocument\.write\s*\(",
    "javascript: URL": r"javascript\s*:",
}
FORBIDDEN_SECTION_LABELS = {"music", "pv", "video"}
REQUIRED_CSP_DIRECTIVES = {
    "default-src": "'none'",
    "img-src": "'self'",
    "script-src": "'self'",
    "script-src-attr": "'none'",
    "connect-src": "'none'",
    "object-src": "'none'",
    "frame-src": "'none'",
    "base-uri": "'none'",
    "form-action": "'none'",
}


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[tuple[str | None, str | None]] = []
        self.scripts: list[str | None] = []
        self.external_resources: list[str] = []
        self.section_labels: list[str] = []
        self._capture_heading: str | None = None
        self._heading_text: list[str] = []
        self.lang: str | None = None
        self.has_viewport = False
        self.csp: str | None = None
        self.referrer_policy: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "html":
            self.lang = data.get("lang")
        if tag == "meta":
            name = data.get("name", "").lower()
            http_equiv = data.get("http-equiv", "").lower()
            if name == "viewport":
                self.has_viewport = bool(data.get("content"))
            if name == "referrer":
                self.referrer_policy = data.get("content")
            if http_equiv == "content-security-policy":
                self.csp = data.get("content")
        if tag == "img":
            self.images.append((data.get("src"), data.get("alt")))
        if tag == "script":
            self.scripts.append(data.get("src"))
        if tag in {"script", "link", "img", "source"}:
            key = "href" if tag == "link" else "src"
            ref = data.get(key)
            if ref and urlparse(ref).scheme in {"http", "https"}:
                self.external_resources.append(ref)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._capture_heading = tag
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        if self._capture_heading:
            self._heading_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._capture_heading:
            text = " ".join("".join(self._heading_text).split()).strip().lower()
            if text:
                self.section_labels.append(text)
            self._capture_heading = None
            self._heading_text = []


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def parse_csp(policy: str) -> dict[str, str]:
    directives: dict[str, str] = {}
    for item in policy.split(";"):
        item = item.strip()
        if not item:
            continue
        name, _, value = item.partition(" ")
        directives[name.lower()] = value.strip()
    return directives


def main() -> int:
    errors: list[str] = []

    if not INDEX.is_file():
        fail(errors, "index.html がありません")
        return report(errors)

    for asset in REQUIRED_ASSETS:
        if not asset.is_file():
            fail(errors, f"必須アセットがありません: {asset.relative_to(ROOT)}")
        elif asset.stat().st_size == 0:
            fail(errors, f"アセットが空です: {asset.relative_to(ROOT)}")

    text = INDEX.read_text(encoding="utf-8")
    lowered = text.lower()

    if "アシカガ" not in text or "ashikaga" not in lowered:
        fail(errors, "人物名『アシカガ / ASHIKAGA』が維持されていません")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            fail(errors, f"危険なパターンを検出しました: {label}")

    parser = SiteParser()
    parser.feed(text)

    if parser.lang != "ja":
        fail(errors, "<html lang=\"ja\"> が設定されていません")
    if not parser.has_viewport:
        fail(errors, "viewport meta がありません")
    if parser.referrer_policy != "no-referrer":
        fail(errors, "Referrer Policy が no-referrer ではありません")

    if not parser.csp:
        fail(errors, "Content-Security-Policy meta がありません")
    else:
        directives = parse_csp(parser.csp)
        for name, expected in REQUIRED_CSP_DIRECTIVES.items():
            if directives.get(name) != expected:
                fail(errors, f"CSP directive が不足または不正です: {name} {expected}")
        if "'unsafe-inline'" in directives.get("script-src", ""):
            fail(errors, "CSP script-src に unsafe-inline を許可しないでください")
        if "'unsafe-eval'" in directives.get("script-src", ""):
            fail(errors, "CSP script-src に unsafe-eval を許可しないでください")

    for src, alt in parser.images:
        if alt is None or not alt.strip():
            fail(errors, f"alt が空の画像があります: {src or '(dynamic image)'}")
        if not src:
            continue
        parsed = urlparse(src)
        if not parsed.scheme and not src.startswith(("data:", "#")):
            target = ROOT / src.split("?", 1)[0].split("#", 1)[0]
            if not target.is_file():
                fail(errors, f"HTMLから参照された画像がありません: {src}")

    for src in parser.scripts:
        if not src:
            fail(errors, "インライン script を検出しました。CSP維持のため外部同一オリジンファイルへ移してください")
            continue
        parsed = urlparse(src)
        if not parsed.scheme and not src.startswith(("data:", "#")):
            target = ROOT / src.split("?", 1)[0].split("#", 1)[0]
            if not target.is_file():
                fail(errors, f"HTMLから参照されたscriptがありません: {src}")

    if parser.external_resources:
        for ref in parser.external_resources:
            fail(errors, f"外部HTTP(S)リソース依存を検出しました: {ref}")

    for heading in parser.section_labels:
        normalized = re.sub(r"[^a-z0-9]+", " ", heading).strip().split()
        if any(token in FORBIDDEN_SECTION_LABELS for token in normalized):
            fail(errors, f"禁止セクション見出しを検出しました: {heading}")

    return report(errors)


def report(errors: list[str]) -> int:
    if errors:
        print("STATIC QUALITY GATE: FAIL")
        for item in errors:
            print(f"- {item}")
        return 1
    print("STATIC QUALITY GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

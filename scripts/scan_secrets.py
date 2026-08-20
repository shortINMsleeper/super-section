from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str
    line: int | None = None


TEXT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("OpenAI-style API key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("GitHub classic token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Bearer credential", re.compile(r"(?i)\bauthorization\s*[:=]\s*[\"']?Bearer\s+[A-Za-z0-9._~+/-]{20,}")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)

FORBIDDEN_BASENAMES = {
    ".env",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "service-account.json",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


def git_tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return [item.decode("utf-8", errors="surrogateescape") for item in result.stdout.split(b"\0") if item]


def git_blob(path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f":{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def path_findings(path: str) -> list[Finding]:
    normalized = path.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1]
    lowered = base.lower()
    findings: list[Finding] = []

    if lowered in FORBIDDEN_BASENAMES or lowered.startswith(".env."):
        if lowered != ".env.example":
            findings.append(Finding(path, "forbidden secret filename"))

    if any(lowered.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        findings.append(Finding(path, "forbidden credential/private-key file"))

    return findings


def text_findings(path: str, data: bytes) -> list[Finding]:
    if b"\0" in data:
        return []

    text = data.decode("utf-8", errors="ignore")
    findings: list[Finding] = []
    for rule, pattern in TEXT_RULES:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(Finding(path, rule, line))
    return findings


def scan_repository() -> list[Finding]:
    findings: list[Finding] = []
    for path in git_tracked_files():
        findings.extend(path_findings(path))
        try:
            findings.extend(text_findings(path, git_blob(path)))
        except subprocess.CalledProcessError:
            findings.append(Finding(path, "could not read tracked blob"))
    return findings


def self_test() -> int:
    samples = [
        ("OpenAI-style API key", "sk-" + "A" * 24),
        ("GitHub classic token", "ghp_" + "B" * 24),
        ("GitHub fine-grained token", "github_pat_" + "C" * 24),
        ("AWS access key", "AKIA" + "D" * 16),
        ("Google API key", "AIza" + "E" * 35),
        ("Bearer credential", "Authorization: Bearer " + "F" * 24),
        ("Private key", "-----BEGIN PRIVATE KEY-----"),
    ]

    errors: list[str] = []
    for expected, sample in samples:
        rules = {item.rule for item in text_findings("fixture.txt", sample.encode())}
        if expected not in rules:
            errors.append(f"self-test missed {expected}")

    if path_findings("config/.env") == []:
        errors.append("self-test missed .env")
    if path_findings("config/.env.example"):
        errors.append("self-test rejected .env.example")
    if path_findings("keys/server.pem") == []:
        errors.append("self-test missed private-key file")

    if errors:
        print("SECRET SCAN SELF-TEST: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("SECRET SCAN SELF-TEST: PASS")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    findings = scan_repository()
    if findings:
        print("SECRET LEAKAGE GATE: FAIL")
        for finding in findings:
            location = f":{finding.line}" if finding.line is not None else ""
            # Never print the matched secret itself.
            print(f"- {finding.path}{location} — {finding.rule}")
        return 1

    print("SECRET LEAKAGE GATE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

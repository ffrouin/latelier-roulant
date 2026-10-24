#!/usr/bin/env python3
"""Check L'Atelier Roulant runtime dependencies without exposing secrets."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse


COMMANDS = {
    "qrencode": "PDF QR-code generation",
    "qpdf": "PDF follow-up overlay",
    "pdftotext": "admin PDF analysis",
}
OPTIONAL_COMMANDS = {"git": "runtime commit display"}


def check_module(name: str, label: str) -> tuple[bool, str]:
    available = importlib.util.find_spec(name) is not None
    return available, f"Python module {label}"


def check_path(path: Path, label: str) -> tuple[bool, str]:
    return path.is_file(), f"{label}: {path}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="fail on optional checks too")
    args = parser.parse_args()

    root = Path(os.environ.get("APP_HOME", Path(__file__).resolve().parents[1])).expanduser()
    default_request_dir = root / "requests" if (root / "requests").is_dir() else root / "data" / "requests"
    request_dir = Path(os.environ.get("REQUEST_STORAGE_DIR", default_request_dir))
    failures: list[str] = []
    warnings: list[str] = []

    def report(ok: bool, label: str, required: bool = True) -> None:
        if ok:
            print(f"OK      {label}")
        elif required or args.strict:
            print(f"MISSING {label}")
            failures.append(label)
        else:
            print(f"WARN    {label}")
            warnings.append(label)

    print(f"Application root: {root}")
    print(f"Request storage:  {request_dir}")
    for command, purpose in COMMANDS.items():
        report(bool(shutil.which(command)), f"{command} ({purpose})")
    for command, purpose in OPTIONAL_COMMANDS.items():
        report(bool(shutil.which(command)), f"{command} ({purpose})", required=False)

    ok, label = check_module("PIL", "Pillow")
    report(ok, label)

    geoip_mmdb = Path(os.environ.get("GEOIP_DB_PATH", "/usr/share/GeoIP/GeoLite2-City.mmdb"))
    geoip_dat = Path(os.environ.get("GEOIP_LEGACY_DB_PATH", "")) if os.environ.get("GEOIP_LEGACY_DB_PATH") else None
    if geoip_mmdb.is_file():
        report(importlib.util.find_spec("geoip2") is not None, f"geoip2 for {geoip_mmdb}", required=False)
    else:
        print(f"INFO    GeoIP2 database not found: {geoip_mmdb}")
    if geoip_dat and geoip_dat.is_file():
        report(importlib.util.find_spec("GeoIP") is not None, f"GeoIP legacy for {geoip_dat}", required=False)
    elif geoip_dat:
        print(f"INFO    GeoIP legacy database not found: {geoip_dat}")

    for relative in ("index.html", "js/main.js", "assets/site-qr.png"):
        report((root / relative).is_file(), f"asset {root / relative}")

    if request_dir.is_dir():
        report(os.access(request_dir, os.W_OK), f"writable request storage {request_dir}")
    else:
        report(os.access(request_dir.parent, os.W_OK), f"request storage parent writable {request_dir.parent}")

    smtp_values = {
        "SMTP_HOST": os.environ.get("SMTP_HOST", "smtp.my.mail"),
        "SMTP_PORT": os.environ.get("SMTP_PORT", "587"),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD"),
        "OWNER_EMAIL": os.environ.get("OWNER_EMAIL", "me@my.mail"),
    }
    report(bool(smtp_values["SMTP_HOST"]), "SMTP_HOST configured")
    report(smtp_values["SMTP_PORT"].isdigit(), "SMTP_PORT numeric")
    report(bool(smtp_values["SMTP_PASSWORD"]), "SMTP_PASSWORD present")
    report(bool(smtp_values["OWNER_EMAIL"]), "OWNER_EMAIL configured")

    public_url = os.environ.get("PUBLIC_BASE_URL", "https://atelier-roulant.linuxtribe.fr")
    parsed_url = urlparse(public_url)
    report(parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc), "PUBLIC_BASE_URL valid")

    if warnings:
        print(f"Warnings: {len(warnings)}")
    if failures:
        print(f"Required checks failed: {len(failures)}")
        return 1
    print("All required dependency checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

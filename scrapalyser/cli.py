"""Command line: scrapalyser https://example.com [more urls] [options]"""

import argparse
import json
import os
import sys
from typing import Optional

from . import __version__
from .scanner import DEFAULT_TIMEOUT, scan

PROXY_ENV = "SCRAPALYSER_PROXY"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scrapalyser",
        description="Scan websites before scraping them: antibot, blocking, engine to use, "
                    "embedded data, APIs, robots.txt, sitemaps, login wall.",
        epilog=f"The proxy can also be set with the {PROXY_ENV} environment variable "
               "(format: http://USER:PASSWORD@HOST:PORT), so it stays out of your shell history.",
    )
    p.add_argument("urls", nargs="+", metavar="URL", help="one or more URLs to scan")
    p.add_argument("--json", action="store_true", help="print JSON instead of the text report")
    p.add_argument("--lang", default="en", choices=["en", "fr", "es", "br"], help="text report language (default: en)")
    p.add_argument("--engine", default="auto", choices=["auto", "curl", "playwright"], help="default: auto")
    p.add_argument("--proxy", help="proxy, e.g. http://USER:PASSWORD@HOST:PORT")
    p.add_argument("--headless", action="store_true", help="hide the Playwright browser (easier to detect)")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"seconds to wait for a page (default: {DEFAULT_TIMEOUT:g})")
    p.add_argument("--workers", type=int, default=4, help="parallel scans when several URLs are given (default: 4)")
    p.add_argument("--save", metavar="PATH", help="write the report to a file (one URL)")
    p.add_argument("--save-dir", metavar="DIR", help="write one report per site into a folder (several URLs)")
    p.add_argument("--screenshot", metavar="PATH", help="save a Playwright screenshot (one URL)")
    p.add_argument("--version", action="version", version=f"scrapalyser {__version__}")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _parser().parse_args(argv)
    proxy = args.proxy or os.environ.get(PROXY_ENV) or None
    output = "json" if args.json else "txt"
    common = dict(output=output, lang=args.lang, engine=args.engine, headless=args.headless,
                  proxy=proxy, timeout=args.timeout)

    try:
        if len(args.urls) > 1 and (args.save or args.screenshot):
            print("scrapalyser: --save and --screenshot take one URL; use --save-dir for several", file=sys.stderr)
            return 2
        target = args.urls[0] if len(args.urls) == 1 else args.urls
        result = scan(target, save=args.save, screenshot=args.screenshot, workers=args.workers,
                      save_dir=args.save_dir, **common)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if isinstance(result, list):
            return 1 if any(isinstance(r, dict) and "error" in r for r in result) else 0
        return 0
    except ValueError as e:  # bad proxy format, workers, timeout...
        print(f"scrapalyser: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:  # site unreachable
        print(f"scrapalyser: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python
"""VNC経由でブラウザを開くスクリプト.

使用方法:
    docker compose exec dev uv run python scripts/open_browser.py
    docker compose exec dev uv run python scripts/open_browser.py https://google.com
    docker compose exec dev uv run python scripts/open_browser.py --wait 120
"""

import argparse
import time

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description="Open browser in VNC")
    parser.add_argument("url", nargs="?", default="https://note.com", help="URL to open")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to keep browser open")
    args = parser.parse_args()

    print(f"Opening {args.url} in browser...")
    print("Check VNC viewer (localhost:5900)")
    print(f"Browser will stay open for {args.wait} seconds")
    print("Press Ctrl+C to close early")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url)
        print(f"Page loaded: {page.title()}")

        try:
            time.sleep(args.wait)
        except KeyboardInterrupt:
            print("\nClosing browser...")

        browser.close()
        print("Done")


if __name__ == "__main__":
    main()

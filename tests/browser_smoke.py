"""Exercise the built starter at a project subpath in Chromium."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    screenshots = ROOT / "browser-checks"
    screenshots.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        shutil.copytree(ROOT / "dist", Path(temporary) / "example-tool")
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=temporary))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/example-tool/")
                page.get_by_role("heading", name="Peggy's Point", exact=True).first.wait_for()
                assert page.locator("#map-light").inner_text() == "Peggy's Point"
                assert "Red · Flashing · 5-second cycle" in page.locator("#map-pattern").inner_text()
                page.get_by_role("button", name="See signal").click()
                assert page.locator("#name").evaluate("el => el === document.activeElement")
                assert "1.5 s" in page.locator("#preview").inner_text()
                page.locator("#preview button").click()
                assert page.locator("#preview button").inner_text() == "Pause signal"
                page.locator("#query").fill("Point Atkinson")
                page.locator("#rows button").filter(has_text="Point Atkinson").first.click()
                assert page.locator("#map-light").inner_text() == "Point Atkinson"
                assert "Fl(2)" in page.locator("#signal").inner_text()
                assert "0.25 s" in page.locator("#preview").inner_text()
                page.locator("#near").select_option(index=1)
                assert page.locator("#comparison article").count() == 2
                assert page.locator("#options button").count() == 3
                for b in page.locator("#options button").all():
                    if b.is_enabled(): b.click()
                assert "Correct" in page.locator("#answer").inner_text()
                page.locator("#query").fill("no matches 123456789")
                assert "No matches" in page.locator("#listcount").inner_text()
                page.locator("#query").fill("")
                page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                assert not errors, errors
                browser.close()
            print("Browser checks passed: project subpath, station lookup, timing, comparison, identify mode and mobile layout")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()

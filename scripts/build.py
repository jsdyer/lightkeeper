#!/usr/bin/env python3
"""Build a browser tool using Python's standard library; no network required."""
from html import escape
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit

from records import generate, key as light_key, interpretation

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def metadata(root=ROOT):
    tool = json.loads((root / "tool.json").read_text(encoding="utf-8"))
    required = {"id", "title", "description", "category", "tags", "icon", "url", "source", "hosting", "access", "data_info"}
    if not isinstance(tool, dict) or set(tool) - {"result_directory", "dataset"} != required:
        raise ValueError("tool.json has missing or unknown fields")
    for key in required - {"tags", "data_info"}:
        if not isinstance(tool[key], str) or not tool[key].strip():
            raise ValueError(f"tool.json: {key} must be a nonempty string")
    if not SLUG.fullmatch(tool["id"]) or tool["url"] != f'/{tool["id"]}/' or tool["hosting"] != "project":
        raise ValueError("Use a lowercase tool ID, matching /id/ URL and project hosting")
    if not isinstance(tool["tags"], list) or not all(isinstance(t, str) and t.strip() for t in tool["tags"]):
        raise ValueError("tags must be an array of nonempty strings")
    if tool["access"] != "browser":
        raise ValueError("This starter produces an immediately usable browser tool; use access: browser")
    info = tool["data_info"]
    if (not isinstance(info, dict) or info.get("mode") not in ("snapshot", "live", "local", "reference", "mixed")
            or not isinstance(info.get("detail"), str) or not info["detail"].strip()
            or ("cadence" in info and (not isinstance(info["cadence"], str) or not info["cadence"].strip()))):
        raise ValueError("Describe the tool's inputs and scheduled checks in data_info")
    directory = tool.get('result_directory', {})
    if directory.get('path') != 'records/' or not directory.get('title'):
        raise ValueError('Declare the light record directory with its title')
    dataset = tool.get('dataset', {})
    if (dataset.get('file') != 'data/lights.json' or dataset.get('format') != 'JSON'
            or dataset.get('section') != 'dataset' or not dataset.get('title')):
        raise ValueError('Point the dataset catalogue entry at the native light snapshot')
    source = urlsplit(tool["source"])
    if source.scheme != "https" or not source.hostname or source.username is not None or any(c.isspace() for c in tool["source"]) or "\\" in tool["source"]:
        raise ValueError("source must be an HTTPS URL without credentials or whitespace")
    return tool


def build(root=ROOT):
    tool = metadata(root)
    output = root / "dist"
    if output.is_symlink():
        raise ValueError("dist must not be a symlink")
    web = root / "web"
    if web.is_symlink() or any(p.is_symlink() for p in web.rglob("*")):
        raise ValueError("web/ must not contain symlinks")
    with tempfile.TemporaryDirectory(prefix="coolcode-tool-") as temporary:
        stage = Path(temporary) / "site"
        shutil.copytree(web, stage)
        index = stage / "index.html"
        page = index.read_text(encoding="utf-8")
        for token, key in {"TITLE": "title", "DESCRIPTION": "description", "TOOL_ID": "id", "SOURCE_URL": "source"}.items():
            placeholder = "{{" + token + "}}"
            if placeholder not in page:
                raise ValueError(f"Missing template placeholder: {placeholder}")
            page = page.replace(placeholder, escape(tool[key], quote=True))
        page = page.replace("BUILD_DATE_UTC", datetime.now(timezone.utc).date().isoformat())
        snapshot = json.loads((stage / "data/lights.json").read_text())
        example = generate(stage, snapshot)
        if example is None:
            raise ValueError('Light index contains no eligible records')
        page = (page.replace('{{EXAMPLE_NAME}}', escape(example['name']))
                    .replace('{{EXAMPLE_PATH}}', light_key(example))
                    .replace('{{EXAMPLE_MEANING}}', escape(interpretation(example)))
                    .replace('{{LIGHT_COUNT}}', format(len(snapshot['lights']), ',')))
        retrieved = snapshot.get("retrieved")
        if retrieved is not None:
            retrieved = date.fromisoformat(retrieved).isoformat()
        page = page.replace('{{SOURCE_CAPTURE}}', f'Retrieved {retrieved}.' if retrieved else 'The retrieval date is unrecorded.')
        if re.search(r"\{\{[A-Z_]+\}\}", page):
            raise ValueError('Unresolved template placeholder in web/index.html')
        status = {"retrieved": retrieved, "lights": len(snapshot["lights"]), "sections": len(snapshot["sections"])}
        (stage / "data-status.json").write_text(json.dumps(status) + "\n", encoding="utf-8")
        label = f"Data retrieved · {retrieved}" if retrieved else "Retrieval date unrecorded"
        badge = (f'<svg xmlns="http://www.w3.org/2000/svg" width="188" height="22" role="img">'
                 f'<title>{label}</title><rect width="100%" height="100%" rx="4" fill="#e4ece7"/>'
                 f'<text x="8" y="15" fill="#183a43" font-family="system-ui,sans-serif" font-size="12">{label}</text></svg>')
        (stage / "data-date.svg").write_text(badge, encoding="utf-8")
        index.write_text(page, encoding="utf-8")
        (stage / ".nojekyll").touch()
        if output.exists():
            shutil.rmtree(output)
        shutil.copytree(stage, output)
    print(f'Built dist/ for {tool["id"]}')


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Build failed: {exc}")

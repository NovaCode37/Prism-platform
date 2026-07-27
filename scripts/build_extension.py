import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "extension")
OUT = os.path.join(ROOT, "dist")

SKIP_NAMES = {"README.md"}
SKIP_DIRS = {"__pycache__", ".git"}


def collect_files():
    for base, dirs, files in os.walk(SRC):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name in SKIP_NAMES:
                continue
            full = os.path.join(base, name)
            rel = os.path.relpath(full, SRC).replace(os.sep, "/")
            yield full, rel


def manifest_for(target):
    with open(os.path.join(SRC, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)

    if target == "chromium":
        manifest.pop("browser_specific_settings", None)
        background = manifest.get("background", {})
        background.pop("scripts", None)
        manifest["background"] = background

    return manifest


def build(target):
    manifest = manifest_for(target)
    os.makedirs(OUT, exist_ok=True)
    out_path = os.path.join(OUT, "prism-extension-%s-%s.zip" % (target, manifest["version"]))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in collect_files():
            if rel == "manifest.json":
                zf.writestr(rel, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            else:
                zf.write(full, rel)

    with zipfile.ZipFile(out_path) as zf:
        names = zf.namelist()
        bad = [n for n in names if "\\" in n]
        if bad:
            raise SystemExit("backslash paths in zip: %s" % bad)
        json.loads(zf.read("manifest.json").decode("utf-8"))

    size_kb = round(os.path.getsize(out_path) / 1024, 1)
    print("%-9s %s  (%s files, %s KB)" % (target, os.path.relpath(out_path, ROOT), len(names), size_kb))


if __name__ == "__main__":
    targets = sys.argv[1:] or ["firefox", "chromium"]
    for target in targets:
        if target not in ("firefox", "chromium"):
            raise SystemExit("unknown target: %s" % target)
        build(target)

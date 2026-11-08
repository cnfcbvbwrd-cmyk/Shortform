#!/usr/bin/env python3
"""Build the installable PWA from the single source page.

The app is authored once, as the Claude artifact page (app/index.html). That
file has no document skeleton and loads its libraries from a CDN, because the
artifact host supplies the first and allows only the second. This script turns
it into a standalone page for GitHub Pages: a real <head>, vendored libraries
so the app works with no signal, and a service worker registration.

    python3 build.py            # ../app/index.html -> ./index.html
"""

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE.parent / "app" / "index.html"
TARGET = HERE / "index.html"

CDN = {
    "https://cdnjs.cloudflare.com/ajax/libs/pdf-lib/1.17.1/pdf-lib.min.js": "pdf-lib.min.js",
    "https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js": "jszip.min.js",
}

# A GitHub Pages site is public even when its repository is private, so the
# hosted build carries no real candidate. The roster starts empty and is filled
# on the device, where it stays in that browser's storage.
SEED_ROSTER_SRC = (
    'var SEED_ROSTER = { "noah weeden": "RB2C", "nikko trinidad": "RB2C", '
    '"john kelly": "RB5C" };'
)
SEED_ROSTER_PUBLIC = (
    "var SEED_ROSTER = {};  // filled on the device; never committed"
)

EVAL_DEFAULTS_SRC = (
    'var EVAL_DEFAULTS = { rank: "CA", assignment: "RB2C", name: "Lawton" };'
)
EVAL_DEFAULTS_PUBLIC = (
    'var EVAL_DEFAULTS = { rank: "CA", assignment: "", name: "" };'
    "  // set on the device under \"Your details\""
)

# Real names also sit in the placeholder, the example filename and the code
# comments that quote sample input. Rename consistently for the hosted copy.
NAME_SWAPS = [
    ("Weeden, Noah", "Delgado, Sam"), ("Noah Weeden", "Sam Delgado"),
    ("noah weeden", "sam delgado"), ("nweeden@sanjoseca.gov", "sdelgado@example.gov"),
    ("Noah R. Weeden", "Sam R. Delgado"), ("Weeden", "Delgado"), ("Noah", "Sam"),
    ("Nikko Trinidad", "Dana Okafor"), ("Trinidad", "Okafor"),
    ("John Kelly", "Alex Rivera"), ("Kelly", "Rivera"),
    ("Harnett", "Brooks"), ("Lawton", "Alvarez"),
]

SAMPLE_PUBLIC = '''var SAMPLE = [
    "TO: CA Alvarez    FROM: FF Sam Delgado E7 RB1A",
    "SUBJECT: Daily Performance Summary    DATE: 01/06/2026",
    "",
    "Summary: This report covers January 6th 2026",
    "",
    "I entered Station 7 and made introductions to crew members. I completed my",
    "rig and equipment checkout and reviewed shift expectations with my company.",
    "In the afternoon we were dispatched to a car fire. I donned my SCBA, took the",
    "bumper line and extinguished the fire.",
    "Later Engine 7 was sent to a vegetation fire of about one acre. I advanced a",
    "progressive hose lay and knocked down the fire and hot spots.",
    "",
    "Medical: 9",
    "Physical Fitness Completed",
    "Fire/Other: 2",
    "Training: Hose deployment and hose streams",
    "Sign Offs: 112/457 Firefighter I and II",
    "",
    "Sam Delgado",
    "Probationary Firefighter, RB1A",
    "San Jose Fire Department"
  ].join("\\n");'''

# Appended to the page. Two jobs: register the worker, and give iOS a way out
# when a home-screen launch refuses to download (WebKit bug 275288).
TAIL = """
<script>
(function () {
  "use strict";
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }

  // An installed iOS web app often previews a download instead of saving it.
  // Opening the PDF in a real tab gives the share sheet, and from there Save
  // to Files or Mail behave normally.
  var standalone = window.navigator.standalone === true ||
    (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
  if (!standalone) return;

  var row = document.getElementById("saveRow");
  if (!row) return;
  var open = document.createElement("button");
  open.className = "ghost";
  open.type = "button";
  open.textContent = "Open in a tab";
  open.addEventListener("click", function () {
    var src = document.querySelector("#saveRow");
    var blob = window.__shortFormBlob;
    if (!blob) return;
    var url = URL.createObjectURL(blob);
    window.open(url, "_blank");
    setTimeout(function () { URL.revokeObjectURL(url); }, 60000);
  });
  row.appendChild(open);
})();
</script>
"""

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Short Form Builder</title>
<meta name="description" content="Turns a probationary firefighter's Daily Performance Summary into a filled, signable Short Form Performance Report.">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#f6f4f0" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#16150f" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Short Form">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" href="icon-192.png">
{fonts}
{style}
<style>
  /* The artifact host supplies these; a plain page has to set them itself. */
  html, body {{ margin: 0; }}
  :root {{
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }}
  img {{ max-width: 100%; }}
  [hidden] {{ display: none !important; }}
</style>
</head>
<body>
"""


def main() -> int:
    if not SOURCE.exists():
        print(f"source not found: {SOURCE}", file=sys.stderr)
        return 1
    src = SOURCE.read_text()

    fonts = "".join(re.findall(r'<link rel="stylesheet"[^>]*fonts\.googleapis[^>]*>', src))
    style_match = re.search(r"<style>.*?</style>", src, re.S)
    style = style_match.group(0) if style_match else ""

    body = src

    # Strip real names before the page goes to a public URL.
    if SEED_ROSTER_SRC not in body:
        print("seed roster line not found; refusing to publish a page that may "
              "still carry real names", file=sys.stderr)
        return 1
    body = body.replace(SEED_ROSTER_SRC, SEED_ROSTER_PUBLIC, 1)

    if EVAL_DEFAULTS_SRC not in body:
        print("evaluator defaults not found; refusing to publish", file=sys.stderr)
        return 1
    body = body.replace(EVAL_DEFAULTS_SRC, EVAL_DEFAULTS_PUBLIC, 1)

    sample = re.search(r"var SAMPLE = \[.*?\]\.join\(\"\\n\"\);", body, re.S)
    if not sample:
        print("sample block not found; refusing to publish", file=sys.stderr)
        return 1
    body = body.replace(sample.group(0), SAMPLE_PUBLIC, 1)

    for real, stand_in in NAME_SWAPS:
        body = body.replace(real, stand_in)

    body = re.sub(r"<title>.*?</title>\s*", "", body, count=1, flags=re.S)
    body = re.sub(r'<meta name="claude:[^>]*>\s*', "", body)
    if fonts:
        body = body.replace(fonts, "", 1)
    if style:
        body = body.replace(style, "", 1)
    for url, local in CDN.items():
        body = body.replace(url, local)

    # Keep the built bytes reachable for the standalone "Open in a tab" button.
    body = body.replace(
        'var blob = new Blob([builtBytes], { type: "application/pdf" });',
        'var blob = new Blob([builtBytes], { type: "application/pdf" });\n'
        "    window.__shortFormBlob = blob;",
    )

    out = HEAD.format(fonts=fonts, style=style) + body.lstrip() + TAIL + "</body>\n</html>\n"

    # Last check before a public URL: no real candidate names in the output.
    leaked = [n for n in ("Weeden", "Trinidad", "Kelly", "Harnett", "Lawton")
              if n.lower() in out.lower()]
    if leaked:
        print("refusing to write: real names still present -> " + ", ".join(leaked),
              file=sys.stderr)
        return 1

    TARGET.write_text(out)
    print(f"wrote {TARGET} ({len(out):,} bytes), roster empty, sample anonymised")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

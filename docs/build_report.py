"""Build docs/report.pdf from docs/report.md.

Usage:  pip install markdown  &&  python docs/build_report.py
Needs Google Chrome or Chromium (set CHROME=/path/to/chrome if it isn't found).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

DOCS = Path(__file__).resolve().parent
CSS = """
@page { size: Letter; margin: 0.8in 0.85in; }
body { font-family: "Charter", "Georgia", "DejaVu Serif", serif; font-size: 10.5pt; line-height: 1.42; color: #1a1a1a; }
h1 { font-size: 17pt; line-height: 1.2; margin: 0 0 6pt; }
h2 { font-size: 12.5pt; margin: 14pt 0 4pt; border-bottom: 0.6pt solid #999; padding-bottom: 2pt; }
p { margin: 4pt 0 6pt; text-align: justify; }
.titleblock { text-align: center; margin-bottom: 10pt; }
.titleblock p { text-align: center; font-size: 10pt; }
.eq { margin: 6pt 0 8pt 22pt; font-size: 10.5pt; line-height: 1.6; }
table { border-collapse: collapse; margin: 6pt auto 8pt; font-size: 9pt; }
th, td { border-bottom: 0.5pt solid #bbb; padding: 2.5pt 7pt; text-align: left; }
th { border-bottom: 1pt solid #333; }
figure { margin: 8pt 0; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; }
figcaption { font-size: 9pt; color: #444; margin-top: 3pt; }
code { font-size: 9pt; font-family: "DejaVu Sans Mono", monospace; }
ol, ul { margin: 2pt 0 6pt; padding-left: 20pt; }
.pagebreak { break-before: page; }
"""


def find_chrome():
    for c in [os.environ.get("CHROME"), "/opt/pw-browsers/chromium", "google-chrome", "chromium",
              "chromium-browser", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]:
        if c and (Path(c).exists() or shutil.which(c)):
            return c
    sys.exit("Chrome/Chromium not found; set CHROME=/path/to/chrome")


def main():
    body = markdown.markdown((DOCS / "report.md").read_text(encoding="utf-8"),
                             extensions=["tables", "md_in_html"])
    html = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'
    out_html = DOCS / "report.html"
    out_html.write_text(html, encoding="utf-8")
    subprocess.run([find_chrome(), "--headless", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", f"--print-to-pdf={DOCS / 'report.pdf'}",
                    out_html.as_uri()], check=True, capture_output=True)
    out_html.unlink()
    print("wrote", DOCS / "report.pdf")


if __name__ == "__main__":
    main()

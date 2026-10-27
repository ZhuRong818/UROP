"""Two-pass pagination for the static table of contents: build, render, map headings to footer labels, rebuild."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOFFICE = '/Applications/LibreOffice.app/Contents/MacOS/soffice'


def render():
    subprocess.run(['nice', '-n', '10', 'node', 'build_report.js'], cwd=HERE, check=True)
    (HERE / 'render').mkdir(exist_ok=True)
    subprocess.run(['nice', '-n', '10', SOFFICE, '--headless', '--convert-to', 'pdf', '--outdir', 'render', 'EventX_UROP_Report.docx'],
                   cwd=HERE, check=True, capture_output=True)
    text = subprocess.run(['pdftotext', '-layout', 'render/EventX_UROP_Report.pdf', '-'], cwd=HERE, check=True,
                          capture_output=True, text=True).stdout
    return text.split('\f')


def labels(pages):
    headings = json.loads((HERE / 'headings.json').read_text())
    toc_end = next(i for i, p in enumerate(pages) if 'Table of Contents' in p)
    found = {}
    for i, page in enumerate(pages):
        lines = [l.strip() for l in page.splitlines() if l.strip()]
        if not lines:
            continue
        label = lines[-1]
        for h in headings:
            if h not in found and h in lines and not (i <= toc_end + 1 and h not in ('Abstract', 'Acknowledgement')
                                                         and 'Table of Contents' in page):
                found[h] = label
    return found, [h for h in headings if h not in found]


if __name__ == '__main__':
    for attempt in range(3):
        pages = render()
        found, missing = labels(pages)
        old = json.loads((HERE / 'toc_pages.json').read_text()) if (HERE / 'toc_pages.json').exists() else None
        (HERE / 'toc_pages.json').write_text(json.dumps(found, indent=1))
        print(f'pass {attempt + 1}: {len(pages) - 1} pages, missing {missing}')
        if found == old:
            break

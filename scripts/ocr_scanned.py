"""OCR sidecars for scanned PDFs (pages without a text layer).

Writes <pdf>.ocr.json = {"pages": {page_no: text}} next to the raw file; the
parser uses OCR text only for pages whose text layer is empty. Requires the
`tesseract` binary (brew install tesseract). OCR text is marked in chunk
metadata (ocr=true) so citations can be re-checked against the page image.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
import pymupdf

def ocr(pdf: Path, dpi: int = 200) -> int:
    doc = pymupdf.open(str(pdf))
    pages = {}
    with tempfile.TemporaryDirectory() as td:
        for i, page in enumerate(doc, 1):
            if len(page.get_text("text").strip()) > 30:
                continue
            png = Path(td) / f"p{i}.png"
            page.get_pixmap(dpi=dpi).save(str(png))
            txt = subprocess.run(["tesseract", str(png), "stdout", "-l", "eng", "--psm", "6"],
                                 capture_output=True, text=True).stdout
            pages[str(i)] = txt
    (pdf.parent / (pdf.name + ".ocr.json")).write_text(json.dumps({"engine": "tesseract", "dpi": dpi, "pages": pages}))
    return len(pages)

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(arg, ocr(Path(arg)), "pages OCRed")

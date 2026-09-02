---
name: pdf-reading
description: >-
  Decide how to read a PDF. Small documents → render pages to images and read
  them visually. Large documents (or when the model has no vision) → convert to
  text (PDF-to-text) for reading/searching. If the text output is empty or is
  missing the content you need (e.g. content lives in an image/figure), read the
  relevant pages visually when vision is available; otherwise — or when too much
  would need visual reading — do not decide on your own, discuss with the user.

whenToUse: When you need to read or extract content from a PDF file, and you must choose how (visually vs. as text).
---

# Reading a PDF

Pick a path by document size and whether vision is available.

## 0. Classify the size first

- **Small** — ~tens of pages (typically up to ~50). → Path A
- **Large** — hundreds of pages. → Path B
- **Ambiguous (~100–200 pages)** — ASK the user whether to treat it as small (Path A) or large (Path B).

## A. Small document, vision available

- Render pages to images and read them visually:
  `pdftoppm -png -r 150 doc.pdf prefix` → read each `prefix-NN.png`.
- Best for figures, tables, formulas, and layout.

## B. Large document, OR no vision

- Convert to text and read/search it:
  `pdftotext -layout doc.pdf doc.txt`.
- Treat the text as a searchable index; if a specific part later needs visual reading, see Path C.

## C. Text output is empty, or misses the content you need (e.g. it's in an image)

- If vision is available and the amount is small: pick the relevant pages and read them visually.
- If there is **no vision**, or the amount to read visually is **large**: do **not** decide on your own — discuss with the user how to proceed.

## Notes

- "Small" = can be read in full visually. "Large" = must be indexed/searched, not read end-to-end.
- To jump from a text hit to a page: page breaks are form-feed (`\f`); count them to find the page, then render just that page.

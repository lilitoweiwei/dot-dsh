---
name: svg-rendering
description: >-
  Turn an SVG (or a web page) into a PNG so you can actually look at it. Default to
  rsvg-convert — milliseconds, no sandbox; fall back to headless Chromium when you need
  browser-exact output, HTML→PNG, a page screenshot, or features librsvg lacks. Covers
  the verified commands, what every flag does, the pitfalls, and the rule that you must
  look at the rendered image before delivering.

whenToUse: >-
  When you need to rasterize an SVG or screenshot a page — especially whenever you have
  authored or edited an SVG and must see the result to check it.
---

# Rendering SVG to PNG

An LLM can only *see* raster images (PNG/JPEG/WebP/GIF). So: if you wrote or edited an
SVG, render it and **look at the PNG** before delivering — and look again after each fix.
The SVG source looks fine even when the picture is broken.

## Environment (already installed — do not install anything, do not set env vars)

- `rsvg-convert` (librsvg) and `chromium` are both on PATH for the AI.
- CJK fonts are installed **system-wide**: `fc-list :lang=zh` lists ~100 entries and
  `fc-match "sans-serif:lang=zh"` resolves to `Noto Sans CJK SC`, with **no environment
  variables at all**. If you ever feel the need to set `FONTCONFIG_FILE`, stop — something
  is wrong; the global fonts are the supported path.
- Quick sanity check: `command -v rsvg-convert chromium && fc-list :lang=zh | head -3`

## A. Default: rsvg-convert (fast path — use this first)

```bash
rsvg-convert -w 1200 diagram.svg -o diagram.png   # scale to 1200px wide (aspect kept)
rsvg-convert diagram.svg -o diagram.png           # intrinsic size
rsvg-convert -z 2 diagram.svg -o diagram.png      # zoom 2x
rsvg-convert -f pdf diagram.svg -o diagram.pdf    # when you also need a PDF
```

| flag | meaning |
|---|---|
| `-w N` / `-h N` | output width / height in px (aspect preserved) |
| `-z F` | zoom factor |
| `-o FILE` | output path |
| `-f png\|pdf\|ps` | output format (default: guessed from the `-o` extension) |
| `-b COLOR` | background color |
| `-a` | keep alpha channel (alpha is preserved by default anyway) |

Runs in milliseconds, never touches the network, no sandbox involved, transparent
background preserved. Prefer it unless you hit case **B**.

## B. Fallback: headless Chromium (browser-exact)

Use when the SVG uses something librsvg lacks (filters, `foreignObject`, web fonts, some
CSS), when output must match what a browser shows, when you need HTML→PNG, or when you
want to screenshot a running page.

```bash
chromium --headless --disable-gpu --hide-scrollbars --no-proxy-server \
  --user-data-dir=/tmp/chrome-shot --window-size=1200,900 \
  --screenshot="$PWD/out.png" "file://$PWD/diagram.svg"
```

| flag | why |
|---|---|
| `--headless` | no display needed (this VM has none) |
| `--disable-gpu` | no GPU here; also silences noisy errors |
| `--window-size=W,H` | viewport — **set it to the SVG's own width/height**, else the image gets scaled or letterboxed |
| `--screenshot=PATH` | output file; give an **absolute** path |
| `--user-data-dir=/tmp/...` | keeps `~/.config/chromium` clean and avoids profile-lock failures |
| `--hide-scrollbars` | otherwise a scrollbar can show up on an exact-fit SVG |
| `--no-proxy-server` | only matters for `http(s)://` targets (this machine has a global proxy); harmless for `file://` |
| `--default-background-color=00000000` | transparent background (the default is opaque white **without** an alpha channel) |
| `--force-device-scale-factor=2` | 2× device pixels (sharper output) |
| `--virtual-time-budget=5000` | for page URLs: let it render/run JS before the shot |

Facts verified on this machine (2026-10-13, Chromium 147):

- It runs headless **without `--no-sandbox`** — the namespace sandbox works. Only add
  `--no-sandbox` if you actually see a sandbox error.
- Stderr noise about `vaapi`, `UPower`, or `dbus` is normal in this VM — ignore it, and
  judge success by the exit code plus the output file.
- `TMPDIR`, if set, must be an absolute path; on "Socket path too long", use `TMPDIR=/tmp`.

## C. Always look at the result

Read the PNG back as an image. ToFu boxes (□□□) mean the font didn't resolve; wrong
geometry, overlapping labels, text overflowing the canvas, and mis-aimed arrows are all
invisible in the SVG source. Fix, re-render, look again. Only then deliver.

## Writing SVG that renders well in both engines

- Give explicit `width`, `height` **and** `viewBox`.
- One `<text>` per label with explicit `x`/`y`. Never rely on automatic line wrapping —
  librsvg and Blink wrap differently.
- Avoid `foreignObject`, scripts, external CSS, external/web fonts, and remote `<image href>`.
- Font family: use `sans-serif` / `serif` (globally mapped to Noto CJK) or an explicit
  `"Noto Sans CJK SC"`. Avoid exotic family names.
- Prefer plain presentation attributes or a tiny inline `<style>`; heavy selectors may not
  survive librsvg.
- For rotated copies of a shape: define it once in `<defs>` and place copies with
  `<use transform="rotate(deg, cx, cy)">` — exact, and the file stays hand-editable.
- Keep the file self-contained (no external references) so it renders standalone anywhere.
- Put the output where the workspace's own `AGENTS.md` says images belong.

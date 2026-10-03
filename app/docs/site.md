# Install site - jobs.enrriquez.com

`docs/` = install page, GitHub Pages, custom domain (`docs/CNAME`). Guarded by
`app/tests/test_site.py` (no network; helpers in `site_checks.py`) + `test_install.py` (install
line, steps). Site tests run in the developer checkout only: no `.git` (installed copy, may keep a
stale `docs/`) -> skipped. Every `docs/**/*.html` but `mac/` + `win/` (install scripts) is a page.
Not in the app download: `/docs/** export-ignore` (`.gitattributes`) keeps the site out of the
`main.zip` every launch fetches; an empty `docs/` entry stays so updates clear a stale copy
(anchored + `/**` measured, why in `.gitattributes`; `test_update.py` checks it).

## What is where

- Hand-written: `index.html`, `privacy.html`, `404.html`, `robots.txt`, `sitemap.xml`,
  `manifest.webmanifest`, `icon.svg`; share card source `app/web/og.html`.
- Generated, committed, never hand-edited: `fonts/` (Caladea WOFF2 + `OFL.txt`), `icon-*.png`,
  `apple-touch-icon.png`, `favicon.ico` (PNG frames 16/32/48), `og.png`. Change the source, rerun
  `uv run app/web/assets.py [--only fonts|icons|og]` - PEP 723 script w/ own deps (uv ignores the
  project's), icons + og drawn in Google Chrome. Two runs = byte-identical files.

## Look

- Ink on paper, like the resume it makes: tokens in one `:root` block - paper #fff, ink #000,
  ink-2 #3a3a3a, highlighter #ffe433 only on marks + Copy button; dark mode changes the desk,
  the sample sheet stays white paper.
- One family: Caladea (= resume typeface), Latin subset 400 + 700 (~18 KB each), name table kept
  (licence); metric-matched fallbacks (Cambria, Georgia w/ size-adjust) so the swap moves nothing.
  System mono for the command only.
- One motion moment: highlighter sweep on the sample sheet + Copy click. Only under
  `prefers-reduced-motion: no-preference`; marks visible w/o it.

## Rules + why

- No third-party requests (fonts, scripts, images, CSS `url()`): privacy page promises it; test enforces.
- Loaded URLs root-relative (`/fonts/x.woff2`, or `data:`): 404.html is served at any depth.
  Links: `/...`, `#id`, `https:` or `mailto:` only; folder links end in `/` (`/research/`, else
  Pages redirects); every `#id` must exist on its target page.
- Paths exact-case: macOS disks match `/Fonts/x` to `fonts/x`, Pages answers 404. Tests compare
  against names listed from disk, never `is_file()`.
- Each indexed page's canonical = its own URL (folder `index.html` -> the folder); page w/o
  canonical -> `noindex`. Sitemap = exactly the indexed URLs, once each. Titles + descriptions unique.
- Shared CSS (`/* shared */` ... `/* /shared */`: fonts, tokens, header, footer, `.wrap`) identical
  on every page; test guards. Header (brand, Install `/#install`, Source code) + bare `<footer>` (Made
  by, Privacy, Source code) byte-identical on every page; test guards.
- Phone header: brand + 3 links need 399px, a 360/375/390px screen has 328/343/358 => header
  Source code hidden <= 600px (footer keeps it); <= 359px the links may wrap below the brand.
- Layout checked in a real browser: `uv run app/web/qa.py` (PEP 723, Chrome) serves `docs/`,
  opens every page as a phone at 320/360/375/390px + desktop at 768/1366px; fails on sideways
  scroll, a two-line header from 360px, or Copy below the fold at 1366x768. Screenshots in
  `.data/screens/`. Width = `clientWidth`: a phone's `innerWidth` grows to fit a too-wide page.
- Install line static in HTML (Windows), JS swaps for Mac; FAQ carries the Mac line as text ->
  no-JS readers + crawlers see a command.
- Never look like a fake "paste this to verify" page: clipboard written only on Copy click, full
  command always visible, no key combos, "Read the script first" link to the GitHub file (never
  `/win` `/mac`: served as HTML), no command on the share image.
- robots.txt Disallow `/mac/` `/win/` - not `/mac` (prefix: would also block a future `/macos.html`).
- JSON-LD = WebSite only (site name in results). SoftwareApplication w/o ratings = invalid in
  Search Console; FAQ rich results now limited to government + health sites.
- `og:title` w/o brand suffix (`og:site_name` carries it). `og.png` 1200x630, < 300 KB (WhatsApp
  drops larger); changed -> bump `og.png?v=N` on every page (tests read og:image as a URL, query ignored) (LinkedIn caches a preview ~7 days).
- 404.html: root paths only (served at any depth), noindex, no canonical.
- No front matter in any file, no `.md`, no path segment starting `_` `.` `#` or ending `~`:
  GitHub Pages runs Jekyll, which would template or drop them (test checks tracked `docs/` files).

## Measured

- GitHub Pages types: `.ico` image/vnd.microsoft.icon, `.webmanifest` application/manifest+json,
  `.woff2` font/woff2 - no headers file needed.
- `/privacy` + `/index.html` also answer 200 -> every page carries a canonical == sitemap URL.
- Font subset: regular 18.2 KB, bold 18.2 KB; og.png 81.5 KB.

# Install site - jobs.enrriquez.com

`docs/` = install page, GitHub Pages, custom domain (`docs/CNAME`). Guarded by
`app/tests/test_site.py` (no network; helpers in `site_checks.py`) + `test_install.py` (install
line, steps). Site tests run in the developer checkout only: no `.git` (installed copy, may keep a
stale `docs/`) -> skipped. Every `docs/**/*.html` but `mac/` + `win/` (install scripts) is a page.
Not in the app download: `/docs/** export-ignore` (`.gitattributes`) keeps the site out of the
`main.zip` every launch fetches; an empty `docs/` entry stays so updates clear a stale copy
(anchored + `/**` measured, why in `.gitattributes`; `test_update.py` checks it).

## What is where

- Hand-written: `index.html`, `privacy.html`, `terms.html` (terms of use: as is, no warranty, not advice; installers + home
  install box show the same notice, claim `install-terms`), `404.html`, `robots.txt`,
  `manifest.webmanifest`; share card sources `app/web/og.html` (home) +
  `og-research.html` (every generated page); the CSS sources (below).
- CSS (owner 2026-10-07: "more reusable css shared ... can be multiple css files", then "do what is best for
  speed"): one source per rule in `app/web/css/` - `site.css` for every page (fonts, tokens, base type, links,
  marks, `.grid` + `.wrap`, skip link, header, footer, touch boxes, print, page change), `doc.css` for the reading
  pages (research articles, hub, About, methods, privacy, 404: editorial type, notes, tables, citations + the source
  card, Sources, On this page, Keep reading; `main.plain` = privacy, terms + 404's smaller h1). `pages.py` builds them into
  each page's `<style>` - `/* shared */ ... /* /shared */` then `/* doc */ ... /* /doc */`, comments + blank lines
  cut (~3 KB gzip off every page) - the hand-written pages' blocks too (their only generated part); one-off styles
  follow in the same `<style>` (home's scenes, privacy's ledger, 404's drawing). Element box rules (h1 size, p + li
  margins) live in doc.css only, so home never inherits them (test); both sources must be tracked by git (test).
  Never linked: a linked `site.css` (+ `doc.css`) measured ~220 ms later LCP on the phone profile (home 784 vs 568
  built in, an article 788 vs 568) and a 510 ms long load frame (gate < 300) - a render-blocking request on a 150 ms
  line, while GitHub Pages caches every file 10 min only (`cache-control: max-age=600`, read 2026-10-07), so the
  cache saved little. Was: the shared block hand-copied into 3 pages + checked equal, the article CSS a string in
  pages.py, privacy + 404 trimmed copies of it. The move changed no computed style on home or a generated page
  (every element, phone + desktop, light + dark + print, diffed); privacy's h2 took the articles' line-height
  (1.15 -> 1.2) + 16px scroll-margin (an anchor jump, e.g. /privacy.html#delete, stops 16px short of the edge, as
  on articles) and the 404 prints w/o its padding.
- Generated, committed, never hand-edited: `fonts/` (Caladea WOFF2 + `OFL.txt`), `icon.svg`, `icon-*.png`,
  `apple-touch-icon.png`, `favicon.ico` (PNG frames 16/32/48), `og.png`, `og-research.png`.
  Icons = the app's own mark, the blackbird, one home `app/install/` (owner 2026-10-04: site
  always shows what the desktop shows; crop system: site = bare bird beside the name, Desktop =
  bird on the dark tile, `desktop-icon.md`). Bare bird: `mark-32.svg` (small cut, whole pixels at
  32 + 16px) + `mark.svg` (master, share cards). Pages carry it inline (`<svg class="bird">`:
  header brand 32px, hero title bar 16px), never an `<img>` - an img switching by its own colour
  scheme prints pale on white paper from a dark-mode machine. The bird sits on a paper disc (the
  Desktop icon's, `<circle class="disc">` inscribed in the 32 grid): black bird on every ground,
  the disc vanishes on the light desk + white paper and shows on the dark desk (owner 2026-10-05: a pale
  bird read as a white one, its yellow lost on it). `site.css` colours it: ink = `--ink`, disc =
  `--disc` (the desk in light - a white disc ghosted on the cream, 1.13:1 - paper in dark; the hero window sets it
  to `--paper`: white in light, the softened paper on its dark grey; CanvasText + Canvas in forced colours), beak +
  eye `--mark`, lower beak `--beak-low` (2.62:1 on the cream: a logo, WCAG 1.4.11 exempts it);
  the 16px title-bar bird's whole beak `--beak-low` (`desktop-icon.md`). `assets.py --only
  icons` rewrites the inline bird in the hand-written pages (`assets.HAND_PAGES`) from `mark-32.svg` (fills cut, disc
  added), then `pages.py` copies the header on. `icon.svg` (tab only) = `mark-32.svg` w/ `<desc>`
  cut, on the white disc, whole beak orange (a tab draws 16 px); one drawing for light + dark tab
  strips. `favicon.ico`, PNGs = the Desktop tile icon (an .ico can't follow a
  dark tab strip; the tile works on any ground): 16/32 from the 16/32 rungs, 48 + PNGs from the
  1024 master; apple-touch + maskable on its ink (#0c0c0e), tile full-bleed, bird 0.363 of the
  side from centre (safe circle 0.40; `icons()` measures `<g id="bird">`, fails past it). Share
  cards `<img src="/app/install/mark*.svg">`, inlined at render as drawn for their size
  (`card_art`: 48px bird w/o pupil, 16px bird's beak all orange). `app/web/icon-sync.json`
  = art hashes (`icon*.svg`, `mark*.svg`) + every made file's;
  `test_site_icons_follow_the_app_icon` fails when the art moved and the site didn't follow.
  Art changed => `uv run --with pillow python app/install/icons.py`, `uv run app/web/assets.py
  --only icons`, `--only og` (+ bump both `?v=N`), `uv run app/web/pages.py`.
  `uv run app/web/assets.py [--only fonts|icons|og]` - PEP 723 script w/ own deps (uv ignores the
  project's), icons + og drawn in Google Chrome. Two runs = byte-identical files (icons:
  one browser page per file - a reused page drifted a few levels on some runs, measured).
- Generated by `uv run app/web/pages.py` (project env, one file), committed, never hand-edited (and the built-in CSS
  blocks of every page, the hand-written pages' too - their only generated part):
  `sitemap.xml` (canonicals of every page w/o noindex, home first then sorted; `<lastmod>` = a
  page's `article:modified_time`, dated pages only - Google drops lastmod once it's seen wrong), `research/**` +
  `about/**` from `app/web/research/*.md` (next section). Owns those two folders: a file there it didn't build = orphan,
  deleted on the next run (dotfiles ignored). `--check` lists stale / missing / orphaned, exits 1;
  `test_generated_files_are_fresh` runs it => added a page or edited a source, rerun + commit.
  Deterministic: no clock, sorted, UTF-8 + LF (CRLF checkout counts as fresh); dates from a
  month-name list, never strftime.

## Claims - site matches the app

Owner 2026-10-04: site always says what the app does now. Every sentence or label on a page that
describes the app (buttons, first start, privacy rows, hiring systems, installer question) carries
`data-claim="<id>"`; `app/web/claims.yml` maps id -> page, its text, the app facts it rests on.
`test_site_claims_still_match_the_app` (`site_checks.claim_problems`): page text = `text`, each
fact still holds - `contains` (file says it, exact), `rows` (AGENTS.md privacy rows matching a
regex = exactly these: a row added or reworded fails), `say` (button label in
`app/vscode/say.json`), `apply_systems` (`app/apply/systems` NAMEs, start-box ones apart).
Failure = `<page>: claim <id>: <what changed> -> update ...`. App change described on the site =>
fix the sentence, then `text` + fact. Icon: `icon-sync.json` (above). Hero window + share card
stay hand-drawn (owner): sample jobs, no claim. New sentence about the app => add a claim.

## Research pages

- Source `app/web/research/<slug>.md`: YAML header between `---` lines, then Markdown. Keys only
  `title`, `description`, `published`, `modified`, `status` (draft | published), `og_title`,
  `uncited`, `data` + `license` (data page, below); a key twice = error (plain YAML keeps the last). Dates `YYYY-MM-DD`, kept as text.
  Slug `^[a-z0-9]+(-[a-z0-9]+)*$`; `feed`, `reviews`, `sources` reserved. Draft = not built.
- Data page: header `data: <slug>.csv` (file next to the source: UTF-8, header row, every row as wide, last
  line break) -> the file at `/research/<slug>/<slug>.csv`, a "Download the data (CSV, N rows, K KB)" line
  first, Dataset JSON-LD (name, creator = the byline Person, dates, `variableMeasured` = header row,
  DataDownload; Dataset Search only) in place of Article. Not an article: off the hub + feed, keeps byline,
  AI note, Keep reading, sitemap lastmod. `license:` = a `LICENSES` name (owner picks) -> shown on the line +
  Dataset `license`; on any other page = error. First one: knockout-questions-2026-10 (counting code
  `app/web/knockout_count.py`; raw sample never published - it holds posting titles + links).
- `<slug>.md` -> `/research/<slug>/`, `methods.md` -> `/research/methods/`, `about.md` ->
  `/about/` (must be published w/ the first page: every byline links it), `index.md` = hub intro.
- Hub `/research/` = `index.md` (published, no review: its first paragraph over the list) + every article,
  newest published first, each title an h2 holding its link (screen readers jump article to article; set
  like the folder it is), description (the answer in a sentence) + dates under it; the list comes right
  after the page column, before `index.md`'s other paragraphs and the labels column (a phone reaches the
  articles first, not the method); the labels column heads itself w/ an h2 too. Built once >= 1 article is
  published (article = not about / methods / index); an article w/o a published `index.md` = error.
  Before the hub exists the Research breadcrumb is text, after it's a link named w/ the hub's own title
  (one name per URL in every crumb + BreadcrumbList, D22). From 1280px: `index.md`'s first paragraph stays
  under the h1, the rest sits beside it, evidence labels beside the list, articles in 2 columns (>= 4 titles
  in a 1440x900 first screen, qa HUB_FOLD). Short windows (< 820px tall) the labels scroll w/ the page: sticky,
  they hid 99px of themselves at 1280x720 (qa STICKY_FIT).
- Article top (`page()`, `boxes()`; why: research.md Style): h1, `description` as `<p class="answer">`,
  one `<p class="meta">` (byline, dates, AI note), then the body's leading notes - a bold-label
  paragraph + its list before the first heading gets `class="box"` / `class="box-list"` (What to do,
  What the evidence says; "More in What helps" `box-more` link when that h2 exists). The closed On this
  page (below 1280px) sits right after the first note: the answer + What to do own a phone's first screen,
  the list starts within 1.25 screens (owner 2026-10-07; qa TOC_NARROW, was: inside the first screen).
- Citations render `<small>(Label; Author year)</small>` (an evidence label written right before a
  citation joins it, LEAD_CITE). `CITE_JS` (<= 1 KB, test_pages; after the footer, only on pages that
  cite): a plain click on a `#src-` link opens that Sources entry in a modal `<dialog class="card">`
  (Close autofocused; Esc, backdrop, Close or "All sources" close it; focus returns to the citation). A
  modified click, or no JS, still jumps to the list.
- Keep reading (`keep_reading()`): 3 articles - the ones the page links to, then the ones linking to it,
  then the next in hub order (wrapping) - each w/ its description, and its own share card small (120x63,
  `<li class="thumb">`, `alt=""`: the title says it; lazy; the whole row is the link's hit box) when it has
  one; then All research, install line, Back to top. Related + end-of-article links got more clicks in a
  1.8M-visit field test, w/ images 63% more (`~/code/research/topics/web/reader-engagement.md`).
- Share card per article: header `card:` (the key finding; `pages.card()`: <= 100 chars w/o citation, a
  number needs `[@id]` or an `uncited:` snippet, articles only) -> `assets.py --only cards` draws
  `docs/cards/<slug>.png` (1200x630, `app/web/og-article.html`: title, finding, source line = author-year
  w/o the a/b twin letter + plain evidence word, or "our own measurement") + `<slug>-small.png` (240x126)
  and records spec hash + PNG hashes in `app/web/card-sync.json`. Build error when a `card:` line, the
  template or the bird changed since its card was drawn; og:image + twitter alt + JSON-LD image = that card,
  `?v=` = the PNG's own hash (no number to bump). test_site: files == the record, sizes, < 300 KB.
  `pages.py --cards` prints the specs (assets.py runs it in the project env).
- Blocks (fences, parsed after block parsing so lints, citations + typesetting read their text; GitHub
  shows code, the site is the reader's copy): ```` ```case ```` = your-case figure - caption, `Label |
  Finding | What to do` heads, 3-cell rows -> `<figure class="case">` + table (no scroll box; td
  `data-label`, a phone stacks each row under its column names); the caption is a citation unit and its
  citation covers every row, else each row cites itself. ```` ```guess ```` = question line, `- choice`
  lines (2+), `Answer: ...` (needs a citation or an `uncited:` snippet) -> `<div class="guess">`, the
  answer in a closed `<details>`; one unit for the lints (the answer's citation covers the choices);
  `GUESS_JS` (<= 400 B, test_pages; only on pages w/ a guess) turns choices into `aria-pressed` buttons
  that open it. ```` ```sure ```` = Markdown inside `<details class="sure"><summary>How sure is
  this?</summary>`; line numbers stay the file's; lint: not right after a heading, no bold, no heading
  inside. Print opens both. Each block's CSS ships only on pages that hold it (`BLOCK_CSS`).
- Page CSS ships w/o its comments (`shipped()`, also cutting app/web/css/site.css + doc.css on their way in): the
  why stays in the source, not in every download (saved ~1.6 KB gzip on the longest article; ~3 KB w/ site.css).
- Render: markdown-it-py `js-default` (raw HTML shown as text, tables on). Heading id = the
  `test_docs.anchors()` rule, so `x.md#h` lands in VS Code, on GitHub and on the site. Table
  wrapped in a focusable, labelled scroll box (wide table scrolls, not the page). A table or bar figure
  right before an h2 drops its last row's rule: the heading's rule closes it (two hairlines 49px apart, qa
  RULES_STACKED). Code (inline + blocks) carries `translate="no"`, and so does the app's name in page
  text (`<span translate="no">`, `pages.BRAND`): a browser translating the page (a reader's own
  language) left commands + names mangled.
- Bar figure (A15): a ```` ```bars ```` fence = line 1 caption (Markdown: citation, evidence label, links), line 2
  `Label | Value` column heads, then `label | value` rows -> `<figure class="bars">` w/ `<figcaption>` + a real
  table (row heads `scope="row"`, no scroll box), an ink bar under each value (a border: prints, forced colours
  paint it; `aria-hidden`, the number says it). Bar = value's share of its whole: `51%` of 100, `99 of 143` of
  143, plain numbers of the largest; from zero, one kind per figure, never over its whole - else `file:line`
  error. Citation lints read the figure as one unit: the caption's citation covers every row. The source shows
  a code block on GitHub - fine, the site is the reader's copy.
- Links: `x.md#h` -> `/research/x/#h` (x published, heading exists); `https://jobs.enrriquez.com/p`
  -> `/p` (must exist); `#h` on the same page; other relative repo paths -> GitHub file URL (must be a file or folder git
  tracks, exact case: a macOS disk finds `SITE.md` for `site.md`, an ignored private file would name
  itself on the page); `https://github.com/cezkid/jobs/issues...` as is (corrections link); `OWN_LINKS` as
  is (the app's code, www.enrriquez.com - About's contact + code are links, not addresses to copy; fragment
  allowed, look-alikes not). Feed counts as a page. Anything else = error: other sites go through the sources list, not body links.
- Feed `/research/feed.xml` (Atom, ElementTree, built w/ the hub): entries = published articles,
  newest first, id + link = canonical, summary = description; feed `updated` = latest modified.
  Dates as `YYYY-MM-DDT00:00:00Z` (RFC 3339 date-time: a date alone is invalid). `rel=self`
  absolute; hub + articles carry `<link rel="alternate" type="application/atom+xml"
  href="/research/feed.xml">` (root-relative: tests check every loaded `<link>` is a file).
- Page: `<title>` = title alone, canonical = `og:url`, `og:type` article + published/modified
  time; `site.css` + `doc.css` built in, header, footer, icon + font links, `og:image` copied from `index.html`.
  Breadcrumb, h1, "By ... · Published · Updated" (Updated only when it differs). Share card =
  `pages.CARD` (`/og-research.png`, alt `CARD_ALT`), size lines from `index.html`; an article w/ a
  `card:` line gets its own (above).
- JSON-LD: one `@graph` block per page (`jsonld()`: compact, UTF-8, `<` -> `\u003c`). Article
  (headline, dates == the byline `<time>`s, author Person `@id` `/about/#person` w/ name + url,
  image = og:image, no publisher) + BreadcrumbList on articles; BreadcrumbList on hub + methods;
  ProfilePage (mainEntity Person, `sameAs` GitHub + www.enrriquez.com, both shown on About) + BreadcrumbList on about. Breadcrumb items =
  canonicals that exist. `site_checks.structured_data()` checks it on fixture + real pages.
- Citations: `[@id]`, `[@id, p. 12]`, `[@a; @b]` (markdown-it core rule after `text_join`: never in
  code or link text) -> `(<a href="#src-id">Quillian et al. 2017</a>, p. 12)`; `\[@id]` stays text. Label = surname
  (1 author), "A and B" (2), "A et al." (3+) or org, + year; two alike -> 2017a / 2017b by id.
  Cited page ends w/ `<h2 id="sources">Sources</h2>` (a body heading `## Sources` = error; heading id `src-...` or empty = error,
  one id per element):
  `<ol>` sorted by label, `<li id="src-id">` = authors (year), title, venue, DOI + url links,
  plain-words evidence (Guides scale, `EVIDENCE`) + sample, "Preprint, not peer-reviewed.",
  "Checked <date>".
- `app/web/research/sources.yml` = list of entries: `id` (a-z0-9 joined by -), `type` (article |
  book | report | law | web), `authors` (list of `Surname, Given`) or `org`, `year`, `title`,
  `evidence` (strength labels, `app/docs/resume/fair-screening.md`), `checked`, `doi` (`10.x/y`,
  no `https://doi.org/`) and/or `url` (https only); `venue` for article + book, `url` +
  `recheck_by` for law; optional `sample`, `preprint` (true/false), `recheck_by`. Unknown key,
  key twice, id twice = error.
- Statistic needs a citation in its sentence or later in its paragraph (published pages; headings
  skipped): `%`, percent, points, "N in M" / "N out of M", `n=`, fraction words ("a third", "one
  fifth"). Split knows "et al.", "p.", "e.g."; a citation right after the full stop counts for that
  sentence; a table row is one unit (source may sit in another cell). Own numbers: header
  `uncited:` list of snippets - a sentence containing one passes.
- One citation per run: same source cited in 3 sentences in a row in one paragraph = error - cite
  a run of sentences from one source once, at its end (repeating it after every sentence reads
  heavy). A sentence inside the run must come from that source; our own words go after the cite.
- Review gate: every built page (articles, methods, about) needs `reviews/<name>.md` (same
  folder), header `reviewed: YYYY-MM-DD` (on or after the page's modified), `verdict: publish`
  (else the page fails), optional `reviewer:`; body = the review. Never built into `docs/`.
- Real sources: `uv run app/web/pages.py --links [file]` (no file = the repo's `sources.yml`, from any
  folder; a file given that doesn't exist = exit 1) (network; never in tests - those fake it w/
  `httpx.MockTransport`). DOI -> doi.org handle API (404 = doesn't exist), then Crossref: title
  similarity < 0.9 or year off by > 1 = names another work (catches invented + mistyped citations).
  arXiv id (from an `arxiv.org/abs|pdf` url or a `10.48550/arXiv.` DOI) -> arXiv export API, same
  title + year test, 3 s between calls (its terms); its page isn't fetched. Other urls: 404/410
  broken; 401/403/429/5xx, no answer, DOI not in Crossref (DataCite) = check by hand. One
  `file:line: id: level: what` per check + a count; exit 1 on any broken. Measured: arXiv answers
  429 "Rate exceeded." for a while after a burst.
- Warnings, never fail: registry entry no page cites (drafts count), `recheck_by` passed, review
  w/o a page.
- Any problem -> `file:line: what`, nothing written, exit 1.
- Lints, published sources only (drafts may hold notes): no `#` h1 in the body, no skipped
  heading level, heading = plain text (no link, citation, HTML, `&...;` entity, closing `#`); no raw HTML
  outside code (shown as text), no image, no `[owner:` / `TODO`, no `](<`; title <= 60,
  description <= 155, og_title <= 70 (cut off in results / previews); dates not in the future,
  modified not before published; no invisible character (`resume/lint.py` INVISIBLE), no app
  jargon (`test_docs.py` JARGON - a test keeps both copies equal); titles + descriptions unique.
  Warning only (page still built): a character outside `assets.UNICODES` (site + share-card font
  subset: it falls back to another font).

## Look

Concept: "A morning with Job Finder" - the paper objects the app really makes, told as one
morning (hero app window, the resume corrected, applications filled, who sees what, research,
questions, install). Real behaviour only: employers, titles, dates never change; you approve every line.

- The job-search desk (owner 2026-10-07, plan-h14: "no cohesion ... white text on dark background the whole page";
  then "the yellow highlighter and blue pen ... memo pad, manila folder, sticky note ... keep going with the whole
  theme", "still follow Apple design guidelines, a premium look like Apple designed the pages"). Everything on a page
  is an object on one desk, each with one job:
  - Paper + ink: what the app prints (the resume sheet, the 404 drawing, the window in light). Ink = `--text`.
  - Highlighter yellow (`--mark`): what the app marks - the posting's words in the window + on the resume, the
    bar figures' bars (the number that matters), Copy (the one filled yellow control) + the bird's upper beak and
    eye. Marks keep black text in both schemes.
  - Blue pen (`--pen`): the person's own hand - the ring round the job you pick, the proofreader's strike +
    insert mark, "You approved this line" + its tick, the Submit you press, the guess you choose - and every place
    you can go: a link in the page keeps the text's ink, the pen draws its underline (2px), hover writes the word
    in pen; the section in view gets a 3px pen stroke in On this page. Bylines, citations, Sources + crumbs
    underline in a quiet grey; navigation underlines in ink. The pen is opposite the yellow on the colour wheel,
    so the two never read as one (the orange tint before it did: gold read as the highlighter, peach as random).
  - Sticky note (`--sticky`): what to do - an article's first note ("What to do", a data page's "Short answer"),
    home's closing steps.
  - Memo card (`--raised`): the next note ("What the evidence says"), the source card (an index card: a pen-blue
    head rule under its label).
  - Manila folder (`--folder`, `--folder-tab`): research filed - home's picks, the hub list, Keep reading. A tab
    on the left with a concave fillet; hovering pulls the folder up 4px (transform, eased in full motion only).
  - Apple's restraint (HIG Color, Dark Mode, Materials): objects drawn, not costumed - one radius (`--radius`
    14px, tab 10px), flat faces, no textures, ruled lines, perforations or tape (tried 2026-10-07: the index card's
    ruled lines crossed its text, the memo's binding + perforation read as a costume); no shadows - depth is the
    face against the desk (and an offset second sheet for the window + resume).
- Light = the morning desk: warm paper (`#f6f1e7`, cf. Apple's #f5f5f7 bands, Apple Books' sepia), objects in
  their full colour on it - white memo + cards, pale canary sticky, manila folders.
- Dark = the same desk, lamp low (HIG: "dimmer backgrounds and brighter foreground ... not necessarily
  inversions"): warm charcoal `#1a1712` (OKLCH 0.205, chroma 0.010 at the cream's hue: lively dark modes tint
  toward their brand - GitHub, Wikipedia, Josh Comeau all blue-tinted, flat grey only on monochrome brands; Radix:
  a grey "saturated with the hue closest to your accent" reads more harmonious); paper-white text `#eae6dd`
  (APCA Lc 90.8: its preferred body contrast, and large text stays under Lc 90-100 - `#f2f2f2` on the old grey
  read glaring); headings the body's colour (brighter headings break APCA's cap for large text in dark). The
  objects' big faces dim to a lamp-lit tint of their colour (chroma <= 0.022) and their colour stays on the
  object's edge: the sticky's top edge, the folder's tab + top edge (a field of 13 light folders turned the hub
  into a light page, measured side by side). The resume sheet + 404 drawing stay paper (`#ebe8e2`, HIG "soften
  white backgrounds"; dimmer paper lost the sheet's hairlines, `--rule` Lc < 15). The hero window raised one step
  (`--raised`), as the app's own dark Today page. Thick rules (masthead, notes, Sources, Keep reading, table
  heads) a step under the text (`--heavy`), so no white line glares. Grayscale font smoothing (macOS draws light
  text on dark heavy). The pen takes a lighter ink on the desk (`#81b4f6` strokes, `#afd1fc` words; Apple + Material
  agree: blue lighter in dark, saturated blue vibrates), its dark ink on the paper sheets (`--pen-paper`).
- Increase Contrast (macOS + iOS -> `prefers-contrast: more`, Safari 14.1+, Chrome 96+): HIG asks a higher-contrast
  variant of every custom colour - grey text becomes ink, hairlines 3:1 (`#767676`), the pen's ink 7:1. Sheets + the
  window keep theirs: they mirror what the app prints (and `--rule` also draws the 404's placeholder lines).
- Print: ink on white from either scheme - the body resets every desk + object token (objects print as plain
  paper, the pen as ink, bars in ink).
- Forced colours: faces drop, so every object keeps a CanvasText outline (folders, notes, sticky, source card); bars
  CanvasText; marks `Mark`/`MarkText`.
- Tokens: one `:root` block in `site.css` + a dark-scheme override + two Increase Contrast overrides (all
  schemes, then dark); these tables = those blocks (`test_site_md_tokens_table_is_the_shared_root`). The paper
  tokens (`--paper` aside) never follow the scheme; `--win*` = the hero window's own (paper in light).

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#ffffff` | `#ebe8e2` | sheets (the resume, the 404 drawing); softened in dark (HIG) |
| `--ink` | `#000000` | same | text + rules on paper, text on marks |
| `--ink-2` | `#3a3a3a` | same | secondary text on paper |
| `--mark` | `#ffe433` | same | the highlighter: marks, bar figures' bars, Copy, the bird's upper beak + eye |
| `--beak-low` | `#e57a00` | same | the bird's lower beak (two-tone bill: 3.0:1 on white, its edge) - the logo only |
| `--rule` | `#c8c8c8` | same | hairlines on paper (sheets; Lc 29.5 on white, 16.1 on the dark paper) |
| `--desk` | `#f6f1e7` | `#1a1712` | page background: the morning desk (ink 18.65:1); lamp low, warm charcoal |
| `--text` | `#000000` | `#eae6dd` | text, headings, navigation links, control borders, focus ring on the desk (dark: Lc 90.8) |
| `--text-2` | `#3a3a3a` | `#d7d0c6` | secondary text on the desk + objects (dark: Lc 77.5 desk, 76 on the faces) |
| `--line` | `#d0c5b0` | `#5f5a52` | hairlines between sections + rows (decorative; Lc 22.5 light, 17.3 dark, 16 on a card) |
| `--heavy` | `var(--text)` | `#a39e94` | thick rules: masthead, Sources, Keep reading, table heads, On this page (dark: a step under the text) |
| `--disc` | `var(--desk)` | `var(--paper)` | the header bird's disc: the desk itself in light (no halo), paper on the dark desk |
| `--pen` | `#2a51b8` | `#81b4f6` | the blue pen's stroke: link underlines, the ring, Submit, the current section, a chosen guess (6.29:1; 8.33:1) |
| `--pen-text` | `var(--pen)` | `#afd1fc` | a word written in pen on the desk: hovered link, the OS switch, Submit (dark Lc 75.9) |
| `--pen-paper` | `#23459d` | same | the pen on a paper sheet: strike, insert mark, the approval + its tick (7.13:1 Lc 75.9 on the dark paper) |
| `--raised` | `#ffffff` | `#23201c` | memo card, source card, the window in dark: white on the desk, one step up in dark |
| `--sticky` | `#fbf1ae` | `#252317` | the sticky note's face: pale canary (under the highlighter's chroma); dimmed in dark |
| `--sticky-edge` | `var(--sticky)` | `#ded392` | the sticky's top edge: its own face in light, the canary kept in dark |
| `--folder` | `#eedcb9` | `#282217` | a manila folder's face; dimmed in dark (`--text-2` Lc 76.8 light) |
| `--folder-tab` | `var(--folder)` | `#d2ba92` | the folder's tab + top edge: the face in light, the manila kept in dark |
| `--radius` | `14px` | same | every object's corner (cards, sticky, folders, source card) |
| `--win` | `var(--paper)` | `var(--raised)` | the hero window's ground: paper in light, raised one step in dark |
| `--win-ink` | `var(--ink)` | `var(--text)` | window text, frame, title bar + day rules |
| `--win-ink-2` | `var(--ink-2)` | `var(--text-2)` | window secondary text |
| `--win-rule` | `var(--rule)` | `#6a645b` | hairlines between the window's jobs |
| `--serif` | `"Caladea", "Caladea Fallback", "Caladea Fallback Georgia", serif` | same | all text |
| `--mono` | `ui-monospace, "Cascadia Mono", Consolas, Menlo, monospace` | same | the install command only |
| `--gutter` | `clamp(16px, 2.5vw, 32px)` | same | grid column gap (phones; 768px up below) |
| `--side` | `var(--gutter)` | same | page side margin of `.grid` / `.wrap` + the skip link (phones; 768px up below) |
| `--max` | `1320px` | same | widest content box (`.grid`, `.wrap`) |
| `--step--1` | `0.9375rem` | same | small print (15px at default zoom) |
| `--step-0` | `1.25rem` | same | body text (20px) |
| `--step-1` | `1.375rem` | same | lede, large body |
| `--step-2` | `1.75rem` | same | small headings |
| `--display` | `min(clamp(2.5rem, 1.2rem + 3vw, 6rem), 8.6vh + 0.5rem)` | same | home h1: as large as the 1366x641 fold allows |
| `--track-display` | `-0.016em` | same | letter-spacing of display lines (h1 + scene h2, 941px+ wide) |
| `--lead-display` | `1.06` | same | line-height of the same lines: 0.98 (2026-10-03) read cramped at 82-131px in bold - owner 2026-10-04; multi-line text <= 18px >= 1.45 |
| `--ease-mark` | `cubic-bezier(0.3, 0.7, 0.4, 1)` | same | highlighter sweeps, a folder pulled up |

Increase Contrast overrides (`@media (prefers-contrast: more)`, then `... and (prefers-color-scheme: dark)`), checked
per scheme (`more_table`): `--text-2` resolves to `--text`, `--line` >= 3:1, `--pen-text` >= 7:1 on the desk.

| When | Token | Light | Dark | Use |
|---|---|---|---|---|
| more | `--text-2` | `var(--text)` | same | secondary text in full ink |
| more | `--line` | `#767676` | same | hairlines seen: 4.03:1 on the cream, 3.9:1 on the dark desk |
| more | `--pen` | `#1f3c9c` | `#a9cdfb` | the pen's stroke deeper / lighter |
| more | `--pen-text` | `var(--pen)` | `#cfe2fd` | a word in pen: 8.54:1 / 13.57:1 |

768px up, the spacing grows with the display type (owner, plan-dxn.37, S1 look: "such large font and
tiny gutter" - 107px label h2s over a 32px gap, 60px side margin at 1440). Linear in the window width,
continuous with the phone values, so tablets sit in between; phones (< 768) keep the rows above:

| From | Token | Value | Gives |
|---|---|---|---|
| 768px+ | `--gutter` | `min(72px, 5vw - 16px)` | gap 22 / 56 / 72px at 768 / 1440 / 1920: >= 0.4x the largest h2 (107px at 1440x900, 131px at 1920x1080) |
| 768px+ | `--side` | `max(var(--gutter), min(9.52vw - 41px, 11vh - 16px, 128px))` | side margin 32 / 54 / 83px at 768x1024 / 1366x641 / 1440x900 (1576px up the `--max` centring margin is wider: 300px at 1920) - >= 0.75x the h1; capped by height like the display type (`8.6vh` cap): 56px+ at 1366x641 pushes the Mac Copy button under the fold (645px) |

`--max` stays 1320px: at 1440x900 the content box is 1274px (83px margins), columns 55px wide, still wider
than the gap; the 68ch reading measure is unchanged. Home scenes (1080px up) take their block padding from their h2:
`max(clamp(56px, 9vh, 104px), 0.9x the h1)`, label scenes (who sees what, research, closing) 1.15x the h1.
qa SPACE_RATIO (every page at 1440x900 + 1920x1080): gap >= 0.4x the largest h2, side margin >= 0.75x the h1,
each display heading (>= 48px) >= 0.5x its size clear of the next column.

- Hand-written pages use ’ “ ” and spaced – in prose (straight `'` reads as typewriter text at
  display size); the app window + resume sheet keep ` - ` because they mirror what the app prints.
  Test: `test_hand_written_pages_use_typographic_quotes_and_dashes`. Generated pages get the same
  from `pages.typeset` on output only (markdown-it smartquotes + ` - ` / `--` / `10-15` -> –, `...` -> …,
  never in code, URLs or ids like `103-0804`; its (c)/(tm) replacements stay off - not in the font). Sources
  stay straight: lints, `uncited:` snippets and heading ids read them as written. Titles go through
  the same function, so h1 = `<title>` = og:title = JSON-LD = feed. Test:
  `test_every_page_uses_typographic_quotes_and_dashes`.
- Contrast tested statically per scheme (`site_checks.contrasts`): text pairs 4.5:1, control
  borders + focus ring 3:1 (WCAG 1.4.3, 1.4.11); text pairs also APCA Lc >= 75 (its floor for body-size
  text: the secondary grey sets 12-17px bylines, footer, Sources) + hairlines Lc >= 15 (its floor for a
  line still seen). WCAG 2 rated dark mode too kindly: `#bdbdbd` passed at 9.1:1 but read at Lc 65 (light
  Lc 96), dark hairlines `#48484a` at Lc 10 (light 30). The yellow itself carries no meaning => not
  tested. Focus ring two-tone (outline `--text` + spread-only `box-shadow` `--desk`): a
  near-white ring alone vanished on a white sheet in dark mode (1.12:1, measured); the desk band
  keeps it 3:1+ on desk and sheet. Spread-only shadow = a ring, not a depth shadow.
  `::selection` = `--text` on `--desk` (ink, inverted); the check fails it if it paints `--mark`
  or drops under 4.5:1. On the sheets it is their own ink on their own ground (`.proof`: `--ink` on `--paper`,
  `.window`: `--win-ink` on `--win`): the desk's selection was #f2f2f2 on white in dark mode (1.12:1); checked
  >= 3:1 vs each sheet's ground (`SHEETS`). Four schemes checked: light, dark, light + dark w/ Increase Contrast.
- site.css also carries: `<details>` +/- drawn as two `border-top` bars (U+2212 is not in
  the subset; borders survive forced colours, backgrounds don't); forced colours = `<mark>` in
  `Mark`/`MarkText`; print = ink on white in either scheme (tokens reset on `body`, not `:root`,
  so the token table stays one source), no skip link or nav, marks printed (`print-color-adjust`).
- Hover + press (audit A5; before it the site had 0 `:hover` rules - jurors hover every control):
  in the link's own colour (ink; a link in the page is written in pen), never yellow, inside `@media (hover: hover)`
  so a tap leaves nothing stuck. Links + summaries underline 2px (instant), the current Research link 3 -> 4px; Copy a 3px ink border (padding gives the 1px
  back: nothing moves), `:active` 1px into the paper; picks, hub items + Keep reading (folders) pull up
  4px (`transform`, the only eased one, full motion only). No rotating +/- (details
  motion was cut). qa HOVER: every visible link/button/summary on home, hub + an article changes
  on hover and newly paints no `--mark`.
  Home print adds the desktop install steps, no buttons: 3 Letter pages (cap 5).
- One family: Caladea (= resume typeface), Latin subset 400 + 700 preloaded (~19 KB each), name
  table kept (licence); metric-matched fallbacks (Cambria, Georgia w/ size-adjust; Georgia Italic
  for the italic) so the swap moves nothing. Italic 400 (13.7 KB, unhinted: 20.7 hinted) never
  preloaded, never in the first viewport. Features kept: kern liga lnum onum tnum case frac;
  Caladea's `case` only swaps combining accents, so U+0300-0328 stay in the subset or it drops.
  System mono for the command only.
- Home forced colours (B4): the correction's strike becomes a real `line-through` 2px, resume
  bullet dots a border - gradients + backgrounds vanish there. No JS (B6): `@media (scripting:
  none)` hides Copy + the OS switch (nothing would run them) and shows a link to the Mac answer
  (`#mac`); Chrome w/ JS off matches it (measured).
- Questions: every answer `<div>` has an id (`/#mac`, `/#safe` ...), so an answer can be linked. The id sits on
  the answer, not the `<details>`: a link to an element inside a closed `<details>` opens it in Chrome, JS
  or not (measured, 152); the body script opens it elsewhere (`hashchange` + load). `scroll-margin-top`
  keeps the question in view. Mac steps say Return (the Mac key), Windows steps Enter.
- Sizes in rem + vw (text zoom, WCAG 1.4.4); no vh in the home h1 below 1080px wide: browser zoom
  halves the viewport, and the vh cap made the h1 smaller at 200% (x0.95 at 1920x1080); >= 1080
  it stays, guarding the Copy fold (B8); body measure <= 68ch; `text-wrap: balance` on
  headings, `pretty` on body.
- Kept: literal h1 ("A free job-search app for your Windows or Mac computer." - answers "is this
  a website?"); OS-matched app window; no eyebrows, no middle-dot strings, no highlighted word in a
  headline; placeholders generic ("Your Name", no real company or person).
- Scenes: at most one framed object per viewport; marks visible by default; selection, hover +
  focus in ink (never yellow); an illustrated Submit = ink w/ an ink circle (never a 2nd yellow
  control); no clickable control inside an illustration.
- Wide screens fill both halves with real content, never decoration: at 1440x900 + 1920x1080 no home
  row leaves a band > 400 x 200 px empty right of its content, hero columns end within 24 px of each
  other, articles carry an "On this page" column (their h2s, sticky, >= 1280 px only, one gutter right of the
  text - at the window's edge it sat 297 px off at 1440; `pages.py`), the
  hub an "Evidence labels" column (sticky, read from the methods page's label table, >= 1280 px only) and
  About its h2 sections beside its opening (stacked below 1280 px), privacy its Short version (sticky,
  >= 1280 px only), the 404 its drawing in the right half (>= 1024 px). qa.py checks the band (home per
  row; hub, about, methods, privacy + 404 with main as one row, a sticky column counted to its parent's
  bottom) + the article column (TOC_BESIDE: <= 120 px from the text, <= 400 px empty right of it). Privacy: no two rules stacked within 60 px w/o text between (RULES_STACKED).
  A sticky column never hides part of itself: at 1280x720, 1366x641, 1440x780 + 1440x900 each fits the
  window or scrolls w/ the page (qa STICKY_FIT) - the longest On this page hid 88px at 1366x641 (on a Mac
  the last entries just weren't there; Windows drew a 2nd scrollbar). Under 820px tall its rows tighten.
  18 rows fit at 1366x641 (30px each); a list of 19+ scrolls w/ the page there (`.toc:has(li:nth-child(19))`).
- On this page sits before the article in the source (grid places it): after the article, the wide-screen
  list was the 85th Tab stop on the longest page, behind every citation link. The h1 is still main's
  first heading (the list's label is a `<p>`); below 1280px the closed list right after the What to do note is the one shown.
- `<symbol>` + `<use>` on the home page only; shared marks are CSS only (generated pages carry site.css, never
  the home page's SVG).

## Motion

Native CSS only - no animation library, no 3D, no WebGL. Text never waits for motion.

- Opening moment (the one unprompted motion): hero window only, CSS `@keyframes`, <= 2.8 s, once
  per session, skipped after a view transition; never loops; LCP element outside it; hero
  objects opaque from first paint (may shift <= 12px; only marks draw).
  Home: the window's marks, strike, ring + check, timings in `--t0` / `--t1` (s); phones run
  the same drawing on the window's view timeline (cover 5% -> 45%: it starts below the fold).
- Scenes: scroll-driven (`animation-timeline: view()`) as the single path, inside `@supports` +
  `prefers-reduced-motion: no-preference`. No scroll timelines (Firefox) => finished state. Only
  circles, checks + small object shifts animate (one exception below); text opacity 1 at every
  scroll position; start + end layout boxes identical. Home: the resume sheet lifts 12px + its
  second sheet slides out, the "You approved this line" circle + tick and the Submit circle draw in.
- Signature sheet only (owner decision 1, 2026-10-03; relaxes the "only circles + checks" lock
  there): the correction replays on the `.proof` view timeline `--sheet` as the sheet arrives -
  strike on the old line (cover 26-31%), then the new line's two marks (31-36%, 35-40%), all
  finished by cover 40%, before the sheet is centred; then the circle (40-47%) + tick (47-51%).
  Cover ranges only: the figure is taller than a 641px screen, so `entry 70%` lands after
  `cover 26%` (an inverted range: Safari never draws it, Chrome jumps it). Measured: each line is
  wholly on screen when its range starts (bottom in at cover 17-32%; 1366x641 the latest) and finished by mid-screen (48-54%),
  phone through 1920. Reduced motion + Firefox keep the finished state; CSS only, so nothing waits on JS. qa SHEET_REPLAY:
  under way at cover 10%, finished at 40%; MARK_STATE counts the strike as a mark. A drawn shape inside
  an SVG takes its parent `<svg>`'s named `view-timeline` (a subject with a real CSS box). A
  transformed sheet is a stacking context: its paper + border live on `::after`, the second sheet
  on `::before`, so the back sheet never paints over the front one.
- Copy click: sweep on the command line + "Copied". Page change (PICK P-d2, "page laid down"):
  cross-document View Transition, header holds (`view-transition-name: masthead`), `main` is the
  `sheet` - old lifts 8px + fades (300ms), new rises from 12px (340ms, 40ms late), `--ease-mark`;
  keyframes move `transform` + `opacity` only, each done by 400ms (test). No-preference only: all of
  it lives in site.css inside `@media (prefers-reduced-motion: no-preference)` (test fails
  any of it outside), so every page opts in and reduced motion changes page instantly. Browsers w/o
  cross-document transitions (Firefox) change page instantly.
- Animated properties only `transform`, `opacity`, `clip-path`, `stroke-dashoffset` (SVG circle /
  check), `background-size` (wrapping marks + Copy line): compositor-cheap or small paints; any
  other property relayouts or repaints big areas every frame (test fails `@keyframes` +
  `transition` outside the list, `transition: all` too). <= 3 paint animations at once.
- No `will-change` (test): a layer per element for the page's life costs memory on phones; the
  browser promotes during an animation anyway. `overflow: clip`, never `hidden` (hidden makes a
  scroll container, breaking `view()` timelines + sticky).
- Reduced motion: `animation: none; transition: none !important` (never `.01ms`: still fires
  events + a frame of motion). Marks finished, nothing hidden.
- Never: preloader, "scroll to begin", content shown only after an animation, scroll-jacking,
  smooth-scroll libraries, custom cursor, looping or autoplay motion, motion before LCP.

## Budgets

Speed is a design material: Lighthouse 100 kept. Static budgets = tests (`site_checks.budgets`,
every page, each rule w/ a fixture that trips it, `test_each_budget_rule_trips_on_its_fixture`);
KB = 1000 bytes.

| Budget | Max | At redesign start | Why |
|---|---|---|---|
| HTML, gzip | 25 KB | 7.5 KB | phone LCP on a slow line is mostly HTML + fonts |
| Inline JS (raw, JSON-LD aside) | 5 KB | 2.9 KB | main thread free for the first tap |
| Elements in `<body>` | 800 | 162 | style + layout cost per frame of scroll motion |
| First load: gzip HTML + every `@font-face` woff2 + `icon.svg` (+ any linked CSS) | 100 KB | ~45 KB; 73.1 KB home (tab icon 0.6 KB; the header bird is inline) | colophon promises "under 100 KB" |
| Critical requests: HTML + preloads + stylesheets + icon | 5 | 4 | each one a round trip before first paint (why the CSS is built in, never linked) |

- No `<script src>`: an extra request + a parser block; all JS inline.
- Every `<use href="#x">` target on the page: a missing symbol draws nothing, silently.
- Header + footer hold no `<title>`, `<style>` or `id`: copied to every page (an id twice, a 2nd title).
- At most one inline script names `LINES`: tests read the install line from the one that does.
- `<head>` script <= 600 B, no `LINES`: sets `html.is-mac`, `html.is-phone`, `html.seen` before
  first paint (no flash of the wrong OS, no layout shift; classes set at the end of `<body>` came
  after it). `html.seen` = opening moment already ran this session (sessionStorage) or the page
  came in through a view transition (`pagereveal`). CSS selects `html.is-*`, never `body.is-*`.
  Body script keeps Copy, the OS switch and share.
- Browser checks (`uv run app/web/qa.py`): Copy above the fold at 1366x641 (gate) + 1280x593
  (report); phone "Send this page to my computer" ends <= 675px at 390x844 (844 minus Safari's
  bars); phone 320-390, 768, 1366, 1440, 1920 widths + jurors' Mac windows 1440x780, 1512x860,
  1728x1000 (home again w/ a Mac browser name at every desktop size); home <= 8 screens at 1366x641 and
  <= 9 at 375x812 (owner, plan-dxn; 7.12 + 7.90 at the polish base e704f97); <= 1 framed object
  (window, resume sheet) >= 40% on screen at every scroll step (1366x641, 1440x900); <= 3 paint
  animations (background-size, clip-path, stroke-dashoffset) mid-way at once; Mac install line on one
  line (768-1920 wide, a gate); a check finding 0 elements fails; reduced motion = 0 animations + marks
  finished; no JS = all text + the Windows line, no visible
  button, a link to the Mac answer; h1 at 200% zoom >= 100% (1366x641, 1440x900, 1920x1080); text opacity 1 at every scroll step once the
  timed animations end; layout equal reduced vs full motion; forced colours = marks still paint, every
  `<del>` struck, every bullet dot painted; phone 390x844 + iPad 1366x1024 (touch) every non-inline link + button
  >= 44px tall + wide, and each header / footer / nav one keeps >= 24px of its height uncovered by its neighbours'
  hit boxes (Lighthouse target-size); light + dark colours read off computed styles (desk, the pen underline vs ink
  navigation, the hero window + its marks + bird), Increase Contrast (footer text = body text, hairlines #767676)
  and print from a dark screen (window + desk ink on white) - the static contrast check can't see those;
  Research link thicker on /research/** only (1366x641); footer at the window/page bottom (1440x900);
  print <= 5 pages w/ the install line; 0 console errors; every dashed SVG stroke at
  `stroke-dashoffset` 0 in reduced motion, after a full scroll, and above the screen after a
  reload at the bottom; opening moment (1366x641 + 390x844):
  only the hero window animates at load (outside it only scroll-driven scenes), timed ones end <= 2800 ms, hero text opaque + boxes
  within 12px at first paint, LCP element outside every animated element (selector reported),
  a same-tab reload animates nothing; page change via the header links (1366x641):
  `pagereveal.viewTransition` set both ways in full motion, null in reduced, home arriving through
  one skips its opening; `--engines` webkit + firefox; `--self-test` injects 66 faults (G1) into home, articles, hub,
  privacy + 404 (a new check's fault must be caught by that check), each must fail; `--capture DIR` = shots of
  every page at 5 sizes light + dark + `numbers.md` (lengths, print pages, h1/h2 px) for before/after. Mark = `<mark>` or class `mark` (new kinds
  carry it, or the checks can't see them).
- Perf (`qa.py --perf`, median of 3 vs a frozen copy of the polish base): phone LCP <= 1.5 s
  + <= baseline + 0.3 s; desktop LCP <= 0.5 s; CLS <= 0.01; long frames during scroll <= baseline
  max + 50 ms and < 250 ms; click -> next paint <= 100 ms; Copy -> "Copied" <= 150 ms. Idle frame
  interval > 18 ms = invalid run (busy machine), not a failure. Profiles: phone, desktop (Win +
  Mac UA), no-GPU desktop w/ raster trace (frames > 33.4 ms <= 5%). Baseline = `docs/` at the
  polish base sha (`BASELINE_SHA`, e704f97) in `.data/site-baseline/`, made by `git archive SHA:docs` - plain
  `git archive SHA docs` comes back empty (`/docs/** export-ignore`).
- Lighthouse (`qa.py --lighthouse`, pinned version, gzip server, JSON in `.data/site-qa/`):
  Accessibility + Best Practices 100 every run; Performance median of 3 = 100 desktop, >= 99
  phone; every SEO audit passes but canonical (localhost) + is-crawlable on the noindex 404 -
  so the 404 keeps a meta description.

## Judging

Awwwards jury: Design 40 / Usability 30 / Creativity 20 / Content 10 (checked 2026-10-03).

- No model scores its own work: a model rates what it made high, whatever it is.
- Mechanical checks first (tests, qa.py); then pairwise yes/no comparisons that name something
  checkable - new vs the frozen pre-redesign site, new vs reference winners without WebGL
  (mosbyfiles.com, seasoned.koto.studio, stateofaidesign.com, adaline.ai, exat.hottype.co).
- Owner = outside judge: two reviews, one batch of fixes, one confirming look, then stop -
  endless polish rounds drift.

## Rules + why

- No third-party requests (fonts, scripts, images, CSS `url()`): privacy page promises it; test enforces.
- Loaded URLs root-relative (`/fonts/x.woff2`, or `data:`): 404.html is served at any depth.
  Links: `/...`, `#id`, `https:` or `mailto:` only; folder links end in `/` (`/research/`, else
  Pages redirects); every `#id` must exist on its target page.
- Paths exact-case: macOS disks match `/Fonts/x` to `fonts/x`, Pages answers 404. Tests compare
  against names listed from disk, never `is_file()`.
- Each indexed page's canonical = its own URL (folder `index.html` -> the folder); page w/o
  canonical -> `noindex`. Sitemap = exactly the indexed URLs, once each. Titles + descriptions unique.
- Shared CSS = `app/web/css/site.css` (fonts, tokens, base type, `.grid`, `.wrap`, skip link, header, footer), built
  into every page by pages.py, the same block on each; test guards. `.grid` = 12 columns, gap
  `--gutter`, side margin `--side`, max `--max`, for composed pages (home); `.wrap` = the same outer box w/o columns
  (generated pages, privacy, 404), so every edge lines up with the header.
- Header (`<header class="masthead">`: skip link to `<main id="main">`, brand, Research
  `/research/`, Install `/#install`, Source code) + bare `<footer>` (Made by -> www.enrriquez.com
  · Terms `/terms.html` - in the credit line, so the nav keeps 6 links; then `<nav aria-label="Footer">` Home, Research, Install, About, Privacy, Source code - owner,
  plan-dxn: no dead end at the bottom of a 20-screen article, About one click from home)
  byte-identical on every page; test guards. Every page's `<main>` carries `id="main"`. Under the
  header a full-bleed double rule (3px + 1px, 4px apart) - the newspaper masthead.
- Current page: on /research/** the header's Research link has a 3px underline (ink), keyed off the
  page's canonical (`:root:has(link[rel=canonical][href*="/research/"])`) so header bytes stay one copy.
- Phone header: brand + 4 links don't fit a 360/375/390px screen (328/343/358 usable) => header
  Source code hidden <= 600px (footer keeps it); <= 359px the links may wrap below the brand.
  Phone footer: the credit, then its 6 links as 2 even rows of 3 (no link alone on a row).
- Touch (`pointer: coarse`): links in nav + footer, the brand and `.tap` links get hit boxes >= 44px
  tall (Apple HIG 44x44pt; WCAG 2.5.8's 24px is the floor) via padding + an equal negative margin, so
  layout + look don't change; the short inline words in header links, crumbs + footer also grow 6px each side
  (footer Home + About were 42px wide, the crumb Home 36px) - only those: block links (On this page) kept the
  shared margin and shifted out of line. Wide touch screens (iPad landscape): On this page's rows are real 44px rows
  (the shared margin overprinted them 12px apart, measured 2026-10-07), and home's desktop install controls get
  touch boxes too: Copy 44px tall, the OS switch, "Read the script first" + the closing "Go to the install steps"
  45px boxes (they were 26-40px; a wrapped switch row sets its rows 45px apart). A Sources entry's links (DOI, Publisher,
  Open copy) sit on their own row 28px apart (HIG: spacing matters as much as size; they were two 18px words one
  space apart at the end of the sentence), each a 45px x >= 44px box on touch, in the source card too, and so is
  its "All sources". Links inside running text are exempt. Footer links are grid/flex items
  (box = 1lh, not 1.1em): exactly 45px each, rows `45px - 1lh` apart - two rows 8px apart w/ 53px boxes
  overlapped, Lighthouse read Research as covered (20.4px left) => accessibility 95 on phones (G1, 2026-10-04).
- Taps: links, buttons + summaries `touch-action: manipulation` (no double-tap zoom wait) and an ink tap
  tint (`color-mix` of `--text`, 14%) - the browser's grey box vanished on the dark desk. A research pick /
  hub item is one link (title link's `::after` covers the item): its rule + description react to the
  pointer, so a click there lands (it was a dead zone). Copy sits 10px inside its box (2px border + 8px
  padding): radii 6 + 16, so the corners run parallel.
- Words that belong together don't break: `&nbsp;` in 5&nbsp;minutes, 100&nbsp;KB, Windows&nbsp;10,
  Copilot&nbsp;Pro (hand-written pages). Dates US order ("October 3, 2026", `pages.long_date`): en_US site.
- Short pages: body is a flex column, min-height 100svh, main grows => the footer sits at the window's
  bottom (404), never a blank band under it. Screen only (print keeps block flow).
- `docs/index.html` marks each part with `<!-- region: name -->` ... `<!-- /region: name -->` so a
  change finds its part by grep.
- Layout checked in a real browser: `uv run app/web/qa.py` (PEP 723, Chrome; playwright pinned
  to the cached WebKit + Firefox builds) serves `docs/` gzipped, opens every page as a phone at
  320/360/375/390px + desktop at 768/1366x641/1440/1920px; fails on sideways scroll, a two-line
  header from 360px, or Copy below the fold at 1366x641. Screenshots in `.data/screens/`.
  Width = `clientWidth`: a phone's `innerWidth` grows to fit a too-wide page.
- No-JS pages still run CSS animations but never fire timers or frames: qa.py sleeps out the
  timed ones from Python (an awaited promise there hangs forever).
- Install line static in HTML (Windows), JS swaps for Mac; FAQ carries the Mac line as text ->
  no-JS readers + crawlers see a command.
- Never look like a fake "paste this to verify" page: clipboard written only on Copy click, full
  command always visible, no key combos, "Read the script first" link to the GitHub file (never
  `/win` `/mac`: served as HTML), no command on the share image.
- robots.txt Disallow `/mac/` `/win/` - not `/mac` (prefix: would also block a future `/macos.html`).
- robots.txt allows search, retrieval AND AI training bots on purpose (free public tool, research meant to be quoted; Google-Extended never blocked): a `# Training bots:` comment lists both groups (2026-10-03). `.well-known/security.txt` Contact = GitHub private advisory; `docs/_config.yml` `include` keeps Jekyll from dropping the dot folder; test fails within 30 days of Expires - renew yearly.
- Home JSON-LD = WebSite only (site name in results); research pages carry their own (above). SoftwareApplication w/o ratings = invalid in
  Search Console; FAQ rich results now limited to government + health sites.
- `og:title` w/o brand suffix (`og:site_name` carries it). Cards 1200x630, < 300 KB (WhatsApp
  drops larger). `assets.render_card()` screenshots a 1200x630 clip and fails loudly on an element
  outside the card, in its bottom 90px (X lays its headline there) or clipped by an overflow-hidden
  box. Changed -> bump `og.png?v=N` (home, privacy, terms) or `pages.CARD_V` (tests follow it) (LinkedIn caches a preview ~7 days).
- 404.html: root paths only (served at any depth), noindex, no canonical.
- No front matter in any file, no `.md`, no path segment starting `_` `.` `#` or ending `~`:
  GitHub Pages runs Jekyll, which would template or drop them (test checks tracked `docs/` files).

## Measured

- GitHub Pages types: `.ico` image/vnd.microsoft.icon, `.webmanifest` application/manifest+json,
  `.woff2` font/woff2 - no headers file needed.
- `/privacy` + `/index.html` also answer 200 -> every page carries a canonical == sitemap URL.
- Font subset: regular 18.2 KB, bold 18.2 KB; og.png 81.4 KB, og-research.png 51.6 KB.
- Polish pass end (plan-dxn G1, 2026-10-04, vs base e704f97): home 7.28 screens at 1366x641 (was 7.12),
  8.11 at 375x812 (was 7.90), print 5; perf median of 3 phone LCP 532 ms (base 516), desktop 116 (92),
  no-GPU 336 (276), CLS 0, scroll long frame 136-149 ms (base 136-146); Lighthouse 6 pages x phone +
  desktop x 3 runs: Accessibility + Best Practices 100 every run, Performance median 100 everywhere.
  First Lighthouse run caught footer tap boxes overlapping on phones (accessibility 95) - fixed + qa HIT_OVERLAP.

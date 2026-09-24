// Page model arrives as JSON (resume/render.py page_model) => strings never parsed as markup
#let d = json(bytes(sys.inputs.data))
// one ink for every glyph: VMock's colour check (2026-09-24) flagged the navy name, headings and
// titles - "all text should be black" - and render.py's text-color gate holds the page to it
#let ink = rgb("#1A1A1A")

#set document(title: d.title)
#set page(paper: "us-letter", margin: (x: d.page.margin_x_in * 1in, y: d.page.margin_y_in * 1in), header: none, footer: none)
// family comes from settings (resume.font) so page rules and measurements stay one source
// ligatures off => extracted text never carries U+FB01/FB02
#set text(font: d.page.font, size: 11pt, tracking: d.page.tracking_em * 1em, fill: ink, lang: "en", hyphenate: false, ligatures: false)
// default edges: line pitch = cap-height (~0.66em) + leading => 1.40
#set par(justify: false, leading: 0.74em, spacing: 0.74em)
#set list(marker: [•], indent: 0.2em, body-indent: 0.5em, spacing: 0.74em + 3.5pt)
// wrap at hyphen glues halves in pdftotext default mode ("LLM-backed" -> "LLMbacked") => box keeps token whole
#show regex("\w+(-\w+)+"): it => box(it)

#let sep = [ #h(0.3em)|#h(0.3em) ]

// no letterspacing of its own: at +0.08em VMock read EXPERIENCE back as "EXP E R I ENC E"
// (2026-09-24), while body text at the page's +0.015em came back whole - split-words gate
#let section(heading-text, body) = {
  block(above: 14pt, below: 6pt, sticky: true)[
    #text(size: 11.5pt, weight: 600)[#upper(heading-text)]
    #v(-6pt)
    #line(length: 100%, stroke: 0.6pt + ink)
  ]
  body
}

// first thing under a heading sits the same distance below it in every section, entry or line:
// a job's 10pt lead there made EXPERIENCE 7.5pt looser than SKILLS (VMock "Section Spacing",
// 2026-09-24) - heading-gap gate
#let first-gap = 0.74em + 2.5pt

// dates inline, never h(1fr) right column: pdftotext default mode read it as 2nd column, after bullets
// no bullets (a school, a career break) => spaced like a line, not a job: two rows, no empty list gap
#let entry(e, first) = block(above: if first { first-gap } else { 0.74em + if e.bullets.len() > 0 { 10pt } else { 2.5pt } }, below: 0pt, breakable: true)[
  #block(below: if e.bullets.len() > 0 { 0.74em + 2.5pt } else { 0pt }, sticky: true)[
    #text(weight: 600)[#e.heading]#if e.at("org", default: none) != none [#sep#text(weight: 600)[#e.org]]
    #if e.at("subline", default: none) != none [ \ #text(number-width: "tabular")[#e.subline]]
  ]
  #if e.bullets.len() > 0 { list(..e.bullets.map(b => [#b])) }
]

#text(size: 20pt, weight: 700, tracking: -0.01em)[#d.contact.name]
#v(-4pt)
// box per part => wrap breaks at separators only, never inside an email or url (contact-in-body gate)
// part_urls is parallel to parts, "" where the part is not a link => that part stays plain text.
// link() takes the part as a string body, so nothing here is parsed as markup, and a link
// carries the same glyphs at the same widths => measurement and the text layer are untouched
#let urls = d.contact.at("part_urls", default: ())
#d.contact.parts.enumerate().map(p => {
  let url = urls.at(p.at(0), default: "")
  box(if url == "" { p.at(1) } else { link(url, p.at(1)) })
}).join(sep)

// the user's own one-line headline: what they are, in their words, read first (VMock "Branding Title")
#let headline = d.at("headline", default: none)
#if headline != none [
  #block(above: 10pt)[#text(weight: 600)[#headline]]
]

#if d.summary != none [
  #block(above: if headline != none { first-gap } else { 10pt }, width: 90%)[#d.summary]
]

#for s in d.sections {
  section(s.title, {
    for (i, e) in s.at("entries", default: ()).enumerate() { entry(e, i == 0) }
    for line in s.at("lines", default: ()) {
      block(above: first-gap, below: 0pt)[
        #if line.at("label", default: none) != none [#text(weight: 600)[#line.label: ]]#line.text
      ]
    }
  })
}

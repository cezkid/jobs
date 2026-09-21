// Page model arrives as JSON (resume/render.py page_model) => strings never parsed as markup
#let d = json(bytes(sys.inputs.data))
#let accent = rgb("#1F3A5F")
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

#let section(heading-text, body) = {
  block(above: 14pt, below: 6pt, sticky: true)[
    #text(size: 11.5pt, weight: 600, fill: accent, tracking: 0.08em)[#upper(heading-text)]
    #v(-6pt)
    #line(length: 100%, stroke: 0.6pt + accent)
  ]
  body
}

// dates inline, never h(1fr) right column: pdftotext default mode read it as 2nd column, after bullets
#let entry(e) = block(above: 0.74em + 10pt, below: 0pt, breakable: true)[
  #block(below: 0.74em + 2.5pt, sticky: true)[
    #text(weight: 600, fill: accent)[#e.heading]#if e.at("org", default: none) != none [#sep#text(weight: 600)[#e.org]]
    #if e.at("subline", default: none) != none [ \ #text(number-width: "tabular")[#e.subline]]
  ]
  #list(..e.bullets.map(b => [#b]))
]

#text(size: 20pt, weight: 700, fill: accent, tracking: -0.01em)[#d.contact.name]
#v(-4pt)
// box per part => wrap breaks at separators only, never inside an email or url (contact-in-body gate)
#d.contact.parts.map(part => box(part)).join(sep)

#if d.summary != none [
  #block(above: 10pt, width: 90%)[#d.summary]
]

#for s in d.sections {
  section(s.title, {
    for e in s.at("entries", default: ()) { entry(e) }
    for line in s.at("lines", default: ()) {
      block(above: 0.74em + 2.5pt, below: 0pt)[
        #if line.at("label", default: none) != none [#text(weight: 600)[#line.label: ]]#line.text
      ]
    }
  })
}

// Cover letter (resume/letter.py). Same header, ink, type and spacing as resume.typ - the two
// go to one employer side by side. Data arrives as JSON => strings never parsed as markup
#let d = json(bytes(sys.inputs.data))
#let ink = rgb("#1A1A1A")

#set document(title: d.title)
#set page(paper: "us-letter", margin: (x: d.page.margin_x_in * 1in, y: d.page.margin_y_in * 1in), header: none, footer: none)
#set text(font: d.page.font, size: 11pt, tracking: d.page.tracking_em * 1em, fill: ink, lang: "en", hyphenate: false, ligatures: false)
#set par(justify: false, leading: 0.74em, spacing: 1.2em)
#show regex("\w+(-\w+)+"): it => box(it)

#let sep = [ #h(0.3em)|#h(0.3em) ]

#text(size: 20pt, weight: 700, tracking: -0.01em)[#d.contact.name]
#v(-4pt)
#let urls = d.contact.at("part_urls", default: ())
#d.contact.parts.enumerate().map(p => {
  let url = urls.at(p.at(0), default: "")
  box(if url == "" { p.at(1) } else { link(url, p.at(1)) })
}).join(sep)

#v(18pt)
#d.date

#v(6pt)
#d.greeting

#for p in d.paragraphs [
  #p

]
#d.closing \
#d.contact.name

// Shared by every layout (METHOD.md): same text, same typeface, only the arrangement changes.
// Facts arrive as JSON (parser_test.py build) => strings are never parsed as markup.
#let d = json(bytes(sys.inputs.data))
#let sep = [ #h(0.3em)|#h(0.3em) ]

#let setup(body) = {
  // date none => Typst writes no creation date (default: the clock) => rebuilds are byte-identical
  set document(title: "Resume parser test", date: none)
  set page(paper: "us-letter", margin: 0.6in)
  // the app's own text settings: ligatures off, no hyphenation
  set text(font: "Caladea", size: 10.5pt, fill: black, lang: "en", hyphenate: false, ligatures: false)
  set par(justify: false, leading: 0.6em, spacing: 0.6em)
  set list(marker: [•], indent: 0.2em, body-indent: 0.5em, spacing: 0.45em)
  // a wrap at a hyphen would split 010-0199 => kept whole, as the app does
  show regex("\w+(-\w+)+"): it => box(it)
  body
}

#let name-text = text(size: 20pt, weight: 700)[#d.name]
#let contact-line = [#box(d.email)#sep#box(d.phone)#sep#box(d.location)]
#let heading-text(t, tracking: 0em) = text(size: 11pt, weight: 700, tracking: tracking)[#upper(t)]

#let section(t, body, tracking: 0em) = {
  block(above: 12pt, below: 6pt, sticky: true)[
    #heading-text(t, tracking: tracking)
    #v(-5pt)
    #line(length: 100%, stroke: 0.5pt)
  ]
  body
}

#let job-header(j) = [#text(weight: 700)[#j.title]#sep#j.employer#sep#j.dates]
#let job(j) = block(above: 9pt, below: 0pt)[
  #block(below: 5pt, sticky: true, job-header(j))
  #list(..j.bullets.map(b => [#b]))
]
#let jobs = d.jobs.map(job).join()
#let edu-line(e) = [#e.degree#sep#e.school#sep#e.dates]
#let education = d.education.map(e => block(above: 0pt, below: 4pt, edu-line(e))).join()
#let skills = d.skills.map(s => block(above: 0pt, below: 4pt)[#s]).join()

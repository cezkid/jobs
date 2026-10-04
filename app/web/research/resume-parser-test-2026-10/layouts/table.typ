// The whole page as one 2-column table: section names + dates in the left cell, content in the
// right (METHOD.md). A job's dates share a row with its title and employer.
#import "common.typ": *
#show: setup

#let head(t) = (table.cell(colspan: 2, inset: (top: 10pt, bottom: 4pt, x: 0pt))[#heading-text(t)], )
#let job-row(j) = (
  [#j.dates],
  [#text(weight: 700)[#j.title]#sep#j.employer
   #list(..j.bullets.map(b => [#b]))],
)
#table(columns: (1.35in, 1fr), stroke: none, inset: (x: 0pt, y: 3pt), column-gutter: 0.2in,
  [], [#name-text \ #contact-line],
  ..head("Summary"),
  [], [#d.summary],
  ..head("Experience"),
  ..d.jobs.map(job-row).flatten(),
  ..head("Education"),
  ..d.education.map(e => ([#e.dates], [#e.degree#sep#e.school])).flatten(),
  ..head("Skills"),
  ..d.skills.map(s => ([], [#s])).flatten(),
)

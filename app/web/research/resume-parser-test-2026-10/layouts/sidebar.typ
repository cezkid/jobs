// Two columns: name + summary across the top, a sidebar (contact, education, skills) beside the
// experience column (METHOD.md).
#import "common.typ": *
#show: setup

#name-text
#section("Summary")[#d.summary]
#v(6pt)
#grid(columns: (2.05in, 1fr), column-gutter: 0.3in,
  [
    #block(above: 12pt, below: 4pt, box(d.email))
    #block(above: 0pt, below: 4pt, box(d.phone))
    #block(above: 0pt, below: 4pt, box(d.location))
    #section("Education", education)
    #section("Skills", skills)
  ],
  section("Experience", jobs),
)

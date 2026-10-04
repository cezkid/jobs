// Designer template of placed boxes: each block sits at a fixed spot on the page. The file draws
// them out of reading order - experience first, then the side box, the summary, the header last
// (METHOD.md).
#import "common.typ": *
#show: setup

#place(top + left, dy: 1.45in, block(width: 4.55in, section("Experience", jobs)))
#place(top + left, dx: 4.85in, dy: 1.45in, block(width: 2.45in)[
  #section("Education", education)
  #section("Skills", skills)
])
#place(top + left, dy: 0.55in, block(width: 100%, section("Summary")[#d.summary]))
#place(top + left, block(width: 100%)[
  #name-text
  #v(-4pt)
  #contact-line
])

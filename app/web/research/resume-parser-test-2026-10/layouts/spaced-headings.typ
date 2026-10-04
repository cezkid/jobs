// The control with letter-spaced section headings, +0.25em between letters (METHOD.md).
#import "common.typ": *
#show: setup

#name-text
#v(-4pt)
#contact-line
#section("Summary", tracking: 0.25em)[#d.summary]
#section("Experience", jobs, tracking: 0.25em)
#section("Education", education, tracking: 0.25em)
#section("Skills", skills, tracking: 0.25em)

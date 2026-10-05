// Name in the page header, email, phone and city in the page footer (METHOD.md).
#import "common.typ": *
#show: setup
#set page(margin: (x: 0.6in, top: 1.1in, bottom: 0.9in),
  header: align(left + bottom, name-text),
  footer: align(center, contact-line))

#section("Summary")[#d.summary]
#section("Experience", jobs)
#section("Education", education)
#section("Skills", skills)

// Icons in place of contact labels: drawn (vector) envelope, phone, pin; no text in them (METHOD.md).
#import "common.typ": *
#show: setup

#let svg(body) = box(baseline: 15%, image(bytes(
  "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='none' stroke='black' stroke-width='1.4'>" + body + "</svg>"),
  format: "svg", height: 0.85em))
#let envelope = svg("<rect x='1.5' y='3.5' width='13' height='9'/><path d='M1.5 3.5 L8 9 L14.5 3.5'/>")
#let phone = svg("<rect x='4.5' y='1.5' width='7' height='13' rx='1.5'/><path d='M7 12.5 H9'/>")
#let pin = svg("<path d='M8 15 C4 10 3 8 3 6 A5 5 0 0 1 13 6 C13 8 12 10 8 15 Z'/><circle cx='8' cy='6' r='1.8'/>")

#name-text
#v(-4pt)
#envelope #h(0.25em)#box(d.email) #h(1.2em) #phone #h(0.25em)#box(d.phone) #h(1.2em) #pin #h(0.25em)#box(d.location)
#section("Summary")[#d.summary]
#section("Experience", jobs)
#section("Education", education)
#section("Skills", skills)

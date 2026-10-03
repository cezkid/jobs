---
reviewed: 2026-10-03
verdict: publish
reviewer: fresh AI session, bead plan-xsy.16 (no drafting context)
---
# Review: Research hub intro (`index.md`)

The build exempts the hub intro from the review gate (`pages.reviews()`: "a few lines over the
list"); reviewed anyway because its two promises frame every article. Read against the methods
page, `research.md` labels, `pages.EVIDENCE`.

## Claim table

| # | Claim | What is true | Verdict |
|---|---|---|---|
| 1 | "What studies say about AI, hiring and resumes. Plain words, short answers first." | `research.md` Style: Short answer box first, plain-words lint | Supported |
| 2 | "Every claim links to a source you can open." | Convention claims have no study; Our measurement has no outside source (same as methods M5) | Overstated (H1) |
| 3 | "Every source is graded: big study, small study, survey, lab test, law or convention." | Scale also has Vendor survey + Our measurement; in-text label is "Lab study", Sources list says "Lab test (not real hiring)" | Incomplete (H2) |
| 4 | Link to How we research | `methods.md` - resolves once methods is published | Supported |

## Findings

Status: open = for the revise bead (plan-xsy.17). All answered by plan-xsy.17 on 2026-10-03.

- **H1 (medium) - "every claim links to a source".** status: fixed. Same wording as methods M5. Reword in step with methods
  M5: "Every claim from a study links to it. Every claim carries a label for how strong it is."
- **H2 (low) - grade list incomplete + label drift.** status: fixed. Full label list incl. company survey, lab study, our own tests. Add "company survey" (vendor
  survey in plain words) and "our own tests", or say "graded by how the study was done" and let
  the methods page carry the list. Use "lab study" to match the in-text label.
- **H3 (low) - no AI note on the hub.** status: fixed. "Written with AI help, checked by a fresh AI review and by Cesar." + methods link. The hub is the section's front door; one
  line "Written with AI help, checked by a fresh AI review and by Cesar" + the methods link makes
  the disclosure self-evident (Google How guidance) at little cost. Keep it in step with methods
  M1 wording.
- **H4 (info) - no `og_title`.** status: fixed. og_title "Research: AI and resumes, with sources". Hub falls back to title "Research" (8 chars) on
  share previews - vague out of context. Consider og_title "Research: AI and resumes, with sources".

## Verdict

revise - H1 is the same over-promise as methods M5 and should land with it. Not gated by the
build; this file records the review for the revise bead.

## Revision (plan-xsy.17, 2026-10-03)

Every finding above fixed on the page or moved to a filed bead (named in its status). Verdict set to publish by the revise bead per app/docs/research.md; the owner read at ship (plan-xsy.36) is still required, and plan-xsy.44 holds the owner facts.

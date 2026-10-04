---
reviewed: 2026-10-04
verdict: publish
reviewer: fresh AI session, bead plan-xsy.60 (no drafting context; sources opened before the draft was read)
---
# Review: AI hiring laws in 2026: what employers must tell you (`ai-hiring-laws.md`)

Verdict **revise**: 3 high, 9 medium, 12 low findings (all closed in plan-xsy.61: 23 fixed, 1 rebutted - see Resolution). Most facts match their sources:
New York City's rule, Connecticut's act, Illinois' synopsis, the FAccT and Comptroller numbers and
the Mobley order all check out. The problems: the article misses rights that already exist (EU
GDPR Article 22, California's privacy-agency rules from January 2027), so "Colorado only" and
"only Colorado lets you ask a person" are wrong; it misses that Colorado's law is under a federal
court enforcement stay (lead, primary not yet opened); the FAccT count is sold as an enforcement
measure and as "New York City employers" when 124 of the 391 had no city jobs; and Colorado's
"explanation" is a description of the tool's role, not of the decision.

## Sources, read before the draft (all opened 2026-10-04, fresh downloads in `~/.cache/plan-xsy.60/`)

| id | What it actually supports | Limits |
|---|---|---|
| nyc-ll144 | DCWP page: no AEDT unless bias audit within 1 year, audit info public, notices given; enforcement from July 5, 2023; complaint form for missing audit, summary or notice; notice 10 business days before use | Agency summary page; the law text itself not opened |
| nyc-aedt-rule | 6 RCNY 5-303: before use, post audit date + summary + distribution date; keep posted 6 months after last use. 5-304(a): notice explains how to ask for an alternative process or accommodation "if available"; no duty to offer one. 5-304(b): notice to city residents on careers page, posting or mail/email 10 business days before use. 5-304(d): post data retention policy, data type and source on the careers site AND answer written requests within 30 days | Rule, not the law; "unless already on website" wording is the law's (§ 20-871(b)(3)), not opened |
| wright-2024 | FAccT 2024, peer-reviewed. 155 student investigators, 391 employers (random draw from employers hiring Cornell grads), data Oct 24-Nov 9, 2023; 18 audit reports (5%), 13 notices (3%) (Table 1 p. 8). Of 267 employers listing NYC jobs: 14 audits, 12 notices; 124 had no NYC listing. Abstract p. 1: law gives "substantial discretion"; null result "cannot be said to indicate non-compliance". Notices shown only after applying could not be seen. 23 of 26 responding firms said the law did not apply | Measures what was posted, not enforcement; not a sample of all NYC employers |
| nys-comptroller-2025 | State audit Dec 2, 2025, period July 2023-June 2025: DCWP reviewed 32 companies, found 1 issue; auditors found >= 17 instances of potential non-compliance at the same companies; 2 AEDT complaints; "complaint process is ineffective"; penalties $500-$1,500 per day | Audit of the agency, not of employers generally |
| co-sb26-189 | Bill page summary (as enacted): signed 05/14/2026; ADMT = output used to make, guide or assist a decision; consequential decision includes employment; developer duties "starting January 1, 2027"; deployer gives clear notice at point of interaction; "plain language description of a covered ADMT's role" within 30 days after an adverse outcome; AG rules on that by Jan 1, 2027; right to request personal data + correct factually incorrect data; right to request "meaningful human review and reconsideration"; AG enforces as deceptive trade practice; 60-day cure before 2030 "if a cure is deemed possible"; no new private right of action; repeals + reenacts SB24-205 | Summary only - the signed act text was not reachable (bill-text links load by script; guessed PDF URLs 404). The summary states January 1, 2027 for developer duties only; deployer/consumer start date not in the summary |
| co-sb23-058 | Bill page summary: "Starting July 1, 2024" no age, birth date, school attendance or graduation dates on an initial application; BFOQ / law age checks allowed; transcripts may be asked for if employer says the dates may be redacted; CDLE enforces, penalties from 2nd violation; no private cause of action; act effective August 7, 2023 | Not an AI law. Registry `sample` says the ban applies "from August 7, 2023" - the summary says July 1, 2024 |
| ct-pa26-15 | Public Act 26-15, approved May 27, 2026. Sec 7 definitions (substantial factor, employment-related decision). Sec 8-10 apply to deployment on/after Oct 1, 2027: Sec 9 plain-language disclosure of interaction unless obvious; Sec 10 written notice before the decision: that it is deployed, purpose + nature of decision, trade name, categories of personal data + how assessed, sources, deployer contact. Sec 11 trade-secret withholding with a notice. Sec 12 AG only, 60-day cure for violations through Dec 31, 2027, no private right. Sec 13 (eff. Oct 1, 2026) use of the tech "shall not be a defense" to a discrimination complaint | No explanation, correction or human-review right in secs 7-13 (confirmed) |
| il-hb3773 | ilga.gov bill status (fetched live 2026-10-04 with a browser user agent; same bytes as the Aug 28 Wayback copy): Governor approved 8/9/2024, PA 103-0804, effective Jan 1, 2026. Synopsis: civil rights violation to use AI that "has the effect of subjecting employees to discrimination" or zip codes as a proxy; and "to fail to provide notice to an employee" that AI is used | Synopsis, not the enrolled text; synopsis says "employee" (the Act's definitions decide whether applicants count - not opened) |
| ca-crc-ads-2025 | Council announcement: approved June 27, 2025, effective Oct 1, 2025; ADS may violate CA law if it harms applicants on protected traits; keep records incl. ADS data 4 years; ADS tests/puzzles eliciting disability info may be an unlawful medical inquiry | Announcement only; registry `sample` claims Attachment B was read - not re-opened by the drafter (bead .59 notes) or by me. No notice or request right here |
| nj-dcr-2025 | AG announcement Dec 17, 2025: DCR "adopted" disparate impact rules under the LAD; rules explain how "automated online application tools or facial analysis software in hiring" may have disparate impact | Announcement; effective date not stated on the page (rule PDF not opened) |
| eeoc-ada-preemployment | EEOC 1995 enforcement guidance: no disability questions before a conditional offer; employer may describe the hiring process and ask whether an accommodation is needed for it; may ask for documentation if need not obvious | Agency guidance, not the statute; says nothing about AI tools |
| eu-ai-act | artificialintelligenceact.eu reproduction: Annex III 4(a) recruitment/selection, "analyse and filter job applications, and to evaluate candidates"; Art 26(11) deployers of Annex III systems that make or assist decisions inform the persons; Art 86 right to "clear and meaningful explanations of the role of the AI system" (decisions with legal or similarly significant effects) | Reproduction site; may not show the July 2026 omnibus amendments |
| eu-omnibus-2026 | Commission news 27 July 2026: omnibus in force; Annex III high-risk rules apply from 2 December 2027; Annex I from 2 August 2028 | News page, not the amending regulation |
| eo-14281 | EO of Apr 23, 2025 (FR Apr 28): policy "to eliminate the use of disparate-impact liability in all contexts to the maximum degree possible"; agencies "deprioritize enforcement" of disparate-impact provisions incl. 42 U.S.C. 2000e-2; AG + EEOC Chair review pending matters within 45 days | Directs federal agencies; does not amend Title VII |
| eo-14365 | EO of Dec 11, 2025: AG sets up AI Litigation Task Force within 30 days, "sole responsibility" to challenge state AI laws; Colorado law named ("may even force AI models to produce false results") | - |
| doj-xai-2026 | DOJ press release Apr 24, 2026: moved to intervene in xAI suit against Colorado SB24-205; alleges Equal Protection violation | Press release on a motion; nothing decided |
| mobley-2026-order | ECF 360, June 22, 2026 (12 pp.): plaintiffs allege Workday's screening tools discriminated by race, age, disability (p. 1); Mobley earlier proceeded on Title VII race, ADA, ADEA disparate impact (p. 1-2); FEHA nexus adequately pled (p. 3-4); Hughes ADA kept; Rowe race claim dismissed; claim about Workday's own hiring dismissed (p. 11) | Pleading ruling only. Says nothing on whether federal law bans AI screening |
| clearinghouse-mobley | Case summary updated Dec 17, 2025: Workday answered denying allegations; May 16, 2025 preliminary collective certification (ADEA); July 7, 2025 HiredScore included; Dec 2, 2025 notice plan; docket list through June 22, 2026 | Secondary summary of court events |
| lawyer-monthly-2026 | News, Sept 2026 (date from URL only): plaintiffs asked the court "to certify four proposed subclasses" (African American applicants, women, over 40, disability); class-certification hearing March 9, 2027, Judge Rita F. Lin | News; does not itself say "Workday denies" in the passages read |

No text in any source addressed an AI (scanned all 19 for instruction-like text).

## Claim table

Counts: the article has 41 citation groups and 47 source-id citations (`grep -o '\[@[^]]*\]' | wc -l` = 41; per-id `grep -o '@[a-z0-9-]*'` totals 47). The table has 70 rows.

| # | Line | Claim (short) | Source | What the source says | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|---|
| 1 | SA1 | No federal law bans AI resume screening, Oct 2026 | mobley-2026-order | Order is silent on this; absence of a ban is not in any source | unsupported (wrong cite) | medium | Move to `uncited:` with what was searched, or cite statute-level framing; keep the order only for "old laws apply" |
| 2 | SA1 | Old discrimination laws still apply | mobley-2026-order | Claims under Title VII/ADA/ADEA/FEHA proceed at pleading stage | supported, needs caveat | low | "a court let claims under them go on" |
| 3 | SA2 | Notice now: NYC | nyc-ll144 | Yes | supported | - | - |
| 4 | SA2 | Notice now: Illinois | il-hb3773 | Synopsis: notice to "an employee" | needs caveat | low | See F14 |
| 5 | SA2 | Colorado 2027 | co-sb26-189 | Summary gives Jan 1, 2027 for developer duties only; enforcement stayed by court (lead, F3) | needs caveat | high | See F3, F7 |
| 6 | SA2 | Connecticut 2027 | ct-pa26-15 | Oct 1, 2027 deployments | supported | - | - |
| 7 | SA2 | EU 2027 | eu-omnibus-2026 | Annex III from Dec 2, 2027 - but GDPR notice + Art 22 rights exist now | overstated by omission | high | See F1 |
| 8 | SA3 | Explanation + human review: Colorado only | co-sb26-189 | Colorado yes; EU AI Act Art 86 explanation (2027), GDPR Art 22 human intervention (now), California CPPA ADMT rules (2027, lead) | wrong | high | See F1, F2 |
| 9 | SA4 | Enforcement thin: 18 of 391 NYC employers posted an audit | wright-2024 | 391 employers hiring Cornell grads, 124 without NYC listings; authors: absence ≠ non-compliance | overstated, misattributed purpose | medium | See F4 |
| 10 | 25 | Yes, legal in US; no federal ban | - (uncited) | No source | unsupported | medium | Same as row 1 |
| 11 | 27 | June 2026 federal court let AI-screening lawsuit go on | mobley-2026-order | Order denied most of a motion to dismiss | supported | - | - |
| 12 | 27 | Claims going on: race, disability, age (federal) + California claims | mobley-2026-order p. 1-2, 11 | Mobley's Title VII race, ADA, ADEA continue; FEHA kept except Rowe race | supported | - | - |
| 13 | 27 | Court decided only which claims continue | mobley-2026-order | Pleading ruling | supported | - | - |
| 14 | 29 | Discrimination law applies whether a person or a program turns you down | - | No source holds this generally; no jurisdiction or date | unsupported legal generalization | medium | See F9 |
| 15 | 35 | LL144: audit within past year, public summary | nyc-ll144 | Yes | supported | - | - |
| 16 | 35 | Notice to city residents 10 business days before | nyc-ll144 | DCWP page: notice 10 business days before; residency is in the rule | supported (residency from nyc-aedt-rule) | low | Cite both |
| 17 | 35 | Enforced since July 5, 2023 | nyc-ll144 | Yes | supported | - | - |
| 18 | 37 | Notice via careers page, posting, mail/email | nyc-aedt-rule 5-304(b) | Yes | supported | - | - |
| 19 | 37 | Notice explains how to ask for another process or accommodation | nyc-aedt-rule 5-304(a) | Yes, "if available" | supported | - | - |
| 20 | 37 | Rule does not make employer offer another process | nyc-aedt-rule 5-304(a) | Yes | supported | - | - |
| 21 | 37 | Ask in writing what data the tool uses, answer in 30 days, unless already on website | nyc-aedt-rule 5-304(d) | Rule makes employers post it AND answer requests in 30 days; "unless" is the law's wording (not opened) | misattributed | low | See F15 |
| 22 | 41 | Illinois: AI with discriminatory effect = civil rights violation | il-hb3773 | Synopsis yes | supported | - | - |
| 23 | 41 | ZIP codes as stand-in also counts | il-hb3773 | Yes | supported | - | - |
| 24 | 41 | Failing to tell applicants is a violation | il-hb3773 | "notice to an employee" | needs caveat | low | See F14 |
| 25 | 41 | PA 103-0804 in force Jan 1, 2026 | il-hb3773 | Yes | supported | - | - |
| 26 | 43 | No final Illinois notice rule found | uncited | Search claim | supported as own search | low | List searched pages in `uncited:` |
| 27 | 47 | SB26-189 takes effect Jan 1, 2027 | co-sb26-189 | Summary: Jan 1, 2027 for developers; not stated for deployers; stay (lead) | needs caveat | high | See F3, F7 |
| 28 | 47 | Covers automated systems in decisions like hiring | co-sb26-189 | ADMT that materially influences consequential decisions incl. employment | supported | - | - |
| 29 | 47 | Clear notice when you deal with such a system | co-sb26-189 | "at the point of interaction" | supported | - | - |
| 30 | 47 | Must explain it (the decision) in plain words within 30 days | co-sb26-189 | "plain language description of a covered ADMT's role" | overstated | medium | See F6 |
| 31 | 47 | May correct factually wrong personal data | co-sb26-189 | Yes (also may request the data) | supported | - | Add "see the data" |
| 32 | 47 | May ask for "meaningful human review and reconsideration" | co-sb26-189 | Yes (law-firm leads add "to the extent commercially reasonable") | needs caveat | low | Open act text; add limit if there |
| 33 | 47 | AG enforces; no new right to sue | co-sb26-189 | Yes | supported | - | - |
| 34 | 47 | Signed May 14, 2026, replaced 2024 law | co-sb26-189 | Yes | supported | - | - |
| 35 | 49 | Colorado age law: no age, birth date, school dates on first application | co-sb23-058 | Yes, BFOQ exception | supported | - | - |
| 36 | 49 | Must tell you you may black out dates on transcripts | co-sb23-058 | Only if the employer asks for transcripts/certs at that stage | needs caveat | low | "If they ask for transcripts..." |
| 37 | 49 | Enforced since July 1, 2024 | co-sb23-058 | Prohibition starts July 1, 2024 | supported | low | Fix registry `sample` date (F16) |
| 38 | 53 | CT notice duties from Oct 1, 2027 | ct-pa26-15 | Yes | supported | - | - |
| 39 | 53 | Plain-words disclosure unless obvious | ct-pa26-15 Sec 9 | Yes | supported | - | - |
| 40 | 53 | Written notice before decision: what tool is, what it decides, product name, data kinds + sources | ct-pa26-15 Sec 10 | Yes (+ how data is assessed, contact) | supported | - | - |
| 41 | 53 | AG enforces, no new right to sue | ct-pa26-15 Sec 12 | Yes | supported | - | - |
| 42 | 53 | Sec 13 since Oct 1, 2026: tool use no defense | ct-pa26-15 Sec 13 | Yes | supported | - | - |
| 43 | 55 | Some summaries claim CT explanation/correction right; text grants neither | ct-pa26-15 | Text confirms none | supported | - | - |
| 44 | 59 | EU AI Act lists hiring AI as high-risk (filter, evaluate) | eu-ai-act | Annex III 4(a) | supported | - | - |
| 45 | 59 | Employers must tell people (present tense) | eu-ai-act Art 26(11) | Applies from Dec 2, 2027 | needs caveat | medium | See F1 (tense) |
| 46 | 59 | May ask for clear explanation of AI's role | eu-ai-act Art 86 | Yes, for significant-effect decisions, from 2027 | supported | - | - |
| 47 | 59 | 2026 change moved start to Dec 2, 2027 | eu-omnibus-2026 | Yes | supported | - | - |
| 48 | 65 | California rules in force Oct 1, 2025; harm by protected trait; 4-year records; puzzles = medical inquiry | ca-crc-ads-2025 | Yes, all four | supported | - | Fix registry sample (F17) |
| 49 | 67 | NJ rules took effect Dec 2025; name online application tools + face analysis | nj-dcr-2025 | "adopted", published Dec 15; effective date not on page | needs caveat | low | "adopted in December 2025" |
| 50 | 69 | ADA: no disability questions pre-offer; ask for accommodation in hiring process | eeoc-ada-preemployment | Yes | supported | low | Label as agency guidance on the ADA |
| 51 | 73 | EO: end disparate impact "in all contexts"; deprioritize | eo-14281 | Full phrase adds "to the maximum degree possible" | overstated (quote cut) | low | Quote the limiter |
| 52 | 75 | Dec 2025 EO task force; names Colorado | eo-14365 | Yes | supported | - | - |
| 53 | 75 | DOJ asked to join xAI suit vs 2024 law; Equal Protection | doj-xai-2026 | Yes | supported | - | - |
| 54 | 75 | Colorado replaced the law in May 2026 | co-sb26-189 | Yes | supported | - | - |
| 55 | 75 | No court ruling on the challenge | uncited | Leads: court granted a joint stay of enforcement April 27, 2026, extended to SB26-189 | outdated / incomplete | high | See F3 |
| 56 | 77 | EOs did not stop the June 2026 order letting federal claims go on | mobley-2026-order | Order exists; no causal link stated | supported, wording | low | "Private lawsuits under those laws still go on" |
| 57 | 81 | 2024 study, 155 investigators, 391 websites; 18 audits; 13 notices | wright-2024 p. 1, 8 | Yes; data Oct-Nov 2023; also LinkedIn/Indeed | supported, needs caveat | medium | See F4 |
| 58 | 81 | "substantial discretion"; missing audit doesn't prove breach | wright-2024 p. 1 | Yes | supported | - | - |
| 59 | 84 | Bars caption "2024" | wright-2024 p. 8 | Data collected 2023 | needs caveat | low | See F11 |
| 60 | 90 | State audit Dec 2025, July 2023-June 2025; 32 companies, 1 issue; >= 17; 2 complaints; "ineffective" complaint process | nys-comptroller-2025 | All match | supported | - | - |
| 61 | 96 | Plaintiffs allege race, age, disability | mobley-2026-order p. 1 | Yes | supported | - | - |
| 62 | 96 | May 2025 age claim forward for wider group, preliminary | clearinghouse-mobley | May 16, 2025 preliminary collective certification | supported | - | - |
| 63 | 96 | Sept 2026 plaintiffs "asked to add four groups"; hearing March 2027 | lawyer-monthly-2026 | Asked to certify four proposed subclasses | misdescribed | medium | See F8 |
| 64 | 96 | Workday denies; nothing proven | lawyer-monthly-2026 | Denial is in clearinghouse-mobley (answer), not found in the LM passages read | misattributed | low | Cite clearinghouse-mobley for the denial |
| 65 | 102-110 | Summary table rows | per row | Match the body, inheriting rows 5, 8, 21, 27, 30, 45; Illinois "No request right found in the text" = synopsis, not text; California row omits CPPA rules | needs caveat | medium | Update with F1-F3, F14 |
| 66 | 112 | Only Colorado, from 2027, lets you ask a person to look again | (table) | GDPR Art 22(3) human intervention now; CPPA ADMT (lead) | wrong | high | See F1, F2 |
| 67 | 123 | NYC allows notice on posting/careers page | nyc-aedt-rule | Yes | supported | - | - |
| 68 | 124 | NYC written request, 30 days | nyc-aedt-rule | Yes | supported | - | - |
| 69 | 125 | Accommodation if an AI test doesn't work for you | eeoc-ada-preemployment | Guidance covers hiring process generally; AI not named | supported (reasonable extension) | low | Say "any test in the hiring process, AI ones too" |
| 70 | 126 | Colorado Jan 2027: ask for explanation + human review | co-sb26-189 | Description of the tool's role; stay (lead) | needs caveat | medium | F3, F6 |

## Findings (status: fixed or rebutted, plan-xsy.61)

High

- **F1 - EU rights that exist now are missing (fixed).** GDPR Article 22 (in force since 2018) gives a right not to be subject to a solely automated decision with significant effects, and where allowed, "at least the right to obtain human intervention" and to contest it (gdpr-info.eu reproduction of Art 22, opened 2026-10-04). So "Explanation + human review: Colorado only" (SA3), "Only Colorado, from 2027, lets you ask a person to look at an AI decision again" (line 112), "EU 2027" for notice (SA2) and the present-tense "Employers must tell people" before the 2027 date (line 59) are wrong or misleading for EU readers. Fix: add GDPR Art 22 (+ Art 13(2)(f)/14(2)(g) notice of solely automated decisions) from EUR-Lex via an archive copy, registry entry `eu-gdpr` (law, recheck_by), limit to "solely automated"; rewrite SA3, line 112, line 59 tense, EU table row.
- **F2 - California privacy-agency ADMT rules missing (fixed).** CPPA announcement Sept 23, 2025 (opened): businesses using ADMT for "significant decisions" must comply with ADMT requirements from January 1, 2027. Law-firm leads (not evidence): pre-use notice, opt-out or human appeal, access right, for firms over $25M revenue, covering employment. If the regulation text confirms, Colorado is not the only 2027 human-review route and the California row's "No request right" is wrong. Fix: open the final regulation text (cppa.ca.gov/regulations, 11 CCR 7200ff), add entry, add to section + table + "What helps". Also lead: California SB 947 (chaptered 09/30/26, "Employment: automated decision systems") - leginfo page opened, text not read; leads say it covers discipline/firing, not hiring; include only if it touches applicants.
- **F3 - Colorado's law is under a court enforcement stay (lead, fixed).** Several law-firm reports (Norton Rose Fulbright, McDermott, Littler "Law and the Workplace", May 2026) say the federal court in xAI v. Weiser granted a joint stay of enforcement on April 27, 2026, extended to SB26-189 until after a preliminary-injunction ruling tied to the AG's rulemaking. The draft says "We found no court ruling on the challenge" and presents Jan 1, 2027 as firm in SA2, line 47, table and "What helps". Fix: open the docket or order (CourtListener, D. Colo.; try an archive copy or the AG's site), then state status with date; if unconfirmed, at least say the law's start may move and the case is open.

Medium

- **F4 - FAccT count framed as enforcement and as "New York City employers" (fixed).** The 391 were a random draw from employers that hired Cornell graduates; 124 had no NYC job listing (14 of 267 NYC-listing employers posted an audit). Data are Oct 24-Nov 9, 2023. The authors say an absence "cannot be said to indicate non-compliance" and the method could not see notices shown after applying. SA4 "Enforcement thin: 18 of 391 New York City employers" overstates. Fix: SA4 lead with the Comptroller (2 complaints in 2 years; city found 1 issue vs >= 17), or reword "of 391 large employers checked in late 2023, 18 had posted an audit"; body adds sample + dates.
- **F5 - Absence-of-law claim cited to a court order (fixed).** SA1 and line 25 "No federal law bans..." cite `mobley-2026-order`, which says nothing on it. Fix: put the search in `uncited:` ("No federal law found that bans...") or reword to what the order shows.
- **F6 - Colorado "explain it" overstated (fixed).** Summary: "plain language description of a covered ADMT's role" after an adverse outcome, details left to AG rules due Jan 1, 2027. Line 47 "must explain it", SA3 "Explanation", line 126 "ask for the explanation" promise more. Fix: "describe what the system did in the decision"; add the AG-rules gap to What we don't know.
- **F7 - Colorado start date not in the opened source for employers (fixed).** The bill summary states January 1, 2027 only for developer duties. Fix: open the signed act (try leg.colorado.gov in a browser, or an archive copy of the "Signed Act" PDF) and cite the deployer effective-date section; until then say "the bill summary gives January 1, 2027".
- **F8 - Workday class step misdescribed (fixed).** Line 96 "asked to add four groups of applicants" - source: asked the court to certify four proposed subclasses (a class-certification motion). Fix: "asked the court to certify four groups as a class action ... hearing set for March 9, 2027".
- **F9 - Unsourced legal generalization (fixed).** Line 29 "a law against discrimination applies whether a person or a program turns you down" - no jurisdiction, date or source; the order is a pleading ruling. Fix: "In the US, as of October 2026, a court let discrimination claims against a screening vendor go on" or cite Connecticut Sec 13 for the Connecticut-only version.
- **F10 - Federal "Title VII/ADA/ADEA unchanged" point implicit (fixed).** Bead brief asks for it; line 77 implies it via the court case. EO 14281 itself names 42 U.S.C. 2000e-2 for deprioritized agency enforcement - so private suits vs agency enforcement should be split plainly: "The order changes what federal agencies pursue. It does not change the laws, and people can still sue under them." Needs a citation for the second half (the statute, or the order's own scope).
- **F11 - Missing searched-for laws (fixed).** Brief: any law passed or changed since 2026-09 (NY, NJ, MA, TX, VA). Search 2026-10-04 found leads only for California SB 947 (F2) and Texas TRAIGA (HB 149, effective Jan 1, 2026, mostly government AI). "What we don't know" says "We searched state legislature sites" - list the searched sites in `uncited:`; decide TRAIGA in/out from its text.
- **F12 - "For you," used 3 times (fixed).** Lines 29, 61, 92; Wave 1 lessons cap it at 2.

Low

- **F13 - Bars figure has 2 rows (fixed).** research.md asks for >= 3 comparable shares. Use Table 1's four cells (NYC-listing vs not, audits vs notices) or drop; caption "2024" -> "late 2023 (published 2024)".
- **F14 - Illinois "applicants" (fixed).** Synopsis says notice "to an employee"; whether applicants are covered depends on the Act's definitions - open the enrolled text (775 ILCS 5/2-101, 2-102(L)) and say so. Table "No request right found in the text" -> "in the bill summary".
- **F15 - NYC "unless already on its website" (fixed).** That is the law's wording, not the cited rule's; the rule requires posting the data info on the careers site and answering written requests. Fix wording or cite the law text. Line 37 also lacks a final period after the citation.
- **F16 - Registry `co-sb23-058` sample date (fixed).** Says "from August 7, 2023"; summary says the ban starts July 1, 2024 (act effective Aug 7, 2023).
- **F17 - Registry `ca-crc-ads-2025` sample claims Attachment B was read (fixed).** Neither the drafter (bead .59 notes) nor I re-opened it; say "Council announcement" only, or open Attachment B.
- **F18 - EO 14281 quote cut (fixed).** "in all contexts" drops "to the maximum degree possible".
- **F19 - EU source host (rebutted).** Annex/Article text read in the artificialintelligenceact.eu reproduction, which may not show omnibus edits; ship bead browser check of EUR-Lex consolidated text.
- **F20 - Workday denial cite (fixed).** Cite `clearinghouse-mobley` (answer denying allegations) for "Workday denies the claims".
- **F21 - SEO wording (fixed).** Searched terms "NYC Local Law 144", "Colorado AI hiring law", "Illinois AI hiring law" - H3s could read "New York City (Local Law 144)", "Colorado (SB26-189)", "Illinois (HB 3773)"; title OK (52 chars); description should drop "the EU" from "make employers tell you" if F1 lands (EU already does under GDPR).
- **F22 - What helps omits two sourced actions (fixed).** NYC complaint route exists on the DCWP page (nyc-ll144) and the Comptroller found complaints rare; Colorado also lets you see your data. Add one line each.
- **F23 - Colorado age law sits under "make employers tell you they use AI" (fixed).** Not an AI law; move to "Which laws limit how AI may judge you?" or a short "related" line.
- **F24 - Internal links (fixed).** 4 links out (methods, ai-resume-screening-bias, ats-rejection-myth, index); revise bead adds >= 2 links in from published siblings per Wave 1 lessons.

## Checks

- Sources read first: all 19 cited ids opened and noted above before the article was read (except one header peek at the Short answer while extracting citation ids).
- Every cited id appears in this review: checked with `for id in $(grep -o '@[a-z0-9-]*' app/web/research/ai-hiring-laws.md | sort -u | tr -d @); do grep -q "$id" app/web/research/reviews/ai-hiring-laws.md || echo MISSING $id; done` -> no output.
- Quotes in the article: all <= 15 words ("in all contexts", "meaningful human review and reconsideration", "substantial discretion", "ineffective").
- Privacy: no owner data, no real employer as an example (Workday appears only as a named lawsuit party, described as alleged with status).
- Laws rules: "Not legal advice" line present (line 21); "as of October 2026" in most legal sentences - missing in lines 29, 73-77 (federal section) and 96 has it; fix with F9/F10.
- Jargon: "deprioritize", "disparate-impact liability" (explained), "bias audit" (unexplained - add "a check of whether the tool's results differ by sex and race").
- Own measurement: none on this page.

## Re-review (2026-10-04, fresh session)

Fresh subagent, no editing context. Read `git diff` of the article + `sources.yml`, then checked every new or changed sentence against the cached primary text (`~/.cache/plan-xsy.61/`: `il.txt` p. 20-21, `fn.txt`, `cppa.txt` §§ 7001, 7200, 7220-7222, `dkpage.html` ECF 24, `gdpr.html`/`g13.html`; `~/.cache/plan-xsy.60/`: `sb947.txt`, `nycrule.txt`, `nyc.txt`, `facct.txt`, `osc.txt`, `co-sb26-189.txt`, `co-sb23-058.txt`, `ctpa.txt`, `eo14281.txt`, `eo14365.txt`, `euom.txt`, `eu26/86/3.txt`, `eeoc.txt`, `nj.txt`, `lm.txt`, `ch.txt`). Mechanics: every cited id in the registry; quotes exact + <= 15 words ("to an employee", "meaningful human review and reconsideration", "in all contexts to the maximum degree possible", "substantial discretion", "ineffective"); "For you," 1 time; no body sentence over 21 words; bars cells match Table 1 (14/267, 12/267, 4/124, 1/124); description 153 chars; 2 inbound links from siblings. Nothing in any source addressed an AI. Confirmed: GDPR Art 22(1)/(3) + 13(2)(f) wording, CPPA § 7200(b) date + § 7221(b)(2) hiring exception + § 7222 access, ECF 24 terms (no enforcement through 14 days after the PI ruling; PI motion due 28 days after final rules), SB 947 approval date + July 1, 2027, IL § 2-102(L) on p. 20, CT § 13, EO 14281 quote + 2000e-2, NYC rule § 5-304(a)/(d), Comptroller numbers, Mobley class-cert motion + March 9, 2027.

- F1 addressed (GDPR Art 22 + 13-14 added; SA3, EU section tense, table, line 112 removed).
- F2 addressed (CPPA regulation text cited by section; SB 947 in with employee-only scope).
- F3 addressed (ECF 24 cited; status stated in SA, body, table, What we don't know, What helps).
- F4 addressed (SA4 now Comptroller; body gives sample, dates, 124 non-city employers, after-apply limit).
- F5 addressed (search moved to `uncited:`).
- F6 addressed ("describe the system's role"; AG-rules gap listed).
- F7 partly: now cites the fiscal note, but the note's own effective-date section reads differently - see R1.
- F8 addressed. F9 addressed (Connecticut § 13). F10 addressed (agencies vs private claims split).
- F11 partly: SB 947 in; Texas TRAIGA in/out decision not visible on the page or registry.
- F12 addressed (1 use). F13 addressed (4 rows, "late 2023, published 2024").
- F14 addressed in body + table (enrolled text, "to an employee") - but SA + description still say Illinois tells you now, see R2; definition nuance R3.
- F15 addressed. F16 addressed. F17 addressed. F18 addressed.
- F19 still open as ship-bead item (EU AI Act + GDPR read in reproductions; `sample` says so).
- F20 addressed here (denial cited to clearinghouse) - sibling still cites the news piece, see R8.
- F21 addressed (H3s carry law names; description reordered). F22 addressed. F23 addressed. F24 addressed (2 links in).

New findings:

- **R1 - Colorado start date rests on half of a pre-passage staff note (fixed).** Article: "The legislature's staff say these duties start January 1, 2027" [@co-sb26-189-fiscal]; also SA2 "From 2027: Colorado" and the table "Starts January 2027". The note's summary says "Beginning on January 1, 2027, developers and deployers ... must provide certain disclosures" (`fn.txt` l. 246), but its Effective Date section says "The sections of the bill pertaining to deployer disclosures, consumer rights and enforcement by the Attorney General take effect upon signature of the Governor ... All other sections ... take effect on January 1, 2027" (l. 648-651). The note is dated May 6, 2026; the bill page lists later Rerevised (05/09) and Final Act (05/12) versions. Registry label `law` for a staff note overstates it. Fix: open the Signed Act PDF (05/14/2026, bill page "All Versions") and cite its applicability section; until then say "The staff note's summary gives January 1, 2027 for these duties; the note predates final amendments" and drop the date from SA2/table to "2027 (staff note)", or state both readings.
- **R2 - Illinois "notice now" in Short answer + description vs body (fixed).** SA2 "Notice now: New York City, Illinois" and description "New York City, Illinois and the EU make employers tell you about AI screening"; body: notice "to an employee", "It does not name job applicants outright", no final rule on when or how (`il.txt` p. 20: "fail to provide notice to an employee"; "The Department shall adopt any rules ... the circumstances and conditions that require notice"). Same in sibling `ai-resume-screening-bias.md` l. 113 "In New York City and Illinois, employers must tell you". Fix: SA2 "Notice now: New York City, EU (fully automated decisions); Illinois requires notice to employees, rules pending"; description e.g. "New York City and the EU make employers tell you about AI screening; Illinois, Colorado, California and Connecticut add rules. Few let you ask why."
- **R3 - Illinois "does not name job applicants outright" needs the apprenticeship carve-in (fixed).** § 2-101(A)(1): "'Employee' includes: ... (c) An applicant for any apprenticeship" (`il.txt` l. 35-45); § 2-102(L)(1) also covers "recruitment, hiring". Fix: "Its definition of employee names only applicants for apprenticeships. Whether other job applicants get notice is left open."
- **R4 - SB 947 scope wording (fixed).** Article: "it limits automated discipline and firing, not hiring". § 1522(a) also bars using an ADS to "Infer an employee's protected status" or predict and act against workers using their rights; scope is "any person employed" (§ 1520(d)(2)). Registry `sample` says "sections 1520-1524"; the part runs to § 1526.7. Fix: "it limits how employers use automated systems on their workers, including discipline and firing. It does not cover job applicants." Sample: "Labor Code sections 1520-1526.7".
- **R5 - FAccT sample + page cite (fixed).** "391 employers that hire Cornell graduates": frame = 568 employers that hired 2021-22 Cornell graduates, plus pilot-study employers and the top 100 internship providers, trimmed to 511; 391 drawn at random (`facct.txt` §5). "Notices shown only after applying were not visible" is footnote 13 on p. 7; cite says p. 1, 8. Fix: "391 employers, mostly ones that hire Cornell graduates" and cite "p. 1, 7-8".
- **R6 - Mobley allegations now include sex (fixed).** Article: "The plaintiffs allege Workday's screening tools discriminated by race, age and disability" (order p. 1, June 2026). The Sept 2026 motion asks to certify subclasses of "African American applicants, women, people aged over 40 and applicants with disabilities" (`lm.txt`). Fix: name the four groups in the September sentence: "... four groups of applicants: African American applicants, women, people over 40 and people with disabilities."
- **R7 - Federal section legal sentences lack "as of" (fixed).** "People can still bring their own claims under the federal laws." and the EO paragraphs carry no jurisdiction-date frame (research.md Laws rule). Fix: "As of October 2026, people can still bring their own claims under federal job discrimination laws."
- **R8 - Sibling sentences next to the new inbound links contradict this page (fixed).** `ai-resume-screening-bias.md` l. 113 "From 2027, Colorado employers must also explain a rejection" - this page (F6, F3) says describe the system's role, and enforcement is paused (ECF 24). `ats-rejection-myth.md` l. 126 cites `lawyer-monthly-2026` for "Workday denies the claims" (F20: denial is in `clearinghouse-mobley`) and says "widen the case to more groups" (F8: certify four subclasses). Fix: bias l. 113 "From 2027, Colorado employers must also describe the system's role after a rejection; a court has paused enforcement" [@co-sb26-189; @xai-weiser-stay]; ats l. 126 "asking the court to certify four groups as a class action" and move the denial cite to `clearinghouse-mobley`.
- **R9 - California's human appeal missing from Short answer + What helps (fixed).** Body: "Usually you may also opt out, or appeal to a person who can change the decision" (§ 7221(a), (b)(1)); SA3 "Ask a person to look again: EU now ...; Colorado from 2027" and What helps list only EU + Colorado for a person's review. Fix: SA3 add "California from 2027, for some tools"; What helps California line add "or appeal to a person, where offered".

## Resolution (plan-xsy.61, 2026-10-04)

All F and R findings are closed. Notes where the fix is partial or a finding is rebutted:

- F3: docket opened (CourtListener 73171074, ECF 24 minute order 2026-04-27); stay stated with date in SA, Colorado section, table, What we don't know.
- F7 + R1: signed act still not opened (leg.colorado.gov renders by script; file guesses 404). Article now says the staff note's summary gives January 1, 2027, the same note puts the notice, rights and enforcement sections at signing, and the signed act was not opened; SA "date not settled", table "per a staff note". Registry label stays `law`: research.md's scale has no row for official legislative staff material and the `sample` names it a staff note on the pre-passage bill (rebuttal of the label part only).
- F11: Texas TRAIGA left out - its text was not opened, and the page lists only laws whose text was opened ("What we don't know"). California SB 947 added (R4 wording).
- F19 (rebutted for this bead): `eu-gdpr` and `eu-ai-act` samples say which reproduction was read; the EUR-Lex browser check is a ship-bead item, not an article change.
- F20 + R8: sibling `ats-rejection-myth.md` now cites `clearinghouse-mobley` for the denial and says "certify four groups ... as a class action"; sibling `ai-resume-screening-bias.md` now says Colorado employers "describe an AI tool's role in a rejection" with the court pause cited. Remaining law lines there filed as a follow-up bead.
- R2: Illinois moved out of "Notice now" in SA + description; table says "Notice to employees".
- R3: "Its definition of employee names only applicants for apprenticeships" (il.txt 2-101(A)(1)(c)).
- R4: SB 947 sentence + registry sample (1520-1526.7, incl. inferring protected status) corrected.
- R5: "mostly ones that hire Cornell graduates"; cite p. 1, 7-8.
- R6: the four proposed groups named (lm.txt l. 30); the 2026 order's race, age and disability sentence kept, as it describes that order.
- R7: "As of October 2026" added to the federal private-claims sentence.
- R9: California added to SA bullet 3 and What helps.


# Fair screening - names, age, work breaks, records: what the evidence supports

Checked 2026-09-29 from research notes + an adversarial evidence review (every core source opened,
figures corrected against primary text). Laws re-checked by 2027-03-29, or before any law line
reaches a user guide - whichever comes first. Each rule names its basis + strength; thin basis
says so. Preprints (not peer-reviewed) labelled *preprint*.

Framing for every user line: bias is the employer's, not a flaw in the applicant. The program
informs both ways, then carries the user's choice through resume + every form.

Strength labels, strongest first: **meta-analysis** · **large field experiment** (thousands of
real applications) · **field experiment** · **survey** · **vendor survey** (seller of a service,
method thin) · **lab/LLM audit** (raters or AI models, not real hiring) · **law** · **convention**
(career-centre consensus, no study).

Not here: [What did not survive](#advice-we-dont-follow), [Unverified](#unverified) - read both
before adding a claim; a figure listed there never reaches a user as fact.

---

## Names + identity signals

| Rule | Basis | Strength |
|---|---|---|
| Name bias is real + not shrinking | Quillian 2017 (28 US studies, 55,842 applications, incl. in-person audits): white applicants +36% callbacks vs Black (CI 25-47%), +24% vs Latino; no change vs Black since 1989. Lippens 2023 (mostly European studies): Arab -46%, East/South-East Asian -43% (wide prediction interval), Black -36%. Bertrand & Mullainathan 2004 (Boston, Chicago): 9.65% vs 6.45%. | meta-analysis |
| Apply widely - the best-supported action | Kline/Rose/Walters 2021 (83k applications, 108 Fortune 500 firms): Black names 2.1 pts fewer contacts on a 24% base; worst fifth of firms = nearly half of lost Black contacts. Federal contractor + centralised HR *correlated* with smaller gaps, not proven causes. | large field experiment |
| Bias grows after the callback | Quillian/Lee/Oliver 2020: majority applicants 53% more callbacks, 145% more job offers. Name tweaks at the first screen can't reach the interview. | meta-analysis |
| Pro-diversity statements don't predict fairer screening | Kang 2016: postings w/ them discriminated just as much. | field experiment |
| Initials: **their call, never recommended** | Direct evidence thin and mixed: 2 small tests of an English first name + ethnic surname disagree (Canada 2008 no significant gain; US 2015 borderline gain). No test of bare initials. Detail: Oreopoulos 2011 "Allen Wang" 12.5% - below English 16.0%, not significantly above Chinese 11.3%. Kang 2016 "Lei -> Luke Zhang" (surname kept) 11.5% -> 18.0%, p<.10, 200 applications per cell. Black "Lamar J. -> L. James Smith" 10.0% -> 13.0%, not significant at that size - a test too small to tell, not a null. | 2 field experiments, small cells |
| Say what initials hide + don't | Hide the first name on the page only. Not the surname, the email address, or any form box asking the legal name. AI recovers ethnicity from redacted prose (below). | follows from the above |
| Affinity items: their call, same info for all | Kang 2016: whitening activities alone lifted Black callbacks 10% -> 18%, more than the name. But Kang *renamed* organisations - in real life a false name. Omit, or describe generally ("Treasurer, 40-member student group"); never rename (Hold). Removing loses real leadership; value lost unmeasured. | field experiment; trade-off unmeasured |
| Languages: ask every user | Oreopoulos 2011 (Canada): several languages lifted callbacks +5.8 pts for foreign-educated applicants only (French counted); no effect for locally educated ethnic names. | large field experiment, Canada |
| Hard-to-say names | Ge & Wu 2024: economics PhDs w/ hard-to-say names ~10% less likely to get an academic job. A pronunciation line: no evidence, their call. | field experiment + observational |
| Full street address -> city + state | Phillips 2020 (Washington DC, 2,260 applications): far addresses 14% fewer callbacks; neighbourhood wealth no effect once distance held equal. Already push-back in AGENTS.md. | field experiment |
| Disability disclosure: voluntary, never prompted | Ameri 2018 (6,016 accounting jobs): disclosing got 26% fewer expressions of interest, mostly small firms outside the ADA. Glazko 2024: GPT-4 ranked a CV w/ disability awards first 15 of 60 times. | large field experiment; lab/LLM audit |
| Never comment on how a name, accent or looks read | Offers fire only on facts in the file (dates, page content), identically for everyone; never on inferred race, ethnicity, gender or age. | convention (policy) |

## What the recruiter sees on forms

| Fact | Basis | Strength |
|---|---|---|
| Greenhouse shows "Legal (Preferred) Last" | Greenhouse docs: legal name first, preferred name in brackets. Preferred-name field set per job post, optional by default, can be hidden; not offered via LinkedIn Apply / Indeed Apply; background checks use the legal name. | vendor docs |
| Greenhouse blurring is narrow | Pro tier, switched on per job, application + hiring-manager review stages only, full resume stays on the profile, custom questions can leak identity. | vendor docs |
| Workday recruiter view: unknown | Candidate form has a Legal Name section + preferred-name checkbox; collecting preferred names needs the employer's setting. What recruiters see for a candidate: not found. Never say "Workday shows X". | vendor docs (partial) |
| No native blind review found | Workday, iCIMS, Ashby, Lever. Their "anonymize" features delete data after hiring (GDPR), not blind review. | vendor docs |
| Legal name: I-9 after hire + background-check consent | I-9 asks full legal first + last name - completed after hire, not at application. Background checks search the name given + listed aliases (Checkr). So: legal name where the box says legal or it's a background-check form; plain Name box -> ask once, remember. | law; vendor docs |
| Upshot for initials | Initials on the resume + full name in the form very likely do **not** hide the first name at first screen: candidate list shows the form name, AI tools may read both. | inference from vendor docs |

## AI screening

| Rule | Basis | Strength |
|---|---|---|
| Direction varies by model - say so, promise nothing | Gao 2026 *preprint* (14 models): 2023 model +2.12 pts pro-white; 2024+ models null or pro-Black up to 3.01; same for gender. An 2025 (~361k resumes, 5 models): Black men scored lower, women higher. Wilson & Caliskan 2024 (embedding search): white names favoured in 85.1% of tests. | lab/LLM audit |
| Order effects as big as names | Rozado 2025 (22 models): first-listed candidate won 63.5%; names -> "Candidate A/B" + swapped order gave parity. | lab/LLM audit |
| Real vendor data leans against Black + Asian applicants | Bommasani 2026 *preprint* (3M applicants, one vendor): 25.87% of Black + 14.74% of Asian applicants' applications went to positions w/ adverse impact against their group; 4% of people applying to 10 jobs were recommended for rejection by all 10. | large observational, preprint |
| Removing the name doesn't hide ethnicity from AI | Chen & Xiao 2026 *preprint* (9 models, 620 resumes): ethnicity recovered from redacted prose 76% on average, 100% when cues strong. | lab/LLM audit, preprint |
| Humans copy AI bias | Wilson 2025 (528 people): followed a biased AI's race preference up to 90% of the time. | lab experiment |
| No candidate trick has evidence | Nothing tested shows an applicant-side wording beats a screener. Program advice stays: accurate, relevant, readable. | absence of evidence |

## Age cues

| Rule | Basis | Strength |
|---|---|---|
| Penalty onset ~50, not 40 | US audits: none at 35-43 (Farber 2017: 35-37 = 40-42, p=0.97; Farber 2019 peak 33-43, 12.6-12.9%, then 11.0% at 51-52, 9.7% at 60-61). Appears ~50, women first (Neumark 2019); large 55-66: women 64-66 admin 7.6% vs 14.4% (-47%), men in sales -30%. Europe, age stated outright: from early 40s (Carlsson 2019, Sweden). 40 = federal legal line (some states protect younger ages), not the measured onset. | large field experiment + field experiments |
| Graduation year = the cue | Every US age audit signals age this way (Lahey, Neumark, Farber) and it moves callbacks. | large field experiment |
| Cues work together - offer them as one bundle | Neumark 2019: shorter job history alone, grad year still shown -> no significant change (janitors the exception, -9.4 pts; low-skill jobs only). Neumark 2024 (one restaurant employer): age-blind online screening -> 40+ not under-selected for interviews; offers after interview still 40% lower. Each part alone untested. | large field experiment |
| Recommend the bundle once degree is 20+ years old | Bundle = grad + cert years, oldest roles, "25 years" wording. 20 years ~ implied age 42+: covers every band where a penalty was found, w/ margin. Threshold itself = judgement from the audits, not tested. | derived from field experiments |
| Hiding has a small cost - name it | 60% of hiring managers say candidates should always list grad year (ResumeBuilder 2024, n=1,000, self-report). Derous 2017 (610 Belgian HR raters): leaving out birth date lowered ratings slightly (η²=0.02) - birth date, where customary, not grad year. | vendor survey; lab/LLM audit |
| Keep the year early in career | Students + within ~10 years of graduating keep it ("Expected May 2027"); new-grad programmes screen on it. Farber 2019: ages 22-23 at 9.4% was mostly missing experience. | convention + field experiment |
| Dated tools read as age | Van Borm 2021: perceived tech skill, flexibility, trainability explain ~41% of the age effect. Show current tools really used; no test shows recent training closes the gap. | lab/LLM audit |
| AI reads grad year too | Bone 2026 *preprint* (COLM 2026, 10 open-model families): post-training moved callbacks against older applicants 3.6 pts on average, 8 of 10 models. Tamkin 2023 (Claude 2.0, explicit age): negative over 60. | lab/LLM audit, preprint |
| Never a false date | Leaving a date off = fine; a false one = Hold. National Student Clearinghouse covers ~97% of US college enrollment for degree checks. Required form field -> answer truthfully; optional -> blank is fine. | vendor docs; law |
| Wording | "This year lets a reader guess age" - never "because you're older". Offer fires on dates in the file, same for everyone. | convention (policy) |

## Work breaks

| Rule | Basis | Strength |
|---|---|---|
| Length matters | D'hert/Baert/Lippens 2024 (~67k applicants, 7 countries pooled): 1-6 months +8% (n.s.), 7-12 n.s., 13-18 -21.4% (CI -34 to -6), 19-36 -27.0%. Pooled; US studies show it earlier: Kroft 2013 (12,054 resumes) callbacks ~7% at 1 month -> ~4% by ~8 months, then flat. | meta-analysis; large field experiment |
| Some screening software filters gaps | Hidden Workers 2021 Fig 7: 48% of executives whose software ranks or filters said it filtered middle-skill candidates on gaps over 6 months. 2,275 execs, US/UK/DE pooled, self-report, Jan-Feb 2020. Not "half of all employers". | survey |
| 6+ months: a one-line reason is worth adding | Namingit 2021 (US, 3,771 applications, mostly 7-12 month gaps): no gap 27.4%, explained 25.6%, unexplained 23.3% - about half the penalty recovered (~55%). Reason = illness + full recovery, in the cover letter. Kristal 2023 / BIT (UK, 9,022 applications, 2.5-yr gap): childcare line vs silence 0.1 pt - but that trial found no clear gap penalty either (35.0% vs 32.9%, p=.146). | one US field study; one UK trial |
| 12+ months: line + recent work, study or volunteering really done | Length evidence above. Baert & Vujić 2018 (Belgium): volunteering +7.3 pts. Never suggest paying for courses: no US study behind it. | meta-analysis; field experiment |
| Search still running: no penalty talk | Current search isn't a break to explain; never show month-penalty numbers at the user. | convention (policy) |
| Caregiver penalty hits fathers too; positive info doesn't fix it | Weisshaar 2018 (1.5-yr gap): mothers employed 15.3% / laid off 9.7% / stay-at-home 4.9%; fathers 14.6 / 8.8 / 5.4. Weisshaar 2021: performance info erased the unemployed penalty, not the caregiver one. So the reason line is their call: "small help for health and layoffs, no difference for childcare in one trial". | large field experiment; survey experiment |
| Health: "a health matter, now resolved or well managed" | Never "recovered" as the only option (false for ongoing conditions); never name a condition. ADA: no disability-related questions before an offer. | law; large field experiment |
| Layoff: one line under the last job when true | "Role cut in company-wide layoff" - Gibbons & Katz 1991: discretionary layoffs read worse than plant closings. No audit compares layoff vs firing. | observational |
| Stop-gap job below skill: their call on the page, full history on forms | Pedulla 2016, men: below-skill job 4.7% ~ unemployed 4.2% vs full-time 10.4%. Farber 2016: interim lower-level job 9.8% -> 8.5%. | field experiment |
| Dates on forms match employer records | HireRight 2025: over 3/4 of employers found discrepancies in 12 months, employment history the top one. Background checks compare the form. | vendor survey |
| Years-worked format ("3 years"): not recommended, not a Hold | Kristal 2023 UK: +4.8 pts (+14.6%) vs unexplained gap. UK only, untested in US; US forms still ask month + year. | large field experiment, UK |

## Criminal-record questions

| Rule | Basis | Strength |
|---|---|---|
| Asking the question costs callbacks | Agan & Starr 2018 (~15,000 applications, NJ + NYC): employers who asked called back no-record applicants 63% more (13.4% vs 8.2%). | large field experiment |
| Removing the box alone isn't a fix | Same study: at box-removing employers the white/Black callback gap grew 7% -> 43%. Burton & Wasser 2025: population-level effect mixed. | large field experiment; observational |
| Answer what the question legally covers - no more | Many states let sealed, expunged or juvenile records go unmentioned (e.g. CA Lab. Code 432.7) - varies by state; check the state's rules or free legal aid. A lawful "No" is not a Hold; a false answer is. | law |
| Never auto-answer; read the exact wording back | Wording decides scope (conviction vs arrest, time window). The user picks; the program never does. | convention (policy) |
| Page needn't name it | Break line optional; real work, training or education done in custody listed under its real name. "Personal leave" to cover incarceration -> push back once: dates show on a check. | convention; vendor docs |
| Certificates of relief help | Leasure & Andersen 2016 (319 applications, Columbus OH): no record ~30%, felony ~10%, felony + certificate ~26%. Pager 2008: record cut callbacks 28% -> 15%; talking w/ the employer helped. | small field experiments |
| Sensitive details stay short | Before break or record help, one line: "A few words is enough - no diagnosis or case details. What you type here goes to your AI account." | convention (policy) |

## Laws

As of 2026-09. General information, not legal advice. Which law applies to a job depends on its
location + employer size - itself a legal question. No line here says a user may refuse a
required box, or that any employer broke the law.

| Law | What it says | Status (as of 2026-09) | Source |
|---|---|---|---|
| Federal age law (ADEA) | Protects 40+. Asking age or birth date isn't itself unlawful, but forms asking are "closely scrutinized" (29 CFR 1625.5). Courts split on whether applicants can bring impact claims (7th + 11th Circuits no: Kleber v. CareFusion, 914 F.3d 480 (7th Cir. 2019); Villarreal v. R.J. Reynolds (11th Cir. 2016)). | In force | [eCFR 29 CFR 1625.5](https://www.ecfr.gov/current/title-29/section-1625.5) |
| ADA | No disability-related or medical questions before an offer. Applicants may ask for a reasonable accommodation in the hiring process (tests, interviews); if one volunteers a condition or need, the employer may ask only about the accommodation, not the condition itself. | In force | [EEOC guidance](https://www.eeoc.gov/laws/guidance/enforcement-guidance-preemployment-disability-related-questions-and-medical) |
| Form I-9 | Full legal name; filled in after the offer is accepted, by the first day of work. | In force | [USCIS I-9](https://www.uscis.gov/i-9) |
| Work-permit questions | Employers may generally ask whether you're authorised to work in the US + whether you'll need visa sponsorship. | In force | [DOJ IER FAQ](https://www.justice.gov/crt/iers-frequently-asked-questions-faqs) |
| California 2 CCR 11079 | Limits age-revealing questions (age, birth date, graduation dates) at every pre-employment stage, unless age is a genuine job requirement. | Operative 2020-07-01 | [2 CCR 11079](https://www.law.cornell.edu/regulations/california/2-CCR-11079) |
| Oregon HB 3187 | Limits age, birth date, attendance/graduation dates until after the first interview (or a conditional offer). | Effective 2025-09-26 (91 days after the session ended) | [Oregon Legislature](https://olis.oregonlegislature.gov/liz/2025R1/Measures/Overview/HB3187) |
| Connecticut PA 21-69 | Limits age, birth date, graduation dates on the initial application; 3+ staff; job-requirement + legal exceptions. | In force 2021-10-01 | [CT General Assembly](https://www.cga.ct.gov/asp/cgabillstatus/cgabillstatus.asp?selBillType=Public+Act&which_year=2021&bill_num=69) |
| Delaware SB 211 (19 Del. C. 711) | Same, initial application; 4+ staff. | In force since 2022-09-08 (signed) | [Delaware Code title 19](https://delcode.delaware.gov/title19/c007/sc02/index.html) |
| Colorado SB23-058 | Same, initial application, any employer size; employers must say applicants may black out age details on transcripts + certificates. | In force 2024-07-01 | [Colorado General Assembly](https://leg.colorado.gov/bills/sb23-058) |
| Colorado SB 26-189 (AI in hiring) | Employers using AI decisions must give notice, explain a rejection within 30 days, correct wrong data, human review "when commercially reasonable". | Signed 2026-05-14, from 2027-01-01; Attorney General enforces only, no private suits; 60-day cure until 2030, none for knowing or repeated violations | [Colorado General Assembly](https://leg.colorado.gov/bills/sb26-189) |
| Illinois HB 3773 | Bars AI that discriminates + ZIP code as a stand-in; requires notice to applicants. | In force 2026-01-01; draft notice rules proposed 2026-05-15, temporarily withdrawn 2026-06-02 | [Illinois General Assembly](https://www.ilga.gov/ftp/legislation/103/BillStatus/HTML/10300HB3773.html) |
| NYC Local Law 144 | Employers using automated tools must post a yearly bias-audit summary on their jobs page + tell candidates 10 business days before use. | Enforced since 2023-07-05; only 18 of 391 employers had posted audits (FAccT 2024); state comptroller called enforcement "ineffective" (2025-12-02) | [NYC DCWP](https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page) |
| Fair-chance rules | Federal agencies, and federal contractors for jobs tied to a federal contract, can't ask criminal history before a conditional offer. At least 15 states + DC + 21 localities extend fair-chance rules to private employers (NELP count, Oct 2021 - likely more now), each w/ its own timing. | Fair Chance Act in force 2021-12-20; OPM rule for agencies effective 2023-10-02 | [OPM rule, Federal Register](https://www.federalregister.gov/documents/2023/09/01/2023-18242/fair-chance-to-compete-for-jobs), [contractors: 41 U.S.C. 4714](https://www.law.cornell.edu/uscode/text/41/4714), [NELP guide](https://www.nelp.org/insights-research/ban-the-box-fair-chance-hiring-state-and-local-guide/) |
| Sealed / expunged records (CA example) | Many states bar employers from asking about sealed, dismissed or juvenile records; CA Labor Code 432.7 is one. Rules differ by state. | In force | [CA Labor Code 432.7](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=LAB&sectionNum=432.7) |
| EU AI Act | Hiring AI = high-risk; those duties moved to 2027-12-02. | Omnibus in force 2026-07-27 | [European Commission](https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force) |
| Mobley v. Workday (N.D. Cal.) | 2026-03-06: court held federal age law covers applicants' impact claims. Allegations only, no merits finding; class-certification hearing set 2027-03-09. | Pending | [HR Dive report](https://www.hrdive.com/news/workday-partial-loss-judge-refuses-claims-dismissal/814227/) (news, not official); [docket](https://www.courtlistener.com/docket/66831340/), [Duane Morris 2026-09-25](https://blogs.duanemorris.com/classactiondefense/2026/09/25/the-class-action-weekly-wire-episode-166-job-applicants-seek-class-certification-in-mobley-v-workday-ai-bias-suit/) (hearing date) |

Federal enforcement context: EEOC AI guidance removed Jan 2025; Executive Order 14281 (Apr 2025)
deprioritised disparate-impact enforcement; Title VII, ADA, ADEA unchanged, private suits remain.
A Dec 2025 executive order set up a task force to challenge state AI laws (Colorado named).

## What the program does

| Choice | Where it's carried | State |
|---|---|---|
| Ranking never sees the resume | `rank.py` scores jobs from search settings only: no name, school, date or address reaches it | done |
| Tailor AI task without name + contact | `tailor.build_request` sends the resume file minus the contact block; resume import still sends the name (reads the PDF text as is) | done (plan-1fw.2) |
| Graduation year hidden everywhere | `hide_year` -> `schema.shown_end`, used by page, Workday profile, UKG | done (plan-1fw.1) |
| Name on the page vs legal name | `contact.legal_*` only in boxes labelled legal; plain Name box asks once (`form_name`), never guessed from a 3+ word name | done (plan-1fw.3) |
| Other names used | `contact.other_names` -> "other names" boxes + background-check forms only | done (plan-1fw.3) |
| Sensitive questions never auto-answered | `questions.SENSITIVE` tags date of birth, graduation date, criminal history, work break, disability or health, other names (none saved); answer left blank even when a saved answer fits, `apply-form prepare` prints the kind. "18 or older?" is a plain yes/no, not tagged | done (plan-1fw.5) |
| Saved break words reused on forms | `career_break[i].explain` (1-2 sentences the user approved, never on the page) fills a work-break text box: breaks in the question's window ("last 5 years", "since 2019") or all, newest first w/ dates when several; any of them unexplained -> left blank. Source "read it before Submit"; no other sensitive kind ever filled | done (plan-1fw.6) |
| Old jobs left off the page stay off forms | `questions.form_roles`: Workday (`apply --complete-history` when the form asks for it) + UKG work history get the tailored page's jobs when `contact.form_jobs: page`, every job when `all` or the form asks for complete / all employment history (leaving jobs out there is a false answer); unset -> no jobs added, the ask printed w/ counts ("same 4 jobs as your resume, or all 6") | done (plan-1fw.7) |
| Break severity, no penalty numbers at user | `schema.gap_note`: 6+ months a line, 12+ a line + real recent work; running search nothing | done (plan-1fw.4) |
| Old dates offered, not forced | `lint` `old-graduation-year` + `old-certification-year` (`OLD_GRADUATION_YEARS` = 15) offer `hide_year` (degrees + certifications); degree 20+ years (`AGE_BUNDLE_YEARS`) -> detail recommends it, `resume-feedback` adds the bundle note once (grad + cert years, jobs ended 15+ years ago, long years count) w/ its small cost. No years-of-experience cap | done (plan-1fw.9) |

## Advice we don't follow

- **"Initials hide your ethnicity."** Surname, email, form name + prose still signal it, to humans
  and AI (76% recovery, preprint). Only direct tests: small + mixed.
- **"Blind hiring fixes it."** France: anonymous CVs -> fewer minority interviews + hires
  (Behaghel 2015). Australia: de-identifying removed a pro-minority lift (Hiscox 2017). Germany,
  Sweden: helped first contact, not offers. Bias returns at interview (Neumark 2024).
- **"Gaps don't matter anymore."** 13-18 months -21%, 19-36 months -27% (meta-analysis); US
  studies earlier. Pandemic gaps ~20% in vignettes (Bateson 2023).
- **"Explaining a gap adds 60%."** One vendor study (ResumeGo 2019, +58%, not peer-reviewed).
  Peer-reviewed: about half the penalty recovered (US), none for childcare (UK).
- **"Year-only dates hide gaps safely."** No experiment; forms + checks still need month + year.
- **"An AOL or Hotmail address costs interviews."** No hiring study. Only test found: unpublished,
  n=400, no significant difference. Informal addresses without the name do rate lower - so name-
  based address, any provider.
- **"Age bias starts at 40."** US audits: none at 35-43. 40 is the federal legal line.
- **Judging an employer by the Discrimination Report Card.** Kline/Rose/Walters 2024 grade 97
  named large firms (authors: grades mislead in under 4% of comparisons) - a sliver of the
  employers in any search, one audit round each. Apply widely instead: works for every posting.
- **"Only a full name change works."** Kang's name-only lift was borderline; recommending a new
  name has a well-being cost (Biernat 2024 review). Their call, never advice.
- **"Remove every identity signal."** Loses real accomplishments; languages can help.
- **"Screening software commonly rejects by age or max-years filter."** Exists in lawsuits
  (Kleber, Villarreal); how common: unmeasured.
- **"The ATS rejects 75% of resumes."** No primary source (see `bullets.md`).

## Unverified

Never stated to a user as fact.

- Workday: what recruiters see for a candidate - preferred or legal name.
- Bone 2026: a separate grad-year signal figure + a range of -10.0 to +1.7 - not in the abstract.
- Kristal 2023 lab replication, n=2,650.
- Quillian & Midtbøen 2026 exact figures (foreign-education penalty reported as both 35% + 42%).
- Any field test of bare initials, or initials w/ an ethnic surname.
- Any HBCU field experiment.
- Minnesota + Pennsylvania restricting age questions on applications.
- NYC grad-date questions "illegal" (contradicts the city's 2020 guidance).
- "Resumes implying 50+ get 29% fewer callbacks (41% in tech)" - no source traced.
- Hiring-manager shares for age cues (82% / 79% / 46%) - secondary sources only.
- Mobley complaint naming grad year as the proxy; "1.1 billion rejections".
- Lever: typed-in details override parsed names (search snippet only).
- How widely any blind-review feature is used.
- Ghayad 2013 sample size; ResumeGo per-reason rates; LinkedIn break-type counts + "61% see gaps
  as negative"; SHRM functional-resume shares; Path Forward 80% conversion (self-reported).
- Batinovic 2023 published figures (thesis version only read).
- Oregon HB 3187 exact effective date (19 vs 26 Sep 2025).

## Sources

Quillian et al., PNAS 2017. Quillian, Lee & Oliver, Social Forces 2020. Lippens, Vermeiren &
Baert, Eur. Econ. Rev. 2023 (IZA DP 14966). Bertrand & Mullainathan, AER 2004. Kline, Rose &
Walters, QJE 2022 (NBER w29053) + AER 2024. Kang, DeCelles, Tilcsik & Jun, ASQ 2016. Oreopoulos,
AEJ: Policy 2011. Ge & Wu, AEJ: Policy 2024. Phillips, JHR 2020. Ameri et al., ILR Review 2018.
Behaghel, Crépon & Le Barbanchon, AEJ: Applied 2015. Hiscox et al., BETA 2017. Krause, Rinne &
Zimmermann 2012. Åslund & Nordström Skans, ILR Review 2012. Biernat, Zhao & Watkins 2024.
Greenhouse support docs (preferred name, blurring). Checkr docs.
Gao, Jiang & Yan, arXiv 2606.28978 (preprint). Bommasani et al., arXiv 2605.27371 (preprint).
Chen & Xiao, arXiv 2609.16501 (preprint). Bone, Stephany & del Rio-Chanona, arXiv 2609.22169
(preprint, COLM 2026). Rozado, PeerJ CS 2026. An et al., PNAS Nexus 2025. Wilson & Caliskan,
AIES 2024. Wilson et al., AIES 2025. Glazko et al., FAccT 2024. Tamkin et al. 2023.
Neumark, Burn & Button, JPE 2019 (NBER w21669). Neumark, JHR 2024. Lahey, JHR 2008. Farber,
Silverman & von Wachter, RSF 2017. Farber, Herbst, Silverman & von Wachter, JOLE 2019. Carlsson
& Eriksson, Labour Econ. 2019. Derous & Decoster 2017. Van Borm, Burn & Baert 2021. ResumeBuilder
survey 2024.
Fuller & Raman, *Hidden Workers*, HBS/Accenture 2021. D'hert, Baert & Lippens, IZA DP 17141.
Kroft, Lange & Notowidigdo, QJE 2013. Namingit, Blankenau & Schwab, JEBO 2021. Kristal et al.,
Nature Human Behaviour 2023 + BIT report 2021. Weisshaar, ASR 2018 + Socius 2021. Pedulla, ASR
2016. Farber, Silverman & von Wachter, AER P&P 2016. Baert & Vujić 2018. Bateson 2023. Gibbons &
Katz 1991. HireRight 2025 benchmark. ResumeGo 2019.
Agan & Starr, QJE 2018. Burton & Wasser 2025. Pager 2008 (EEOC testimony). Leasure & Andersen
2016. NELP fair-chance guide. Wright et al., FAccT 2024. Epstein Becker Green, Seyfarth, Littler,
HR Dive (law status).

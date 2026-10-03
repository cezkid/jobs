---
reviewed: 2026-10-03
verdict: revise
reviewer: fresh AI session, bead plan-xsy.25 (no drafting context; sources opened before the draft was read)
---
# Review: Can employers tell if AI wrote your resume? (`ai-written-resumes.md`)

Verdict **revise**: 2 high, 7 medium, 12 low findings, all open. The numbers are copied right
almost everywhere - every figure checked matched its source. The problems are framing: the
detector section and short answer lean on 2023 tools while the article's own 2025 source shows a
paid detector near-perfect; the description promises "using AI is not the risk", which no source
shows; and the short answer + "What helps" borrow the Wiles result (spelling and grammar help,
not chat AI) as support for using AI.

## Sources, read before the draft (all opened 2026-10-03)

No source contained text addressing an AI. arXiv PDFs read as text (latest versions: Cui v2,
Galdin v1, Kobak v5 = Science Advances, Liang v3, Russell v2, Xu v4 of 2026-06-06, Wiles WP v1);
Jakesch full text via Europe PMC; OpenAI page via the Wayback copy the registry names; Insight
Global PDF, page 9 rendered as an image (the text layer puts a nearby "53%" next to the "can tell"
line - the rendered page shows 88%); Resume Genius via WebFetch; Wiles published abstract,
volume and pages via Crossref.

| id | What it actually supports | Sample / design | Limits |
|---|---|---|---|
| jakesch-2023 | Main experiments: people picked the source with 50-52% accuracy; bonus for accuracy 51.6%; feedback after each answer (professional context) 51.2%. Flawed clues: first-person pronouns, contractions, family topics read as human. AI text tuned to those clues was judged human 65.7% vs 51.7% for real human text (71% in the professional context) | 4,600 people (Lucid US-representative 2,000; Prolific 1,000 + 1,000; validation runs), 7,600 self-presentations. Professional texts = Guru.com freelancer profiles, 60-90 words. AI = fine-tuned GPT-2 (774M) and GPT-3 (13B) | Online panel judges, not hiring managers; models of 2021-22; short profiles, not resumes |
| openai-2023 | Classifier released 2023-01-31; on a "challenge set" caught 26% of AI text, flagged human text 9% of the time; unreliable below 1,000 characters; note of 2023-07-20: withdrawn "due to its low rate of accuracy" | Maker's page (archived) | One early tool; maker's own test |
| liang-2023 | 7 detectors: near-perfect on 88 US 8th-grade essays; average false-positive rate 61.22% on 91 TOEFL essays (Chinese forum); 18/91 flagged by all 7, 89/91 (97.80%) by at least one. GPT "enhance word choices" cut false positives to 11.77%; "simplify word choices" raised 8th-grade false positives 5.19% -> 56.65%. A self-edit prompt dropped detection of AI essays from 100% to 13% | Lab, 179 human essays, 7 public detectors of early 2023 | 2023 detectors; small essay set; contrary study not cited (Jiang et al. 2024, see Also found) |
| russell-2025 | Nonexperts (4, rarely use AI for writing): TPR 56.7%, FPR 52.5% in text (Table 1 prints 51.7%), confident (4.03 of 5). 5 "experts" who use AI for writing: majority vote wrong on 1 of 300. Pangram (paid) matches experts (TPR 99.3%, humanizer version); GPTZero 85.3% TPR / 0.7% FPR overall; on o1-pro humanized: Binoculars 6.7%, Fast-DetectGPT 23.3%. Top clue: "AI vocabulary" (vibrant, crucial, significantly) | 9 Upwork annotators, all native English speakers, $2 per text, 300 news-style non-fiction articles, fully AI-written by GPT-4o, Claude 3.5 Sonnet, o1-pro (some paraphrased / humanized) | Experts recruited to resemble the best first-round annotator (selection); 5 people; whole articles, not AI-edited human drafts, not resumes |
| insight-global-2025 | p.9: 88% "say they can tell when candidates are using AI to help with applications, cover letters, or resumes"; 54% would care if a resume or cover letter was written by AI, 46% would not. Method p.14: Atomik Research online survey, 1,005 full-time HR / talent-acquisition executives responsible for hiring, firms of 100+, fieldwork 2024-10-17 to 10-22, stated margin +/-3 pts | Vendor survey (staffing firm that also sells AI services) | Question wording not published; self-report |
| resume-genius-2026 | 80% "can often tell"; 77% many resumes look partly or fully AI; 76% AI resumes make it harder to see what a candidate did; 72% heavy reliance makes candidates seem less skilled; 79% candidates should disclose AI help; tells: unnatural phrasing 51%, repetitive / generic 44%, vague or inflated 41%, buzzwords 41%, perfect grammar 39%, formatting e.g. em dashes 32%, incorrect or irrelevant details 27%; 4% notice no signs | Vendor survey (resume builder), 1,000 US hiring managers, Pollfish random device engagement, screened for hiring duty; updated 2026-03-24; dates not given | Self-report; wording not published |
| wiles-2025 | Published abstract: "nongenerative algorithmic writing assistance"; hired 8% more often (WP: 95% interval 3%-13%), 10% higher wages, 7.8% more contracts; no evidence employers less satisfied; treated resumes had fewer errors and were easier to read; treated did not apply more or bid higher. Effect concentrated among the worst spellers | 480,948 new jobseekers, one online labor market, randomized | Pre-ChatGPT; one platform; authors funded by the platform (published funding note) |
| cui-2025 | Freelancer.com AI Bid Writer (April 2023). Access: +0.16 SD tailoring, +0.43 pts callbacks; usage: +1.36 SD, +3.56 pts (= +51% on a 7.02% base), significant at 10% not 5%, tapered after 2 months; awards too imprecise. Tailoring-callback correlation fell 51%, tailoring-offer 79%; review-score-callback correlation rose 5%. Most AI letters sent with little or no editing; 1 SD more editing time -> +0.31 pts offer chance (worker fixed effects). No change found in overall hiring | 5 million letters, 100,000+ jobs, difference-in-differences around launch (GPT-4 one month earlier complicates it) | Preprint; one platform; usage not randomized |
| galdin-silbert-2025 | Before LLMs employers had a high willingness to pay for tailored applications, "but not after". Model counterfactual where writing no longer signals: top-ability quintile hired 19% less, bottom quintile 14% more | 61,000 coding job posts, 2.7 million applications, 212,000 workers, Freelancer.com, Jan 2021-Jul 2024; LLM-scored tailoring; structural model | Preprint (job market paper); 19%/14% are simulated, extreme scenario (signal fully gone) |
| kobak-2025 | Excess-word study: delves r = 28.0, underscores 13.8, showcasing 10.7; common words with excess use: potential, findings, crucial; at least 13.5% of 2024 abstracts processed with LLMs, up to 40% in some subgroups; "pivotal" on the excess list | 15 million+ PubMed abstracts 2010-2024 | Science abstracts, not resumes; says nothing about readers noticing |
| xu-2025 | Executive summary of each resume replaced by an AI-written one, rest unchanged. 8 of 9 models prefer their own summary over the human one (26%-98%; large models 67%-82%, GPT-4o 82%+). Simulated shortlisting, 24 occupations: same-model users 23%-60% more likely shortlisted; largest in sales, accounting. Simple prompts / majority voting cut the bias by more than half (GPT-4o 82% -> 30%) | 2,245 pre-AI resumes from a resume-builder site; 9 models; lab | Numbers from arXiv v4 (2026-06); earlier versions gave other ranges (drafter's notes: 68-88%) - EAAMO'25 text unopened |

Also found (not cited in the draft; leads, open before citing):
- Jiang, Hao, Fauss & Li 2024, Computers & Education 105070 - ETS detector on GRE essays, reported
  near-100% accuracy and tested native vs non-native fairness; widely cited as finding no bias
  against non-native writers. Only the ETS talk page opened (no results on it). Counter-evidence to Liang.
- Ort 2026, SSRN 7426699, "The Style Penalty: How AI Resume-Writing Tools Shape Outcomes in
  Automated Hiring Screens" (1,576 decisions, 4 models) - SSRN returned 403; not read.
- "SHRM survey, early 2026: 43% of large employers use AI detection tools" - seen only in a search
  summary from a vendor blog; find the SHRM source or drop. Bears on "no study showing how many
  employers run them".
- Robert Half, March 2026, 2,000+ US hiring managers: 67% say AI-generated applications slowed
  hiring (search summary only).
- ResumeBuilder 2023 "blind test of 1,000 recruiters" on AI cover letters - vendor, method unseen; skip unless a method is published.

## Claim table

72 citation markers in the article (77 id citations, 11 distinct ids); 138 rows below.

| # | Line | Claim | Source | What the source says | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|---|
| 1 | 2 | Title "Can employers tell if AI wrote your resume?" | - | Matches search intent; 44 chars | Supported | - | - |
| 2 | 3 | Most people can't reliably spot AI writing | jakesch-2023 | 50-52%, older models | Needs caveat | low | "in tests with older AI" or keep, body carries it |
| 3 | 3 | Detector tools misfire | liang, openai, russell | 2023 tools misfired; 2025 paid tools near-perfect on articles | Overstated | high | F1 |
| 4 | 3 | Using AI is not the risk; generic lines and unbacked claims are | none | No source tests "AI use carries no risk"; 54% say they'd care, 72% say heavy reliance looks less skilled, AI screeners prefer own text | Unsupported | high | F2 |
| 5 | 7 | og_title "... What studies show" | - | Fine | Supported | - | - |
| 6 | 15 | Most readers can't reliably tell AI from human writing (Lab study, 4,600) | jakesch-2023 | Yes, for GPT-2/GPT-3 profiles, online panel | Needs caveat | medium | F8: add "older AI models" |
| 7 | 16 | Frequent AI users spot it far better (Lab study, small) | russell-2025 | 5 hand-picked readers, news articles | Supported, needs caveat | low | "5 readers, news articles" |
| 8 | 17 | Detector tools misfire | openai-2023; liang-2023 | 2023 tools; 2025 commercial tool matched experts | Outdated | high | F1 |
| 9 | 17 | ... and wrongly flag non-native English writers | liang-2023 | 7 detectors, 91 essays, 2023; contrary ETS study exists | Overstated | medium | F1, F7 |
| 10 | 18 | Hiring managers say they can tell | insight; resume-genius | 88%, 80% "often" | Supported | - | - |
| 11 | 18 | ... and dislike generic AI text | insight; resume-genius | 54% would care / 46% not; "tells" list, not dislike | Overstated | medium | F6 |
| 12 | 19 | Writing help raised hires in one big test | wiles-2025 | Non-generative spelling / grammar help | Needs caveat | medium | F3 |
| 13 | 19 | AI-tailored letters now count for less | cui-2025 | Tailoring-callback link -51% | Supported | - | label preprint |
| 14 | 19 | Labels "Big study; Real records, preprints" | registry | wiles large field exp; cui observational preprint | Supported | - | - |
| 15 | 21 | H2 question-led | - | - | Supported | - | - |
| 16 | 23 | Most people can't, in the largest test | jakesch-2023 | Largest found; online panel | Supported | low | name "online panel" |
| 17 | 23 | 2023, 4,600 people judged short self-descriptions | jakesch-2023 | 4,600, 7,600 texts | Supported | - | - |
| 18 | 23 | Texts included freelancer profiles used to win work | jakesch-2023 | Guru.com profiles, 60-90 words | Supported | - | - |
| 19 | 23 | Right source only 50% to 52% | jakesch-2023 | "50 to 52% accuracy" | Supported | - | - |
| 20 | 23 | about as good as a coin toss | jakesch-2023 | "close to chance" | Supported | - | - |
| 21 | 23 | Paying for right answers: 51.6% | jakesch-2023 | 51.6% | Supported | - | - |
| 22 | 23 | Feedback after each answer: 51.2% | jakesch-2023 | 51.2% | Supported | - | - |
| 23 | 25 | Wrong clues: first-person words, contractions, family topics | jakesch-2023 | Same three in abstract | Supported | - | - |
| 24 | 25 | Models were GPT-2 and GPT-3 (no citation) | jakesch-2023 | Fine-tuned GPT-2 774M, GPT-3 13B | Supported, uncited | low | L1 add cite |
| 25 | 25 | (missing) AI text tuned to the clues read as more human than humans | jakesch-2023 | 65.7% vs 51.7%; 71% professional | Missing | low | L9 |
| 26 | 27 | Strongest counter-evidence: 2025 study of practiced readers | russell-2025 | ACL 2025 | Supported | - | - |
| 27 | 27 | Nine paid readers labeled 300 articles | russell-2025 | 9 annotators, 300 articles | Supported | - | - |
| 28 | 27 | Four rare-AI readers about chance | russell-2025 | "similar to random chance" | Supported | - | - |
| 29 | 27 | Flagged 56.7% of AI, 52.5% of human | russell-2025 | Text 52.5%, Table 1 51.7% | Supported (source inconsistent) | low | L1: footnote or use text value with "about half" |
| 30 | 27 | Five frequent-AI readers far better | russell-2025 | Yes; recruited to resemble the top performer | Needs caveat | medium | F4 |
| 31 | 27 | Majority vote 299 of 300 right | russell-2025 | "misclassifies only 1 of 300" | Supported | - | - |
| 32 | 27 | Top clue "AI vocabulary", "vibrant", "crucial" | russell-2025 | Same | Supported | - | - |
| 33 | 27 | News-style articles, not resumes (uncited) | russell-2025 | Non-fiction articles | Supported, uncited | low | L1 |
| 34 | 27 | (missing) texts were fully AI-written, not AI-edited drafts | russell-2025 | Generated from scratch | Missing | medium | F4 |
| 35 | 29 | A frequent-AI reader may notice AI wording | russell-2025 | 5 readers, articles | Needs caveat | medium | F4 |
| 36 | 29 | Most readers will guess, some wrongly about your own text | jakesch; russell | Near-chance + 52.5% FPR | Supported | - | - |
| 37 | 31 | H2 Do AI detectors work on resumes? | - | - | Supported | - | - |
| 38 | 33 | Not reliably, and they can be unfair | openai; liang; russell | Mixed by tool + year | Overstated | high | F1 |
| 39 | 33 | OpenAI released detector January 2023 | openai-2023 | 2023-01-31 | Supported | - | - |
| 40 | 33 | Caught 26% of AI text, maker's test | openai-2023 | 26% on "challenge set" | Supported | - | - |
| 41 | 33 | Flagged human text 9% | openai-2023 | 9% | Supported | - | - |
| 42 | 33 | Withdrawn July 2023, "its low rate of accuracy" | openai-2023 | 2023-07-20, same words | Supported | - | - |
| 43 | 35 | 2023 study, seven detectors, essays all by people | liang-2023 | Same | Supported | - | - |
| 44 | 35 | Nearly perfect on US eighth graders | liang-2023 | "near-perfect accuracy" | Supported | - | - |
| 45 | 35 | Non-native essays flagged 61% on average | liang-2023 | 61.22% | Supported | - | - |
| 46 | 35 | 97.8% flagged by at least one | liang-2023 | 89 of 91 | Supported | low | L2 sentence opens with a numeral |
| 47 | 35 | Plainer word choice made human writing look like AI | liang-2023 | 5.19% -> 56.65% | Supported | - | - |
| 48 | 35 | (missing) contrary ETS study on GRE essays | - | Jiang et al. 2024 | Missing | medium | F7 |
| 49 | 37 | Detectors have changed since then | russell-2025 | Yes | Supported | - | - |
| 50 | 37 | One paid detector matched the practiced readers | russell-2025 | Pangram | Supported | - | promote to the section answer (F1) |
| 51 | 37 | Two free detectors caught 6.7% and 23.3% of reworded AI articles | russell-2025 | o1-pro humanized column | Supported | low | name "after a rewording tool" |
| 52 | 37 | (missing) GPTZero 85.3% caught, 0.7% false flags | russell-2025 | Table | Missing | medium | F1 |
| 53 | 39 | No study tests detectors on resumes | uncited search | None found by reviewer either (vendor blog tests only) | Supported | - | - |
| 54 | 39 | No study shows how many employers run them | uncited search | SHRM 2026 claim seen second-hand | Possibly outdated | medium | F7 |
| 55 | 41 | Detector "AI" label is weak evidence | openai; liang | For 2023 tools; 2025 paid tools strong on articles | Overstated | high | F1 |
| 56 | 41 | Plain, simple English can trip it | liang-2023 | Yes, 2023 tools | Needs caveat | low | "older detectors" |
| 57 | 45 | They say they can tell, many say they care | insight; resume-genius | Yes | Supported | - | - |
| 58 | 45 | Both surveys from hiring / resume businesses | registry | Staffing firm; resume builder | Supported | - | use the label word "Vendor survey" in text |
| 59 | 47 | Oct 2024, 1,005 US HR and hiring leaders | insight-global-2025 | HR / TA executives, 100+ staff | Supported | - | - |
| 60 | 47 | 88% can tell when applicants use AI | insight-global-2025 | 88% "say they can tell ... using AI to help" | Supported | - | - |
| 61 | 47 | 54% would care | insight-global-2025 | 54% | Supported | low | L2 numeral start |
| 62 | 47 | 46% would not | insight-global-2025 | 46% | Supported | low | L2 |
| 63 | 47 | Year label 2025 for a 2024 survey | registry | Fieldwork Oct 2024; file IG24 | Check | low | L8 |
| 64 | 49 | 2026 survey, 1,000 US hiring managers, for a resume-builder | resume-genius-2026 | Pollfish, 1,000 | Supported | - | - |
| 65 | 49 | 80% can often tell | resume-genius-2026 | 80% | Supported | - | - |
| 66 | 49 | 76% harder to see what a person did | resume-genius-2026 | 76% | Supported | - | - |
| 67 | 49 | 72% heavy reliance seems less skilled | resume-genius-2026 | 72% | Supported | - | - |
| 68 | 49 | (missing) 79% say candidates should disclose AI help | resume-genius-2026 | 79% | Missing | low | L3 |
| 69 | 51 | Signs mostly about quality | resume-genius-2026 | Interpretation; 27% "incorrect details", 39% "perfect grammar" | Mostly supported | low | L10 |
| 70 | 51 | Unnatural phrasing 51%, generic 44%, vague / inflated 41% | resume-genius-2026 | Same | Supported | - | - |
| 71 | 51 | 32% formatting habits such as long dashes | resume-genius-2026 | Em dashes 32% | Supported | low | L2 |
| 72 | 53 | Saying is not spotting | jakesch; russell | Supported by both | Supported | - | - |
| 73 | 53 | Rare-AI readers felt sure, did no better than chance | russell-2025 | Confidence 4.03 of 5 | Supported | - | - |
| 74 | 55 | Managers' signs = generic, vague, inflated; worth cutting | resume-genius-2026 | Self-report | Supported | - | - |
| 75 | 59 | Writing help raised hiring in the largest real test | wiles-2025 | Yes | Supported | - | - |
| 76 | 59 | Spelling and grammar help, not today's chat AI | wiles-2025 | "nongenerative" | Supported | - | - |
| 77 | 61 | 2021, online freelance platform, 480,948 new jobseekers | wiles-2025 | June-July 2021, 480,948 | Supported | - | - |
| 78 | 61 | Half got suggestions on spelling, grammar and wording for their profile | wiles-2025 | 240,231 / 240,717; errors + readability | Supported | - | - |
| 79 | 61 | Hired 8% more often | wiles-2025 | 8% (interval 3%-13%) | Supported | low | L4 range |
| 80 | 61 | Paid 10% more per hour | wiles-2025 | "10% higher wages"; "per hour" not checked in published text | Needs check | low | L4 drop "per hour" or confirm |
| 81 | 61 | Employers rated hires just as highly | wiles-2025 | No evidence of lower satisfaction | Supported | - | - |
| 82 | 61 | Authors' reading: clearer writing helped employers see ability | wiles-2025 | Same | Supported | - | - |
| 83 | 61 | (missing) authors funded by the platform | wiles-2025 | Funding note | Missing | low | L4 |
| 84 | 63 | Two 2025 studies of one platform after April 2023 AI writer | cui; galdin | Both Freelancer.com; both use the April 2023 tool date | Supported | - | - |
| 85 | 63 | Both preprints | registry | Yes | Supported | - | - |
| 86 | 65 | 5 million letters, 100,000+ jobs | cui-2025 | Same | Supported | - | - |
| 87 | 65 | AI tool users got 3.56 pts more callbacks | cui-2025 | Usage estimate, not randomized; access effect 0.43 pts | Overstated | medium | F5 |
| 88 | 65 | Gain not certain enough to rule out chance; faded after two months | cui-2025 | 10% not 5%; tapered | Supported | - | - |
| 89 | 65 | Close-match letters went with more callbacks before | cui-2025 | Yes | Supported | - | - |
| 90 | 65 | Link 51% weaker after | cui-2025 | 51%; offer link 79% | Supported | low | L5 |
| 91 | 65 | Employers leaned more on past reviews | cui-2025 | Review-score correlation +5% | Supported | low | say "a little more" |
| 92 | 65 | Longer editing went with higher offer chance | cui-2025 | +0.31 pts per SD | Supported | - | - |
| 93 | 65 | Most AI letters sent with little or no editing | cui-2025 | Same | Supported | - | - |
| 94 | 65 | (missing) no change in overall hiring found | cui-2025 | "no evidence of changes" | Missing | low | L5 |
| 95 | 67 | 2.7 million applications to coding jobs | galdin-silbert-2025 | 2.7M, 61,000 posts | Supported | - | - |
| 96 | 67 | Employers paid more for close-fit applications before chat AI | galdin-silbert-2025 | "high willingness to pay" | Supported | - | - |
| 97 | 67 | That premium fell sharply after | galdin-silbert-2025 | "but not after" | Supported (understated) | low | L11 |
| 98 | 67 | Model of a market with no signal | galdin-silbert-2025 | Counterfactual | Supported | - | - |
| 99 | 67 | Most able hired 19% less | galdin-silbert-2025 | Top quintile, model | Supported | - | - |
| 100 | 67 | Least able 14% more | galdin-silbert-2025 | Bottom quintile, model | Supported | - | - |
| 101 | 67 | From the model, not real hires | galdin-silbert-2025 | Yes | Supported | - | - |
| 102 | 69 | Polishing your own wording helped in a large test | wiles-2025 | Spelling / grammar | Supported | - | - |
| 103 | 69 | Echo-the-post letter tells employers less | cui; galdin | Yes, one platform | Supported | - | - |
| 104 | 69 | Your real record carries more weight | cui-2025 | Platform review scores, +5% correlation | Overstated | medium | F5 |
| 105 | 73 | In one lab test, AI wording helped with AI screeners | xu-2025 | Same-model only; mixed across models | Needs caveat | low | "when the screener was the same AI" |
| 106 | 73 | 2,245 real resumes, AI rewrote summary section | xu-2025 | Executive summary replaced | Supported | - | - |
| 107 | 73 | Each model picked own vs person's summary | xu-2025 | Yes | Supported | - | - |
| 108 | 73 | Eight of nine models picked own more often | xu-2025 | 8 of 9, 26%-98% | Supported | medium | F6b: say version |
| 109 | 73 | 24 jobs, 23% to 60% more likely shortlisted | xu-2025 | v4 numbers | Supported for v4 | medium | F6b |
| 110 | 73 | Lab test, not a real employer's system | xu-2025 | Yes | Supported | - | - |
| 111 | 73 | (missing) simple prompts cut the bias by half | xu-2025 | GPT-4o 82% -> 30% | Missing | low | L12 |
| 112 | 75 | AI screener may like AI wording, human may dislike it | xu; surveys | Fair synthesis | Supported | - | - |
| 113 | 75 | Clear, specific lines safest for both | - | Advice, no source tests it | Needs label | low | "no study tests this" or convention |
| 114 | 79 | Some words much more common after chat AI | kobak-2025 | Yes | Supported | - | - |
| 115 | 79 | 15 million+ summaries, 2010-2024 | kobak-2025 | Same | Supported | - | - |
| 116 | 79 | "Delves" 28 times its expected frequency in 2024 | kobak-2025 | r = 28.0 | Supported | - | - |
| 117 | 79 | Underscores 13.8, showcasing 10.7 | kobak-2025 | Same | Supported | - | - |
| 118 | 79 | Common words "crucial", "potential" jumped | kobak-2025 | Excess delta: potential, crucial | Supported | - | - |
| 119 | 79 | At least 13.5% of 2024 summaries processed with AI | kobak-2025 | Same | Supported | - | - |
| 120 | 79 | Science writing, not resumes; not whether employers notice | kobak-2025 | Correct limits | Supported | - | - |
| 121 | 81 | "Delve", "showcase", "pivotal" add no facts | kobak-2025 (pivotal on list) | Opinion, convention | Supported as advice | low | - |
| 122 | 85 | Unknown: how often employers run detectors | - | See SHRM lead | Check | medium | F7 |
| 123 | 86 | No study tests detectors on resumes | - | None found | Supported | - | - |
| 124 | 87 | Unknown whether managers who say they can tell can | - | True | Supported | - | - |
| 125 | 88 | Unknown whether chat AI helps or hurts in real hiring; field test 2021 | wiles-2025 | Cui is real hiring with chat AI (letters) | Needs caveat | low | mention Cui covers letters only |
| 126 | 89 | Freelance results may not hold for regular jobs; one platform | cui; galdin | Yes | Supported | - | - |
| 127 | 90 | Searched web, arXiv, news Oct 2026 | - | Date is today; fine | Supported | low | list search terms in `uncited:` |
| 128 | 94 | Use AI for wording; clearer writing raised hires | wiles-2025 | Non-generative help | Misattributed | medium | F3 |
| 129 | 95 | Own facts + numbers; employers lean on what AI can't make up | cui-2025 | Review scores on the platform | Overstated | medium | F5 |
| 130 | 96 | Edit AI drafts; editing went with more offers | cui-2025 | Correlation, within worker | Supported ("went with") | low | keep "went with" |
| 131 | 97 | Cut generic lines; managers name these as AI signs | resume-genius-2026 | Self-report | Supported | - | - |
| 132 | 98 | Anything on the page can come up in interview | - | Convention, uncited | Needs label | low | L1 |
| 133 | 99 | Never let AI invent; false claim | - | Ethics, no source needed | Supported | - | - |
| 134 | 101 | Internal links: methods, bias article, ATS article | - | 3 internal links | Supported | - | - |
| 135 | 105 | Tool rewords from your facts only | app behaviour | AGENTS.md / tailoring gates | Supported | - | - |
| 136 | 106 | You confirm every changed line | app behaviour | job-tailor skill | Supported | - | - |
| 137 | 107 | Check flags overused AI words from "the kind of word counts above" | app/resume/lint.py:17-23 | Comment cites Kobak with older preprint ratios (plan-xsy.45 open) | Needs fix elsewhere | low | L6 |
| 138 | 108 | Posting term only where experience backs it | AGENTS.md | Keyword rule | Supported | - | - |


## Findings (all status: open)

| # | Sev | Finding | Fix | Status |
|---|---|---|---|---|
| F1 | high | Detector answer is one-sided and outdated. Short answer ("Detector tools misfire"), section opener ("Not reliably") and "weak evidence" (l.41) rest on 2023 tools. The article's own 2025 source shows Pangram matching expert readers (99.3% caught) and GPTZero catching 85.3% with 0.7% false flags on articles. | Reframe: early detectors misfired and flagged non-native writers; a 2025 test found one paid tool near-perfect on whole AI articles; free tools failed on reworded text; no tool tested on resumes. Short answer bullet to match. Keep Liang, add "2023 tools". | open |
| F2 | high | Description says "Using AI is not the risk; generic lines and claims you can't back up are." No source tests that. Surveys say 54% would care and 72% think heavy reliance looks less skilled; Cui shows AI-tailored letters count for less. | Description = what studies show, e.g. "Most people can't spot AI writing, but many hiring managers say they care. What studies show, and what to do." (<= 155). | open |
| F3 | medium | Wiles (non-generative spelling + grammar help) used as support for using AI: short answer bullet 5 ("Writing help raised hires") and What helps l.94 ("Use AI for wording ... Clearer writing raised hires"). Body l.59 handles it right. | Short answer: "Spelling and grammar help raised hires (2021, not chat AI)". What helps: cite Wiles for "fix errors and make lines clearer", not for chat AI. | open |
| F4 | medium | Russell's "experts" are 5 people recruited to resemble the best first-round reader; texts were whole AI-written news articles, not human drafts edited with AI. L.29 extends it to resumes. | Add one sentence: five readers picked for being good; whole AI articles. L.29: "may notice text written wholly by AI". | open |
| F5 | medium | Cui overstated twice. (a) l.65 leads with the 3.56-point usage estimate; usage was not randomized; the access effect was 0.43 points. (b) l.69 + l.95 turn "employers leaned a little more on platform review scores (+5%)" into "put in your own facts and numbers ... employers lean on what AI can't make up". | (a) Give access effect first, usage as a weaker estimate. (b) "Employers leaned a little more on each worker's past reviews on the platform" - keep "own facts" advice but cite it as convention or the bullets doc, not Cui. | open |
| F6 | medium | Short answer bullet 4 "dislike generic AI text": Insight Global was split 54% care / 46% don't; the tell list is not a dislike measure. | "about half say they'd care; they name generic, vague lines as signs". | open |
| F6b | medium | Xu numbers (8 of 9, 23%-60%) are from arXiv v4 (June 2026); registry cites the EAAMO'25 DOI; earlier versions gave different ranges (67-82% / 68-88%). | Say "updated June 2026 version" in sentence or registry `venue`; open the EAAMO text and note any difference. | open |
| F7 | medium | Missing counter-evidence + possible new data: Jiang et al. 2024 (ETS, GRE essays; reported no bias against non-native writers for its detector); SHRM 2026 "43% of large employers use AI detection tools" (second-hand); Ort 2026 SSRN "Style Penalty" (AI screeners vs AI-tool resumes). | Open each. Cite Jiang beside Liang if it holds. SHRM: cite if primary found, else keep "no study" and list the search in `uncited:`. Ort: read; cite in the AI-screener section if it bears on it. | open |
| F8 | medium | Short answer bullet 1 states, present tense, a result from GPT-2/GPT-3 texts judged by online panels. | "Most people in tests couldn't tell (older AI models, 4,600 people)". | open |
| L1 | low | Uncited fact sentences: l.25 (GPT-2/GPT-3), l.27 end (news-style articles), l.98 (interview line = convention). Russell FPR 52.5% (text) vs 51.7% (Table 1). | Add cites; label l.98 convention; "about half" or note the table. | open |
| L2 | low | Sentences open with numerals (l.35 "97.8%", l.47 "54%", "46%", l.49, l.51 "32%") - harder to quote alone. | Lead with the subject: "Of those essays, 97.8% ...". | open |
| L3 | low | Resume Genius 79% "should disclose AI help" omitted - bears on "is it bad to use ChatGPT". | One sentence, Vendor survey label. | open |
| L4 | low | Wiles: 8% has a 3%-13% range; "per hour" not in the published abstract ("wages"); authors funded by the platform. | "about 8% (3% to 13%)"; "10% higher pay"; funding note in Sources or a clause. | open |
| L5 | low | Cui: offer link fell 79%; no change in overall hiring found - both omitted. | Add one sentence each, or note the no-change result. | open |
| L6 | low | Tool box says the word list comes "from the kind of word counts above"; lint.py comment quotes older Kobak ratios (plan-xsy.45). | Land plan-xsy.45 before publish, or word it "a list built from studies like this one". | open |
| L7 | low | "percentage points" unexplained (l.65). | "3.56 more callbacks per 100 letters". | open |
| L8 | low | insight-global-2025 year: fieldwork Oct 2024, file name IG24; check the publication year. | Confirm on the landing page; fix `year` if 2024. | open |
| L9 | low | Jakesch also found AI text tuned to people's clues read as more human than real human text (65.7% vs 51.7%; 71% for job profiles). | Optional sentence - sharpens "people rely on wrong clues". | open |
| L10 | low | "Mostly about quality" is our reading; list also has "perfect grammar" 39%, "incorrect details" 27%. | "Most named signs were about wording quality". | open |
| L11 | low | Galdin "fell sharply" understates "not after" (premium gone). | "mostly disappeared". | open |
| L12 | low | Xu: simple prompt fixes cut self-preference by more than half - omitted; matters for "what helps employers". | Optional clause. | open |

## Checks

- Plain words: no AGENTS.md jargon in body. "Preprints", "percentage points" are the only
  technical words (L7).
- Quotes: "its low rate of accuracy" (5 words), "AI vocabulary", "vibrant", "crucial" - all <= 15
  words, attributed.
- Privacy: no owner data, no real employer as an example. Platforms named (Freelancer.com is not
  named in the text; "one freelance platform") - fine.
- Labels: vendor surveys labelled in text (l.45) and short answer; preprints said (l.63, short answer).
- Title 44 chars, description 145 chars - within limits, but description content fails (F2).
- What we don't know: present, useful; add detector-use survey status after F7.
- Tool box separate, after evidence, short - but see L6.

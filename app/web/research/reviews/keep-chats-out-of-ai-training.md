---
reviewed: 2026-10-07
verdict: publish
reviewer: fresh AI session, bead plan-xsy.31 (no drafting context; sources opened before the draft was read); re-review 2026-10-07 fresh AI session (plan-ngk.6)
---
# Review: Keep your chats out of AI training (`keep-chats-out-of-ai-training.md`)

Verdict **publish** after revision (plan-xsy.32, 2026-10-03): all 23 findings fixed. Original verdict **revise**: 2 high, 7 medium, 14 low findings. The steps are right: every menu
name and click path checked matched the maker's page, word for word. Quotes are exact and short.
The problems are promises the pages don't make. The Gemini section says chats with the switch off
"aren't kept past 72 hours"; Google's own hub says reviewed chats stay 3 years and anonymized use
isn't covered by the switch at all. The body calls Nasr 2023 a preprint; it was published at
ICLR 2025. The short answer's "new chats only" cites the one company (Anthropic) that says the
opposite. "Copilot" is never told apart from Microsoft Copilot.

## Sources, read before the draft (all opened 2026-10-03)

Web pages via curl, read as text. OpenAI's two pages answer 403 to scripts (live and in the
Internet Archive's newest captures): the help page was read from the 2026-09-25 20:03 capture
(the 09-30 capture is itself a 403), the policy page from the 2026-09-28 capture - same copies the
draft used. arXiv abstract pages read; ICLR 2025 status of Nasr found by web search (proceedings
page). No source contained text addressing an AI.

| id | What it actually supports | Design / date | Limits |
|---|---|---|---|
| openai-data-controls | Switch **Improve the model for everyone**; off -> "new conversations won't be used to train"; web steps: account menu > Settings > Data controls > switch off > Done; iOS/Android: sidebar > profile icon (Settings) > Data controls; follows account across devices; Codex tasks covered, but Codex's separate "Include environments" setting is not; privacy-portal "Do not train on my content" - either is enough; turning off doesn't delete or hide chats; Temporary chats: no history, no memory, not used for training, kept up to 30 days for safety; Business/Enterprise/Edu/Healthcare not trained on by default; org policies "still apply"; thumbs up/down -> "the entire conversation ... may be used to train" even after opt-out | Maker's docs; Internet Archive capture 2026-09-25 | Live page unreadable by script; check in a browser before publish |
| openai-model-training | "ChatGPT ... improves by further training on the conversations people have with it, unless you opt out"; privacy-portal "do not train on my content"; Temporary Chat not trained on; Sora separate setting; business products (Team, Enterprise, API) not trained on by default, API opt-in e.g. Playground feedback; "steps to reduce the amount of personal information in our training datasets" | Maker's docs; updated 2026-03-13; Archive 2026-09-28 | Still says "ChatGPT Team" (now Business); no plan names for personal tiers |
| anthropic-consumer-terms-2025 | Aug 28 2025: Free/Pro/Max (incl. Claude Code) choose; deadline Oct 8 2025; new/resumed chats only, older idle chats not used; 5-year retention if on, 30 days if not; deleted chats not used for future training; filter/obfuscate sensitive data; turning off: "will stop using your previously stored chats" in future runs; past runs keep it; not for Claude for Work/Gov/Education/API/Bedrock/Vertex | Maker's announcement; page modified 2026-09-10 | Doesn't say which way the pop-up switch was set by default |
| anthropic-training-setting | Steps: name > Settings > Privacy > "Help Improve our AI models" toggle (capital I in source); phone: name > same toggle; off -> new chats not used, past runs keep it, "we will stop using your previously stored chats"; safety-flagged chats may still improve trust-and-safety models; link claude.ai/settings/data-privacy-controls | Maker's docs, updated 2026-08-03 | - |
| anthropic-training-consumer | Used if: switch on, flagged for safety review, or other explicit opt-in (Trusted Tester); whole conversation incl. Claude for Chrome data, not raw connector content; Incognito never used; thumbs: whole conversation stored up to 5 years, de-linked from user ID, may train | Maker's docs, updated 2026-03-16 | - |
| anthropic-retention | Standard: deleted chat leaves history at once, back-end within 30 days (stated for everyone); switch on: "de-identified format for up to 5 years in our model training pipelines"; switch off: previous or new chats not used in future training; flagged chats: inputs/outputs up to 2 years, safety scores up to 7 years; feedback 5 years; "as required by law" longer | Maker's docs, updated 2026-07-01 | Silent on whether a deleted chat already in the training pipeline is purged |
| anthropic-training-work | Commercial products (Claude for Work, API, Gov): not trained on by default; thumbs/bug reports or opt-in -> may train; feedback 5 years, de-linked; admins can turn off "Rate chats" | Maker's docs, updated 2026-08-18 | - |
| github-copilot-2026 | From April 24 [2026], Free/Pro/Pro+ interaction data (inputs, outputs, code snippets, context, file names, repo structure, chat, inline suggestions, thumbs) "will be used to train" unless opted out; earlier opt-out kept; Business/Enterprise not affected; may be shared with "companies in our corporate family including Microsoft"; not shared with third-party AI model providers | Maker's blog, March 25 2026 | Announcement in future tense |
| github-copilot-docs | Who: Pro, Pro+, Max, Free; steps: profile picture > Copilot settings > "Allow GitHub to use my data for AI model training" > Disabled; setting hidden for Business/Enterprise (DPA "prohibits such use without customer authorization") | Maker's docs, read 2026-10-03 | - |
| github-copilot-faq-2026 | Copilot Student and teachers on free Pro not affected; members/outside collaborators of a paid org excluded; automated PII filtering; service providers may assist with training under contract; third-party model providers don't get it for their own training | GitHub admin post on community forum (shows "Mar 2, 2026") | Forum post, but by GitHub staff account |
| google-gemini-activity | Personal accounts; steps: gemini.google.com > Settings & help > Activity > On > Turn off / Turn off and delete activity; on by default 18+; off -> chats saved with account up to 72 hours; only a few connected apps work; work/school set by admin | Maker's docs, read 2026-10-03 | - |
| google-gemini-privacy | Keep Activity on -> chats train models, human reviewers; reviewed chats kept up to 3 years, disconnected from account, not deleted with activity; off -> future chats not trained on "unless you choose to send Google feedback"; **even off, chats used to protect Google/users "including with help from human reviewers"**; **"Your Gemini settings don't control processing of your chats to create anonymized data to improve Google services"**; feedback with Keep Activity off sends feedback + "the last 24 hours of your chats", human-reviewed, kept 3 years; Temporary chats not trained on, 72 hours | Maker's privacy hub, read 2026-10-03 | - |
| carlini-2021 | GPT-2 (trained on public web scrapes): hundreds of verbatim sequences extracted, incl. "(public)" names, phone numbers, emails; possible even when a sequence is in one document; larger models more vulnerable | Lab attack study; USENIX Security 2021 | Web text, not chats; 2019-era model |
| nasr-2023 | Gigabytes extracted from open models; ChatGPT (GPT-3.5) emits training data 150x more often under a "divergence" attack; alignment doesn't remove memorization | arXiv 2311.17035 v1; **published ICLR 2025** as "Scalable Extraction of Training Data from Aligned, Production Language Models" (adds author Javier Rando), proceedings.iclr.cc | Training text = web data; ChatGPT result is "thousands of training examples" in the ICLR abstract, under $300 spend |

Also found (not cited; open before citing):
- ICLR 2025 proceedings page for Nasr et al. - the citation the registry should carry.
- Third-party 2026 opt-out guides (Medium, trustscan.dev, felloai.com) repeat the same menu names
  ("Improve the model for everyone", "Help Improve our AI models") - agree with the makers; not
  sources.
- Search 2025-2026 found no outside test of whether these switches work, and no study showing one
  user's chat in another user's answer - the draft's "no study found" lines hold.

## Claim table

77 citation markers in the article (88 id citations, 14 distinct ids). 110 rows below: one per id
citation, plus uncited fact claims (U).

| # | Line | Claim | Source | What the source says | Verdict | Sev | Fix |
|---|---|---|---|---|---|---|---|
| 1 | 2 | Title "Keep your chats out of AI training: ChatGPT, Claude, Copilot" | - | 60 chars (limit 60); "Copilot" = GitHub Copilot only | Needs caveat | medium | F6 |
| 2 | 3 | Description: four apps can train on personal-plan chats unless switched off | all | Claude is a choice since 2025, not on unless set | Needs caveat | low | F22 |
| 3 | 7 | og_title "Stop ChatGPT, Claude, Copilot and Gemini training on your chats" | - | 63 chars; "Copilot" ambiguous | Needs caveat | medium | F6 |
| 4 | 9 | Every step checked against maker's page, October 2026 | all | Steps match (this review) | Supported | - | - |
| 5 | 13 | Personal plans can train; one switch each turns it off | openai-data-controls | Switch exists; Codex "Include environments" and Sora separate | Overstated | medium | F4 |
| 6 | 13 | (same) | anthropic-training-setting | Switch exists; safety-flagged chats still used | Overstated | medium | F4 |
| 7 | 13 | (same) | github-copilot-docs | Switch exists | Supported | - | - |
| 8 | 13 | (same) | google-gemini-privacy | Keep Activity doesn't cover anonymized data or safety review | Overstated | high | F2, F4 |
| 9 | 14 | Work and school plans don't train by default | openai-model-training | Team/Enterprise/API; Edu only on data-controls page | Supported | low | F10 |
| 10 | 14 | (same) | anthropic-consumer-terms-2025 | Says commercial products are outside the 2025 change, not that they aren't trained on | Misattributed | low | F10: cite anthropic-training-work |
| 11 | 14 | (same) | github-copilot-docs | Business/Enterprise not used | Supported | - | - |
| 12 | 14 | (same, Gemini) | - | Gemini work/school = admin's choice; not covered | Needs caveat | low | F10 |
| 13 | 15 | Switch = new chats only; past training stays | anthropic-training-setting | "we will stop using your previously stored chats" too; only past runs keep it | Misattributed / contradicts | medium | F3 |
| 14 | 16 | Thumbs can send whole chat to training | openai-data-controls | "the entire conversation ... may be used" even after opt-out | Supported | - | - |
| 15 | 16 | (same) | anthropic-training-consumer | Whole conversation stored 5 years, may train | Supported | - | - |
| 16 | 17 | AI models can repeat rare text from training data (Lab studies) | carlini-2021 | One-document sequences extracted | Supported | - | - |
| 17 | 17 | (same) | nasr-2023 | Yes; label fine | Supported | - | - |
| 18 | 21 | A resume is personal data; job seekers type pay, permits, gaps | - | Plain reasoning | Supported (reasoning) | - | - |
| 19 | 23 | OpenAI quote "improves by further training ..." unless you opt out | openai-model-training | Exact, 11 words | Supported | - | - |
| 20 | 23 | GitHub began training on Free/Pro/Pro+ chats by default April 24 2026 | github-copilot-2026 | "interaction data" incl. code, file names - not just chats; "will be used" (future tense) | Needs caveat | low | F11 |
| 21 | 23 | Anthropic asked Free/Pro/Max users to choose in 2025 | anthropic-consumer-terms-2025 | Yes | Supported | - | - |
| 22 | 25 | 2021 test pulled hundreds of exact passages from an older model | carlini-2021 | "hundreds of verbatim text sequences", GPT-2 | Supported | - | - |
| 23 | 25 | Passages included names, phone numbers, emails | carlini-2021 | "(public) personally identifiable information" | Needs caveat | low | F12: "already public online" |
| 24 | 25 | Could leak from one document | carlini-2021 | Yes | Supported | - | - |
| 25 | 25 | 2023 follow-up pulled large amounts of training text from ChatGPT | nasr-2023 | Gigabytes from open models; ChatGPT: thousands of examples, 150x rate | Overstated | low | F13 |
| 26 | 25 | That study is a preprint, not yet peer-reviewed | nasr-2023 | Published ICLR 2025 | Outdated | high | F1 |
| 27 | 27 | Both studies used public web text, not chats | - | True of both abstracts | Supported | - | - |
| 28 | 27 | No study found showing one user's chat in another's answer | - | This review's search found none either | Supported, uncited | medium | F8: `uncited:` list |
| 29 | 27 | Companies say they reduce personal details | - | OpenAI, Anthropic, GitHub FAQ all say so | Supported | - | - |
| 30 | 27 | OpenAI quote "steps to reduce the amount of personal information" | openai-model-training | Exact, 8 words | Supported | - | - |
| 31 | 27 | Anthropic: feedback chats separated from account before use | anthropic-training-consumer | "de-link your feedback from your user ID" | Supported | low | F18: also cite consumer-terms "filter or obfuscate" |
| 32 | 29 | ChatGPT chats stay in history with switch off | openai-data-controls | "does not delete or hide saved chats" | Supported | - | - |
| 33 | 33 | Switch name on Free/Go/Plus/Pro | openai-data-controls | Name exact; plans listed on page | Supported | - | - |
| 34 | 35 | Web: account menu > Settings | openai-data-controls | "Web (signed in): Open your account menu. Select Settings." | Supported | - | - |
| 35 | 36 | Data controls | openai-data-controls | Exact | Supported | - | - |
| 36 | 37 | Select switch, turn off, Done | openai-data-controls | Exact | Supported | - | - |
| 37 | 39 | Phone: sidebar > profile icon > Data controls | openai-data-controls | "iOS and Android" steps match | Supported | - | - |
| 38 | 39 | Follows account across devices | openai-data-controls | Yes, when signed in | Supported | - | - |
| 39 | 39 | Same switch covers Codex tasks | openai-data-controls | Yes; separate "Include environments" setting for environment context | Needs caveat | low | F14 |
| 40 | 41 | Privacy portal "do not train on my content" | openai-model-training | Exact, 6 words | Supported | - | - |
| 41 | 41 | Either route is enough | openai-data-controls | "Either option is sufficient" | Supported | - | - |
| 42 | 43 | Temporary chats: no history, not trained | openai-data-controls | Yes | Supported | - | - |
| 43 | 43 | Kept up to 30 days for safety | openai-data-controls | Yes | Supported | - | - |
| 44 | 45 | Use Temporary Chat "for anything you don't want saved" | - | Still kept 30 days | Needs caveat | low | F15 |
| 45 | 49 | Claude switch "Help improve our AI models" | anthropic-training-setting | "Help Improve our AI models" | Supported | - | - |
| 46 | 51 | Name > Settings | anthropic-training-setting | Yes | Supported | - | - |
| 47 | 52 | Privacy; claude.ai/settings/data-privacy-controls | anthropic-training-setting | Link target matches | Supported | - | - |
| 48 | 53 | Turn switch off | anthropic-training-setting | Yes | Supported | - | - |
| 49 | 55 | Covers Claude Code on those plans | anthropic-training-setting | Page scope says so | Supported | - | - |
| 50 | 55 | Choice made Aug 28 2025, deadline Oct 8 2025 | anthropic-consumer-terms-2025 | Yes | Supported | - | - |
| 51 | 57 | Switch on: kept up to 5 years for training | anthropic-retention | "de-identified format ... in our model training pipelines" | Needs caveat | low | F5: add "de-identified" |
| 52 | 57 | Switch off: deleted chat gone within 30 days | anthropic-retention | 30 days is the standard for everyone; flagged chats 2 yrs, law holds | Needs caveat | medium | F5 |
| 53 | 57 | Incognito never used for training | anthropic-training-consumer | "even if you have enabled Model Improvement" | Supported | - | - |
| 54 | 59 | Switch shortens how long Anthropic keeps what you delete | - | Source doesn't say deletion differs by switch | Unsupported | medium | F5 |
| 55 | 63 | Copilot Free/Pro/Pro+/Max setting name | github-copilot-docs | Exact | Supported | - | - |
| 56 | 65 | Profile picture > Copilot settings | github-copilot-docs | Exact | Supported | - | - |
| 57 | 66 | Open the setting menu | github-copilot-docs | Exact | Supported | - | - |
| 58 | 67 | Click Disabled | github-copilot-docs | Exact | Supported | - | - |
| 59 | 69 | Covers Copilot chats incl. chat in a code editor | github-copilot-2026 | Covers chat, inline suggestions, code, file names; "editor" inferred | Needs caveat | low | F11, F23 |
| 60 | 69 | Earlier opt-out kept | github-copilot-2026 | Yes | Supported | - | - |
| 61 | 71 | Copilot Student + free-Pro teachers not affected | github-copilot-faq-2026 | Yes | Supported | - | - |
| 62 | 71 | Business/Enterprise never used; setting hidden | github-copilot-docs | DPA prohibits "without customer authorization"; hidden - yes | Overstated | low | F16 |
| 63 | 73 | Quote "companies in our corporate family including Microsoft" | github-copilot-2026 | Exact, 7 words | Supported | - | - |
| 64 | 73 | Other AI companies don't get it for their own training | github-copilot-2026 | Not shared with third-party model providers | Supported | - | - |
| 65 | 73 | (same) | github-copilot-faq-2026 | Same; adds contracted service providers may help train | Supported | low | F16 |
| 66 | 75 | Paid personal plan doesn't protect; only the switch does | - | Students, teachers, paid-org members excluded | Overstated | low | F16 |
| 67 | 79 | Gemini ties training to Keep Activity | google-gemini-activity | Yes (hub says it) | Supported | - | - |
| 68 | 81 | gemini.google.com | google-gemini-activity | Yes | Supported | - | - |
| 69 | 82 | Settings & help > Activity | google-gemini-activity | Yes | Supported | - | - |
| 70 | 83 | On > Turn off / Turn off and delete activity | google-gemini-activity | Yes | Supported | - | - |
| 71 | 85 | On by default 18+ | google-gemini-activity | Yes | Supported | - | - |
| 72 | 85 | Off: kept with account up to 72 hours | google-gemini-privacy | Yes | Supported | - | - |
| 73 | 85 | Off: not trained on unless you send feedback | google-gemini-privacy | Yes, for "future chats"; anonymized data not covered | Needs caveat | high | F2 |
| 74 | 87 | Off: chats aren't kept past 72 hours; few connected apps | google-gemini-activity | 72 h with account; reviewed chats 3 years; human safety review continues | Overstated | high | F2 |
| 75 | 87 | Human reviewers read some chats; kept 3 years apart from account | google-gemini-privacy | Yes; also when off, for safety | Needs caveat | high | F2 |
| 76 | 89 | ChatGPT keeps history with switch off | openai-data-controls | Yes | Supported | - | - |
| 77 | 89 | Gemini's switch costs your saved chats | - | Future chats not in Activity | Supported | - | - |
| 78 | 93 | Quote "will still be included in model training that has already started" | anthropic-training-setting | Exact, 10 words | Supported | - | - |
| 79 | 93 | Anthropic stops using older stored chats | anthropic-training-setting | Yes | Supported | low | F3 (contradicts line 15) |
| 80 | 93 | Pre-2025 chats not used unless reopened | anthropic-consumer-terms-2025 | "Previous chats with no additional activity will not be used" | Supported | - | - |
| 81 | 93 | Heading "Past training stays" (all four apps) | - | Only Anthropic says it | Needs caveat | low | F17 |
| 82 | 95 | ChatGPT switch doesn't delete or hide chats | openai-data-controls | Yes | Supported | - | - |
| 83 | 95 | Delete separately | openai-data-controls | Yes | Supported | - | - |
| 84 | 97 | Thumbs: "the entire conversation" may train | openai-data-controls | Exact, 3 words | Supported | - | - |
| 85 | 97 | Holds even after opt-out | openai-data-controls | Yes | Supported | - | - |
| 86 | 97 | Anthropic keeps feedback 5 years, separated, then may train | anthropic-training-consumer | De-linked before use; may train; "then" implies order | Needs caveat | low | F18 |
| 87 | 97 | Gemini trains on chats you send feedback about | google-gemini-privacy | Feedback sends the last 24 hours of chats, human-reviewed, kept 3 years | Overstated (understates reach) | medium | F9 |
| 88 | 99 | Claude flagged chats still improve safety checks | anthropic-training-setting | Yes | Supported | - | - |
| 89 | 99 | OpenAI keeps Temporary Chats 30 days for safety | openai-data-controls | Yes | Supported | low | F2: add Gemini safety review |
| 90 | 101 | Your name still reaches the AI | - | Reasoning | Supported (reasoning) | - | - |
| 91 | 109 | OpenAI: no training on Business/Enterprise/Edu by default | openai-data-controls | Yes (+ Healthcare) | Supported | - | - |
| 92 | 110 | Anthropic 2025 change excluded Work/Education/developer platform | anthropic-consumer-terms-2025 | Yes | Supported | - | - |
| 93 | 110 | Trained only on feedback or opt-in | anthropic-training-work | Yes | Supported | - | - |
| 94 | 111 | GitHub: no Business/Enterprise training | github-copilot-docs | Yes | Supported | - | - |
| 95 | 112 | OpenAI developer platform opt-in only | openai-model-training | Yes | Supported | - | - |
| 96 | 114 | Claude business thumbs can still train | anthropic-training-work | Yes | Supported | - | - |
| 97 | 116 | A work login may already be covered | - | Org "privacy, retention, and access policies still apply" (openai-data-controls) | Needs caveat | medium | F7 |
| 98 | 120 | Unknown: resume coming back out; studies used web text | carlini-2021 | Yes | Supported | - | - |
| 99 | 120 | (same) | nasr-2023 | Yes | Supported | - | - |
| 100 | 121 | No outside check of personal-data removal found | - | Same in this review | Supported, uncited | medium | F8 |
| 101 | 122 | Can't test switches from outside | - | True | Supported | - | - |
| 102 | 124 | "We searched help pages, news and arXiv" (in unknowns list) | - | Method line, not an unknown; "arXiv" jargon | Style | low | F20 |
| 103 | 128 | Turn off on every app; "One minute each" | - | Unmeasured | Unsupported | low | F8 |
| 104 | 129 | Skip feedback on resume chats | openai-data-controls | Yes | Supported | - | - |
| 105 | 129 | (same) | anthropic-training-consumer | Yes | Supported | - | - |
| 106 | 130 | Temporary / incognito chat for one-offs | openai-data-controls | Yes | Supported | - | - |
| 107 | 130 | (same) | anthropic-training-consumer | Incognito not trained on | Supported | - | - |
| 108 | 131 | Claude deleted chats leave within 30 days | anthropic-retention | Back-end 30 days; training-pipeline copies (switch on), flagged chats, law holds not covered | Needs caveat | medium | F5 |
| 109 | 132 | Leave out street address etc.; common advice | - | Labelled convention | Supported | - | - |
| 110 | 138-141 | Tool box: runs in user's chat; asks once at setup; never asks to rate; can't change the switch | app/skills/job-setup.md:17-32, AGENTS.md | Matches | Supported | - | - |

Check: every cited id appears in this review - see bead plan-xsy.31 close reason (14 of 14).

## Findings

| # | Sev | Status | Line(s) | Finding | Proposed fix |
|---|---|---|---|---|---|
| F1 | high | fixed: sentence deleted; sources.yml now ICLR 2025 title, authors (Rando added, Wallace not on the ICLR list), year 2025, preprint tag removed, url now the ICLR proceedings page (arXiv v1 says 2023, which --links flags against year 2025) - checked on proceedings.iclr.cc 2026-10-03 | 25, sources.yml | "That study is a preprint, not yet peer-reviewed" is outdated: Nasr et al. was published at ICLR 2025 as "Scalable Extraction of Training Data from Aligned, Production Language Models" (Javier Rando added as author). research.md asks to drop the tag once published. | Delete the sentence. In sources.yml: title + authors per ICLR, venue "ICLR 2025 (open copy on arXiv)", year 2025 (id may stay), `preprint` removed; keep arXiv url or add the proceedings url; rerun `--links`. |
| F2 | high | fixed: 72-hour promise removed; safety review, 3-year reviewed chats, anonymized-data gap and Gemini Temporary chat added | 13, 85, 87, 99 | Gemini section promises more than Google does. "With the setting off, chats aren't kept past 72 hours" - Google's hub: even with Keep Activity off it uses chats "to help protect Google ... including with help from human reviewers", reviewed chats are kept up to 3 years, and "Your Gemini settings don't control processing of your chats to create anonymized data to improve Google services." | Line 87: "With it off, chats stay with your account up to 72 hours. Google still has people review some chats for safety; reviewed chats are kept up to 3 years." Add under "What doesn't the switch do?": Google says its switch doesn't cover chats it turns into anonymized data [@google-gemini-privacy]. Mention Gemini Temporary Chat. |
| F3 | medium | fixed: "Switch stops future training; training already done stays" | 15 vs 93 | Short answer "Switch = new chats only" cites Anthropic, whose page says turning off also stops use of "previously stored chats" in future runs; only runs already started keep them. Line 93 says the opposite of line 15. | "Switch stops future training; training already done stays (Maker's docs) [@anthropic-training-setting; @openai-data-controls]." |
| F4 | medium | fixed: "one main switch each turns most of it off" + pointer to what it doesn't do | 13 | "One switch each turns it off" - not quite: Gemini (F2); ChatGPT's Codex "Include environments" and Sora are separate settings; Claude's safety-flagged chats still used. | "...one main switch each turns most of it off" and link to "What doesn't the switch do?". |
| F5 | medium | fixed: de-identified 5-year copy; 30 days stated for everyone; flagged chats 2 years; line 131 adds safety/legal holds | 57, 59, 131 | Anthropic retention is mis-stated. The 30-day back-end deletion is the standard for everyone, not a result of the switch; the page doesn't say the switch shortens deletion. Omitted: flagged chats kept up to 2 years (scores 7), "as required by law", and the 5-year copy is "de-identified" in "training pipelines". Line 131 is unconditional and clashes with line 59. | Line 57: "With it on, a de-identified copy can stay up to 5 years in training data." Line 59: "For you, the switch keeps your chats out of that 5-year training store." Line 131: add "unless flagged for safety or held for legal reasons". |
| F6 | medium | fixed: og_title says GitHub Copilot; Copilot section opens with the Microsoft Copilot line | 2, 7, 61-75 | "Copilot" never told apart from Microsoft Copilot (Windows, Edge, copilot.microsoft.com) - the Copilot most people searching "Copilot training opt out" use. Those readers get the wrong steps. | Keep title (adding "GitHub" makes it 67 chars); og_title -> "GitHub Copilot"; one line at the top of the Copilot section: "This is GitHub Copilot, the coding tool. Microsoft Copilot has its own settings, not covered here." |
| F7 | medium | fixed: proposed wording, cited openai-data-controls | 116 | "A work login may already be covered" nudges a job seeker toward an employer's account. OpenAI's page: the organisation's "privacy, retention, and access policies still apply"; Claude admins control feedback settings. Job hunting on an employer's AI account can be seen by that employer. | Replace: "A work login trains less, but your employer sets its rules and may see it. Job-hunt on your own account." |
| F8 | medium | fixed: uncited: list added; "a few clicks each" | 27, 121, 124, 128 | Absence-of-evidence lines ("no study we found", "no outside check was found") and "One minute each" have no `uncited:` front-matter list; research.md says what was searched goes there. | Add `uncited:` listing the searches (makers' help pages, news, arXiv, 2025-2026 web search for outside tests; this review's search agrees). Drop "One minute each" or say "a few clicks each". |
| F9 | medium | fixed: proposed wording, split into two sentences | 97 | Gemini feedback is understated. With Keep Activity off, sending feedback also sends "the last 24 hours of your chats", reviewed by people and kept up to 3 years. For a job seeker that can be every chat of the day, not one. | "In Gemini, feedback also sends your last 24 hours of chats; people review it, kept up to 3 years [@google-gemini-privacy]." |
| F10 | low | fixed: citations swapped; Gemini work/school bullet added | 14, 105-114 | Short answer cites anthropic-consumer-terms-2025 for "don't train by default" (it only says the change didn't apply); right source is anthropic-training-work. Edu claim leans on openai-model-training, which doesn't list Edu. Gemini work/school (admin-controlled) missing from the work section. | Swap citations to anthropic-training-work and openai-data-controls; add a Gemini bullet: work or school Gemini is set by your admin [@google-gemini-activity]. |
| F11 | low | fixed: "interactions, chats and code ... from April 24, 2026, unless you opt out" | 23, 69 | GitHub uses "interaction data" - code, file names, repo structure, chats, inline suggestions, thumbs - not only chats; "began training" states as done what the blog announces in future tense. | "GitHub started using Copilot Free, Pro and Pro+ interactions - chats and code - for training from April 24, 2026, unless you opt out." |
| F12 | low | fixed | 25 | Carlini's extracted names, phones and emails were "(public)" - already on the web. Omitting it overstates the risk. | "...including names, phone numbers and emails already public online." |
| F13 | low | fixed: "thousands of training passages ... with a special trick" | 25 | "Large amounts ... from ChatGPT itself": gigabytes came from open models; from ChatGPT, thousands of examples under a special attack. | "A 2023 study pulled thousands of training passages from ChatGPT with a special trick." |
| F14 | low | fixed: Include environments named as separate | 39 | Codex has a separate "Include environments" setting the main switch doesn't change. | Add "(Codex's 'Include environments' setting is separate.)" or drop the Codex sentence - job seekers rarely use it. |
| F15 | low | fixed | 45 | "Temporary Chat for anything you don't want saved" - still kept up to 30 days. | "...for anything you don't want in your history or in training." |
| F16 | low | fixed: contracts wording, paid-org members, service firms, "most personal plans" | 71, 73, 75 | "Never used" vs DPA "without customer authorization"; "only the switch does" ignores students, teachers, and members of a paid org (FAQ); FAQ also says contracted service providers may help train. | "aren't used for training under GitHub's contracts"; "For most personal plans, only the switch does." |
| F17 | low | fixed | 93 | Heading "Past training stays" covers all apps; only Anthropic says it. | "Past training stays. Anthropic says so outright; the others don't say." |
| F18 | low | fixed: reworded; consumer-terms "filter or obfuscate" cited | 27, 97 | Anthropic feedback order: de-linked before use, then may be trained on - "keeps ... then may train" reads as a sequence in time. Line 27 could also cite the consumer-terms "filter or obfuscate sensitive data". | Reword; add citation. |
| F19 | low | fixed: line in "Why does this matter" | 23 | Anthropic's 2025 pop-up: the makers' pages don't say which way the switch was preset; users who clicked through may not know their setting. | In "What we don't know" or Claude section: "If you clicked through the 2025 pop-up, check the switch." |
| F20 | low | fixed: method line moved under the links, "research archives" | 124 | Method line sits in the "What we don't know" list; "arXiv" is jargon for this audience. | Move to `uncited:` (F8) or "How we research" link; say "research archives". |
| F21 | low | fixed: matched the maker page text "Help Improve our AI models" (re-read 2026-10-03); live screen not checkable from the loop - noted on plan-xsy.36 | 49, 53 | Source writes "Help Improve our AI models" (capital I). Menu text should match the screen. | Check the live screen in a browser before publish; match its case. |
| F22 | low | fixed: proposed wording | 3 | Description lumps Claude with default-on apps; Claude made it a choice. | "...can train on personal-plan chats. Where each switch is, and what it doesn't stop." |
| F23 | low | fixed: "Copilot Chat and suggestions in your code editor" | 69 | "including chat inside a code editor" is inferred from "chat, inline suggestions". | "including Copilot Chat and suggestions in your code editor". |

Owner-visible note for plan-xsy.32: OpenAI's live pages block scripted reads; open both in a
browser before publishing to confirm the Archive copies still match.

## Re-review 2026-10-03: citations thinned (plan-xsy.48)

Citation placement only - no wording, number or source changed. A run of sentences citing the
same source now cites it once, at the run's end (build rule: 3 in a row = error). Checked: every
sentence the moved citation now covers comes from that source.
16 repeat citations dropped; no sentence that was uncited now falls under a citation.

## Re-review 2026-10-04: voice pass (plan-xsy.53)

Voice only. Six section endings lost "For you," (now no opener, "So" or "In practice,"); "So the switch keeps your chats out of that 5-year training store" follows the 5-year sentence as before; home-page line; `modified` 2026-10-04. No setting, date or citation changed. Checked: each changed line keeps its meaning, scope, hedging and evidence label; section endings still say what the finding means for the reader; no new "this"/"it" across sentences; no app jargon; closing line "CEZ Job Finder is a free job-search app for Windows and Mac" matches docs/index.html title + og:title; link is our own home page. No finding.

Short answer merge (plan-xsy.53): checked the merged bullet 3 (switch stops future training + thumbs) against claim rows 14-15 and F3. Wording of both claims unchanged, "still" kept (openai-data-controls: "even after opt-out"); one label (Maker's docs) fits both halves, as before; citations are the union of the two old bullets - anthropic-training-setting + openai-data-controls cover the switch, openai-data-controls + anthropic-training-consumer cover thumbs. Box stays at 4 bullets. No blocking finding. Optional nit for readability: split the run-on into two sentences inside the bullet - "- Switch stops future training; training already done stays. Thumbs up or down can still send that whole chat to training (Maker's docs) [@anthropic-training-setting; @openai-data-controls; @anthropic-training-consumer]."

## Re-review 2026-10-04: title vs searched wording (plan-xsy.52)

Title only: "Keep your chats out of AI training: ChatGPT, Claude, Copilot" -> "Opt out of AI training: ChatGPT, Claude, Copilot and Gemini" (59 chars, limit 60). Why: searches use "opt out" / "stop ... training", and Gemini is covered but was missing (audit D12). Checked: all four products have a section and a switch in the body; "opt out" matches what the steps do (openai-model-training uses the same verb); "Copilot" stays as accepted in F6 (description + og_title say GitHub Copilot, Copilot section opens with the Microsoft Copilot line). Slug, description, og_title, body unchanged. No finding.

## Re-review 2026-10-04: summary table (plan-xsy.54)

New section "Which switch does each app use?": lead, a 4-row table (switch name, where, default, history with it off, feedback with it off) and a closing line on "The pages don't say". No other text changed. Checked every cell against the source table above, the body sections, and the live pages re-read 2026-10-04 by curl (privacy.claude.com 12109829 + 10023580 + retention page, anthropic.com consumer-terms news, docs.github.com manage-policies, github.blog 2026 policy post, GitHub community post 188488, support.google.com/gemini 13594961; OpenAI pages from the Archive copies as before); no source text addressed an AI. Switch names and click paths match the body and the makers' pages word for word; Gemini 72 hours / 24 hours and ChatGPT history cells match; every row carries a citation; label is Maker's docs throughout (all `vendor docs`); no app jargon. Findings:
1. **Blocking.** GitHub Copilot row, "Feedback still trains with it off?" cell "The pages don't say" is wrong. github-copilot-2026 lists "Your feedback on suggestions (thumbs up/down ratings)" as interaction data, and under "This program does not use": "Interaction data from users who opt out of model training in their Copilot settings". Replace the cell with: "No: thumbs up or down counts as your interaction data, which isn't used once you opt out [@github-copilot-docs; @github-copilot-2026]". Optional, same fix in the body: add to "Feedback can send the whole chat." the sentence "GitHub says thumbs up or down on Copilot is not used for training once you opt out [@github-copilot-2026]."
2. Medium. Claude row, "On by default?" cell "You were asked to choose in 2025" leaves out new users: anthropic-consumer-terms-2025 says "If you're a new user, you can pick your setting for model training during the signup process." Replace with: "No set default: you choose at sign-up, and existing users were asked in 2025".
3. Low. Feedback column says "Yes" where every maker says "may": OpenAI "may be used to train", Anthropic "We may use your feedback to ... train", Google "won't be used to train ... unless you choose to send Google feedback". The body says "may". Replace the three cells with: ChatGPT "It can: the whole chat [@openai-data-controls; @openai-model-training]"; Claude "It can: the whole chat, kept up to 5 years apart from your account [@anthropic-training-setting; @anthropic-consumer-terms-2025; @anthropic-training-consumer]"; Gemini "It can, with your last 24 hours of chats [@google-gemini-activity; @google-gemini-privacy]".
4. Low. Lead "The table sums up the four personal plans" reads as four plans, not four apps. Replace with: "The table sums up each app's personal plans; the sections below give each step."

Revision (plan-xsy.54, 2026-10-04): findings 1-4 fixed with the proposed wording, plus the optional body line on Copilot feedback (under "Feedback can send the whole chat."). Verdict publish.

## Re-review 2026-10-07: what to do note + bold answers (plan-ngk.6)

Fresh AI session; made none of the edits. Read `app/docs/research.md`, `git diff main` of the article, the whole article and the `sources.yml` entries behind each What helps item. No line moved a source's meaning far enough to reopen it. No source text addressed an AI.

Changed: "What to do" note (3 lines) above the old Short answer; "Short answer" -> "What the evidence says", bullets unchanged; 3 section answers set in bold; `modified` 2026-10-07; a new `## Changes` section with one line. Page only (generator): the description now shows as the answer line under the title.

What to do -> What helps:
- "Turn the training switch off on every AI app you use for job hunting." <- same words. Supported.
- "Skip thumbs up, thumbs down and feedback on chats with your resume." <- "Skip thumbs up, thumbs down and "send feedback" on chats with your resume" [@openai-data-controls; @anthropic-training-consumer]. Supported.
- "Use a temporary chat for one-off questions with personal details." <- "Use a temporary or incognito chat ..." [@openai-data-controls; @anthropic-training-consumer]. Same advice; "temporary" is generic, and Claude's name for it (Incognito) is in the Claude section. Supported.
- No statistic, citation or jargon in the note. Nothing says the switch stops the AI reading the resume.

Bold: 3 lines (job seeker, switch table, work plans); deleting the added ** pair gives the main line byte for byte (script). The four how-to sections already bold the switch name; "What doesn't the switch do?" already had bold lead-ins, F17 wording unchanged.
Description vs body: "ChatGPT, Claude, GitHub Copilot and Gemini can train on personal-plan chats. Where each switch is, and what it doesn't stop." = evidence bullet 1, the four step sections and "What doesn't the switch do?". Supported, not stronger.
Changes: new section, one line, accurate. It leaves out the Short answer rename. Optional; no fix needed.

No finding. Verdict: publish.

Changes-line edit after this re-review (2026-10-07): the generic line now also says "renamed the Short answer box "What the evidence says""; accurate, no other article change. Verdict: publish (unchanged).

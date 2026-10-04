---
title: "Opt out of AI training: ChatGPT, Claude, Copilot and Gemini"
description: ChatGPT, Claude, GitHub Copilot and Gemini can train on personal-plan chats. Where each switch is, and what it doesn't stop.
published: 2026-10-03
modified: 2026-10-04
status: published
og_title: "Stop ChatGPT, Claude, GitHub Copilot and Gemini training on your chats"
uncited:
  - "No study we found"
  - "no outside check was found"
  - "We searched the companies' help pages, news and research archives"
---
*A guide. Every step was checked against the company's own help page in October 2026.*

**Short answer**

- Personal plans of ChatGPT, Claude, GitHub Copilot and Gemini can train on your chats; one main switch each turns most of it off (Maker's docs) [@openai-data-controls; @anthropic-training-setting; @github-copilot-docs; @google-gemini-privacy]. See what the switch doesn't do, below.
- Work and school plans don't train on chats by default (Maker's docs) [@openai-data-controls; @anthropic-training-work; @github-copilot-docs].
- Switch stops future training; training already done stays, and thumbs up or down can still send that whole chat to training (Maker's docs) [@anthropic-training-setting; @openai-data-controls; @anthropic-training-consumer].
- AI models can repeat rare text from their training data (Lab studies, web text, not chats) [@carlini-2021; @nasr-2023].

## Why does this matter for a job seeker?

A resume is personal data. It names you, your employers, your schools and your dates. Job seekers also type pay, work permits and gaps into AI chats.

On personal plans, the companies may use those chats to train future AI models. ChatGPT "improves by further training on the conversations people have with it," says OpenAI, unless you opt out [@openai-model-training]. GitHub started using Copilot Free, Pro and Pro+ interactions, chats and code, for training from April 24, 2026, unless you opt out [@github-copilot-2026]. Anthropic asked Claude Free, Pro and Max users to choose in 2025 [@anthropic-consumer-terms-2025]. If you clicked through that pop-up, check where your switch is now.

Training data can come back out. In a 2021 test, researchers pulled hundreds of exact passages from an older AI model's training text. Those passages included names, phone numbers and email addresses already public online. A passage could leak even when it appeared in just one document [@carlini-2021]. A follow-up study pulled thousands of training passages from ChatGPT with a special trick [@nasr-2023].

Both studies used text from public web pages, not users' chats. No study we found shows a chat from one user coming out in another user's answers. The companies say they reduce personal details before training. OpenAI says it takes "steps to reduce the amount of personal information" in training data [@openai-model-training]. Anthropic says it filters or hides sensitive data [@anthropic-consumer-terms-2025]. It also separates feedback chats from your account before using them [@anthropic-training-consumer].

For you, the switch is a cheap step. In ChatGPT, your chats stay in your history with it off [@openai-data-controls].

## Which switch does each app use?

Each app names its switch differently and puts it in a different menu. The table sums up each app's personal plans; the sections below give each step.

| App | Switch name | Where | On by default? | Chats kept in your history with it off? | Feedback still trains with it off? |
|---|---|---|---|---|---|
| ChatGPT | Improve the model for everyone | Settings, then Data controls | Yes, unless you opt out | Yes | It can: the whole chat [@openai-data-controls; @openai-model-training] |
| Claude | Help Improve our AI models | Settings, then Privacy | No set default: you choose at sign-up, and existing users were asked in 2025 | The pages don't say | It can: the whole chat, kept up to 5 years apart from your account [@anthropic-training-setting; @anthropic-consumer-terms-2025; @anthropic-training-consumer] |
| GitHub Copilot | Allow GitHub to use my data for AI model training | Profile picture, then Copilot settings | Yes, from April 24, 2026, unless you opt out | The pages don't say | No: thumbs up or down counts as your interaction data, which isn't used once you opt out [@github-copilot-docs; @github-copilot-2026] |
| Gemini | Keep Activity | Settings & help, then Activity | Yes, for users 18 and over | No: new chats kept up to 72 hours | It can, with your last 24 hours of chats [@google-gemini-activity; @google-gemini-privacy] |

"The pages don't say" means the company's help pages we read in October 2026 don't answer the question.

## How do I stop ChatGPT training on my chats?

On ChatGPT Free, Go, Plus and Pro, the switch is called **Improve the model for everyone** [@openai-data-controls].

1. On the website, open your account menu and select **Settings** [@openai-data-controls].
2. Select **Data controls** [@openai-data-controls].
3. Select **Improve the model for everyone**, turn it off, and select **Done** [@openai-data-controls].

On the phone app, open the sidebar, tap your profile icon, then **Data controls**. The choice follows your account across devices when you're signed in. The same switch covers Codex tasks on a personal plan; Codex's "Include environments" setting is separate [@openai-data-controls].

OpenAI also offers a "do not train on my content" button in its privacy portal [@openai-model-training]. Either route is enough; you don't need both [@openai-data-controls].

**Temporary Chat** is a one-off option. Those chats don't appear in your history and aren't used for training. OpenAI may keep them for up to 30 days for safety [@openai-data-controls].

Turn the switch off once, then use Temporary Chat for anything you don't want in your history or in training.

## How do I stop Claude training on my chats?

On Claude Free, Pro and Max, the switch is called **Help Improve our AI models** [@anthropic-training-setting].

1. Select your name, then **Settings** [@anthropic-training-setting].
2. Select **Privacy**. The direct address is claude.ai/settings/data-privacy-controls [@anthropic-training-setting].
3. Turn **Help Improve our AI models** off [@anthropic-training-setting].

The switch also covers Claude Code on those plans [@anthropic-training-setting]. Anthropic made this a choice on August 28, 2025, with a deadline of October 8, 2025 [@anthropic-consumer-terms-2025].

With the switch on, a de-identified copy of your chats can stay up to 5 years in training data. For everyone, a deleted chat leaves Anthropic's main systems within 30 days. Chats flagged by safety checks are kept up to 2 years [@anthropic-retention]. **Incognito** chats are never used for training, whatever the switch says [@anthropic-training-consumer].

So the switch keeps your chats out of that 5-year training store.

## How do I stop GitHub Copilot training on my chats?

This is GitHub Copilot, the coding tool. Microsoft Copilot has its own settings, not covered here.

On Copilot Free, Pro, Pro+ and Max, the setting is **Allow GitHub to use my data for AI model training** [@github-copilot-docs].

1. On github.com, click your profile picture, then **Copilot settings** [@github-copilot-docs].
2. Open the **Allow GitHub to use my data for AI model training** menu [@github-copilot-docs].
3. Click **Disabled** [@github-copilot-docs].

The setting covers Copilot Chat and suggestions in your code editor, including your code and file names. If you opted out of data collection before, GitHub kept that choice [@github-copilot-2026].

Students on Copilot Student and teachers on free Copilot Pro are not affected. Neither are members of a paid company account [@github-copilot-faq-2026]. Business and Enterprise plans aren't used for training under GitHub's contracts, so the setting doesn't show there [@github-copilot-docs].

GitHub may share this data with "companies in our corporate family including Microsoft" [@github-copilot-2026]. Other AI companies whose models run inside Copilot don't get it for their own training [@github-copilot-2026; @github-copilot-faq-2026]. Hired service firms may help GitHub with training, under contract [@github-copilot-faq-2026].

For you, a paid personal plan does not protect your chats. For most personal plans, only the switch does.

## How do I stop Gemini training on my chats?

Gemini ties training to a setting called **Keep Activity** [@google-gemini-activity].

1. Go to gemini.google.com [@google-gemini-activity].
2. Click **Settings & help**, then **Activity** [@google-gemini-activity].
3. Click **On**, then **Turn off** or **Turn off and delete activity** [@google-gemini-activity].

Keep Activity is on by default for users 18 and over [@google-gemini-activity]. With it off, Google keeps new chats with your account for up to 72 hours. Those chats aren't used to train AI models unless you send feedback [@google-gemini-privacy].

With it off, only a few connected apps keep working [@google-gemini-activity]. Google still has people review some chats for safety, even with the setting off. Reviewed chats are kept for up to 3 years, apart from your account. Gemini also has a **Temporary chat**; those chats aren't used for training and are kept up to 72 hours [@google-gemini-privacy].

Gemini's switch costs you your saved chats. ChatGPT keeps your history with its switch off [@openai-data-controls].

## What doesn't the switch do?

**Past training stays.** Anthropic says so outright; the others don't say. Anthropic says data "will still be included in model training that has already started". Anthropic stops using older stored chats in future training runs [@anthropic-training-setting]. Claude chats from before the 2025 change were not used unless you reopened them [@anthropic-consumer-terms-2025].

**Your history stays.** Turning off ChatGPT's switch doesn't delete or hide saved chats. Delete a chat separately if you want it gone [@openai-data-controls].

**Feedback can send the whole chat.** On ChatGPT, a thumbs up or down means "the entire conversation" may be used to train models. That holds even after you opt out [@openai-data-controls]. Anthropic may train on feedback too; it separates feedback from your account and keeps it up to 5 years [@anthropic-training-consumer]. GitHub says thumbs up or down on Copilot is not used for training once you opt out [@github-copilot-2026]. In Gemini, feedback also sends your last 24 hours of chats. People review it, and it is kept up to 3 years [@google-gemini-privacy].

**Safety review goes on.** Claude chats flagged by safety checks may still be used to improve those checks [@anthropic-training-setting]. OpenAI keeps even Temporary Chats up to 30 days for safety [@openai-data-controls]. Google has people review some Gemini chats even with its setting off [@google-gemini-privacy].

**Gemini's switch has a gap.** Google says its Gemini settings don't cover chats it turns into anonymized data to improve its services [@google-gemini-privacy].

**Your name still reaches the AI.** The switch controls training, not reading. The AI has to read your resume to help with it.

Skip the thumbs buttons on any chat that holds your resume.

## What about work, school and developer accounts?

Business plans are the opposite: no training by default.

- OpenAI doesn't train on ChatGPT Business, Enterprise or Edu workspaces by default [@openai-data-controls].
- Anthropic's 2025 change excluded Claude for Work, Claude for Education and its developer platform [@anthropic-consumer-terms-2025]. Those are used for training only if you send feedback or agree to it [@anthropic-training-work].
- GitHub doesn't train on Copilot Business or Enterprise data [@github-copilot-docs].
- OpenAI's developer platform isn't used for training unless the customer opts in [@openai-model-training].
- Work or school Gemini is set by your admin [@google-gemini-activity].

Feedback is the exception here too. On Claude business plans, thumbs up or down can still send a chat to training [@anthropic-training-work].

In practice, a work login trains less, but your employer sets its rules and may see your chats [@openai-data-controls]. Job-hunt on your own account.

## What we don't know

- Whether a resume typed into a chat could come back out in someone else's answer. The leak studies used public web text, not chats [@carlini-2021; @nasr-2023].
- How well the companies remove personal details before training. Their pages say they try; no outside check was found [@openai-model-training].
- Whether the switches work as described. We can't test that from outside; this guide relies on the companies' own pages.
- How long the menus stay where they are. Menus move; we re-check these steps every three months.

## What helps

- Turn the training switch off on every AI app you use for job hunting. It takes a few clicks each.
- Skip thumbs up, thumbs down and "send feedback" on chats with your resume [@openai-data-controls; @anthropic-training-consumer].
- Use a temporary or incognito chat for one-off questions with personal details [@openai-data-controls; @anthropic-training-consumer].
- Delete chats you don't need. On Claude, deleted chats leave Anthropic's main systems within 30 days, unless flagged for safety or held for legal reasons [@anthropic-retention].
- Leave out what the AI doesn't need. Your street address, birth date and ID numbers rarely help a resume; that is common advice, not a study finding.

What belongs on a resume at all: [What makes a good resume?](what-makes-a-good-resume.md). Using AI to write it: [Can employers tell if AI wrote your resume?](ai-written-resumes.md). How we check sources: [How we research](methods.md). We searched the companies' help pages, news and research archives in October 2026 for outside tests of these switches.

## How CEZ Job Finder uses this

- CEZ Job Finder runs inside your own AI chat: Claude, ChatGPT or GitHub Copilot. Your resume is read there.
- At setup, it asks once whether you want your chats kept out of training, and walks you through the switch.
- It never asks you to rate a chat, because feedback can send that chat to training.
- Only you can change the switch. No setting in CEZ Job Finder reaches your AI account.

CEZ Job Finder is a free job-search app for Windows and Mac: [see how CEZ Job Finder works](https://jobs.enrriquez.com/).

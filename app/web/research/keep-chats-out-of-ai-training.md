---
title: "Keep your chats out of AI training: ChatGPT, Claude, Copilot"
description: ChatGPT, Claude, GitHub Copilot and Gemini can train on personal-plan chats unless you switch it off. Where each switch is, and what it doesn't stop.
published: 2026-10-03
modified: 2026-10-03
status: draft
og_title: "Stop ChatGPT, Claude, Copilot and Gemini training on your chats"
---
*A guide. Every step was checked against the company's own help page in October 2026.*

**Short answer**

- Personal plans of ChatGPT, Claude, GitHub Copilot and Gemini can train on your chats; one switch each turns it off (Maker's docs) [@openai-data-controls; @anthropic-training-setting; @github-copilot-docs; @google-gemini-privacy].
- Work and school plans don't train on chats by default (Maker's docs) [@openai-model-training; @anthropic-consumer-terms-2025; @github-copilot-docs].
- Switch = new chats only; past training stays (Maker's docs) [@anthropic-training-setting].
- Thumbs up or down can still send that whole chat to training (Maker's docs) [@openai-data-controls; @anthropic-training-consumer].
- AI models can repeat rare text from their training data (Lab studies, web text, not chats) [@carlini-2021; @nasr-2023].

## Why does this matter for a job seeker?

A resume is personal data. It names you, your employers, your schools and your dates. Job seekers also type pay, work permits and gaps into AI chats.

On personal plans, the companies may use those chats to train future AI models. ChatGPT "improves by further training on the conversations people have with it," says OpenAI, unless you opt out [@openai-model-training]. GitHub began training on Copilot Free, Pro and Pro+ chats by default on April 24, 2026 [@github-copilot-2026]. Anthropic asked Claude Free, Pro and Max users to choose in 2025 [@anthropic-consumer-terms-2025].

Training data can come back out. In a 2021 test, researchers pulled hundreds of exact passages from an older AI model's training text [@carlini-2021]. Those passages included names, phone numbers and email addresses [@carlini-2021]. A passage could leak even when it appeared in just one document [@carlini-2021]. A 2023 follow-up pulled large amounts of training text from ChatGPT itself [@nasr-2023]. That study is a preprint, not yet peer-reviewed [@nasr-2023].

Both studies used text from public web pages, not users' chats. No study we found shows a chat from one user coming out in another user's answers. The companies say they reduce personal details before training. OpenAI says it takes "steps to reduce the amount of personal information" in training data [@openai-model-training]. Anthropic says feedback chats are separated from your account before use [@anthropic-training-consumer].

For you, the switch is a cheap step. In ChatGPT, your chats stay in your history with it off [@openai-data-controls].

## How do I stop ChatGPT training on my chats?

On ChatGPT Free, Go, Plus and Pro, the switch is called **Improve the model for everyone** [@openai-data-controls].

1. On the website, open your account menu and select **Settings** [@openai-data-controls].
2. Select **Data controls** [@openai-data-controls].
3. Select **Improve the model for everyone**, turn it off, and select **Done** [@openai-data-controls].

On the phone app, open the sidebar, tap your profile icon, then **Data controls** [@openai-data-controls]. The choice follows your account across devices when you're signed in [@openai-data-controls]. The same switch covers Codex tasks on a personal plan [@openai-data-controls].

OpenAI also offers a "do not train on my content" button in its privacy portal [@openai-model-training]. Either route is enough; you don't need both [@openai-data-controls].

**Temporary Chat** is a one-off option. Those chats don't appear in your history and aren't used for training [@openai-data-controls]. OpenAI may keep them for up to 30 days for safety [@openai-data-controls].

For you, turn the switch off once, then use Temporary Chat for anything you don't want saved.

## How do I stop Claude training on my chats?

On Claude Free, Pro and Max, the switch is called **Help improve our AI models** [@anthropic-training-setting].

1. Select your name, then **Settings** [@anthropic-training-setting].
2. Select **Privacy**. The direct address is claude.ai/settings/data-privacy-controls [@anthropic-training-setting].
3. Turn **Help improve our AI models** off [@anthropic-training-setting].

The switch also covers Claude Code on those plans [@anthropic-training-setting]. Anthropic made this a choice on August 28, 2025, with a deadline of October 8, 2025 [@anthropic-consumer-terms-2025].

How long Anthropic keeps your chats depends on the switch. With it on, chats can be kept for up to 5 years for training [@anthropic-retention]. With it off, a chat you delete is gone from Anthropic's systems within 30 days [@anthropic-retention]. **Incognito** chats are never used for training, whatever the switch says [@anthropic-training-consumer].

For you, the switch also shortens how long Anthropic keeps what you delete.

## How do I stop GitHub Copilot training on my chats?

On Copilot Free, Pro, Pro+ and Max, the setting is **Allow GitHub to use my data for AI model training** [@github-copilot-docs].

1. On github.com, click your profile picture, then **Copilot settings** [@github-copilot-docs].
2. Open the **Allow GitHub to use my data for AI model training** menu [@github-copilot-docs].
3. Click **Disabled** [@github-copilot-docs].

The setting covers your Copilot chats, including chat inside a code editor [@github-copilot-2026]. If you opted out of data collection before, GitHub kept that choice [@github-copilot-2026].

Students on Copilot Student and teachers on free Copilot Pro are not affected [@github-copilot-faq-2026]. Business and Enterprise plans are never used for training, so the setting doesn't show there [@github-copilot-docs].

GitHub may share this data with "companies in our corporate family including Microsoft" [@github-copilot-2026]. Other AI companies whose models run inside Copilot don't get it for their own training [@github-copilot-2026; @github-copilot-faq-2026].

For you, a paid personal plan does not protect your chats. Only the switch does.

## How do I stop Gemini training on my chats?

Gemini ties training to a setting called **Keep Activity** [@google-gemini-activity].

1. Go to gemini.google.com [@google-gemini-activity].
2. Click **Settings & help**, then **Activity** [@google-gemini-activity].
3. Click **On**, then **Turn off** or **Turn off and delete activity** [@google-gemini-activity].

Keep Activity is on by default for users 18 and over [@google-gemini-activity]. With it off, Google keeps new chats with your account for up to 72 hours [@google-gemini-privacy]. Those chats aren't used to train AI models unless you send feedback [@google-gemini-privacy].

Gemini differs in two ways. With the setting off, chats aren't kept past 72 hours, and only a few connected apps keep working [@google-gemini-activity]. And human reviewers read some chats; reviewed chats are kept for up to three years, apart from your account [@google-gemini-privacy].

For you, Gemini's switch costs you your saved chats. ChatGPT keeps your history with its switch off [@openai-data-controls].

## What doesn't the switch do?

**Past training stays.** Anthropic says data "will still be included in model training that has already started" [@anthropic-training-setting]. Anthropic stops using older stored chats in future training runs [@anthropic-training-setting]. Claude chats from before the 2025 change were not used unless you reopened them [@anthropic-consumer-terms-2025].

**Your history stays.** Turning off ChatGPT's switch doesn't delete or hide saved chats [@openai-data-controls]. Delete a chat separately if you want it gone [@openai-data-controls].

**Feedback can send the whole chat.** On ChatGPT, a thumbs up or down means "the entire conversation" may be used to train models [@openai-data-controls]. That holds even after you opt out [@openai-data-controls]. Anthropic keeps feedback for up to 5 years, separated from your account, then may train on it [@anthropic-training-consumer]. Gemini also trains on chats you send feedback about [@google-gemini-privacy].

**Safety review goes on.** Claude chats flagged by safety checks may still be used to improve those checks [@anthropic-training-setting]. OpenAI keeps even Temporary Chats up to 30 days for safety [@openai-data-controls].

**Your name still reaches the AI.** The switch controls training, not reading. The AI has to read your resume to help with it.

For you, skip the thumbs buttons on any chat that holds your resume.

## What about work, school and developer accounts?

Business plans are the opposite: no training by default.

- OpenAI doesn't train on ChatGPT Business, Enterprise or Edu workspaces by default [@openai-data-controls].
- Anthropic's 2025 change excluded Claude for Work, Claude for Education and its developer platform [@anthropic-consumer-terms-2025]. Those are used for training only if you send feedback or agree to it [@anthropic-training-work].
- GitHub doesn't train on Copilot Business or Enterprise data [@github-copilot-docs].
- OpenAI's developer platform isn't used for training unless the customer opts in [@openai-model-training].

Feedback is the exception here too. On Claude business plans, thumbs up or down can still send a chat to training [@anthropic-training-work].

For you, check which plan you're signed in to. A work login may already be covered.

## What we don't know

- Whether a resume typed into a chat could come back out in someone else's answer. The leak studies used public web text, not chats [@carlini-2021; @nasr-2023].
- How well the companies remove personal details before training. Their pages say they try; no outside check was found.
- Whether the switches work as described. We can't test that from outside; this guide relies on the companies' own pages.
- How long the menus stay where they are. Menus move; we re-check these steps every three months.
- We searched the companies' help pages, news and arXiv in October 2026 for outside tests of these switches.

## What helps

- Turn the training switch off on every AI app you use for job hunting. One minute each.
- Skip thumbs up, thumbs down and "send feedback" on chats with your resume [@openai-data-controls; @anthropic-training-consumer].
- Use a temporary or incognito chat for one-off questions with personal details [@openai-data-controls; @anthropic-training-consumer].
- Delete chats you don't need. On Claude, deleted chats leave Anthropic's systems within 30 days [@anthropic-retention].
- Leave out what the AI doesn't need. Your street address, birth date and ID numbers rarely help a resume; that is common advice, not a study finding.

What belongs on a resume at all: [What makes a good resume?](what-makes-a-good-resume.md). How we check sources: [How we research](methods.md).

## How CEZ Job Finder uses this

- CEZ Job Finder runs inside your own AI chat: Claude, ChatGPT or GitHub Copilot. Your resume is read there.
- At setup, it asks once whether you want your chats kept out of training, and walks you through the switch.
- It never asks you to rate a chat, because feedback can send that chat to training.
- Only you can change the switch. No setting in CEZ Job Finder reaches your AI account.

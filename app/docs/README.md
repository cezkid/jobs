# Job Finder docs

For **users**, in plain words, visible in the file list:

- [START HERE](../../START%20HERE.md) - what Job Finder does, what to ask, who sees what.
- [What makes a good resume](../../Guides/What%20makes%20a%20good%20resume.md) - every rule
  in one line, with how strong its evidence is.

For **the AI assistant and contributors** - the measured facts and evidence behind the code.
Read the one for the area you are changing before you change it: each records what was
measured and what was rejected, so a retired rule does not come back.

| Area | Doc | What it holds |
|---|---|---|
| Resume | [resume/bullets.md](resume/bullets.md) | What a line has to do: accuracy > substance > relevance > clarity, every wording rule with its basis, what the lint enforces vs reports, advice that did not survive |
| Resume | [resume/page-format.md](resume/page-format.md) | Page hygiene gates (black text, whole words, even heading spacing), headline, summary length, format advice declined |
| Resume | [resume/typeface.md](resume/typeface.md) | Why Caladea, how widths are measured, how to add a font and what it costs |
| Jobs | [jobs/freehire.md](jobs/freehire.md) | The job API: filters, facets, measured pitfalls - read before touching search or ingest |
| Applying | [apply/apply-systems.md](apply/apply-systems.md) | How application filling works, the systems supported, how to add one |
| Applying | [apply/workday.md](apply/workday.md) | Workday forms, filled through the Chrome extension |
| Applying | [apply/ashby.md](apply/ashby.md) | Ashby forms, filled in Job Finder's own Chrome |

Instructions for the assistant itself: [AGENTS.md](../../AGENTS.md) and the skills in
[../skills/](../skills/). Contributing: [.github/CONTRIBUTING.md](../../.github/CONTRIBUTING.md).

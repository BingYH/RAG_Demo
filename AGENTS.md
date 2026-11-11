# Project language and contribution instructions

Use **English by default** for all project-authored text. This includes Markdown
documentation, README files, plans, memory notes, instructions, AGENTS files,
SKILL files, prompts, source comments, docstrings, scripts, CLI output, examples,
test descriptions, and commit messages. Add future project memory and guidance
in English as well.

The explicit exception is the application's multilingual Dashboard. Preserve
its optional Chinese interface for presentations to different audiences, but
keep English as the default interface and new-diagnosis language. Store Chinese
translations in `rag_demo/ui_i18n.py`; use English keys and English source text
everywhere else. Tests may explicitly request Chinese through that catalog.
Switching interface languages must not rewrite evidence, stored reports,
approved drafts, or their hashes.

At the user's explicit request, Chinese translations of `README.md`,
`run_of_show.md` and `speaker_notes.md` live under `docs/interview_demo/Chinese/`.
These three translations are language-policy exceptions. Their originals in
`docs/interview_demo/` remain English; do not mix translations into those files.
The user also requested separate English and Chinese PowerPoint decks under
`docs/interview_demo/Presentation/`. The Chinese deck and its speaker notes are
an explicit language exception. Keep build instructions and supporting code English.

These rules apply only to files generated and maintained for this project.
Keep cloned repositories under `references/repos/` and all other downloaded
third-party files in their original language and form, wherever they are stored.
Do not translate vendor-owned repositories under `references/`, Git history,
immutable historical run/checkpoint/ticket artifacts under ignored `data/`, or
third-party dependencies such as `.venv/`. They are not editable project prose.
Never translate identifiers, evidence IDs, versions, hashes, numeric fixtures,
commands, filesystem paths, or URLs. Preserve their exact meaning and values.

Before finishing language-sensitive changes, run the language audit and the
appropriate tests. Do not introduce Chinese prose outside the approved
exceptions above without an explicit user instruction.

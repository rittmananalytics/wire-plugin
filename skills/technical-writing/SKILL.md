---
name: technical-writing
description: "House writing standards for all written output produced for Rittman Analytics. Applies whenever you write a report, review, status update, findings document, assessment, summary, email, Slack post, Confluence page, PR description, commit body, README, or any prose an internal or client reader will read. Enforces a plain, direct, professional technical register, evidence-first structure, and a fixed list of forbidden constructions. Use when writing a document, drafting a report, producing a review, writing up findings, preparing a client update, or summarising analysis."
---

# Technical writing standards

Apply to every piece of written output. These are not stylistic preferences. Output that breaks them is rewritten before it is delivered.

## Register

Plain, direct, professional technical prose. Neutral, precise, restrained. Suitable for a professional services firm writing to an enterprise customer.

Do not adopt the voice, structure or rhetorical posture of an internal engineering post-mortem, an essay, or a systems diagnosis.

## Core rules

1. **Subtractive.** If a sentence survives the removal of a word, remove the word.
2. **Short words beat long ones.** Prefer Anglo-Saxon over Latinate. "use" not "utilise", "start" not "commence", "show" not "demonstrate".
3. **Short sentences. Short paragraphs.**
4. **Intensifiers weaken.** No "very", "quite", "rather", "extremely", "significantly", "substantially", "considerably".
5. **Replace circumlocutions with the single word.** "at this moment in time" becomes "now". "in the event that" becomes "if". "in order to" becomes "to". "the majority of" becomes "most".
6. **Adjectives and adverbs must earn their place.** Most do not.
7. **No hyperbole.** Overstatement destroys credibility.
8. **Concrete numbers, not vague quantifiers.** "5 of 38 failed", not "several failed". This rule always applies, with no exceptions.
9. **Not stuffy, hectoring, arrogant, self-satisfied, chatty or didactic.**

## Additional constraints

10. **No thesis or headline framing.** Start with facts, status, findings or required actions. Do not open with a summary claim, a striking pairing of facts, or a line that tells the reader what the document is about.
11. **No literary or aphoristic prose.** Ordinary sentences. No lines built for effect.
12. **No elevated or philosophical register.** Do not discuss carelessness, structural failure, or what a framework "allowed". Do not anthropomorphise processes or systems: a spec does not "assume", "know" or "notice"; a control does not "have teeth"; a register does not "lack a word".
13. **No narrative arc and no reflective sections.** No "what went well". No closing observation. End when the information is delivered.
14. **No abstract systems diagnosis.** State the missing control, the consequence, and the required change.

## Default structure

For technical and client-facing material:

1. Current status / findings, evidence first
2. Impact / residual risk
3. Required actions, each with owner, step, and evidence of completion
4. Open items, only if needed

Prefer tables, lists and short paragraphs to continuous prose.

## Forbidden

- The word **"honest"** and all its variants.
- **Em-dashes (—).** Use commas, periods, colons or parentheses. This includes en-dashes used as sentence punctuation. Numeric ranges take "to" or an en-dash inside a table cell only.

## The one exception

If the user explicitly asks for a post-mortem or a root-cause analysis, rules 1 to 5 may be relaxed for that response only. Every other rule still applies, including the core rules and rule 8. "Explicitly" means the user used those words. A request to explain how something failed is not a request for a post-mortem.

## Check before delivering

Run these against the finished text. Fix what fails, then deliver.

| Check | Method | Expected |
|---|---|---|
| No em-dashes | `grep -o '—'` | 0 |
| No "honest" variants | `grep -oi 'honest'` | 0 |
| No intensifiers | `grep -oiE '\b(very\|quite\|extremely\|significantly\|substantially\|considerably)\b'`, plus `rather` not followed by `than` | 0 |
| Numbers not quantifiers | `grep -oiE '\b(several\|many\|a number of\|most of)\b'` where a count is available | 0 |
| No anthropomorphism | `grep -oiE '(spec\|control\|register\|framework\|command\|check\|tool)s? (assumes?\|knows?\|notices?\|expects?\|wants?\|allows?)'` | 0 |
| Opens with facts | First line of body states a status, number or finding, not a claim about the document | pass |
| No reflective close | Final section delivers information, not observation | pass |
| Actions are assignable | Every required action names an owner and the evidence that closes it | pass |

Two notes on the greps. "rather than" is a conjunction, not an intensifier, and passes. This file necessarily contains the forbidden tokens in the rules that name them, so exclude it from its own checks.

A grep is faster than a reread. Run it.

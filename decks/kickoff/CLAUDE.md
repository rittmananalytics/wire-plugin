# Project Kick-off Deck — Tweak spec for Claude Code

This deck (`Project Kickoff.html`) is driven by a single JSON block of tweak values. To re-skin the deck for a new client/engagement, **edit only that block** — do not touch the slide markup, CSS, or scripts.

---

## Where the values live

`Project Kickoff.html`, around line 722, inside an inline `<script>`:

```js
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  …
}/*EDITMODE-END*/;
```

**Hard rules:**
- Replace **only** the JSON object between `/*EDITMODE-BEGIN*/` and `/*EDITMODE-END*/`.
- The block must remain valid JSON: double-quoted keys and strings, no comments, no trailing commas, no JS expressions.
- Do not rename, add, or remove keys unless this spec tells you to. Array lengths are fixed by the matching `*Count` key — see below.
- Preserve escape sequences in long strings (`\n` for line breaks, `\u003c` etc.). HTML fragments inside string values (e.g. `<strong>…</strong>`) are intentional.
- `titlePhoto` is a giant base64 data URI. Leave it alone unless the user gives you a new image — if so, replace the whole string with a new `data:image/...;base64,...` URI or a relative path like `assets/title.jpg`.

If you need to update something **outside** this block (slide order, new slide, layout change), say so explicitly and ask before editing.

---

## Schema — all tweakable keys

### Title slide (Slide 01)
| Key | Type | Notes |
|---|---|---|
| `titleVariant` | `"pitch" \| "minimal" \| "split"` | Layout style for the title slide. |
| `clientName` | string | Client/customer name shown on the title slide. |
| `engagementType` | string | e.g. `"Project"`, `"Discovery"`, `"Engagement"`. |
| `engagementDate` | `"YYYY-MM-DD"` | ISO date; rendered formatted. |
| `titlePhoto` | data URI or path | Full-bleed background. Leave as-is unless replacing. |
| `showPartnerBadge` | boolean | Toggle the "in partnership with" badge. |
| `vignetteStrength` | number 0–100 | Darkening over the title photo. |
| `accentColor` | hex `"#RRGGBB"` | Primary accent across the deck. |

### Slide 04 — Diagnosis section opener (two-column narrative)
| Key | Type | Notes |
|---|---|---|
| `slide4Headline` | string | Use `\n` for the line break. Two short lines work best. |
| `slide4LeftPrompt` | string | LLM prompt that generates `slide4LeftCache`. |
| `slide4RightPrompt` | string | Optional second column prompt. Empty string = single-column. |
| `slide4LeftCache` | string (HTML allowed) | Rendered copy. May contain `<strong style="…">…</strong>`. Use `\n\n` between paragraphs. |
| `slide4RightCache` | string (HTML allowed) | Same as above, for the right column. |

### Slide 05 — Big-number callout
| Key | Type | Notes |
|---|---|---|
| `slide5Number` | string | The headline number, e.g. `"300"`. String, not number. |
| `slide5Suffix` | string | e.g. `"+"`, `"%"`, `"x"`. |
| `slide5Bold` | string | Bold lead-in sentence after the number. |
| `slide5Tail` | string | Supporting sentence. |

### Slide 07 — Problems grid
| Key | Type | Notes |
|---|---|---|
| `slide6Count` | int 1–8 | How many problem cards are visible. |
| `slide6Problems` | array of `{headline, detail}` × **8** | Array length is **always 8**. Items beyond `slide6Count` should have `""` for both fields. |

### Slide 09 — Outcomes list
| Key | Type | Notes |
|---|---|---|
| `slide8Count` | int 1–5 | How many outcome rows render. |
| `slide8Outcomes` | array of `{headline, detail}` × **5** | Length always 5; pad with empty strings beyond `slide8Count`. |

### Slide 11 — Architecture diagram
| Key | Type | Notes |
|---|---|---|
| `slide10Headline` | string | Slide title. |
| `slide10Prompt` | string | Natural-language prompt describing the diagram to generate. |
| `slide10Direction` | `"LR" \| "TB"` | Mermaid flowchart direction. |
| `slide10MermaidCache` | string | Cached Mermaid source. Regenerate from prompt if prompt changes. |
| `slide10AnnotLabel` | string | Annotation label. |
| `slide10AnnotText` | string | Annotation body. |

### Slide 13 — Two-week timeline
| Key | Type | Notes |
|---|---|---|
| `slide12W1Focus` | string | Week 1 focus statement. |
| `slide12W2Focus` | string | Week 2 focus statement. |
| `slide12W1Count` | int 1–6 | Visible items in W1 list. |
| `slide12W2Count` | int 1–6 | Visible items in W2 list. |
| `slide12W1Items` | string × **6** | Pad unused slots with `""`. |
| `slide12W2Items` | string × **6** | Pad unused slots with `""`. |

### Slide 15 — Access requirements
| Key | Type | Notes |
|---|---|---|
| `slide14Count` | int 1–4 | Visible category cards. |
| `slide14Categories` | array of `{name, needs}` × **4** | `needs` is a single comma-separated string. Pad with `{name:"", needs:""}`. |

### Slide 16 — Team / presenters
| Key | Type | Notes |
|---|---|---|
| `presenters` | array of `{name, role}` | Variable length. Order is presentation order. Also rendered on the title slide. |

---

## Editing recipes

**Re-skin for a new client:**
1. Update `clientName`, `engagementType`, `engagementDate`.
2. Update `slide4LeftPrompt` / `slide4RightPrompt` to describe their situation, then regenerate `slide4LeftCache` / `slide4RightCache` from the prompts.
3. Update `slide5*` with their headline metric.
4. Rewrite `slide6Problems` (set `slide6Count` to actual number used).
5. Rewrite `slide8Outcomes` (set `slide8Count`).
6. Update `slide10Prompt` if the architecture differs; regenerate `slide10MermaidCache`.
7. Update `slide12W1Items` / `slide12W2Items` and their `*Focus` + `*Count`.
8. Update `slide14Categories` for their stack; set `slide14Count`.
9. Update `presenters` if the team is different.
10. Optionally swap `accentColor` and `titlePhoto`.

**Add an outcome (slide 09):**
- Increment `slide8Count` (max 5).
- Replace the next empty `{"headline":"", "detail":""}` slot with real content. Don't push — keep array length at 5.

**Shorten the problems list:**
- Decrement `slide6Count`.
- Set the now-hidden trailing entries to `{"headline":"", "detail":""}` (don't pop the array).

---

## When generating copy

- **Headlines** — short, declarative, 4–10 words. No trailing punctuation unless it's a question.
- **Details** — 1–2 sentences, plain prose, no marketing voice. Match the existing tone in the file.
- **HTML inside strings** — only `<strong style="color:#2B3041; font-weight:600;">…</strong>` for inline emphasis, and only inside `slide4LeftCache` / `slide4RightCache`. Don't introduce other tags.
- **Line breaks** — `\n` inside a paragraph for forced wrap, `\n\n` between paragraphs.

---

## Verification

After editing, the deck should still load and every slide should render. The `EDITMODE` block must parse as JSON — if you broke it, the live Tweaks panel won't open and the page will throw on load.

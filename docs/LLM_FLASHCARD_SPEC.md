# LLM Flashcard Deck Spec

Use this spec when asking an LLM to generate decks for Open Cards.

## Output Rules

- Return valid JSON only.
- Do not wrap the JSON in Markdown.
- Use one top-level object with `deck` and `cards`.
- If source citations are needed, put them inside JSON fields. Do not add citations before or after the JSON.
- Keep each card atomic: one fact, concept, procedure, or distinction per card.
- Prefer precise answers over long explanations.
- Use stable, lowercase, hyphenated `id` values so review progress survives deck edits.
- Include `tags` for filtering or future search.
- Avoid duplicate cards, trick wording, and vague prompts like "Explain X".
- Do not describe your process, document search, uncertainty, or tool use in the output.

## JSON Shape

```json
{
  "deck": "Short Deck Name",
  "cards": [
    {
      "id": "topic-specific-stable-id",
      "front": "Question, cloze prompt, or term shown first.",
      "back": "Answer shown after reveal.",
      "tags": ["topic", "subtopic"],
      "extra": "Optional source note, mnemonic, or context.",
      "sources": ["Optional source title, section, page, URL, or line reference."]
    }
  ]
}
```

## Required Fields

`deck`: Human-readable deck name.

`cards`: Array of card objects.

Each card requires:

- `id`: Stable unique string within the deck.
- `front`: The prompt shown before reveal.
- `back`: The answer shown after reveal.

## Optional Fields

- `tags`: Array of short strings. A single string is accepted by the app, but arrays are preferred.
- `extra`: Short optional context shown in the card footer.
- `sources`: Array of citation strings. Use this when cards must remain traceable to source material.

The app ignores unknown fields it does not yet display, so `sources` is safe to include in generated decks.

## Source And Citation Rules

Use these rules when generating from documents, search results, course notes, webpages, PDFs, or any cited source material.

- Every factual card should be grounded in the supplied material.
- If citations are required, include them in `sources`; never place citations outside the JSON.
- Keep `sources` machine-readable: use short strings such as `"Lecture 2, slide 14"`, `"GDPR notes, p. 3"`, `"https://example.com/article#section"`, or `"source.md:42-48"`.
- If exact line numbers are unavailable, cite the closest stable locator you have: document title, section heading, page, slide, URL, or filename.
- Use `extra` for a short human note, not for long quoted passages.
- Do not invent missing details to fill a syllabus or topic list. Generate cards only from supported claims.
- If the source has important gaps, omit unsupported cards rather than adding speculative answers.
- If two sources disagree, either create a card about the distinction or omit the claim unless the source material resolves it.

## Accepted Aliases

The app accepts these aliases for LLM convenience, but the canonical fields above are preferred:

- `question` instead of `front`
- `answer` instead of `back`
- `prompt` instead of `front`
- `response` instead of `back`

## Card Quality Guidelines

Good cards:

- Ask for one retrievable answer.
- Use enough context to remove ambiguity.
- Keep answers short enough to self-grade quickly.
- Split multi-step material into several cards.
- Include contrast cards for easily confused concepts.
- Preserve legal, medical, regulatory, or policy nuance. Do not compress exceptions into false absolutes.

Avoid:

- Multiple unrelated facts in one card.
- Prompts that depend on hidden context.
- Answers like "it depends" without the actual deciding rule.
- Overly broad essay questions.
- IDs based on card number only.
- Cards whose answer requires unstated source context.

## Ready-To-Paste Prompt

Generate an Open Cards deck from the source material below.

Return valid JSON only. Do not use Markdown, commentary, citations outside JSON, or tool/process notes. Follow this exact shape:

{
  "deck": "Short Deck Name",
  "cards": [
    {
      "id": "stable-lowercase-hyphenated-id",
      "front": "One clear prompt.",
      "back": "One concise answer.",
      "tags": ["topic", "subtopic"],
      "extra": "Optional short context, mnemonic, or source note.",
      "sources": ["Document, section, page, slide, URL, or filename locator."]
    }
  ]
}

Requirements:

- Create atomic flashcards, one idea per card.
- Prefer 10 to 25 cards unless the source material clearly needs more.
- Use stable IDs based on the concept, not card numbers.
- Include tags on every card.
- Do not invent facts not supported by the source.
- If citations are available or required, put them in each card's `sources` array.
- If exact line references are unavailable, use the nearest stable source locator.
- If source material has gaps, skip unsupported cards rather than filling gaps from general knowledge.
- Return only parseable JSON.

Source material:

[PASTE SOURCE MATERIAL HERE]

## Prompt Variant For Cited Document Decks

Use this when the generating model has searched or read documents and must cite them.

Generate an Open Cards deck from the provided documents.

Return one valid JSON object only. Do not include Markdown fences, prose explanations, search notes, or citations outside the JSON.

Citation policy:

- Put citations inside each card's `sources` array.
- Use exact line ranges when available.
- If line ranges are unavailable, cite filename plus section/page/slide/URL.
- Do not quote long passages.
- Do not create cards for facts that are not supported by the cited documents.
- If the requested topic has missing coverage, simply omit unsupported cards.

Card policy:

- Create atomic, self-testable cards.
- Prefer concise answers.
- Split lists, legal tests, exceptions, timelines, and procedures into separate cards.
- Preserve conditions, exceptions, thresholds, and definitions accurately.
- Use stable lowercase hyphenated IDs based on concepts.

Return this shape:

{
  "deck": "Short Deck Name",
  "cards": [
    {
      "id": "concept-based-id",
      "front": "One clear prompt.",
      "back": "One concise answer.",
      "tags": ["topic", "subtopic"],
      "extra": "Optional short context.",
      "sources": ["source locator"]
    }
  ]
}

## Prompt Variant For Progress-Based Follow-Up Decks

Use this when generating a new deck from an Open Cards LLM progress report.

Generate a targeted Open Cards follow-up deck from this progress report.

Return one valid JSON object only. Do not include Markdown fences, prose explanations, or citations outside the JSON.

Progress policy:

- Prioritize cards with `learning_signal` values of `forgotten`, `fragile`, `low_ease`, or `relearning`.
- Use `summary.weakest_tags`, `tag_stats`, lapse counts, and recent Again/Hard grades to choose coverage.
- Read individual source cards from `card_progress`.
- Use each card's `suggested_followup_focus` to decide whether to create prerequisite, contrast, application, or smaller atomic cards.
- Include new cards for unreviewed prerequisites only when they support weak concepts.
- Do not duplicate the original card text verbatim.

Source policy:

- Use original `front`, `back`, `extra`, and `sources` as the available source material.
- Preserve useful source locators in each new card's `sources` array.
- Do not add facts that are not supported by the original card text or sources.

Return this shape:

{
  "deck": "Original Deck Name Follow-up",
  "cards": [
    {
      "id": "followup-concept-based-id",
      "front": "One targeted prompt.",
      "back": "One concise answer.",
      "tags": ["follow-up", "topic"],
      "extra": "Optional note explaining the practice angle.",
      "sources": ["source locator from the progress report, when present"]
    }
  ]
}

Progress report:

[PASTE OPEN CARDS LLM PROGRESS REPORT JSON HERE]

# FlashCardBuilder

A small Python flashcard app that reads JSON decks and reviews them with an Anki-style flow:

1. Read the front of the card.
2. Reveal the answer.
3. Grade recall with `Again`, `Hard`, `Good`, or `Easy`.
4. Save review progress to a per-deck file in `progress/`.

Decks are loaded from JSON files in the program directory. Use the in-app deck dropdown to switch decks.

The app can also export an LLM progress report from the current deck. Use `Export LLM Report`
after studying to create a targeted input for generating a follow-up deck. Everything runs locally;
there is no hosted sync service or external account dependency.

## Run

```bash
python3 app.py
```

To open a specific deck:

```bash
python3 app.py path/to/deck.json
```

To store progress somewhere else:

```bash
python3 app.py path/to/deck.json --progress path/to/progress.json
```

By default, progress is stored per deck:

```text
progress/flashcards_progress.json
progress/CS5055V1_progress.json
```

If an older `progress.json` exists and its card IDs match the deck you open, the app will read it
for continuity and then save future reviews to the per-deck progress file. This prevents one deck
from overwriting another deck's study history.

To export an LLM progress report without opening the GUI:

```bash
python3 app.py flashcards.json --export-report
```

## JSON Deck Format

For LLM generation guidance, see [LLM_FLASHCARD_SPEC.md](LLM_FLASHCARD_SPEC.md).

The preferred format is:

```json
{
  "deck": "Python Basics",
  "cards": [
    {
      "id": "py-dict-get",
      "front": "Why use dict.get(key, default) instead of dict[key]?",
      "back": "dict.get returns the default value when the key is missing.",
      "tags": ["python", "dictionaries"],
      "extra": "Optional note shown in the card footer",
      "sources": ["Optional citation or source locator"]
    }
  ]
}
```

For LLM-generated decks, the loader also accepts:

- A top-level list of cards.
- `question` / `answer` instead of `front` / `back`.
- `prompt` / `response` instead of `front` / `back`.
- `tags` as either a string or a list.
- `sources` for citation strings. The app accepts the field even if it does not display it yet.

`id` is optional, but stable explicit IDs are recommended so progress survives edits to the deck text.

## LLM Progress Reports

Use `Export LLM Report` in the app to create a file like:

```text
reports/flashcards_llm_progress_report_20260506_143012_123456.json
```

The report is not a deck. It summarizes:

- Weak, forgotten, new, due, and stable cards.
- Recent grades and lapse counts.
- Tags that need more practice.
- Original card prompts, answers, optional sources, and suggested follow-up focus.
- A `recommended_prompt` that asks an LLM to generate a targeted follow-up deck.

Paste the report JSON into an LLM and ask it to follow the `recommended_prompt`. Save the returned
deck JSON in this folder, then use `Refresh Decks` and load it from the deck dropdown.

## Shortcuts

- `Space`: show answer
- `1`: Again
- `2`: Hard
- `3`: Good
- `4`: Easy
- `A`: study all cards, even when none are due
- `Ctrl/Cmd+R`: reload the current deck

`Study All` uses a priority score rather than deck order. Cards you recently missed, marked hard,
lapsed, have low ease, or are due appear first. Cards with the same score are shuffled so repeat
sessions stay fresh.

## Tests

```bash
python3 -m unittest
```

## Publishing To GitHub

This project is safe to publish as a local-only Python app. Before pushing, review which deck files
you want to share publicly.

Recommended first-time setup:

```bash
git init
git add app.py flashcards.py test_flashcards.py README.md LLM_FLASHCARD_SPEC.md flashcards.json .gitignore
git commit -m "Initial local flashcard app"
```

If you want to publish extra decks, add them explicitly:

```bash
git add CS5055V1.json
git commit -m "Add CS5055 flashcard deck"
```

The `.gitignore` excludes local study state and generated LLM reports:

- `progress.json`
- `progress/`
- `reports/`
- `*_llm_progress_report.json`
- Python cache files and virtual environments

That keeps private review progress out of GitHub while still allowing you to share the app and any
deck JSON files you choose.

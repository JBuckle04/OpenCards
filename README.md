# Open Cards

Open Cards is a local Python flashcard app that reads JSON decks and reviews them with an Anki-style flow:

1. Read the front of the card.
2. Reveal the answer.
3. Grade recall with `Again`, `Hard`, `Good`, or `Easy`.
4. Save review progress to a per-deck file in `progress/`.

Decks are loaded from JSON files in `decks/`. Use the in-app deck dropdown to switch decks.

Open Cards can also export an LLM progress report from the current deck. Use `Export LLM Report`
after studying to create a targeted input for generating a follow-up deck. Everything runs locally;
there is no hosted sync service or external account dependency.

## Project Layout

```text
app.py                  # Tkinter UI
flashcards.py           # deck loading, scheduling, reports
test_flashcards.py      # unit tests
docs/                   # LLM and publishing guidance
decks/                  # local deck JSON files, ignored by git
progress/               # local study progress, ignored by git
reports/                # generated LLM progress reports, ignored by git
```

## Run

Quick start:

- macOS: double-click `Open Cards.command`.
- Windows: double-click `Open Cards.bat`.

If Python is missing, the launcher will explain where to install it from. Open Cards needs Python
3.11 or newer.

For terminal users:

```bash
python3 app.py
```

To open a specific deck:

```bash
python3 app.py decks/path-to-deck.json
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

If an older `progress/legacy_progress.json` exists and its card IDs match the deck you open, the app
will read it for continuity and then save future reviews to the per-deck progress file. This prevents
one deck from overwriting another deck's study history.

To export an LLM progress report without opening the GUI:

```bash
python3 app.py decks/path-to-deck.json --export-report
```

## JSON Deck Format

For LLM generation guidance, see [docs/LLM_FLASHCARD_SPEC.md](docs/LLM_FLASHCARD_SPEC.md).

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
- `sources` for citation strings. Sources appear with the answer after reveal and are included in
  LLM progress reports.

`sources` can be a list of strings:

```json
"sources": ["lecture-2.md:14-20", "Slide 8"]
```

The loader also accepts simple source objects from LLM output and turns them into readable citations:

```json
"sources": [
  {
    "title": "Lecture 2",
    "section": "Retrieval practice",
    "page": 4,
    "url": "https://example.com/lecture-2"
  }
]
```

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
deck JSON in `decks/`, then use `Refresh Decks` and load it from the deck dropdown.

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

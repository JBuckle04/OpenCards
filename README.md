# OpenCards

OpenCards is a local Python flashcard app that reads JSON decks and reviews them with an Anki-style flow:

1. Read the front of the card.
2. Reveal the answer.
3. Grade recall with `Again`, `Hard`, `Good`, or `Easy`.
4. Save review progress to a per-deck file in `progress/`.

Decks are loaded from JSON files in `decks/`. Use the in-app deck dropdown to switch decks.

OpenCards can also export an LLM progress report from the current deck. Use `Export LLM Report`
after studying to create a targeted input for generating a follow-up deck. Everything runs locally;
there is no hosted sync service or external account dependency.

## Getting Started

### 1. Run OpenCards

Double-click the launcher for your system:

- macOS: `OpenCards.command`
- Windows: `OpenCards.bat`

The app looks for deck files in `decks/`. A deck is a `.json` file containing a `deck` name and
an array of `cards`.

### 2. Generate A Deck With ChatGPT

Open a new ChatGPT conversation and upload:

- `docs/LLM_FLASHCARD_SPEC.md`
- The source material you want to study, such as PDFs, Word documents, slides, text files, Markdown
  notes, or copied course notes saved as a file

In ChatGPT, use the attachment or add-file button to upload the files. ChatGPT supports common
document, text, spreadsheet, and presentation formats. If your material is in Google Docs, export it
as `.pdf` or `.docx` first rather than uploading a `.gdoc` shortcut. For current upload limits and
supported file types, see OpenAI's [File Uploads FAQ](https://help.openai.com/en/articles/8555545-uploading-files-in-chatgpt).

Then send a prompt like this:

```text
Use the uploaded OpenCards flashcard spec as the output contract.
Generate a flashcard deck from the uploaded source material.
Return valid JSON only. Do not wrap it in Markdown.
Include sources for each factual card when a source locator is available.
Prefer 20 to 40 cards unless the material clearly needs fewer.
```

The result should start with `{` and end with `}`. If ChatGPT includes Markdown fences such as
````text
```json
````
ask it to resend the answer as raw JSON only.

### 3. Save The Result As A Deck

Create a new file in `decks/` with a clear `.json` name, for example:

```text
decks/information-visualisation-revision.json
```

Paste the JSON into that file. If ChatGPT gives you a downloadable `.json` file, download it, rename
it clearly, and move it into `decks/`.

Before loading it, quickly check:

- The file extension is `.json`.
- The top-level object has `deck` and `cards`.
- Each card has at least `id`, `front`, and `back`.
- The JSON is not wrapped in Markdown fences.

Deck files in `decks/` are ignored by git by default, so your study material stays local unless you
intentionally force-add a sample deck.

### 4. Load The Deck

In OpenCards:

1. Open `More`.
2. Choose `Refresh Decks`.
3. Select the new deck from the dropdown.
4. Press `Load Deck`.

You can also use `More` > `Open JSON...` to load a deck from another location.

To edit a loaded deck, open `Edit Decks` > `Edit Current Deck...`. The deck editor lets you change
the deck name, add or delete cards, and edit each card's ID, front, back, tags, extra note, and
sources without touching raw JSON. Press `Save` in the editor to write the deck and reload it in the
study view.

### 5. Generate Follow-Up Decks From Progress

After studying for a while, press `Export LLM Report`. OpenCards will save a timestamped report in
`reports/`.

Upload these files to ChatGPT:

- `docs/LLM_FLASHCARD_SPEC.md`
- The new report from `reports/`
- The original source files, if you want ChatGPT to stay close to the source material

Then send:

```text
Use the uploaded OpenCards spec and progress report.
Generate a targeted follow-up deck focused on weak, forgotten, fragile, or low-ease cards.
Do not duplicate the original cards verbatim.
Return valid JSON only.
```

Save the new JSON as a separate file in `decks/`, for example:

```text
decks/information-visualisation-follow-up-01.json
```

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

- macOS: double-click `OpenCards.command`.
- Windows: double-click `OpenCards.bat`.

If Python is missing, the launcher will explain where to install it from. OpenCards needs Python
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
- `E`: open the Edit Decks menu
- `M`: open the More menu
- `Ctrl/Cmd+O`: open a deck JSON file
- `Ctrl/Cmd+R`: reload the current deck

`Study All` uses a priority score rather than deck order. Cards you recently missed, marked hard,
lapsed, have low ease, or are due appear first. Cards with the same score are shuffled so repeat
sessions stay fresh.

Use `Edit Decks` in the header to open the visual deck editor, validate, reload, reveal local deck
files, or open the current deck as raw JSON. Use `More` for `Open JSON`, `Refresh Decks`, and
`Dark Mode` / `Light Mode`. The theme choice is saved locally in `progress/theme.txt`.

## Tests

```bash
python3 -m unittest
```

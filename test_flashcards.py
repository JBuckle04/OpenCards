import json
import random
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from app import default_progress_path, default_report_path, discover_deck_options, progress_save_path
from flashcards import (
    Card,
    CardProgress,
    Deck,
    build_llm_progress_report,
    due_cards,
    load_deck,
    load_progress,
    prioritized_study_cards,
    progress_for,
    save_progress,
    study_priority_score,
)


def sample_deck() -> Deck:
    return Deck(
        name="Python Basics",
        cards=[
            Card(
                id="py-list-comprehension",
                front="What does a Python list comprehension create?",
                back="A new list built from an iterable.",
                tags=["python", "syntax"],
            ),
            Card(
                id="py-dict-get",
                front="Why use dict.get(key, default)?",
                back="It returns a default instead of raising KeyError.",
                tags=["python", "dictionaries"],
            ),
            Card(
                id="py-venv",
                front="What is a Python virtual environment used for?",
                back="It isolates project packages.",
                tags=["python", "tooling"],
            ),
        ],
    )


class DeckLoadingTests(unittest.TestCase):
    def test_loads_preferred_deck_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            deck_path = Path(temp_dir) / "deck.json"
            deck_path.write_text(
                json.dumps(
                    {
                        "deck": "Biology",
                        "cards": [
                            {
                                "id": "cell",
                                "front": "What is the basic unit of life?",
                                "back": "The cell.",
                                "tags": "biology",
                                "sources": "biology-notes.md:1-4",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            deck = load_deck(deck_path)

        self.assertEqual(deck.name, "Biology")
        self.assertEqual(deck.cards[0].id, "cell")
        self.assertEqual(deck.cards[0].tags, ["biology"])
        self.assertEqual(deck.cards[0].sources, ["biology-notes.md:1-4"])

    def test_loads_llm_friendly_question_answer_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            deck_path = Path(temp_dir) / "history_deck.json"
            deck_path.write_text(
                json.dumps(
                    [
                        {
                            "question": "Who wrote the Declaration of Independence?",
                            "answer": "Thomas Jefferson was the principal author.",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            first_load = load_deck(deck_path)
            second_load = load_deck(deck_path)

        self.assertEqual(first_load.name, "History Deck")
        self.assertEqual(first_load.cards[0].front, "Who wrote the Declaration of Independence?")
        self.assertEqual(first_load.cards[0].id, second_load.cards[0].id)

    def test_discovers_valid_decks_in_program_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            program_dir = Path(temp_dir)
            deck_path = program_dir / "deck.json"
            progress_path = program_dir / "progress.json"
            invalid_path = program_dir / "notes.json"
            deck_path.write_text(
                json.dumps(
                    {
                        "deck": "Chemistry",
                        "cards": [{"id": "atom", "front": "Smallest unit?", "back": "Atom."}],
                    }
                ),
                encoding="utf-8",
            )
            progress_path.write_text("{}", encoding="utf-8")
            invalid_path.write_text(json.dumps({"not": "a deck"}), encoding="utf-8")

            options = discover_deck_options(program_dir, progress_path)

        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].path, deck_path)
        self.assertEqual(options[0].label, "Chemistry (deck.json)")


class ReviewSchedulingTests(unittest.TestCase):
    def test_good_review_moves_card_to_tomorrow(self):
        progress = CardProgress()
        today = date(2026, 5, 5)

        progress.apply_grade("good", reviewed_on=today)

        self.assertEqual(progress.repetitions, 1)
        self.assertEqual(progress.interval_days, 1)
        self.assertEqual(progress.due, "2026-05-06")

    def test_again_resets_repetitions_and_keeps_card_due_today(self):
        progress = CardProgress(repetitions=3, interval_days=10, ease=2.5)
        today = date(2026, 5, 5)

        progress.apply_grade("again", reviewed_on=today)

        self.assertEqual(progress.repetitions, 0)
        self.assertEqual(progress.interval_days, 0)
        self.assertEqual(progress.due, "2026-05-05")
        self.assertEqual(progress.lapses, 1)

    def test_due_cards_excludes_future_reviews(self):
        deck = sample_deck()
        progress = progress_for(deck)
        progress[deck.cards[0].id].due = (date.today() + timedelta(days=3)).isoformat()
        progress[deck.cards[0].id].last_reviewed = date.today().isoformat()

        due = due_cards(deck, progress, today=date.today())

        self.assertNotIn(deck.cards[0], due)

    def test_progress_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            progress_path = Path(temp_dir) / "progress.json"
            progress = {
                "card-1": CardProgress(
                    repetitions=2,
                    interval_days=3,
                    grade_counts={"again": 0, "hard": 1, "good": 1, "easy": 0},
                )
            }

            save_progress(progress_path, progress)
            loaded = load_progress(progress_path)

        self.assertEqual(loaded["card-1"].repetitions, 2)
        self.assertEqual(loaded["card-1"].interval_days, 3)
        self.assertEqual(loaded["card-1"].grade_counts["hard"], 1)

    def test_llm_progress_report_prioritizes_weak_cards(self):
        deck = sample_deck()
        progress = progress_for(deck)
        progress[deck.cards[0].id].apply_grade("again", reviewed_on=date(2026, 5, 5))
        progress[deck.cards[1].id].apply_grade("easy", reviewed_on=date(2026, 5, 5))

        report = build_llm_progress_report(
            deck,
            progress,
            deck_path=Path("sample.json"),
            today=date(2026, 5, 5),
        )

        weak_rows = [
            row for row in report["card_progress"] if row["learning_signal"] == "forgotten"
        ]
        self.assertEqual(report["report_type"], "opencards.llm_progress_report")
        self.assertEqual(report["summary"]["weak_cards"], 1)
        self.assertEqual(weak_rows[0]["id"], deck.cards[0].id)
        self.assertIn("recommended_prompt", report)
        self.assertIn("python", report["tag_stats"])

    def test_default_progress_is_per_deck(self):
        deck_path = Path("custom_deck.json")

        self.assertEqual(default_progress_path(deck_path).name, "custom_deck_progress.json")
        self.assertEqual(default_progress_path(deck_path).parent.name, "progress")
        self.assertEqual(progress_save_path(deck_path).name, "custom_deck_progress.json")

    def test_default_report_paths_are_timestamped(self):
        deck_path = Path("custom_deck.json")

        first = default_report_path(deck_path)
        second = default_report_path(deck_path)

        self.assertNotEqual(first, second)
        self.assertEqual(first.parent.name, "reports")
        self.assertTrue(first.name.startswith("custom_deck_llm_progress_report_"))

    def test_study_priority_scores_weak_cards_above_easy_cards(self):
        today = date(2026, 5, 6)
        weak = CardProgress(lapses=1, ease=1.9, last_grade="again")
        weak.apply_grade("again", reviewed_on=today)
        easy = CardProgress(interval_days=30, ease=3.0, last_grade="easy")
        easy.apply_grade("easy", reviewed_on=today)

        self.assertGreater(
            study_priority_score(weak, today),
            study_priority_score(easy, today),
        )

    def test_prioritized_study_cards_randomizes_within_same_score(self):
        deck = sample_deck()
        progress = progress_for(deck)

        ordered = prioritized_study_cards(
            deck,
            progress,
            today=date.today(),
            rng=random.Random(4),
        )

        self.assertCountEqual([card.id for card in ordered], [card.id for card in deck.cards])
        self.assertNotEqual([card.id for card in ordered], [card.id for card in deck.cards])

    def test_prioritized_study_cards_keeps_weak_cards_first(self):
        deck = sample_deck()
        progress = progress_for(deck)
        progress[deck.cards[0].id].apply_grade("easy", reviewed_on=date(2026, 5, 6))
        progress[deck.cards[1].id].apply_grade("again", reviewed_on=date(2026, 5, 6))

        ordered = prioritized_study_cards(
            deck,
            progress,
            today=date(2026, 5, 6),
            rng=random.Random(1),
        )

        self.assertEqual(ordered[0].id, deck.cards[1].id)


if __name__ == "__main__":
    unittest.main()

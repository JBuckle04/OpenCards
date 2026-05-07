from __future__ import annotations

import json
import random
from hashlib import sha1
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


GRADE_LABELS = {
    "again": "Again",
    "hard": "Hard",
    "good": "Good",
    "easy": "Easy",
}


@dataclass(frozen=True)
class Card:
    id: str
    front: str
    back: str
    tags: list[str] = field(default_factory=list)
    extra: str = ""
    sources: list[str] = field(default_factory=list)


@dataclass
class CardProgress:
    due: str = field(default_factory=lambda: date.today().isoformat())
    interval_days: int = 0
    ease: float = 2.5
    repetitions: int = 0
    lapses: int = 0
    last_reviewed: str | None = None
    last_grade: str | None = None
    grade_counts: dict[str, int] = field(
        default_factory=lambda: {grade: 0 for grade in GRADE_LABELS}
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CardProgress":
        progress = cls()
        for key in asdict(progress):
            if key in data:
                setattr(progress, key, data[key])
        progress.grade_counts = _normalized_grade_counts(progress.grade_counts)
        return progress

    def is_due(self, today: date | None = None) -> bool:
        today = today or date.today()
        return date.fromisoformat(self.due) <= today

    def apply_grade(self, grade: str, reviewed_on: date | None = None) -> None:
        if grade not in GRADE_LABELS:
            raise ValueError(f"Unknown review grade: {grade}")

        reviewed_on = reviewed_on or date.today()
        self.last_reviewed = reviewed_on.isoformat()
        self.last_grade = grade
        self.grade_counts = _normalized_grade_counts(self.grade_counts)
        self.grade_counts[grade] += 1

        if grade == "again":
            self.repetitions = 0
            self.lapses += 1
            self.interval_days = 0
            self.ease = max(1.3, self.ease - 0.2)
        elif grade == "hard":
            self.repetitions += 1
            self.interval_days = max(1, round(max(1, self.interval_days) * 1.2))
            self.ease = max(1.3, self.ease - 0.15)
        elif grade == "good":
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval_days = 1
            elif self.repetitions == 2:
                self.interval_days = 3
            else:
                self.interval_days = max(1, round(self.interval_days * self.ease))
        elif grade == "easy":
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval_days = 4
            else:
                self.interval_days = max(4, round(self.interval_days * self.ease * 1.3))
            self.ease += 0.15

        self.due = (reviewed_on + timedelta(days=self.interval_days)).isoformat()


@dataclass
class Deck:
    name: str
    cards: list[Card]


def load_deck(path: str | Path) -> Deck:
    deck_path = Path(path)
    with deck_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    if isinstance(raw, list):
        name = deck_path.stem.replace("_", " ").title()
        raw_cards = raw
    elif isinstance(raw, dict):
        name = str(raw.get("deck") or raw.get("name") or deck_path.stem)
        raw_cards = raw.get("cards")
    else:
        raise ValueError("Deck JSON must be either an object or a list of cards.")

    if not isinstance(raw_cards, list):
        raise ValueError("Deck JSON must contain a 'cards' list.")

    cards = [_parse_card(item, index) for index, item in enumerate(raw_cards, start=1)]
    if not cards:
        raise ValueError("Deck contains no cards.")

    return Deck(name=name, cards=cards)


def load_progress(path: str | Path) -> dict[str, CardProgress]:
    progress_path = Path(path)
    if not progress_path.exists():
        return {}

    with progress_path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    if not isinstance(raw, dict):
        raise ValueError("Progress JSON must be an object keyed by card id.")

    return {
        str(card_id): CardProgress.from_dict(progress)
        for card_id, progress in raw.items()
        if isinstance(progress, dict)
    }


def save_progress(path: str | Path, progress: dict[str, CardProgress]) -> None:
    progress_path = Path(path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    with progress_path.open("w", encoding="utf-8") as file:
        json.dump(
            {card_id: asdict(card_progress) for card_id, card_progress in progress.items()},
            file,
            indent=2,
            sort_keys=True,
        )


def progress_for(deck: Deck, stored: dict[str, CardProgress] | None = None) -> dict[str, CardProgress]:
    stored = stored or {}
    return {card.id: stored.get(card.id, CardProgress()) for card in deck.cards}


def due_cards(
    deck: Deck,
    progress: dict[str, CardProgress],
    today: date | None = None,
    include_new: bool = True,
) -> list[Card]:
    today = today or date.today()
    due = []
    for card in deck.cards:
        card_progress = progress.get(card.id, CardProgress())
        is_new = card_progress.last_reviewed is None
        if card_progress.is_due(today) or (include_new and is_new):
            due.append(card)
    return due


def study_priority_score(card_progress: CardProgress, today: date | None = None) -> int:
    today = today or date.today()
    grade_counts = _normalized_grade_counts(card_progress.grade_counts)
    score = 0

    if card_progress.last_reviewed is None:
        score += 70
    if card_progress.is_due(today):
        score += 50
    if card_progress.last_grade == "again":
        score += 80
    elif card_progress.last_grade == "hard":
        score += 55
    elif card_progress.last_grade == "good":
        score += 15
    elif card_progress.last_grade == "easy":
        score -= 25

    score += min(60, card_progress.lapses * 20)
    score += min(50, grade_counts["again"] * 16 + grade_counts["hard"] * 10)
    score -= min(45, grade_counts["easy"] * 12)
    score -= min(40, max(0, card_progress.interval_days) * 2)

    if card_progress.ease <= 2.1:
        score += 25
    elif card_progress.ease >= 2.8:
        score -= 15

    return max(0, score)


def prioritized_study_cards(
    deck: Deck,
    progress: dict[str, CardProgress],
    today: date | None = None,
    rng: random.Random | None = None,
) -> list[Card]:
    today = today or date.today()
    rng = rng or random.Random()
    buckets: dict[int, list[Card]] = {}

    for card in deck.cards:
        card_progress = progress.get(card.id, CardProgress())
        score = study_priority_score(card_progress, today)
        buckets.setdefault(score, []).append(card)

    ordered_cards: list[Card] = []
    for score in sorted(buckets, reverse=True):
        cards = buckets[score]
        rng.shuffle(cards)
        ordered_cards.extend(cards)
    return ordered_cards


def _parse_card(item: Any, index: int) -> Card:
    if not isinstance(item, dict):
        raise ValueError(f"Card {index} must be an object.")

    front = item.get("front") or item.get("question") or item.get("prompt")
    back = item.get("back") or item.get("answer") or item.get("response")
    if not front or not back:
        raise ValueError(
            f"Card {index} needs front/back fields. question/answer and prompt/response also work."
        )

    card_id = item.get("id") or _stable_card_id(front, back, index)
    tags = item.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        raise ValueError(f"Card {index} tags must be a string or list.")

    sources = item.get("sources", [])
    if isinstance(sources, str):
        sources = [sources]
    if not isinstance(sources, list):
        raise ValueError(f"Card {index} sources must be a string or list.")

    return Card(
        id=str(card_id),
        front=str(front).strip(),
        back=str(back).strip(),
        tags=[str(tag) for tag in tags],
        extra=str(item.get("extra", "")).strip(),
        sources=[str(source) for source in sources],
    )


def _stable_card_id(front: Any, back: Any, index: int) -> str:
    seed = f"{index}:{front}:{back}"
    return f"card-{sha1(seed.encode('utf-8')).hexdigest()[:12]}"


def human_due_text(progress: CardProgress) -> str:
    due = date.fromisoformat(progress.due)
    today = date.today()
    if due <= today:
        return "due now"
    if due == today + timedelta(days=1):
        return "due tomorrow"
    return f"due in {(due - today).days} days"


def format_review_date(value: str | None) -> str:
    if not value:
        return "never"
    parsed = datetime.fromisoformat(value)
    return parsed.strftime("%d %b %Y")


def build_llm_progress_report(
    deck: Deck,
    progress: dict[str, CardProgress],
    deck_path: str | Path | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    today = today or date.today()
    rows = [_card_report_row(card, progress.get(card.id, CardProgress()), today) for card in deck.cards]
    reviewed_cards = [row for row in rows if row["progress"]["last_reviewed"]]
    weak_cards = [
        row
        for row in rows
        if row["learning_signal"] in {"forgotten", "fragile", "low_ease", "relearning"}
    ]
    due_rows = [row for row in rows if row["progress"]["is_due"]]

    tag_stats = _build_tag_stats(rows)
    weakest_tags = sorted(
        tag_stats.items(),
        key=lambda item: (-item[1]["weak_cards"], -item[1]["due_cards"], item[0]),
    )

    return {
        "report_type": "opencards.llm_progress_report",
        "report_version": 1,
        "generated_on": today.isoformat(),
        "deck": {
            "name": deck.name,
            "path": str(deck_path) if deck_path else None,
            "card_count": len(deck.cards),
        },
        "summary": {
            "reviewed_cards": len(reviewed_cards),
            "new_cards": len(deck.cards) - len(reviewed_cards),
            "due_cards": len(due_rows),
            "weak_cards": len(weak_cards),
            "mature_cards": sum(1 for row in rows if row["progress"]["interval_days"] >= 21),
            "total_lapses": sum(row["progress"]["lapses"] for row in rows),
            "weakest_tags": [tag for tag, stats in weakest_tags if stats["weak_cards"] > 0][:8],
        },
        "generation_guidance": {
            "goal": "Generate a targeted follow-up Open Cards deck from this progress report.",
            "prioritize": [
                "Cards with learning_signal forgotten, fragile, low_ease, or relearning.",
                "Tags listed in summary.weakest_tags.",
                "Cards with lapses or recent Again/Hard grades.",
                "New cards that have not been reviewed yet, if they cover prerequisite material.",
            ],
            "avoid": [
                "Duplicating existing cards verbatim.",
                "Adding unsupported facts not present in original card text or sources.",
                "Turning one weak concept into a broad essay question.",
            ],
            "output_contract": "Return an Open Cards deck JSON object with deck and cards only.",
        },
        "recommended_prompt": _recommended_followup_prompt(deck.name),
        "tag_stats": tag_stats,
        "card_progress": rows,
    }


def save_llm_progress_report(path: str | Path, report: dict[str, Any]) -> None:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, sort_keys=True)


def _card_report_row(card: Card, progress: CardProgress, today: date) -> dict[str, Any]:
    grade_counts = _normalized_grade_counts(progress.grade_counts)
    due = date.fromisoformat(progress.due)
    progress_payload = {
        "due": progress.due,
        "is_due": due <= today,
        "days_until_due": (due - today).days,
        "interval_days": progress.interval_days,
        "ease": progress.ease,
        "repetitions": progress.repetitions,
        "lapses": progress.lapses,
        "last_reviewed": progress.last_reviewed,
        "last_grade": progress.last_grade,
        "grade_counts": grade_counts,
    }

    return {
        "id": card.id,
        "front": card.front,
        "back": card.back,
        "tags": card.tags,
        "extra": card.extra,
        "sources": card.sources,
        "progress": progress_payload,
        "learning_signal": _learning_signal(progress, grade_counts),
        "suggested_followup_focus": _suggested_followup_focus(card, progress, grade_counts),
    }


def _learning_signal(progress: CardProgress, grade_counts: dict[str, int]) -> str:
    if progress.last_reviewed is None:
        return "new"
    if progress.last_grade == "again":
        return "forgotten"
    if progress.last_grade == "hard":
        return "fragile"
    if progress.lapses > 0 and progress.repetitions <= 1:
        return "relearning"
    if progress.ease <= 2.1 or grade_counts["again"] + grade_counts["hard"] >= 2:
        return "low_ease"
    if progress.interval_days >= 21 and progress.last_grade in {"good", "easy"}:
        return "stable"
    return "learning"


def _suggested_followup_focus(
    card: Card,
    progress: CardProgress,
    grade_counts: dict[str, int],
) -> str:
    if progress.last_reviewed is None:
        return "Introduce the concept with one prerequisite or definition card."
    if progress.last_grade == "again":
        return "Create simpler prerequisite, recognition, and contrast cards for this concept."
    if progress.last_grade == "hard":
        return "Create near-miss contrast cards and a short application question."
    if progress.lapses > 0 or grade_counts["again"] > 0:
        return "Create a relearning card that tests the deciding rule, not just recall."
    if progress.ease <= 2.1:
        return "Break the concept into smaller atomic prompts."
    if card.tags:
        return f"Add one varied practice card for the {card.tags[0]} tag."
    return "Add one varied practice card for this concept."


def _build_tag_stats(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for row in rows:
        tags = row["tags"] or ["untagged"]
        for tag in tags:
            tag_stats = stats.setdefault(
                tag,
                {"cards": 0, "reviewed_cards": 0, "due_cards": 0, "weak_cards": 0, "lapses": 0},
            )
            tag_stats["cards"] += 1
            if row["progress"]["last_reviewed"]:
                tag_stats["reviewed_cards"] += 1
            if row["progress"]["is_due"]:
                tag_stats["due_cards"] += 1
            if row["learning_signal"] in {"forgotten", "fragile", "low_ease", "relearning"}:
                tag_stats["weak_cards"] += 1
            tag_stats["lapses"] += row["progress"]["lapses"]
    return stats


def _normalized_grade_counts(value: Any) -> dict[str, int]:
    counts = {grade: 0 for grade in GRADE_LABELS}
    if isinstance(value, dict):
        for grade in GRADE_LABELS:
            counts[grade] = int(value.get(grade, 0) or 0)
    return counts


def _recommended_followup_prompt(deck_name: str) -> str:
    return (
        "Use this Open Cards LLM progress report to generate a targeted follow-up deck. "
        f"Name the new deck '{deck_name} Follow-up'. Return valid JSON only with top-level "
        "fields deck and cards. Focus on weak_cards, weakest_tags, lapses, and recent Again/Hard "
        "grades. Do not duplicate original cards verbatim. Use each source card's front, back, "
        "tags, extra, sources, and suggested_followup_focus to create new atomic cards. Preserve "
        "citations in each new card's sources array when sources are present."
    )

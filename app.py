from __future__ import annotations

import argparse
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from flashcards import (
    GRADE_LABELS,
    Card,
    CardProgress,
    Deck,
    build_llm_progress_report,
    due_cards,
    format_review_date,
    human_due_text,
    load_deck,
    load_progress,
    prioritized_study_cards,
    progress_for,
    save_llm_progress_report,
    save_progress,
)

PROGRAM_DIR = Path(__file__).resolve().parent
DEFAULT_DECK = PROGRAM_DIR / "flashcards.json"
LEGACY_PROGRESS = PROGRAM_DIR / "progress.json"
PROGRESS_DIR = PROGRAM_DIR / "progress"
REPORTS_DIR = PROGRAM_DIR / "reports"

COLORS = {
    "bg": "#f6f8fb",
    "panel": "#ffffff",
    "panel_alt": "#f9fbfd",
    "text": "#1f2937",
    "muted": "#667085",
    "line": "#d9e2ec",
    "brand": "#2563eb",
    "brand_hover": "#1d4ed8",
    "mint": "#0f766e",
    "mint_hover": "#0d5f59",
    "amber": "#b45309",
    "amber_hover": "#92400e",
    "rose": "#be123c",
    "rose_hover": "#9f1239",
    "soft_blue": "#dbeafe",
    "soft_mint": "#ccfbf1",
}


@dataclass(frozen=True)
class DeckOption:
    label: str
    path: Path


def discover_deck_options(program_dir: Path, progress_path: Path | None = None) -> list[DeckOption]:
    progress_path = progress_path.resolve() if progress_path else None
    options: list[DeckOption] = []
    for path in sorted(program_dir.glob("*.json")):
        if progress_path and path.resolve() == progress_path:
            continue
        try:
            deck = load_deck(path)
        except (OSError, ValueError):
            continue
        options.append(DeckOption(label=f"{deck.name} ({path.name})", path=path))
    return options


def default_progress_path(deck_path: Path) -> Path:
    return PROGRESS_DIR / f"{deck_path.stem}_progress.json"


def progress_load_path(deck_path: Path, requested_progress_path: Path | None = None) -> Path:
    if requested_progress_path:
        return requested_progress_path
    deck_progress_path = default_progress_path(deck_path)
    if deck_progress_path.exists() or not LEGACY_PROGRESS.exists():
        return deck_progress_path
    if legacy_progress_matches_deck(deck_path):
        return LEGACY_PROGRESS
    return deck_progress_path


def legacy_progress_matches_deck(deck_path: Path) -> bool:
    try:
        deck = load_deck(deck_path)
        legacy_progress = load_progress(LEGACY_PROGRESS)
    except (OSError, ValueError):
        return False
    deck_card_ids = {card.id for card in deck.cards}
    return any(card_id in deck_card_ids for card_id in legacy_progress)


def progress_save_path(deck_path: Path, requested_progress_path: Path | None = None) -> Path:
    if requested_progress_path:
        return requested_progress_path
    return default_progress_path(deck_path)


def default_report_path(deck_path: Path, generated_at: datetime | None = None) -> Path:
    generated_at = generated_at or datetime.now()
    timestamp = generated_at.strftime("%Y%m%d_%H%M%S_%f")
    return REPORTS_DIR / f"{deck_path.stem}_llm_progress_report_{timestamp}.json"


def draw_round_rect(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int,
    **kwargs: object,
) -> int:
    radius = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = [
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class RoundedPanel(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        radius: int = 18,
        fill: str = COLORS["panel"],
        outline: str = "",
        background: str = COLORS["bg"],
        padding: tuple[int, int, int, int] = (20, 20, 20, 20),
        width: int = 1,
        height: int = 1,
    ):
        super().__init__(
            master,
            width=width,
            height=height,
            bg=background,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
        )
        self.radius = radius
        self.fill = fill
        self.outline = outline
        self.padding = padding
        self.content = tk.Frame(self, bg=fill, highlightthickness=0, borderwidth=0)
        self._window = self.create_window(0, 0, anchor="nw", window=self.content)
        self.bind("<Configure>", self._redraw)

    def _redraw(self, _: tk.Event | None = None) -> None:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        left, top, right, bottom = self.padding
        self.delete("panel")
        draw_round_rect(
            self,
            1,
            1,
            width - 2,
            height - 2,
            self.radius,
            fill=self.fill,
            outline=self.outline,
            width=1 if self.outline else 0,
            tags="panel",
        )
        self.tag_lower("panel")
        self.coords(self._window, left, top)
        self.itemconfigure(
            self._window,
            width=max(1, width - left - right),
            height=max(1, height - top - bottom),
        )


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        text: str,
        command: object,
        fill: str,
        active_fill: str,
        foreground: str = "#ffffff",
        disabled_fill: str = "#eef2f7",
        disabled_foreground: str = "#98a2b3",
        background: str = COLORS["bg"],
        radius: int = 15,
        height: int = 46,
        min_width: int = 118,
    ):
        super().__init__(
            master,
            height=height,
            width=min_width,
            bg=background,
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            cursor="hand2",
        )
        self.text = text
        self.command = command
        self.fill = fill
        self.active_fill = active_fill
        self.foreground = foreground
        self.disabled_fill = disabled_fill
        self.disabled_foreground = disabled_foreground
        self.radius = radius
        self.button_state = "normal"
        self.is_hovered = False
        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def configure(self, cnf: object | None = None, **kwargs: object) -> None:
        if cnf:
            super().configure(cnf)
        if "state" in kwargs:
            self.button_state = str(kwargs.pop("state"))
            self.configure(cursor="arrow" if self.button_state == "disabled" else "hand2")
        if "text" in kwargs:
            self.text = str(kwargs.pop("text"))
        if kwargs:
            super().configure(**kwargs)
        self._redraw()

    config = configure

    def _redraw(self, _: tk.Event | None = None) -> None:
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        disabled = self.button_state == "disabled"
        fill = self.disabled_fill if disabled else self.active_fill if self.is_hovered else self.fill
        foreground = self.disabled_foreground if disabled else self.foreground
        self.delete("all")
        draw_round_rect(self, 1, 1, width - 2, height - 2, self.radius, fill=fill, outline=fill)
        self.create_text(
            width // 2,
            height // 2,
            text=self.text,
            fill=foreground,
            font=("TkDefaultFont", 10, "bold"),
        )

    def _on_enter(self, _: tk.Event) -> None:
        self.is_hovered = True
        self._redraw()

    def _on_leave(self, _: tk.Event) -> None:
        self.is_hovered = False
        self._redraw()

    def _on_click(self, _: tk.Event) -> None:
        if self.button_state != "disabled" and callable(self.command):
            self.command()


class FlashcardApp(tk.Tk):
    def __init__(self, deck_path: Path, progress_path: Path | None):
        super().__init__()
        self.title("FlashCardBuilder")
        self.geometry("1040x720")
        self.minsize(820, 600)
        self.configure(bg=COLORS["bg"])

        self.deck_path = deck_path
        self.requested_progress_path = progress_path
        self.progress_path = progress_save_path(deck_path, progress_path)
        self.deck: Deck | None = None
        self.progress: dict[str, CardProgress] = {}
        self.queue: list[Card] = []
        self.current_card: Card | None = None
        self.answer_visible = False
        self.deck_options: dict[str, Path] = {}
        self.deck_var = tk.StringVar()

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()
        self._load_initial_deck()

    def _configure_styles(self) -> None:
        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.style.configure("App.TFrame", background=COLORS["bg"])
        self.style.configure("Panel.TFrame", background=COLORS["panel"], relief="flat")
        self.style.configure("Subtle.TFrame", background=COLORS["panel_alt"], relief="flat")
        self.style.configure("Header.TFrame", background=COLORS["panel"])
        self.style.configure("Controls.TFrame", background=COLORS["bg"])

        self.style.configure(
            "Title.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("TkDefaultFont", 22, "bold"),
        )
        self.style.configure(
            "Eyebrow.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("TkDefaultFont", 10, "bold"),
        )
        self.style.configure(
            "CardTitle.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("TkDefaultFont", 10, "bold"),
        )
        self.style.configure(
            "Muted.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["muted"],
            font=("TkDefaultFont", 10),
        )
        self.style.configure(
            "PanelMuted.TLabel",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            font=("TkDefaultFont", 10),
        )
        self.style.configure(
            "Stats.TLabel",
            background=COLORS["soft_blue"],
            foreground="#1e3a8a",
            padding=(12, 6),
            font=("TkDefaultFont", 10, "bold"),
        )

        self.style.configure(
            "TCombobox",
            fieldbackground=COLORS["panel_alt"],
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            bordercolor=COLORS["panel_alt"],
            lightcolor=COLORS["panel_alt"],
            darkcolor=COLORS["panel_alt"],
            arrowcolor=COLORS["brand"],
            padding=(8, 6),
        )

        self._configure_button_style("Primary.TButton", COLORS["brand"], COLORS["brand_hover"])
        self._configure_button_style("Mint.TButton", COLORS["mint"], COLORS["mint_hover"])
        self._configure_button_style("Amber.TButton", COLORS["amber"], COLORS["amber_hover"])
        self._configure_button_style("Rose.TButton", COLORS["rose"], COLORS["rose_hover"])
        self._configure_button_style("Ghost.TButton", COLORS["panel"], COLORS["soft_blue"], COLORS["text"])

    def _configure_button_style(
        self,
        name: str,
        background: str,
        active_background: str,
        foreground: str = "#ffffff",
    ) -> None:
        self.style.configure(
            name,
            background=background,
            foreground=foreground,
            bordercolor=background,
            lightcolor=background,
            darkcolor=background,
            focusthickness=0,
            padding=(12, 9),
            font=("TkDefaultFont", 10, "bold"),
        )
        self.style.map(
            name,
            background=[("active", active_background), ("disabled", "#e5e7eb")],
            foreground=[("disabled", "#98a2b3")],
            bordercolor=[("active", active_background), ("disabled", "#e5e7eb")],
        )

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build_menu()

        header_panel = RoundedPanel(self, radius=24, padding=(24, 20, 24, 18), height=220)
        header_panel.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header = header_panel.content
        header.columnconfigure(0, weight=1)

        header_text = tk.Frame(header, bg=COLORS["panel"], highlightthickness=0)
        header_text.grid(row=0, column=0, sticky="ew")
        header_text.columnconfigure(0, weight=1)

        ttk.Label(header_text, text="FLASHCARDBUILDER", style="Eyebrow.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.deck_label = ttk.Label(header_text, text="No deck loaded", style="Title.TLabel")
        self.deck_label.grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.stats_label = RoundedButton(
            header_text,
            text="",
            command=None,
            fill=COLORS["soft_blue"],
            active_fill=COLORS["soft_blue"],
            foreground="#1e3a8a",
            background=COLORS["panel"],
            radius=18,
            height=40,
            min_width=220,
        )
        self.stats_label.grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0))

        picker = tk.Frame(header, bg=COLORS["panel"], highlightthickness=0)
        picker.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        picker.columnconfigure(1, weight=1)

        ttk.Label(picker, text="Deck", style="PanelMuted.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        combo_shell = RoundedPanel(
            picker,
            radius=17,
            fill=COLORS["panel_alt"],
            outline=COLORS["line"],
            background=COLORS["panel"],
            padding=(12, 5, 12, 5),
            height=48,
        )
        combo_shell.grid(row=0, column=1, sticky="ew")
        combo_shell.content.columnconfigure(0, weight=1)

        self.deck_combo = ttk.Combobox(
            combo_shell.content,
            textvariable=self.deck_var,
            state="readonly",
        )
        self.deck_combo.grid(row=0, column=0, sticky="ew")
        self.deck_combo.bind("<<ComboboxSelected>>", lambda _: self.load_selected_deck())
        self.deck_combo.bind("<Return>", lambda _: self.load_selected_deck())

        action_bar = tk.Frame(header, bg=COLORS["panel"], highlightthickness=0)
        action_bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        self.load_button = RoundedButton(
            action_bar,
            text="Load Deck",
            command=self.load_selected_deck,
            fill=COLORS["brand"],
            active_fill=COLORS["brand_hover"],
            background=COLORS["panel"],
        )
        self.load_button.grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.open_button = RoundedButton(
            action_bar,
            text="Open JSON",
            command=self.open_deck,
            fill=COLORS["panel_alt"],
            active_fill=COLORS["soft_blue"],
            foreground=COLORS["text"],
            background=COLORS["panel"],
        )
        self.open_button.grid(row=0, column=1, sticky="w", padx=(0, 8))

        self.refresh_button = RoundedButton(
            action_bar,
            text="Refresh",
            command=self.refresh_deck_list,
            fill=COLORS["panel_alt"],
            active_fill=COLORS["soft_blue"],
            foreground=COLORS["text"],
            background=COLORS["panel"],
        )
        self.refresh_button.grid(row=0, column=2, sticky="w", padx=(0, 8))

        self.due_button = RoundedButton(
            action_bar,
            text="Due Only",
            command=self.rebuild_queue,
            fill=COLORS["panel_alt"],
            active_fill=COLORS["soft_blue"],
            foreground=COLORS["text"],
            background=COLORS["panel"],
        )
        self.due_button.grid(row=0, column=3, sticky="w", padx=(0, 8))
        self.due_button.configure(state="disabled")

        self.report_button = RoundedButton(
            action_bar,
            text="Export LLM Report",
            command=self.export_llm_report,
            fill=COLORS["panel_alt"],
            active_fill=COLORS["soft_blue"],
            foreground=COLORS["text"],
            background=COLORS["panel"],
            min_width=160,
        )
        self.report_button.grid(row=0, column=4, sticky="w")
        self.report_button.configure(state="disabled")

        body = ttk.Frame(self, padding=(18, 0, 18, 10), style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        self.front_text = self._build_card_panel(body, "Front", row=0)
        self.back_text = self._build_card_panel(body, "Back", row=1)

        footer = ttk.Frame(self, padding=(18, 0, 18, 18), style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        self.detail_label = ttk.Label(footer, text="", anchor="w", style="Muted.TLabel")
        self.detail_label.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self.shortcut_label = ttk.Label(
            footer,
            text=(
                "Keyboard: Space show answer | 1 Again | 2 Hard | 3 Good | 4 Easy | "
                "A study all | Ctrl/Cmd+R reload"
            ),
            anchor="w",
            style="Muted.TLabel",
        )
        self.shortcut_label.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        controls = ttk.Frame(footer, style="Controls.TFrame")
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)
        controls.columnconfigure(3, weight=1)
        controls.columnconfigure(4, weight=1)
        controls.columnconfigure(5, weight=1)

        self.show_button = RoundedButton(
            controls,
            text="Show Answer (Space)",
            command=self.show_answer,
            fill=COLORS["brand"],
            active_fill=COLORS["brand_hover"],
            min_width=180,
        )
        self.show_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.grade_buttons: dict[str, RoundedButton] = {}
        grade_colors = {
            "again": (COLORS["rose"], COLORS["rose_hover"]),
            "hard": (COLORS["amber"], COLORS["amber_hover"]),
            "good": (COLORS["mint"], COLORS["mint_hover"]),
            "easy": (COLORS["brand"], COLORS["brand_hover"]),
        }
        for index, grade in enumerate(("again", "hard", "good", "easy"), start=1):
            fill, active_fill = grade_colors[grade]
            button = RoundedButton(
                controls,
                text=f"{GRADE_LABELS[grade]} ({index})",
                command=lambda selected=grade: self.grade_current(selected),
                fill=fill,
                active_fill=active_fill,
            )
            button.grid(row=0, column=index, sticky="ew", padx=(0 if index == 1 else 8, 0))
            self.grade_buttons[grade] = button

        self.study_all_button = RoundedButton(
            controls,
            text="Study All (A)",
            command=self.study_all_cards,
            fill=COLORS["panel"],
            active_fill=COLORS["soft_blue"],
            foreground=COLORS["text"],
        )
        self.study_all_button.grid(row=0, column=5, sticky="ew", padx=(8, 0))
        self.study_all_button.configure(state="disabled")

        self._set_grade_buttons(enabled=False)

    def _build_card_panel(self, parent: ttk.Frame, title: str, row: int) -> tk.Text:
        panel_shell = RoundedPanel(
            parent,
            radius=24,
            fill=COLORS["panel"],
            outline="",
            background=COLORS["bg"],
            padding=(22, 18, 22, 22),
        )
        panel_shell.grid(row=row, column=0, sticky="nsew", pady=(0, 14 if row == 0 else 0))
        panel = panel_shell.content
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        ttk.Label(panel, text=title.upper(), style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        text_shell = RoundedPanel(
            panel,
            radius=18,
            fill=COLORS["panel_alt"],
            outline=COLORS["line"],
            background=COLORS["panel"],
            padding=(18, 18, 18, 18),
        )
        text_shell.grid(row=1, column=0, sticky="nsew")
        text_shell.content.columnconfigure(0, weight=1)
        text_shell.content.rowconfigure(0, weight=1)

        text = tk.Text(
            text_shell.content,
            height=7,
            wrap="word",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            highlightbackground=COLORS["panel_alt"],
            highlightcolor=COLORS["brand"],
            bg=COLORS["panel_alt"],
            fg=COLORS["text"],
            insertbackground=COLORS["brand"],
            selectbackground=COLORS["soft_blue"],
            selectforeground=COLORS["text"],
            padx=0,
            pady=0,
            font=("TkDefaultFont", 17),
        )
        text.grid(row=0, column=0, sticky="nsew")
        text.configure(state="disabled")
        return text

    def _build_menu(self) -> None:
        return

    def _bind_shortcuts(self) -> None:
        self.bind_all("<space>", self._shortcut_show_answer)
        self.bind_all("1", lambda _: self._shortcut_grade("again"))
        self.bind_all("2", lambda _: self._shortcut_grade("hard"))
        self.bind_all("3", lambda _: self._shortcut_grade("good"))
        self.bind_all("4", lambda _: self._shortcut_grade("easy"))
        self.bind_all("a", lambda _: self._shortcut_study_all())
        self.bind_all("A", lambda _: self._shortcut_study_all())
        self.bind_all("<Command-r>", lambda _: self._shortcut_reload())
        self.bind_all("<Control-r>", lambda _: self._shortcut_reload())
        self.bind_all("<Command-o>", lambda _: self._shortcut_open())
        self.bind_all("<Control-o>", lambda _: self._shortcut_open())

    def _load_initial_deck(self) -> None:
        self.refresh_deck_list()
        if self.deck_path.exists():
            self.load_deck_file(self.deck_path)
        elif self.deck_options:
            self.load_deck_file(next(iter(self.deck_options.values())))
        else:
            self._show_empty_state(f"Create a deck JSON file in {PROGRAM_DIR}.")

    def refresh_deck_list(self) -> None:
        options = discover_deck_options(PROGRAM_DIR, self.progress_path)
        self.deck_options = {option.label: option.path for option in options}
        labels = list(self.deck_options)
        self.deck_combo.configure(values=labels)
        self.load_button.configure(state="normal" if labels else "disabled")

        if not labels:
            self.deck_var.set("")
            return

        current_label = self._label_for_deck_path(self.deck_path)
        self.deck_var.set(current_label or labels[0])

    def load_selected_deck(self) -> None:
        selected = self.deck_var.get()
        deck_path = self.deck_options.get(selected)
        if deck_path:
            self.load_deck_file(deck_path)

    def open_deck(self) -> None:
        selected = filedialog.askopenfilename(
            title="Open flashcard deck",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            initialdir=str(PROGRAM_DIR),
        )
        if selected:
            self.load_deck_file(Path(selected))

    def reload_deck(self) -> None:
        if self.deck_path:
            self.load_deck_file(self.deck_path)

    def load_deck_file(self, deck_path: Path) -> None:
        load_path = progress_load_path(deck_path, self.requested_progress_path)
        save_path = progress_save_path(deck_path, self.requested_progress_path)
        try:
            deck = load_deck(deck_path)
            stored_progress = load_progress(load_path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Could not load deck", str(error))
            self._show_empty_state("Deck failed to load.")
            return

        self.deck_path = deck_path
        self.progress_path = save_path
        self.deck = deck
        self.progress = progress_for(deck, stored_progress)
        self.report_button.configure(state="normal")
        self.due_button.configure(state="normal")
        self._select_deck_in_picker(deck_path)
        self.rebuild_queue()

    def rebuild_queue(self) -> None:
        if not self.deck:
            return
        self.queue = due_cards(self.deck, self.progress)
        self._load_next_card()

    def study_all_cards(self) -> None:
        if not self.deck:
            return
        self.queue = prioritized_study_cards(self.deck, self.progress)
        self._load_next_card()

    def export_llm_report(self) -> None:
        if not self.deck:
            messagebox.showinfo("No deck loaded", "Load a deck before exporting an LLM report.")
            return

        report = build_llm_progress_report(self.deck, self.progress, self.deck_path)
        report_path = default_report_path(self.deck_path)
        try:
            save_llm_progress_report(report_path, report)
        except OSError as error:
            messagebox.showerror("Could not export report", str(error))
            return

        self.refresh_deck_list()
        self._select_deck_in_picker(self.deck_path)
        messagebox.showinfo(
            "LLM report exported",
            f"Saved progress report for follow-up deck generation:\n{report_path}",
        )

    def show_answer(self) -> None:
        if not self.current_card or self.answer_visible:
            return
        self.answer_visible = True
        self._write_text(self.back_text, self.current_card.back)
        self.show_button.configure(state="disabled")
        self._set_grade_buttons(enabled=True)

    def grade_current(self, grade: str) -> None:
        if not self.current_card or not self.answer_visible:
            return

        card = self.current_card
        self.progress[card.id].apply_grade(grade)
        save_progress(self.progress_path, self.progress)

        if grade == "again":
            self.queue.append(card)

        self._load_next_card()

    def _load_next_card(self) -> None:
        if not self.deck:
            return

        self.current_card = self.queue.pop(0) if self.queue else None
        self.answer_visible = False
        self._update_stats()

        if not self.current_card:
            self._show_empty_state("No cards are due. Use Study All (A) to keep studying.")
            return

        self.deck_label.configure(text=self.deck.name)
        self._write_text(self.front_text, self.current_card.front)
        self._write_text(self.back_text, "Press Show Answer when you are ready.")
        self.show_button.configure(state="normal")
        self.study_all_button.configure(state="normal")
        self._set_grade_buttons(enabled=False)
        self._update_detail_label()

    def _show_empty_state(self, message: str) -> None:
        self.current_card = None
        self.answer_visible = False
        self.deck_label.configure(text=self.deck.name if self.deck else "No deck loaded")
        self._write_text(self.front_text, message)
        self._write_text(self.back_text, "")
        self.show_button.configure(state="disabled")
        self.study_all_button.configure(state="normal" if self.deck else "disabled")
        self.report_button.configure(state="normal" if self.deck else "disabled")
        self.due_button.configure(state="normal" if self.deck else "disabled")
        self._set_grade_buttons(enabled=False)
        self.detail_label.configure(text="")
        self._update_stats()

    def _update_stats(self) -> None:
        if not self.deck:
            self.stats_label.configure(text="")
            return

        reviewed = sum(1 for item in self.progress.values() if item.last_reviewed)
        total = len(self.deck.cards)
        due_count = len(due_cards(self.deck, self.progress))
        queue_count = len(self.queue) + (1 if self.current_card else 0)
        self.stats_label.configure(
            text=f"{queue_count} in session | {due_count} due | {reviewed}/{total} reviewed"
        )

    def _update_detail_label(self) -> None:
        if not self.current_card:
            self.detail_label.configure(text="")
            return

        progress = self.progress[self.current_card.id]
        tags = ", ".join(self.current_card.tags) if self.current_card.tags else "untagged"
        detail = (
            f"Card {self.current_card.id} | {tags} | "
            f"last reviewed {format_review_date(progress.last_reviewed)} | {human_due_text(progress)}"
        )
        if self.current_card.extra:
            detail += f" | {self.current_card.extra}"
        self.detail_label.configure(text=detail)

    def _write_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _set_grade_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for button in self.grade_buttons.values():
            button.configure(state=state)

    def _select_deck_in_picker(self, deck_path: Path) -> None:
        label = self._label_for_deck_path(deck_path)
        if label:
            self.deck_var.set(label)

    def _label_for_deck_path(self, deck_path: Path) -> str | None:
        resolved = deck_path.resolve()
        for label, path in self.deck_options.items():
            if path.resolve() == resolved:
                return label
        return None

    def _shortcut_show_answer(self, _: tk.Event) -> str:
        self.show_answer()
        return "break"

    def _shortcut_grade(self, grade: str) -> str:
        self.grade_current(grade)
        return "break"

    def _shortcut_reload(self) -> str:
        self.reload_deck()
        return "break"

    def _shortcut_open(self) -> str:
        self.open_deck()
        return "break"

    def _shortcut_study_all(self) -> str:
        self.study_all_cards()
        return "break"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review JSON flashcards with a small Anki-style GUI.")
    parser.add_argument(
        "deck",
        nargs="?",
        type=Path,
        default=DEFAULT_DECK,
        help="Path to a JSON deck file. Defaults to flashcards.json.",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=None,
        help=(
            "Path to review progress JSON. Defaults to progress/<deck-name>_progress.json. "
            "Existing legacy progress.json is still read until a per-deck file is created."
        ),
    )
    parser.add_argument(
        "--export-report",
        nargs="?",
        const=True,
        default=False,
        metavar="PATH",
        help="Export an LLM progress report for the selected deck and exit. Optionally pass an output path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.export_report:
        deck = load_deck(args.deck)
        progress_path = progress_load_path(args.deck, args.progress)
        progress = progress_for(deck, load_progress(progress_path))
        report = build_llm_progress_report(deck, progress, args.deck)
        report_path = (
            default_report_path(args.deck)
            if args.export_report is True
            else Path(args.export_report)
        )
        save_llm_progress_report(report_path, report)
        print(f"Saved LLM progress report to {report_path}")
        return

    app = FlashcardApp(args.deck, args.progress)
    app.mainloop()


if __name__ == "__main__":
    main()

"""Diary-context block builders for the chatbot.

Turns a user's diary entries plus their NLP analyses into the text blocks
that get inlined into the LLM prompt — both the single-window view and the
two-period comparison view. Extracted from the chatbot route.
"""

from datetime import date

from app.models.diary import DiaryEntry
from app.models.diary_analysis import DiaryEntryAnalysis


def _summarize_window(
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> dict:
    """Compute counts for a window so the model can compare two periods at a glance."""
    mood_counts: dict[str, int] = {}
    emotion_counts: dict[str, int] = {}
    sentiment_counts: dict[str, int] = {}

    for entry in entries:
        analysis = analyses.get(entry.id)
        if not analysis:
            continue
        if analysis.mood:
            mood_counts[analysis.mood] = mood_counts.get(analysis.mood, 0) + 1
        if analysis.emotion:
            emotion_counts[analysis.emotion] = emotion_counts.get(analysis.emotion, 0) + 1
        if analysis.sentiment:
            sentiment_counts[analysis.sentiment] = sentiment_counts.get(analysis.sentiment, 0) + 1

    return {
        "entry_count": len(entries),
        "moods": mood_counts,
        "emotions": emotion_counts,
        "sentiments": sentiment_counts,
    }


def _format_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{label}={count}" for label, count in sorted(counts.items(), key=lambda x: -x[1]))


def build_comparison_context(
    period_a: tuple[date, date, str],
    entries_a: list[DiaryEntry],
    period_b: tuple[date, date, str],
    entries_b: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> tuple[str, bool]:
    """Build a context block for a two-period comparison."""
    start_a, end_a, label_a = period_a
    start_b, end_b, label_b = period_b

    summary_a = _summarize_window(entries_a, analyses)
    summary_b = _summarize_window(entries_b, analyses)
    used_memory = any(analyses.get(e.id) for e in entries_a + entries_b)

    def render_entries(entries: list[DiaryEntry]) -> str:
        if not entries:
            return "  (no entries in this window)"
        rendered = []
        for entry in entries:
            snippet = (entry.content or "")[:250]
            analysis = analyses.get(entry.id)
            if analysis and analysis.emotion:
                rendered.append(
                    f"  - [{entry.entry_date}] mood={analysis.mood} | "
                    f"emotion={analysis.emotion} | sentiment={analysis.sentiment} | "
                    f"{entry.title or 'Untitled'}: {snippet}"
                )
            else:
                rendered.append(
                    f"  - [{entry.entry_date}] (no NLP yet) | "
                    f"{entry.title or 'Untitled'}: {snippet}"
                )
        return "\n".join(rendered)

    header = (
        "User is asking for a comparison between two periods. Use the NLP signals "
        "and the entry content together — call out concrete shifts in mood, "
        "emotion, sentiment, and what themes they wrote about.\n"
    )

    block = (
        f"{header}\n"
        f"=== PERIOD A: {label_a} ({start_a} → {end_a}) ===\n"
        f"  entries: {summary_a['entry_count']} | "
        f"moods: {_format_counts(summary_a['moods'])} | "
        f"emotions: {_format_counts(summary_a['emotions'])} | "
        f"sentiments: {_format_counts(summary_a['sentiments'])}\n"
        f"{render_entries(entries_a)}\n\n"
        f"=== PERIOD B: {label_b} ({start_b} → {end_b}) ===\n"
        f"  entries: {summary_b['entry_count']} | "
        f"moods: {_format_counts(summary_b['moods'])} | "
        f"emotions: {_format_counts(summary_b['emotions'])} | "
        f"sentiments: {_format_counts(summary_b['sentiments'])}\n"
        f"{render_entries(entries_b)}"
    )
    return block, used_memory


def build_context(
    entries: list[DiaryEntry],
    analyses: dict[int, DiaryEntryAnalysis],
) -> tuple[str, bool]:
    """Build the single-window context block and whether any NLP memory was used."""
    if not entries:
        return ("The user has no diary entries for the selected period.", False)

    lines: list[str] = []
    used_memory = False

    for entry in entries:
        snippet = (entry.content or "")[:300]
        analysis = analyses.get(entry.id)

        if analysis and analysis.emotion:
            used_memory = True
            emotion_score = (
                f"{analysis.emotion_score:.2f}"
                if analysis.emotion_score is not None
                else "n/a"
            )
            lines.append(
                f"[{entry.entry_date}] mood={analysis.mood} | "
                f"emotion={analysis.emotion} ({emotion_score}) | "
                f"sentiment={analysis.sentiment} | "
                f"Title: {entry.title or 'Untitled'} | Content: {snippet}"
            )
        else:
            lines.append(
                f"[{entry.entry_date}] (no NLP analysis yet) | "
                f"Title: {entry.title or 'Untitled'} | Content: {snippet}"
            )

    header = (
        "User's diary entries with local NLP analysis:"
        if used_memory
        else "User's diary entries:"
    )
    return (header + "\n\n" + "\n\n".join(lines), used_memory)

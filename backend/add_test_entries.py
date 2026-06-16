"""Append fresh diary entries to the test account (without wiping existing ones).

Run from backend/ with the venv active:
    python add_test_entries.py

Unlike seed_test_account.py (which wipes + reseeds the canonical 20 entries),
this script ADDS extra entries anchored to recent days and runs NLP on each.
Idempotent: entries already present (matched by date + title) are skipped, so
it is safe to rerun.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal  # noqa: E402
from app.models.diary import DiaryEntry  # noqa: E402
from app.models.diary_analysis import DiaryEntryAnalysis  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.analysis_service import analyze_text  # noqa: E402


TEST_EMAIL = "testuser@mindtrack.dev"


# (days_ago, title, content, self-reported mood)
NEW_ENTRIES: list[tuple[int, str, str, str]] = [
    (
        0,
        "Aksam yurudum",
        "Bugun aksam uzun bir yuruyuse ciktim. Hava serindi, kafam dagildi. "
        "Telefonu evde biraktim, sadece muzik dinledim. Eve donerken kendimi "
        "cok daha sakin hissettim.",
        "high",
    ),
    (
        1,
        "Yogun bir gun",
        "Sabahtan aksama kadar toplanti ve ders vardi, nefes alacak vakit "
        "bulamadim. Yorgunum ama bir seyleri bitirmis olmak da iyi geldi. "
        "Yine de yarin biraz daha yavas olsun istiyorum.",
        "medium",
    ),
    (
        2,
        "Eski bir arkadas",
        "Lise arkadasim aradi, yillar sonra. Bir saat konustuk, eski gunleri "
        "andik. Beklemedigim bir andi ama icimi isitti. Insan bazen sadece "
        "tanidik bir ses duymak istiyor.",
        "high",
    ),
    (
        3,
        "Biraz kaygiliyim",
        "Gelecek hafta sonuclar aciklanacak ve aklim surekli orada. Ne yapsam "
        "dusuncesi gitmiyor. Kendimi oyalamaya calistim ama tam olmadi. "
        "Erken yatmayi deneyecegim.",
        "low",
    ),
    (
        5,
        "Yemek yaptim",
        "Uzun zamandir hazir yemek aliyordum, bugun kendim pisirdim. Basit bir "
        "makarna ama kendi yaptigim icin daha guzel geldi. Mutfakta vakit "
        "gecirmek beklemedigim kadar dinlendirici oldu.",
        "high",
    ),
]


def main() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == TEST_EMAIL).first()
        if not user:
            print(f"Test user {TEST_EMAIL} not found. Run seed_test_account.py first.")
            return

        today = date.today()
        added = 0
        for days_ago, title, content, mood in NEW_ENTRIES:
            entry_date = today - timedelta(days=days_ago)

            exists = (
                db.query(DiaryEntry.id)
                .filter(
                    DiaryEntry.user_id == user.id,
                    DiaryEntry.entry_date == entry_date,
                    DiaryEntry.title == title,
                )
                .first()
            )
            if exists:
                print(f"  skip (already present): [{entry_date}] {title}")
                continue

            entry = DiaryEntry(
                user_id=user.id,
                entry_date=entry_date,
                title=title,
                content=content,
                mood=mood,
                tags_csv="",
            )
            db.add(entry)
            db.flush()

            print(f"  add [{entry_date}] running NLP on '{title}'...")
            result = analyze_text(content)
            db.add(
                DiaryEntryAnalysis(
                    entry_id=entry.id,
                    user_id=user.id,
                    sentiment=result["sentiment"],
                    sentiment_score=result["sentiment_score"],
                    emotion=result["emotion"],
                    emotion_score=result["emotion_score"],
                    mood=result["mood"],
                )
            )
            db.commit()
            added += 1

        total = db.query(DiaryEntry).filter(DiaryEntry.user_id == user.id).count()
        print(f"\nDone. Added {added} new entries. Test user now has {total} entries total.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

"""
Seed a test account with ~3 weeks of varied Turkish diary entries.

Run from backend/ with the venv active:
    python seed_test_account.py

Idempotent: if the test user already exists, entries get refreshed (old
entries + analyses deleted, new ones inserted). Safe to rerun.

Login credentials after seed:
    email:    testuser@mindtrack.dev
    password: TestUser123!
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Allow running as a standalone script: add backend/ to sys.path.
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

# Force UTF-8 stdout so Turkish characters in entry titles can be printed
# on Windows consoles that default to cp1251 / cp1254.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.database import SessionLocal  # noqa: E402
from app.models.diary import DiaryEntry  # noqa: E402
from app.models.diary_analysis import DiaryEntryAnalysis  # noqa: E402
from app.models.user import User  # noqa: E402
from app.utils.auth import get_password_hash  # noqa: E402
from services.analysis_service import analyze_text  # noqa: E402


TEST_EMAIL = "testuser@mindtrack.dev"
TEST_PASSWORD = "TestUser123!"


# Each tuple: (days_ago, title, content, self-reported mood)
# Designed so:
#   - Week 1 (oldest, days 20-14 ago): mostly heavy — stress, exam, lonely, tired
#   - Week 2 (days 13-7 ago): mixed — some recovery, some bad days
#   - Week 3 (most recent, days 6-0 ago): lighter overall — friends, sport, lighter mood
# This lets "this week vs last week" comparisons show a real shift.
ENTRIES: list[tuple[int, str, str, str]] = [
    # ---------------- Week 1 (3 weeks ago) ----------------
    (
        20,
        "Yine uykusuz bir gece",
        "Sabaha kadar uyuyamadım. Final dönemi geliyor ve hâlâ matematikten "
        "geride hissediyorum. Her şeyi geri bırakmış olmamın suçluluğu çok "
        "yoruyor. Kendimi başkalarıyla kıyaslayıp duruyorum.",
        "low",
    ),
    (
        19,
        "Kendimi kötü hissettim",
        "Sabah hocayla konuştum, ödevi geç teslim etmem yüzünden bayağı "
        "rahatsız oldu. Bütün gün canım sıkkındı, kimseyle konuşmak "
        "istemedim. Akşam telefonu bile sessize aldım.",
        "low",
    ),
    (
        18,
        "Bugun sakindim",
        "Pek bir sey olmadi gun icinde. Ders calistim, biraz dizi izledim. "
        "Ne cok iyi ne cok kotu, ortada bir gun gibiydi.",
        "medium",
    ),
    (
        17,
        "Anksiyete",
        "Sunum yapacagim icin akşamdan beri midem agriyor. Insanlarin önünde "
        "konusurken sesim titriyor genelde. Yatmadan önce uzun uzun düsündüm.",
        "low",
    ),
    (
        16,
        "Sunum bitti",
        "Sunum nihayet bitti ama beklediğim kadar iyi geçmedi, kelimelerim "
        "karıştı bir yerde. Yine de geçti gitti diye rahatladım. Sonra eve "
        "döndüm ve direkt uyudum.",
        "medium",
    ),
    (
        15,
        "Yorgun ve sinirli",
        "Sabahtan beri her şeye sinirleniyorum. Trafik, otobüsteki kalabalık, "
        "arkadaşımın saçma şakası. Bir an yalnız kalmak istedim, bütün gün.",
        "low",
    ),
    (
        14,
        "Yine ders calistim",
        "Butun gun kutuphanedeydim. Kafam patladi gibi hissediyorum. Spor "
        "yapmadigim ortaya cikiyor, surekli halsizim.",
        "low",
    ),

    # ---------------- Week 2 (last week) ----------------
    (
        13,
        "Annemle konuştum",
        "Telefon ettim anneme, uzun zamandır konuşmuyorduk. Sesini duymak "
        "iyi geldi. Bir saat falan konuştuk, biraz da güldük. Sonra biraz "
        "ders çalıştım, daha rahattım.",
        "medium",
    ),
    (
        12,
        "Kötü bir gün daha",
        "Sınav sonucum geldi, beklediğimden çok düşüktü. Bir an kafamda "
        "her şey çöktü. Akşam ağladım biraz, sonra kendime topladım ama "
        "moralim hâlâ yerinde değil.",
        "low",
    ),
    (
        11,
        "Normal bir gün",
        "Bugun cok bir sey yapmadim. Kahvaltıda misir gevregi yedim, derse "
        "gittim, eve döndüm. Sakin bir gundu, gercekten ozetlenecek bir sey "
        "yok.",
        "medium",
    ),
    (
        10,
        "Arkadasla bulustum",
        "Ezgi ile kahve ictik, uzun zamandir gormuyordum. Hem dertlestik "
        "hem guldukle ictik. Iyi geldi cikip biraz konusmak. Eve donerken "
        "daha hafif hissettim.",
        "high",
    ),
    (
        9,
        "Spor yaptim",
        "Kosuya çıktım sabah, bayadır yapmıyordum. İlk 10 dakika zor geldi "
        "ama sonra ritm tutturdum. Bittiginde gercekten enerji geldi, "
        "kahvalti bile guzel olmus gibi geldi.",
        "high",
    ),
    (
        8,
        "Yorgun ama sakin",
        "Gece geç yattım, sabah erken kalktım. Bütün gün biraz halsizdim "
        "ama kafam çok karışık değildi. Akşam erken yatacağım, kararlı.",
        "medium",
    ),

    # ---------------- Week 3 (this week, most recent) ----------------
    (
        6,
        "Iyi bir baslangic",
        "Bu hafta daha düzenli baslamak istedim. Sabah 7'de kalktım, "
        "kahvaltı yaptım gerçek bir şekilde. Listeyi yazdım yapacaklarımın. "
        "Ufak şeyler ama farkı hissediyorum.",
        "high",
    ),
    (
        5,
        "Yine biraz stres",
        "Proje teslimi yaklaşıyor, sabah biraz panik oldum. Ama bu sefer "
        "bir oturup parçaladım işleri, bir kısmını bitirdim. Geçen haftaki "
        "halime göre çok daha iyi başa çıkıyorum gibi.",
        "medium",
    ),
    (
        4,
        "Mutlu bir gun",
        "Ezgi ve Mert ile aksam bulustum, dısarıda yemek yedik. Cok uzun "
        "zaman sonra gercekten kahkaha attım. Eve donerken yuruyerek "
        "geldim, hava da guzeldi.",
        "high",
    ),
    (
        3,
        "Spor + ders dengesi",
        "Sabah kosuya, ogleden sonra kutuphaneye. Iki tarafi da yapinca "
        "kendimi cok daha verimli hissediyorum. Aksam yemegi de yaptim, "
        "hazir yemek almadim bugun.",
        "high",
    ),
    (
        2,
        "Biraz yorgun",
        "Üst üste yoğun günlerden sonra bugün biraz çöktüm. Pek bir şey "
        "yapmadım, sadece dinlendim. Yine de geçen hafta gibi karanlık "
        "değil, sadece dinlenme ihtiyacı.",
        "medium",
    ),
    (
        1,
        "Iyi bir aksam",
        "Aksam evde tek basima film izledim, kendime kahve yaptim. Sakin "
        "ve guzel bir aksamdi. Telefonu da elime az aldim, kafam dinlendi.",
        "high",
    ),
    (
        0,
        "Bugun",
        "Bugun gercekten iyi hissediyorum. Sabah yine spor yaptim, sonra "
        "okula gittim. Hocayla konustugumda bile gerilmedim, eskisi gibi "
        "degil. Bu hafta gercekten farkli geciyor gibi geliyor.",
        "high",
    ),
]


def ensure_test_user(db) -> User:
    """Create or refresh the test user. Returns the user instance."""
    user = db.query(User).filter(User.email == TEST_EMAIL).first()
    if user:
        print(f"  Found existing test user (id={user.id}), will refresh entries.")
        return user

    user = User(
        email=TEST_EMAIL,
        first_name="Test",
        last_name="User",
        hashed_password=get_password_hash(TEST_PASSWORD),
        age=22,
        gender="other",
        degree="bachelor",
        university="Demo University",
        city="Istanbul",
        country="TR",
        is_active=True,
        is_verified=True,
        baseline_completed=True,
        baseline_completed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"  Created test user (id={user.id}).")
    return user


def wipe_existing_entries(db, user: User) -> None:
    entry_ids = [row[0] for row in db.query(DiaryEntry.id).filter(DiaryEntry.user_id == user.id).all()]
    if not entry_ids:
        return

    db.query(DiaryEntryAnalysis).filter(DiaryEntryAnalysis.entry_id.in_(entry_ids)).delete(synchronize_session=False)
    db.query(DiaryEntry).filter(DiaryEntry.id.in_(entry_ids)).delete(synchronize_session=False)
    db.commit()
    print(f"  Wiped {len(entry_ids)} existing entries (and their analyses).")


def seed_entries(db, user: User) -> None:
    today = date.today()
    total = len(ENTRIES)
    for index, (days_ago, title, content, mood) in enumerate(ENTRIES, start=1):
        entry_date = today - timedelta(days=days_ago)
        entry = DiaryEntry(
            user_id=user.id,
            entry_date=entry_date,
            title=title,
            content=content,
            mood=mood,
            tags_csv="",
        )
        db.add(entry)
        db.flush()  # populates entry.id

        print(f"  [{index:>2}/{total}] {entry_date}  - running NLP on '{title[:40]}'...")
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


def main() -> None:
    db = SessionLocal()
    try:
        print(f"Seeding test account: {TEST_EMAIL}")
        user = ensure_test_user(db)
        wipe_existing_entries(db, user)
        print("Seeding diary entries (this will take 1-2 minutes — NLP runs on each)...")
        seed_entries(db, user)
        print("\nDone.")
        print(f"  Login email:    {TEST_EMAIL}")
        print(f"  Login password: {TEST_PASSWORD}")
        print(f"  Entries seeded: {len(ENTRIES)} across last 21 days")
    finally:
        db.close()


if __name__ == "__main__":
    main()

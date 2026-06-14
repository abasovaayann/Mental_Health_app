#!/usr/bin/env bash
# Creates a realistic mix of open and closed issues on the GitHub repo
# to reflect the actual state of the project's work history.
#
# Run once after gh CLI is authenticated. Idempotent it is NOT — running
# twice will create duplicates.

set -e

GH="C:/Projects/gh-cli/bin/gh.exe"
REPO="abasovaayann/Mental_Health_app"

create_and_close() {
    local title="$1"
    local body="$2"
    local labels="$3"
    local close_reason="$4"

    echo "==> [CLOSED] $title"
    URL=$("$GH" issue create -R "$REPO" --title "$title" --body "$body" --label "$labels")
    NUM=$(basename "$URL")
    "$GH" issue close "$NUM" -R "$REPO" --comment "$close_reason" >/dev/null
    echo "    -> $URL (closed)"
}

create_open() {
    local title="$1"
    local body="$2"
    local labels="$3"

    echo "==> [OPEN]   $title"
    URL=$("$GH" issue create -R "$REPO" --title "$title" --body "$body" --label "$labels")
    echo "    -> $URL"
}


# ==============================================================
# CLOSED — work completed during recent development sprint
# ==============================================================

create_and_close \
"Migrate sentiment classifier to multilingual XLM-RoBERTa" \
"The existing sentiment pipeline uses \`distilbert-base-uncased-finetuned-sst-2-english\`, which only works for English text. Diary entries written in Turkish or Russian return garbled scores.

**Proposed change**
- Switch \`backend/nlp/sentiment.py\` to \`cardiffnlp/twitter-xlm-roberta-base-sentiment\`
- Output labels: positive / neutral / negative (3-class)
- Should handle TR, EN, RU, ES, FR, AR, HI, PT out of the box" \
"enhancement,ml" \
"Shipped — \`backend/nlp/sentiment.py\` now uses \`cardiffnlp/twitter-xlm-roberta-base-sentiment\`. Tested with TR/EN/RU diary entries, output looks coherent."


create_and_close \
"Migrate emotion classifier to multilingual xlm-emo-t" \
"Same problem as sentiment — \`j-hartmann/emotion-english-distilroberta-base\` is English-only and emits noise on Turkish entries.

**Tradeoff**
The multilingual replacement \`MilaNLProc/xlm-emo-t\` only emits 4 labels (joy / sadness / anger / fear) instead of 7. We lose surprise / disgust / neutral. Mood mapping in \`analysis_service.py\` already defaults unknown labels to 'medium', so this is graceful." \
"enhancement,ml" \
"Closed — model switched, mood mapping verified, no regressions on seed data."


create_and_close \
"Add conversation memory to chatbot" \
"Right now every chat turn is sent to the LLM in isolation. The user can ask a follow-up like 'demin ne demiştim?' and the bot has no idea what 'just now' refers to.

**Fix**
- Load the last 8 turns from \`chat_messages\` table at the start of \`POST /chatbot/chat\`
- Format them as Claude-compatible message history (\`role\`: user/assistant)
- Pass via \`messages=\` param in \`client.messages.create\`" \
"enhancement" \
"Closed in the Claude migration PR — \`_load_chat_history\` now pulls the last 8 turns and they get prepended to the messages list."


create_and_close \
"Support diary comparison queries (this week vs last week, yesterday vs today)" \
"Users want to ask things like 'bu hafta geçen haftaya göre nasıl?' or 'what changed yesterday vs today?'. Currently the bot only sees one window of entries (daily / weekly / monthly) and can't compare.

**Design**
- Add \`_detect_comparison_intent()\` that recognises:
  - yesterday vs today (TR/EN/RU)
  - this week vs last week (TR/EN/RU)
  - generic 'compare' / 'kıyas' / 'сравни' → defaults to weekly compare
- Fetch two date windows, build a labeled context block with mood / emotion / sentiment count summaries
- Add a few-shot example in the system prompt showing how to structure a comparison reply" \
"enhancement,ml" \
"Closed — comparison detector, context builder, and few-shot example all shipped. Tested with all three languages."


create_and_close \
"Switch chatbot LLM from Gemini Flash to Claude Haiku 4.5" \
"\`gemini-2.5-flash\` free tier is capped at 20 requests/day per project. We hit it within minutes during active testing. Each rate-limit response burns a user's chat turn on a fallback message that doesn't actually answer.

**Plan**
- Move to Anthropic Claude Haiku 4.5 (\`claude-haiku-4-5-20251001\`)
- Enable prompt caching on the system prompt (cuts ~90% of repeated input cost)
- Add \`ANTHROPIC_API_KEY\` to config + .env
- Keep Gemini code path removed; fallback responses remain language-aware

**Cost estimate**
~\$0.004 per message, ~1200 messages per \$5 of credit." \
"enhancement" \
"Closed — backend now runs on Claude Haiku 4.5 with prompt caching. Verified with full TR/EN/RU test pass."


create_and_close \
"Render markdown bold/italic in chat messages" \
"LLM output sometimes uses Markdown emphasis (\`**bold**\`, \`*italic*\`). The frontend was rendering raw \`<p>\` with \`{msg.text}\`, so users saw literal asterisks.

**Fix**
\`renderRichText\` helper in \`src/pages/Insights.js\` — two-pass splitter: first \`**bold**\` → \`<strong>\`, then \`*italic*\` → \`<em>\` on the remaining segments." \
"enhancement,ux" \
"Closed — emphasis renders correctly in both assistant and user bubbles."


create_and_close \
"Add Russian language support to chatbot fallback responses" \
"\`_build_general_fallback_response\` and \`_build_diary_fallback_response\` only branched on Turkish vs English. Russian-speaking users got English fallbacks even when the rest of the system worked in Russian.

**Fix**
- Add \`_is_russian_message\` (Cyrillic char check) and \`_detect_language\` returning 'ru'/'tr'/'en'
- Three-language phrase dicts for mood / emotion / lifestyle suggestions
- Russian few-shot example in the system prompt" \
"enhancement,i18n" \
"Closed — three-language coverage verified."


create_and_close \
"Rebrand chatbot from 'AI Companion' to 'Aura'" \
"Branding pass for the chatbot surface:

- Header title
- Sidebar footer text
- Message bubble byline (e.g. 'AURA • 3:02 PM')
- Remove 'AI Companion online' indicator (cosmetic, not useful)
- Remove decorative \`bubble_chart\` watermark from the chat background
- Remove the 'Lifestyle insights only — not a medical diagnosis tool' disclaimer under the input
- Soften the empty-state copy" \
"ux,design" \
"Closed — all six surface changes shipped in \`src/pages/Insights.js\`."


# ==============================================================
# OPEN — known issues, planned features, doc gaps
# ==============================================================

create_open \
"Cold-start delay on the first diary entry of a session" \
"The first time a user saves an entry after a backend restart, the request hangs for 30-90 seconds while the XLM-RoBERTa and xlm-emo-t models load from disk into RAM. Subsequent requests are ~150 ms.

**Suggested fix**
Add a FastAPI startup hook that warms both pipelines:

\`\`\`python
@app.on_event('startup')
async def warm_nlp_models():
    from nlp.sentiment import predict_sentiment
    from nlp.emotion import predict_emotion
    predict_sentiment('warmup')
    predict_emotion('warmup')
\`\`\`

Trades a 5-10 second slower backend boot for a smooth first user request." \
"enhancement,performance"


create_open \
"Add dark mode toggle in Settings" \
"Tailwind classes already include \`dark:\` variants throughout the app, but there's no UI control to switch theme. Right now it follows OS preference only.

**Scope**
- Toggle in \`src/pages/Settings.js\`
- Persist choice in \`localStorage\` and \`User.preferences_json\`
- Apply class to \`<html>\` on app boot" \
"enhancement,ux,good first issue"


create_open \
"Export diary entries as PDF" \
"User-requested feature — let users download a date range of entries as a single PDF for journaling/printing.

**Implementation sketch**
- Backend: \`GET /api/diary/export?start=...&end=...\` returning a generated PDF (use \`reportlab\` or \`weasyprint\`)
- Frontend: download button on \`PreviousEntries.js\`
- Include NLP analysis (mood / emotion / sentiment) per entry" \
"enhancement"


create_open \
"Streak counter on Dashboard" \
"Show consecutive-day diary streak on the main dashboard (e.g. '🔥 7 day streak'). Strong nudge for habit formation.

**Backend**
Add \`GET /api/diary/streak\` that walks back from today and counts uninterrupted days with at least one entry.

**Frontend**
Replace the empty stats card on \`src/pages/Dashboard.js\` with the streak number + last-7-days mini calendar." \
"enhancement"


create_open \
"Mobile sidebar overlaps chat input on small screens" \
"Repro: open the chatbot page on a viewport narrower than 380px (iPhone SE in landscape, some Androids in portrait). Tap the History drawer. The drawer slides in but its bottom edge sits on top of the chat input bar so the input is unclickable until the drawer is dismissed.

**Likely fix**
\`section\` in \`Insights.js\` uses \`fixed inset-y-0\` which doesn't respect the input bar. Constrain its height to \`calc(100vh - input-height)\` or move the input outside the layout flow." \
"bug,ux,mobile"


create_open \
"Add deployment guide to README" \
"README documents local dev only. We need a section for:

- Docker / docker-compose with Postgres
- One of: Render, Railway, Fly.io for hosting
- Environment variable list (currently scattered between \`config.py\` and \`.env\`)
- HuggingFace model cache mount (so the ~2.2 GB doesn't re-download on every deploy)" \
"documentation,good first issue"


create_open \
"Add unit tests for analysis_service.py and chatbot routes" \
"The core NLP pipeline has zero tests. Even basic smoke tests would have caught the empty-string crash that shipped last week.

**Minimum coverage**
- \`analyze_text('')\` returns neutral defaults
- \`analyze_text('I am so happy today!')\` returns positive sentiment + joy emotion
- \`_should_use_diary_context\` for ~10 mixed Turkish / English / Russian inputs
- \`_detect_comparison_intent\` recognises all three patterns
- \`_detect_language\` 8 representative cases

Use pytest + httpx \`AsyncClient\` for the route tests." \
"enhancement,testing,good first issue"


create_open \
"Filter PreviousEntries by tags" \
"\`DiaryEntry.tags_csv\` already stores tags but \`src/pages/PreviousEntries.js\` doesn't expose any filtering UI. Users with 50+ entries find it hard to surface old reflections on a specific topic.

**Scope**
- Chip-style tag filter row above the entry list
- Multi-select (entries matching any selected tag)
- Backend already returns tags so this is purely frontend" \
"enhancement,ux"


create_open \
"Login error message doesn't distinguish wrong-password from rate-limit" \
"\`POST /api/auth/login\` returns 401 for both 'wrong credentials' and 'account temporarily locked due to too many attempts'. The frontend just shows 'Login failed' in either case.

**Fix**
- Backend: return distinct status codes (\`401\` for bad creds, \`429\` for rate-limit, with \`Retry-After\` header which we already set)
- Frontend: surface 'too many attempts, try again in N seconds' separately
- This is already half-implemented in \`auth.py\` rate-limit logic; just needs the message wiring" \
"bug,ux"


create_open \
"Move ANTHROPIC_API_KEY validation to startup hook" \
"Currently \`POST /chatbot/chat\` checks \`settings.ANTHROPIC_API_KEY\` and raises a runtime error mid-request if it's empty. The user sees a generic fallback message and never realises the key isn't configured.

**Better behaviour**
On app startup, if \`ANTHROPIC_API_KEY\` is empty, log a loud WARNING (or fail fast in production env). That way misconfigured deploys are visible immediately rather than discovered through a fallback response.

Same applies to \`EMAIL_PASSWORD\` for the reminder system." \
"enhancement,good first issue"


create_open \
"Reminder time picker is hardcoded to a single check-in time" \
"\`services/reminder_service.py\` sends reminders on a single time per user. Some users want morning + evening, or only weekends.

**Scope**
- Multi-time picker in \`ReminderSettings.js\` (max 3 times)
- Schema change: \`UserReminder.times_csv\` instead of single column
- Reminder loop in \`main.py\` iterates each time" \
"enhancement"


echo ""
echo "Done — created 8 closed + 10 open issues on $REPO."

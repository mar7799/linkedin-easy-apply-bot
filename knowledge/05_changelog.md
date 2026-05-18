# Changelog

## 2026-05-18 — Structured Logging
- Added `logger_setup.py`: console + daily `.log` + `events.jsonl` handlers
- `events.jsonl`: one JSON per event with ts, level, event type, job_id, title, company, reason
- `log_event()` called at: applied, skipped (with reason), failed, session redirect
- `main.py` logs bot start/stop and catches unexpected crashes
- Added `logs/` to `.gitignore`

## 2026-05-18 — Title Relevance Filter
- Added `title_must_contain_one_of` and `title_must_not_contain` to config.json
- `_is_relevant_title()` checks before every Easy Apply click
- Logs "skip (irrelevant title)" for anything outside Java/Spring/Backend stack
- Updated search URLs to match user's exact working LinkedIn search params

## 2026-05-13 — Number Field Fix
- `_is_numeric_label()` regex detects numeric-expecting fields by label text
- Strips units at fill time: `re.search(r'\d+', answer).group()`
- `_to_number_only()` in claude_agent.py as second layer
- Claude instructed to return bare integers >= 5 for resume skills
- Cleared `__pycache__` to force fresh bytecode

## 2026-05-13 — Multiple Role Searches
- Added 3 search URLs: senior java developer, java full stack, backend developer
- `_YEARS_MAP` dict with 30+ skill mappings, all resume skills >= 5 years

## 2026-05-07 — Navigation Fix (blank page bug)
- Fixed critical bug: `_process_search_url()` was missing `page.goto(search_url)`
- Added login redirect detection after every navigation
- Added structured logging of current URL for debugging

## 2026-05-07 — currentJobId Navigation Strategy
- Stopped trying to click DOM elements in left panel (fragile, breaks constantly)
- Now navigates to `base_url&currentJobId=ID` — loads two-pane view reliably
- LinkedIn naturally renders job detail in right panel with this URL pattern

## 2026-05-07 — Link-Based Job Discovery
- Replaced all CSS card selectors with JS href extraction
- `_collect_job_ids_from_links()`: finds all `/jobs/view/ID` hrefs via JavaScript
- Immune to LinkedIn DOM restructuring
- Added "Sample href" debug log to verify URL format

## 2026-05-05 — Scroll + Pagination Fix
- `_scroll_job_list()` scrolls left panel 8× to render all 25 cards
- `seen_ids` set tracks processed jobs per page to avoid re-processing
- `_process_search_url()` returns updated `applied` count for multi-URL chaining

## 2026-04-29 — Modal & Form Fixes
- `_force_close_any_modal()`: closes any blocking overlay before pagination
- Radio groups: click label not input (label intercepts pointer events)
- `_handle_resume_step()`: skips resume upload prompt automatically
- `_collect_field_errors()`: logs validation errors for debugging
- Stuck page detection: compares modal HTML between steps

## 2026-04-28 — Initial Build
- Playwright bot with LinkedIn Easy Apply automation
- Claude AI for form question answering (3-tier: profile → config → Claude)
- config.json with pre-answered Q&A for common screening questions
- Session-based auth: save_session.py saves cookies to session.json
- applied_jobs.json deduplication

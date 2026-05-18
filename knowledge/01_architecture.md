# Architecture

## Flow

```
main.py
  └── LinkedInBot.run()
        └── _search_and_apply()
              └── _process_search_url(search_url)  ← one per URL in config
                    ├── page.goto(base_url)          ← navigate to search
                    ├── wait for a[href*="/jobs/view/"]  ← wait for render
                    ├── _scroll_job_list()           ← scroll to load all cards
                    ├── _collect_job_ids_from_links() ← JS: extract /jobs/view/ID hrefs
                    └── for each job_id:
                          ├── page.goto(base_url + &currentJobId=ID)  ← load in right panel
                          ├── _is_relevant_title()   ← skip irrelevant roles
                          ├── _find_easy_apply_button()  ← wait + find button
                          ├── easy_btn.click()
                          └── _handle_modal()
                                ├── wait for modal selector
                                ├── for each step (max 20):
                                │     ├── _handle_resume_step()   ← skip upload prompt
                                │     ├── _fill_visible_fields()  ← fill inputs/selects/radios/textareas
                                │     ├── check for Submit button
                                │     └── _click_advance_button() ← Next/Continue/Review
                                └── _discard_modal() if failed
```

## Answer Resolution (claude_agent.py)

```
get_answer(question, field_type, job_title, company)
  1. _profile_lookup()   → name/email/phone from profile block
  2. _config_lookup()    → keyword match against _KEYWORD_MAP → _YEARS_MAP or answers
  3. _ask_claude()       → Claude with resume context + expects_number flag
  → _to_number_only()    → strips "years"/"units" if numeric field
```

## Number Field Handling (critical fix)
- `_is_numeric_label(label)` regex detects "how many years / years of experience / years with X"
- Forces `field_type="number"` regardless of HTML type attribute
- Strips all non-digit chars before `inp.fill()` at the bot level too
- Years for resume skills always >= 5; related skills 2-3; unknown 1

## Job ID Collection Strategy
- Uses JS `document.querySelectorAll('a[href*="/jobs/view/"]').map(a => a.href)`
- Extracts numeric ID with regex `/jobs/view/(\d+)/`
- Avoids all CSS class selectors (LinkedIn changes classes constantly)
- Navigates via `base_url + &currentJobId=ID` to load right-panel detail view

## Logging (logger_setup.py)
- Console: live feedback
- logs/YYYY-MM-DD.log: full plain text per day
- logs/events.jsonl: structured JSON per event (applied/skipped/failed/session/nav/form/error)

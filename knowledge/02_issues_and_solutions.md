# Issues Encountered & Solutions

## 1. greenlet Build Failure (macOS 26 / Python 3.13)
**Problem:** `pip install playwright` fails building greenlet from source — Apple Clang 16+ rejects old C++ static_cast patterns in greenlet 2.x.
**Solution:** `conda install -c conda-forge greenlet` then `pip install -r requirements.txt`
**Root cause:** PyPI has no pre-built wheel for cp313-macosx26; conda-forge does.

## 2. anthropic Module Not Found
**Problem:** `ModuleNotFoundError: No module named 'anthropic'` even after pip install.
**Solution:** `/opt/anaconda3/bin/pip install anthropic` — multiple Python interpreters on system, pip was installing into wrong one.
**Root cause:** Shell uses Anaconda Python but pip resolved to a different interpreter.

## 3. Modal Overlay Blocking Clicks
**Problem:** After applying/failing, the Easy Apply modal stayed open and blocked the "View next page" button click (30s timeout).
**Solution:** Added `_force_close_any_modal()` after every application attempt and before pagination. Uses Escape key as final fallback.

## 4. Radio Button Click Intercepted by Label
**Problem:** `ElementHandle.click: Timeout` — clicking radio `<input>` blocked because its `<label>` intercepts pointer events.
**Solution:** Find the `label[for="radio-id"]` and click the label instead. Fallback to `radio.click(force=True)`.

## 5. LinkedIn Card Selectors Not Matching
**Problem:** `_collect_job_cards()` always returned 0 cards — LinkedIn's CSS class names for job cards change with every deploy.
**Solution:** Switched to extracting job IDs from `a[href*="/jobs/view/"]` hrefs via JavaScript — URL patterns never change. Then navigate directly to `base_url&currentJobId=ID` to load the two-pane view.

## 6. Page Blank / "No job links appeared"
**Problem:** Bot navigated to search URL but found no content — page text was empty.
**Root cause:** `_process_search_url()` was missing `page.goto(search_url)` — it called `wait_for_selector` on a blank page and timed out after 15s.
**Solution:** Added `page.goto(base_url)` at the start of each while loop iteration.

## 7. Wrong Search URL Format
**Problem:** Using `search-results` endpoint with `f_AL=true` — LinkedIn served different content vs what user saw manually.
**Solution:** Use `/jobs/search/` base endpoint. User-provided working URL params: `f_AL=true`, `f_SAL=f_SA_id_226001%3A274001`, `distance=0.0`, `f_TPR=r604800`.

## 8. Number Fields Getting "8 years" Instead of "8"
**Problem:** LinkedIn form showed "Enter a whole number between 0 and 99" error because bot was filling "8 years" in number fields.
**Root cause:** Two issues — (a) Python `__pycache__` serving old bytecode, (b) field detection using HTML `type` attribute which is often "text" even for numeric fields.
**Solution:**
  - Clear `__pycache__` before running after code changes
  - Added `_is_numeric_label()` regex to detect by label text ("how many years", "years of experience", etc.)
  - Strip non-digits at fill time: `re.search(r'\d+', answer).group()`
  - Added same strip in `claude_agent.py` via `_to_number_only()`

## 9. Bot Applying to Irrelevant Roles
**Problem:** Bot applied to React-only, .NET, Python-only, iOS jobs.
**Solution:** Added `title_must_contain_one_of` and `title_must_not_contain` lists in config.json. `_is_relevant_title()` checks both before clicking Easy Apply.

## 10. Session Expiry Mid-Run
**Problem:** After several days, LinkedIn redirects to login page silently.
**Detection:** `if "login" in current or "authwall" in current` after every `page.goto()`
**Solution:** Bot stops and logs: "session expired — run save_session.py"
**Fix:** Run `python save_session.py` to re-authenticate.

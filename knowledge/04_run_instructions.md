# Run Instructions

## First Time Setup
```bash
# 1. Install deps (macOS with Anaconda)
conda install -c conda-forge greenlet
pip install -r requirements.txt
playwright install chromium

# 2. Create .env
cp .env.example .env
# Add: ANTHROPIC_API_KEY=sk-ant-...

# 3. Add resume
# Create resume_context.txt with plain text resume

# 4. Save LinkedIn session
python save_session.py
# Browser opens → log in → press Enter → session.json created
```

## Every Run
```bash
python main.py
```

## If Session Expired
```bash
python save_session.py  # re-authenticate
python main.py
```

## Reading Logs
```bash
# Live: console output while running
# After run:
cat logs/events.jsonl | python -m json.tool  # pretty print all events
grep '"event":"applied"' logs/events.jsonl   # just applied jobs
grep '"event":"failed"' logs/events.jsonl    # just failures
grep '"event":"skipped"' logs/events.jsonl   # skipped + reason
grep '"event":"session"' logs/events.jsonl   # session issues
grep -c '"event":"applied"' logs/events.jsonl  # count applied
cat logs/$(date +%Y-%m-%d).log               # today's plain text log
```

## Updating Search URL
1. Search LinkedIn manually with desired filters
2. Copy URL from address bar
3. Remove session params: currentJobId, origin, refId, trackingId, eBP
4. Paste into config.json → search.search_urls array

## Adjusting Limits
- More jobs per run: increase `max_applications` in config.json
- Slower/faster: adjust `delay_between_apps_seconds`
- Different roles: edit `title_must_contain_one_of` in config.json

## Common Errors
| Error | Fix |
|-------|-----|
| `No module named 'anthropic'` | `/opt/anaconda3/bin/pip install anthropic` |
| `greenlet` build fails | `conda install -c conda-forge greenlet` |
| "No job links appeared" | Session expired → run save_session.py |
| "Redirected to login" | Session expired → run save_session.py |
| Number field validation error | Clear `__pycache__` and re-run |
| Bot applies to wrong roles | Check `title_must_contain_one_of` in config.json |

# LinkedIn Easy Apply Bot

An intelligent job application bot that uses **Playwright** for browser automation and **Claude AI** to read, understand, and fill out LinkedIn Easy Apply forms — automatically.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        LinkedIn Easy Apply Bot                  │
│                                                                 │
│   1. Playwright    Opens Chrome with your saved LinkedIn        │
│                    session and navigates to your job search     │
│                                                                 │
│   2. Job Finder    Scans search results, collects job IDs,     │
│                    skips already-applied jobs                   │
│                                                                 │
│   3. Form Filler   For every Easy Apply form field:            │
│                    ┌─ checks config.json answers first          │
│                    ├─ falls back to Claude AI if unknown        │
│                    └─ Claude reads your resume + job context    │
│                       and writes a tailored answer              │
│                                                                 │
│   4. Logger        Saves every application to                   │
│                    applied_jobs.json (no duplicate applies)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Check with `python --version` |
| Anthropic API key | — | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| LinkedIn account | — | Personal account you apply from |
| Anaconda (recommended) | — | Handles native dependencies on macOS |

---

## Project Structure

```
LinkedIn EasyApply/
├── main.py               # ← Entry point. Run this to start the bot.
├── linkedin_bot.py       # Playwright browser automation logic
├── claude_agent.py       # Claude AI integration — answers form questions
├── save_session.py       # One-time login script — saves your LinkedIn session
├── config.json           # Your job search filters + all pre-answered Q&A
├── resume_context.txt    # Your resume as plain text (fed to Claude)
├── requirements.txt      # Python dependencies
├── .env.example          # Template — copy to .env and add your API key
├── .env                  # Your secrets (never commit this)
├── session.json          # Saved LinkedIn session (auto-created, never commit)
└── applied_jobs.json     # Application log (auto-created, never commit)
```

---

## Quick Start

### Step 1 — Clone the repo

```bash
git clone https://github.com/mar7799/linkedin-easy-apply-bot.git
cd linkedin-easy-apply-bot
```

### Step 2 — Install dependencies

```bash
# If using Anaconda (recommended on macOS)
conda install -c conda-forge greenlet
pip install -r requirements.txt
playwright install chromium

# If using plain Python
pip install -r requirements.txt
playwright install chromium
```

> **macOS note:** If `pip install` fails building `greenlet` from source, run
> `conda install -c conda-forge greenlet` first, then retry.

### Step 3 — Set up your API key

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your real Anthropic API key:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-real-key-here
```

Get a key at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys).

### Step 4 — Add your resume

Create a file called `resume_context.txt` in the project folder and paste your resume as plain text. Claude uses this to answer screening questions accurately.

```
Name: Your Name
Title: Senior Java Full Stack Developer
...
```

### Step 5 — Configure your profile and job search

Open `config.json`. Fill in every field under `profile` and `answers`:

```json
{
  "search": {
    "search_urls": [
      "https://www.linkedin.com/jobs/search/?keywords=senior+java+developer&geoId=103644278&f_TPR=r86400&f_JT=C&f_WT=2&f_LF=f_AL&sortBy=DD"
    ],
    "max_applications": 25,
    "delay_between_apps_seconds": 4
  },
  "profile": {
    "name": "Your Full Name",
    "email": "you@email.com",
    "phone": "+1 (xxx) xxx xxxx",
    "linkedin_url": "https://www.linkedin.com/in/your-profile/"
  },
  "answers": {
    "authorized_to_work_us": "Yes",
    "require_sponsorship": "No",
    "salary_expectation_annual": "150000",
    ...
  }
}
```

See [Configuration Reference](#configuration-reference) below for every field.

### Step 6 — Save your LinkedIn session (one-time only)

```bash
python save_session.py
```

A Chrome window opens. **Log in to LinkedIn manually**, then come back to the terminal and press **Enter**. Your session is saved to `session.json`. You won't need to log in again unless the session expires (usually several weeks).

### Step 7 — Run the bot

```bash
python main.py
```

Chrome opens visibly so you can watch every application in real time. Press `Ctrl+C` to stop at any time.

---

## How to Get Your Search URL

The most reliable way to search for the right roles:

1. Go to [linkedin.com/jobs](https://www.linkedin.com/jobs)
2. Search for your target role (e.g. `senior java developer`)
3. Apply filters: **Date Posted → Past 24 hours**, **Easy Apply**, **Remote**, **Contract**
4. Copy the full URL from the browser address bar
5. Paste it into `config.json` under `search_urls`

**LinkedIn URL filter parameters explained:**

| Parameter | Value | Meaning |
|-----------|-------|---------|
| `f_TPR=r86400` | 86400 seconds | Posted in last 24 hours |
| `f_LF=f_AL` | — | Easy Apply only |
| `f_JT=C` | C = Contract | Employment type |
| `f_JT=F` | F = Full-time | Employment type |
| `f_WT=2` | 2 = Remote | Work location |
| `f_WT=3` | 3 = Hybrid | Work location |
| `f_WT=1` | 1 = On-site | Work location |
| `geoId=103644278` | US | Location (United States) |
| `sortBy=DD` | — | Sort by most recent |

You can add multiple search URLs to the array to sweep several role titles:

```json
"search_urls": [
  "https://www.linkedin.com/jobs/search/?keywords=senior+java+developer&...",
  "https://www.linkedin.com/jobs/search/?keywords=java+full+stack+developer&...",
  "https://www.linkedin.com/jobs/search/?keywords=java+spring+boot+developer&..."
]
```

---

## Configuration Reference

### `search` block

| Key | Description |
|-----|-------------|
| `search_urls` | Array of LinkedIn search URLs to process in order |
| `max_applications` | Stop after this many successful applications per run |
| `delay_between_apps_seconds` | Pause between each application (recommended: 4–6) |

### `profile` block

| Key | Description |
|-----|-------------|
| `name` | Full name |
| `email` | Email address |
| `phone` | Phone number with country code |
| `linkedin_url` | Your LinkedIn profile URL |
| `github_url` | GitHub URL (optional, leave blank to skip) |

### `answers` block

Pre-configured answers to common screening questions. Claude uses these directly — no API call needed for matched questions.

| Key | Example value | Question it answers |
|-----|--------------|---------------------|
| `authorized_to_work_us` | `"Yes"` | Are you authorized to work in the US? |
| `require_sponsorship` | `"No"` | Will you require visa sponsorship? |
| `salary_expectation_annual` | `"140000"` | Annual salary expectation |
| `salary_expectation_hourly` | `"70"` | Hourly rate (contract roles) |
| `desired_start_date` | `"Immediately"` | When can you start? |
| `notice_period` | `"1 week"` | Current notice period |
| `currently_employed` | `"Yes"` | Are you currently employed? |
| `willing_to_relocate` | `"Yes"` | Willing to relocate? |
| `work_preference` | `"Remote"` | Remote / Hybrid / On-site |
| `employment_type` | `"Contract"` | Full-time / Contract / C2C |
| `security_clearance` | `"No"` | Active security clearance? |
| `education_level` | `"Master's Degree"` | Highest degree |
| `field_of_study` | `"Computer Science"` | Degree field |
| `gpa` | `"3.9"` | GPA (remove key to skip) |
| `years_java` | `"8"` | Years of Java experience |
| `years_spring_boot` | `"7"` | Years of Spring Boot |
| `years_react` | `"6"` | Years of React |
| `years_aws` | `"6"` | Years of AWS |
| `years_microservices` | `"7"` | Years of microservices |
| `years_kubernetes` | `"5"` | Years of Kubernetes |
| `years_docker` | `"6"` | Years of Docker |
| `gender` | `"Male"` | EEO gender question |
| `ethnicity` | `"Asian"` | EEO ethnicity question |
| `veteran_status` | `"I am not a protected veteran"` | EEO veteran status |
| `disability_status` | `"No, I don't have a disability"` | EEO disability |

---

## Answer Resolution — How Claude Fills Forms

Every form field goes through three steps:

```
Step 1 — Profile match
   Is it asking for name / email / phone?
   → Answer instantly from profile block

Step 2 — Keyword match
   Does the question contain "salary", "years of java", "sponsor", etc.?
   → Answer instantly from answers block (no API call)

Step 3 — Claude AI
   Unknown question not in config?
   → Claude reads your resume + job title + company name
   → Generates a tailored, professional answer
```

Claude is only called for questions not covered by your config — keeping API costs minimal.

---

## Applied Jobs Log

Every successful application is written to `applied_jobs.json`:

```json
[
  {
    "id": "4123456789",
    "title": "Senior Java Developer",
    "company": "Acme Corp",
    "applied_at": "2026-05-13T09:30:00"
  }
]
```

On re-runs the bot reads this file and skips any job it has already applied to.

---

## Session Expiry

LinkedIn sessions last several weeks. If the bot gets redirected to a login page mid-run, the terminal will print:

```
Redirected to login — session expired. Run save_session.py.
```

Refresh it with:

```bash
python save_session.py
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No module named 'anthropic'` | `pip install anthropic` |
| `greenlet` build fails on macOS | `conda install -c conda-forge greenlet` then retry |
| `No job links appeared` | Session expired — run `save_session.py` |
| `Redirected to login` | Session expired — run `save_session.py` |
| Bot finds jobs but skips all (no Easy Apply) | URL missing `f_LF=f_AL` — copy a fresh URL from LinkedIn |
| `FILL_IN` warning on startup | Open `config.json` and fill in the remaining fields |

---

## Files to Keep Private

These are listed in `.gitignore` and must **never** be committed:

```
.env               ← Anthropic API key
session.json       ← LinkedIn login cookies
applied_jobs.json  ← Your application history
resume_context.txt ← Your personal resume
```

---

## Requirements

- Python 3.11+
- Anthropic API key
- LinkedIn account
- macOS / Linux / Windows (Playwright supports all three)

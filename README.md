# LinkedIn Easy Apply Bot

Automated LinkedIn job application bot powered by **Playwright** (browser automation) and **Claude AI** (intelligent form answering). Searches for jobs posted in the last 24 hours, filters by Easy Apply, and fills out every application form using your resume and pre-configured answers.

---

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│  1. Playwright   →  Opens Chrome, loads your saved       │
│                     LinkedIn session, searches jobs       │
│                                                          │
│  2. Form Filler  →  Reads each question label, checks    │
│                     config.json first (instant answer)   │
│                                                          │
│  3. Claude AI    →  For any unknown question, Claude     │
│                     reads your resume and generates a    │
│                     tailored, professional answer        │
│                                                          │
│  4. Logger       →  Saves every applied job to           │
│                     applied_jobs.json (no duplicates)    │
└──────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
LinkedIn EasyApply/
├── main.py               # Entry point — run this to start the bot
├── linkedin_bot.py       # Playwright browser automation
├── claude_agent.py       # Claude API integration (form Q&A)
├── save_session.py       # One-time script to save LinkedIn session
├── config.json           # Your search settings + pre-answered questions
├── resume_context.txt    # Resume text fed to Claude as context
├── requirements.txt      # Python dependencies
├── .env.example          # Template for API keys
├── .env                  # Your actual API keys (never commit this)
├── session.json          # Saved LinkedIn browser session (auto-created)
└── applied_jobs.json     # Log of every application (auto-created)
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### 3. Fill in your config

Open `config.json` and replace every `"FILL_IN"` value with your real answers. See the [Configuration Reference](#configuration-reference) section below.

### 4. Save your LinkedIn session (one-time only)

```bash
python save_session.py
```

This opens Chrome. Log in to LinkedIn manually, then press Enter in the terminal. Your session is saved to `session.json` and reused on every future run — you won't need to log in again unless the session expires.

### 5. Run the bot

```bash
python main.py
```

The browser window stays open so you can watch every application in real time. Press `Ctrl+C` to stop at any time.

---

## Configuration Reference

### `search` block

| Key | Default | Description |
|-----|---------|-------------|
| `keywords` | `"Senior Java Full Stack Developer"` | Job title to search for |
| `location` | `"United States"` | Location filter |
| `date_posted_seconds` | `86400` | Only jobs posted in this window (86400 = 24 hours) |
| `easy_apply_only` | `true` | Filter to Easy Apply jobs only |
| `max_applications` | `25` | Stop after this many applications per run |
| `delay_between_apps_seconds` | `4` | Pause between each application (be respectful) |

### `profile` block

Your personal contact details pre-filled into forms.

| Key | Description |
|-----|-------------|
| `name` | Full name |
| `email` | Email address |
| `phone` | Phone number |
| `linkedin_url` | Your LinkedIn profile URL |
| `github_url` | Your GitHub profile URL (optional) |

### `answers` block — Questionnaire

These are your pre-configured answers to common screening questions. Fill in every `"FILL_IN"` before running.

| Key | Example | What it answers |
|-----|---------|-----------------|
| `authorized_to_work_us` | `"Yes"` | Are you legally authorized to work in the US? |
| `require_sponsorship` | `"No"` | Will you require visa sponsorship now or in the future? |
| `salary_expectation_annual` | `"$160,000"` | Expected annual salary |
| `salary_expectation_hourly` | `"$80"` | Expected hourly rate (contract roles) |
| `desired_start_date` | `"2 weeks"` | When can you start? |
| `notice_period` | `"2 weeks"` | Current notice period |
| `currently_employed` | `"Yes"` | Are you currently employed? |
| `willing_to_relocate` | `"Yes"` | Are you willing to relocate? |
| `work_preference` | `"Remote"` | Remote / Hybrid / On-site preference |
| `employment_type` | `"Full-time"` | Full-time / Contract W2 / C2C |
| `security_clearance` | `"No"` | Do you hold active security clearance? |
| `education_level` | `"Master's Degree"` | Highest level of education |
| `field_of_study` | `"Computer Science"` | Degree field |
| `gpa` | `"3.8"` | GPA (leave blank or remove to let Claude skip it) |
| `years_java` | `"8"` | Years of Java experience |
| `years_spring_boot` | `"7"` | Years of Spring Boot experience |
| `years_react` | `"6"` | Years of React experience |
| `years_aws` | `"6"` | Years of AWS experience |
| `years_microservices` | `"7"` | Years of microservices experience |
| `gender` | `"Decline to self-identify"` | EEO gender question |
| `ethnicity` | `"Decline to self-identify"` | EEO ethnicity question |
| `veteran_status` | `"I am not a protected veteran"` | EEO veteran status |
| `disability_status` | `"I don't wish to answer"` | EEO disability question |

---

## How Answers Are Resolved

The bot uses a three-tier resolution strategy for every form field:

```
1. Profile lookup   →  phone, email, name fields → answered from profile block
        ↓ no match
2. Config lookup    →  keyword-matched against answers block → instant, no API call
        ↓ no match
3. Claude AI        →  reads your resume + job context → generates tailored answer
```

This means the bot only calls the Claude API for edge-case questions it hasn't seen before, keeping costs minimal.

---

## Applied Jobs Log

Every application is written to `applied_jobs.json`:

```json
[
  {
    "id": "3912847561",
    "title": "Senior Java Full Stack Developer",
    "company": "Acme Corp",
    "applied_at": "2026-04-27T10:45:32"
  }
]
```

On subsequent runs the bot skips any job ID already in this file, so re-running is safe.

---

## Refreshing Your Session

LinkedIn sessions typically last several weeks. If the bot can't reach jobs or gets redirected to login, re-run the session saver:

```bash
python save_session.py
```

---

## Adjusting the Daily Limit

To apply to more or fewer jobs per run, edit `config.json`:

```json
"max_applications": 50
```

A delay of 3–5 seconds between applications (`delay_between_apps_seconds`) is recommended to avoid rate limiting.

---

## Requirements

- Python 3.11+
- Anthropic API key (Claude Sonnet)
- LinkedIn account

---

## Files to Keep Private

Never commit these files to version control:

```
.env
session.json
applied_jobs.json
```

Add them to `.gitignore` if you use git:

```
.env
session.json
applied_jobs.json
```

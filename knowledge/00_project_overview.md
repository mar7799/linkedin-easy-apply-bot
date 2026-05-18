# Project Overview

## What This Is
A Python bot that automatically applies to LinkedIn Easy Apply jobs on behalf of Amram Raju (Senior Java Full Stack Developer, 8 years experience). It uses Playwright for browser automation and Claude AI (claude-sonnet-4-6) to intelligently fill out application forms.

## Target Candidate
- Name: Amram Raju
- Role: Senior Java Full Stack Developer
- Experience: ~8 years (Java, Spring Boot, React, AWS, Azure, Microservices)
- Current employer: Optum (Jan 2025 - Present)
- Education: MS Computer Science, Wichita State University
- Certs: Oracle Java SE 11, AWS Developer Associate, Azure AI Engineer

## Target Jobs
- Senior Java Developer
- Senior Java Full Stack Developer
- Senior Spring Boot Developer
- Senior Java Backend Developer
- Contract + Remote + Easy Apply + US only
- Salary range: $120k–$140k annual / $60–$75/hr

## Tech Stack
- Python 3.13 (Anaconda on macOS 26)
- Playwright (async) for browser automation
- Anthropic Claude API (AsyncAnthropic) for form Q&A
- python-dotenv for env vars
- greenlet installed via conda (macOS ARM build issue)

## File Structure
```
main.py               Entry point, sets up logging, runs bot
linkedin_bot.py       Core Playwright automation
claude_agent.py       Claude API integration, answer resolution
save_session.py       One-time LinkedIn login session saver
logger_setup.py       File + console + JSONL logging
config.json           Search URLs, profile, pre-answered Q&A
resume_context.txt    Resume as plain text (fed to Claude)
.env                  ANTHROPIC_API_KEY (never committed)
session.json          LinkedIn browser cookies (never committed)
applied_jobs.json     Log of every application (never committed)
logs/                 Daily .log + events.jsonl (never committed)
knowledge/            This folder — project knowledge base
```

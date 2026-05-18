"""
Logging setup for LinkedIn Easy Apply Bot
─────────────────────────────────────────
Writes three outputs simultaneously:
  1. Console          — plain text, live feedback while running
  2. logs/YYYY-MM-DD.log — full plain-text log, one file per day
  3. logs/events.jsonl   — one JSON object per line, machine-readable

events.jsonl schema (one line per event):
  {
    "ts":      "2026-05-18T09:31:04",
    "level":   "INFO" | "WARNING" | "ERROR",
    "event":   "applied" | "skipped" | "failed" | "nav" | "form" | "session" | "general",
    "job_id":  "4404326904",       # optional
    "title":   "Senior Java Dev",  # optional
    "company": "Acme Corp",        # optional
    "reason":  "no Easy Apply",    # optional
    "msg":     "raw log message"
  }

Usage:
    from logger_setup import setup_logging, log_event
    setup_logging()
    log_event("applied", job_id="123", title="...", company="...")
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(__file__).parent / "logs"
EVENTS_FILE = LOGS_DIR / "events.jsonl"

# Regex to extract structured fields from log messages
_JOB_PATTERN = re.compile(r"job (\d+)", re.IGNORECASE)
_APPLIED_PATTERN = re.compile(r"APPLIED.*?:\s*(.+?)\s*@\s*(.+)", re.IGNORECASE)
_SKIP_PATTERN = re.compile(r"skip \((.+?)\):\s*(.+?)\s*@\s*(.+)", re.IGNORECASE)
_FAILED_PATTERN = re.compile(r"FAILED.*?:\s*(.+?)\s*@\s*(.+)", re.IGNORECASE)


class JsonlHandler(logging.Handler):
    """Appends a JSON object per log record to events.jsonl."""

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S")
        level = record.levelname

        event: dict = {"ts": ts, "level": level, "msg": msg}

        # Auto-classify event type and extract fields
        if "APPLIED" in msg:
            event["event"] = "applied"
            m = _APPLIED_PATTERN.search(msg)
            if m:
                event["title"] = m.group(1).strip()
                event["company"] = m.group(2).strip()
        elif "skip" in msg.lower():
            event["event"] = "skipped"
            m = _SKIP_PATTERN.search(msg)
            if m:
                event["reason"] = m.group(1).strip()
                event["title"] = m.group(2).strip()
                event["company"] = m.group(3).strip()
        elif "FAILED" in msg:
            event["event"] = "failed"
            m = _FAILED_PATTERN.search(msg)
            if m:
                event["title"] = m.group(1).strip()
                event["company"] = m.group(2).strip()
        elif "login" in msg.lower() or "session" in msg.lower() or "authwall" in msg.lower():
            event["event"] = "session"
        elif "Navigating" in msg or "Loaded" in msg or "Search URL" in msg:
            event["event"] = "nav"
        elif "Validation" in msg or "field" in msg.lower() or "form" in msg.lower():
            event["event"] = "form"
        elif "goto failed" in msg or "Timeout" in msg or "Error" in msg:
            event["event"] = "error"
        else:
            event["event"] = "general"

        # Extract job ID if present
        m = _JOB_PATTERN.search(msg)
        if m:
            event["job_id"] = m.group(1)

        try:
            with open(EVENTS_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass


def setup_logging() -> None:
    """Call once at startup — configures console + file + jsonl handlers."""
    LOGS_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # 1. Console
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # 2. Daily plain-text log file
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOGS_DIR / f"{today}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    # 3. JSON Lines events file
    root.addHandler(JsonlHandler())

    logging.info(f"Logging to {log_file} and {EVENTS_FILE}")


def log_event(
    event: str,
    *,
    job_id: str = "",
    title: str = "",
    company: str = "",
    reason: str = "",
    extra: dict | None = None,
) -> None:
    """Write a structured event directly to events.jsonl (bypasses log level)."""
    LOGS_DIR.mkdir(exist_ok=True)
    record: dict = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "level": "INFO",
        "event": event,
    }
    if job_id:
        record["job_id"] = job_id
    if title:
        record["title"] = title
    if company:
        record["company"] = company
    if reason:
        record["reason"] = reason
    if extra:
        record.update(extra)

    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

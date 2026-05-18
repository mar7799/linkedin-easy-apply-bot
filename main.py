import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from logger_setup import setup_logging
from linkedin_bot import LinkedInBot

load_dotenv()
setup_logging()  # must come before any logging calls

logger = logging.getLogger(__name__)


def main() -> None:
    config_path = Path(__file__).parent / "config.json"
    config = json.loads(config_path.read_text())

    unfilled = [
        k for k, v in config.get("answers", {}).items() if v == "FILL_IN"
    ] + [
        k for k, v in config.get("profile", {}).items() if v == "FILL_IN"
    ]
    if unfilled:
        print(f"\nWARNING: These config fields are still FILL_IN: {', '.join(unfilled)}")
        print("Edit config.json before continuing.\n")
        if input("Continue anyway? (y/N): ").strip().lower() != "y":
            return

    logger.info("=" * 60)
    logger.info("Bot started")
    logger.info("=" * 60)

    bot = LinkedInBot(config)
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C).")
        print("\nStopped.")
    except Exception as e:
        logger.exception(f"Unexpected crash: {e}")

    logger.info("=" * 60)
    logger.info("Bot finished")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

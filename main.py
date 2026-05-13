import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from linkedin_bot import LinkedInBot

load_dotenv()


def main() -> None:
    config_path = Path(__file__).parent / "config.json"
    config = json.loads(config_path.read_text())

    # Warn about unfilled config values
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

    bot = LinkedInBot(config)
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

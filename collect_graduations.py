"""Collect graduation data incrementally. Run via cron or manually over days/weeks."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.data.firebase import poll_and_persist


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll HN for graduations and append to persistent store")
    parser.add_argument("--duration", type=int, default=60, help="Minutes to poll (default: 60)")
    parser.add_argument("--interval", type=int, default=90, help="Seconds between polls (default: 90)")
    args = parser.parse_args()
    n = poll_and_persist(interval_sec=args.interval, duration_min=args.duration)
    print(f"Collected {n} new graduations")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BuildCalc Pro — Daily Recurring Outreach Dispatcher
Schedules and triggers 50 emails from both sender accounts (andrew4522@gmail.com and andrew@bridgingtheaigap.com)
at exactly 08:47 and 11:46 local recipient time every single day.
"""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("BuildCalcDailyScheduler")

SCRIPT_DIR = Path(__file__).parent.resolve()
SENDER_SCRIPT = SCRIPT_DIR / "snov_sender.py"
PYTHON_EXE = sys.executable

SCHEDULED_TIMES = [
    (8, 47),   # Morning window: 08:47 AM
    (11, 46),  # Midday window: 11:46 AM
]


def run_batch():
    logger.info("Triggering scheduled outreach batch (50 per sender, 35s delay)...")
    cmd = [PYTHON_EXE, str(SENDER_SCRIPT), "--batch-now", "--count", "50"]
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR), capture_output=True, text=True)
    logger.info(f"Subprocess stdout:\n{result.stdout}")
    if result.stderr:
        logger.warning(f"Subprocess stderr:\n{result.stderr}")
    return result.returncode == 0


def continuous_loop():
    logger.info("BuildCalc Pro Daily Daemon started.")
    logger.info("Active schedule windows: 08:47 and 11:46 daily.")
    fired_today = set()

    while True:
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")

        for hour, minute in SCHEDULED_TIMES:
            slot_key = f"{today_date}_{hour:02d}:{minute:02d}"
            if now.hour == hour and now.minute == minute and slot_key not in fired_today:
                logger.info(f"=== Scheduled Time Reached: {hour:02d}:{minute:02d} ===")
                fired_today.add(slot_key)
                run_batch()

        # Clean old keys from previous days
        fired_today = {k for k in fired_today if k.startswith(today_date)}
        time.sleep(30)


if __name__ == "__main__":
    if "--run-now" in sys.argv:
        run_batch()
    else:
        continuous_loop()

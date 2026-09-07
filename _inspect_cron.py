#!/usr/bin/env python
"""Inspect Hermes cron scheduler to understand how to register a cron job."""
import sys, os
sys.path.insert(0, r"C:\Users\hello\AppData\Local\hermes\hermes-agent")
from hermes.cron.scheduler import Scheduler
from hermes.cron.jobs import CronJob
import inspect

print("=== Scheduler ===")
print(inspect.getsource(Scheduler))

print("\n=== CronJob ===")
print(inspect.getsource(CronJob))

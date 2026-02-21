#!/usr/bin/env python3
"""Fix OpenClaw config by removing unrecognized skills keys"""
import json

CONFIG = "/root/.openclaw/openclaw.json"

with open(CONFIG) as f:
    d = json.load(f)

# Remove invalid skills block
if "skills" in d:
    print(f"[FIX] Removing skills block: {d['skills']}")
    del d["skills"]

# Save
with open(CONFIG, "w") as f:
    json.dump(d, f, indent=4)

print("[FIX] Config saved. Current config:")
print(json.dumps(d, indent=2))

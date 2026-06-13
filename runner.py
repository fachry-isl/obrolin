#!/usr/bin/env python3
"""Run Obrolin with 9router API key loaded from Hermes config."""
import os
import sys

# Load API key from Hermes config
config_path = "/home/fachryikhsal/.hermes/config.yaml"
try:
    with open(config_path) as f:
        for line in f:
            if "api_key:" in line and "8642c0e88" in line:
                key = line.split(": ", 1)[1].strip()
                os.environ["LLM_API_KEY"] = key
                sys.stderr.write(f"Runner: API key loaded ({len(key)} chars)\n")
                break
except Exception as e:
    sys.stderr.write(f"Runner: could not load API key: {e}\n")

sys.stderr.flush()

# Run main directly
import uvicorn
import main
uvicorn.run(main.app, host="0.0.0.0", port=8765, reload=False, log_level="info")

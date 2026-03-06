# HackerAdvertising

HN optimal posting time & advertising value model. Implements the research spec in `hn_agent_prompt.md`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Fetch 12 months of HN data from Algolia
python fetch_data.py

# Phase 1: Timing analysis (replication, models, heatmap)
python run_phase1.py

# Phase 2: AEV model and sensitivity
python run_phase2.py

# Full pipeline
python run_all.py
```

## Outputs

- `data/algolia_stories.parquet` — historical story data
- `reports/timing_heatmap.png` — P(front page) by hour-of-week
- Console: prior studies table, feature importance, AEV sensitivity table

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

## Results

*Based on 52,000 stories from Algolia (12 months).*

### Prior Studies Replication

| Study | Their Conclusion | Replicated on Current Data |
|-------|------------------|----------------------------|
| Schaefer/Medium 2017 | Mon/Wed 5–6 PM UTC | Tue 17:00 UTC |
| chanind.github.io 2019 | Sun 6am UTC 2.5× better | Sun 20:00 UTC |
| Myriade 2025 | 12:00 UTC weekends | Tue 15:00 UTC |

### Timing Model (XGBoost)

**Feature importance:** `is_show_hn` (40%), `has_url` (25%), `hour_of_week` (8%), `competition_load` (8%), `hour_of_day` (7%), `title_word_count` (6%), `is_ask_hn` (6%).

**Recommendations:**
- **Maximize P(front page):** Mon 19:00 UTC
- **Maximize reach:** Post during peak traffic (US daytime UTC 14–22)

### Advertising Equivalent Value (AEV)

| Scenario | Rank | Hours | Category | Direct AEV | w/ Influence |
|----------|------|-------|----------|------------|--------------|
| Best case | #1 | 20 | dev_tools | $24,570 | $41,580 |
| Strong result | #3 | 12 | dev_tools | $11,466 | $19,404 |
| Typical result | #10 | 6 | general_tech | $1,065 | $1,802 |
| Marginal | #25 | 2 | adjacent | $66 | $111 |

**Breakeven CPC:** Rank #5 with 30k visitors ≈ $240k–$450k click-equivalent (LinkedIn developer CPC $8–15).

**Expected AEV per submission** (P(front) × typical AEV):
- Dev tools: post Mon 19:00 UTC → ~$2,100 expected
- General tech: post Mon 19:00 UTC → ~$210 expected

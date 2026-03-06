# Agent Prompt: Hacker News Optimal Posting Time & Advertising Value Model

## Role & Objective

You are a quantitative research agent tasked with producing a rigorous, reproducible analysis in two connected phases:

1. **Phase 1 — Timing Model**: Discover, replicate, and synthesize existing research on optimal Hacker News submission timing, then produce an improved model using real-time front-page graduation data.
2. **Phase 2 — Advertising Value Model**: Estimate the monetary value, in tech advertising dollars, of achieving front-page placement on Hacker News — drawing on traffic data, audience demographics, and B2B/developer CPM benchmarks.

Your output should be a research artifact suitable for use in product or go-to-market strategy, with clearly documented methods, assumptions, data sources, and model limitations.

---

## Background Knowledge

### The Existing Research Landscape (synthesize but also re-examine)

Several prior analyses exist that you must locate, summarize, and replicate:

- **High-traffic framing (2017, Schaefer/Medium)**: Focuses on when top posts were submitted — concludes Monday/Wednesday 5–6 PM UTC. Methodology: BigQuery, score >250 as top post proxy.
- **Front-page probability framing (2019, chanind.github.io)**: Reframes as P(front page | posting hour). Conclusion: Sunday 6am UTC is 2.5x better than Wednesday 9am UTC. Methodology: BigQuery, score >50 as front-page proxy, posts/hour normalization.
- **Competition minimization framing (Myriade/2025, Show HN)**: 12:00 UTC weekends for Show HN specifically, because European midday + pre-West-Coast volume window. Methodology: HN BigQuery dataset, 157k+ Show HN posts.
- **Score velocity framing (multiple informal)**: Early upvote velocity (first 20–30 min) may dominate timing effects due to the gravity formula.

The key methodological disagreement across all prior work is: **what is the dependent variable?** Maximize raw front-page views (post at peak traffic), or maximize P(reaching front page) (post during low competition)? Your model should treat these as separate optimization objectives and produce separate recommendations for each.

### The Ranking Algorithm (use this to inform your model)

The HN ranking formula (from published Arc source code):

```
Score = (P - 1)^0.8 / ((T + 120) / 60)^1.8 * penalty_factors
```

Where:
- `P` = upvote score (minus sockpuppet votes)
- `T` = item age in minutes
- `1.8` = gravity constant
- `120` = timebase in minutes (2-hour head start effect)
- Penalty multipliers: `nourl_factor = 0.4` (Ask HN), `lightweight_factor = 0.17` (image posts), `contro_factor` (comments > votes and > 40 comments)
- Every 30 seconds, one of the top 50 stories is randomly re-ranked

**Implication**: Age dominates. A post 4 hours old needs roughly 6x the votes of a fresh post to rank equivalently. Early velocity is therefore structurally more important than submission time.

---

## Phase 1: Timing Analysis

### Step 1: Data Acquisition

Use the following data sources (in order of preference):

**A. Algolia HN Search API** (best for historical bulk analysis, no auth required):
```
GET https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>X,created_at_i<Y&hitsPerPage=1000
```
Fields available: `created_at`, `author`, `points`, `num_comments`, `objectID`, `url`, `title`.

Pull at minimum 12 months of story data. For each story, record:
- `created_at` (Unix timestamp → convert to UTC day-of-week and hour-of-day)
- `points` (score proxy for front-page graduation)
- `num_comments`
- `url` presence (boolean, for penalty modeling)
- `title` (for lightweight detection heuristics)

**B. Firebase Official API** (best for real-time graduation tracking):
```
GET https://hacker-news.firebaseio.com/v0/newstories.json
GET https://hacker-news.firebaseio.com/v0/topstories.json
```
Poll both endpoints every 90 seconds. A story that appears in `newstories` at time T0 and subsequently appears in `topstories` at time T1 has "graduated." Record:
- Story ID
- Submission timestamp
- Score at graduation
- Time-to-graduation (T1 - T0) in minutes
- Final rank position at graduation

**C. BigQuery Public Dataset** (if available, for large-scale replication):
```sql
SELECT 
  TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
  EXTRACT(DAYOFWEEK FROM timestamp) as day_of_week,
  EXTRACT(HOUR FROM timestamp) as hour_of_day,
  COUNT(*) as total_posts,
  COUNTIF(score > 50) as front_page_posts,
  COUNTIF(score > 100) as strong_front_page_posts,
  AVG(score) as avg_score,
  SAFE_DIVIDE(COUNTIF(score > 50), COUNT(*)) as front_page_rate
FROM `bigquery-public-data.hacker_news.full`
WHERE type = 'story'
  AND timestamp > '2023-01-01'
GROUP BY hour, day_of_week, hour_of_day
ORDER BY day_of_week, hour_of_day
```

### Step 2: Replicate Prior Methods

For each major prior study:
1. Reproduce their methodology exactly (same score threshold, same time window normalization)
2. Apply it to current data (2023–2025 instead of 2015–2019)
3. Document whether their conclusions hold, have shifted, or reversed

Report this as a table: `[Study | Their Conclusion | Replicated on Current Data | Delta]`

### Step 3: Build the Improved Model

**Dependent variables** (model separately):
- `Y1` = Binary: did post reach score > 50 within 6 hours? (front-page proxy)
- `Y2` = Continuous: final score (raw visibility proxy)
- `Y3` = Time-to-graduation in minutes (conditional on Y1=1)

**Features**:
```
hour_of_week          # 0–167 (7 days × 24 hours)
day_of_week           # 0–6 (Sunday = 0)
hour_of_day           # 0–23 UTC
competition_load      # number of stories submitted in same hour (from Algolia)
has_url               # boolean
is_show_hn            # boolean
is_ask_hn             # boolean
title_word_count      # proxy for informativeness
comment_to_vote_ratio # at T+1hr, if available from Firebase tracker
early_velocity        # votes at T+30min (Firebase tracker only)
```

**Models**:
- Logistic regression for Y1 (interpretable baseline, replicates prior work)
- Gradient boosted classifier (XGBoost or LightGBM) for Y1 with all features
- Linear regression / gradient boosted regressor for Y2
- Cox Proportional Hazards model for Y3 — this is the most theoretically appropriate framing: time-to-front-page as a survival problem, with stories that never graduate treated as right-censored observations

**Output**: 
- Feature importance rankings
- Hour-of-week heatmap of predicted P(front page)
- Comparison table against prior studies
- Separate recommendations for: (a) maximize reach, (b) maximize P(making front page)

---

## Phase 2: Advertising Value Model

### Conceptual Framework

HN front-page placement is **earned media** — it generates traffic and brand impressions equivalent to paid advertising, but without direct cost. The advertising equivalent value (AEV) should be calculated as:

```
AEV = Impressions × CPM_equivalent / 1000 + Referral_visits × CPC_equivalent
```

Where CPM and CPC are calibrated to the HN audience profile, not generic display benchmarks.

### Step 1: Establish Traffic Priors

Use the following empirically documented traffic ranges as your priors (triangulate across multiple reported observations):

| Rank position | Unique visitors (24h) | Source type |
|---|---|---|
| #1 front page | 50,000–100,000+ | Multiple anecdotes |
| Top 5 | 20,000–50,000 | Multiple anecdotes |
| Top 10 | 10,000–30,000 | HFT Guy, Harrison Broadbent |
| Position 11–30 | 3,000–10,000 | marcotm.com case study |
| Any front page (average) | ~50 unique visitors/min while on front page | marcotm.com rule of thumb |

**Key corrections to apply**:
- Ad-blocker correction: HN audience likely has 35–50% ad-blocker usage (vs. ~30% general web). Reported analytics undercount real visitors by ~1.5–2x.
- Dwell time: HN sends high-intent, low-bounce traffic. Average time-on-page is higher than typical referral traffic.
- Long-tail multiplier: Aggregator scrapers (hckrnews.com, brutalist.report, RSS readers) add 10–30% additional reach not captured in direct analytics.
- HN is approximately 10M pageviews/day across the whole site (2022 estimate), though YCombinator does not publish current figures.

### Step 2: Audience Valuation

The HN audience is structurally more valuable than generic tech traffic. Build an audience profile from available data:

**Audience characteristics** (use for CPM calibration):
- Heavily US/UK/Canada weighted (~75% English-speaking developed markets)
- ~75% male, 25–34 skewed (Similarweb on adjacent properties)
- High proportion of: software engineers, CTOs, founders, VCs, early adopters
- Early-adopter multiplier: HN readers are influencers within their organizations and peer networks — one HN reader may influence 5–20 downstream purchasing decisions

**CPM benchmarks by comparable audience** (use as upper/lower bounds):
- Generic display CPM: $3–7 (floor, not applicable)
- B2B tech programmatic CPM: $5–50 (wide range based on targeting specificity)
- LinkedIn CPM (director-level tech): $50–70 (strong comparable for HN's seniority mix)
- LinkedIn CPM (hyper-targeted, CMO/CTO level): $100–200
- B2B SaaS Google Search CPM equivalent: ~$50
- Developer-specific ad networks (e.g., Carbon Ads, BuySellAds tech): $30–80 CPM

**Recommended HN CPM equivalent**: $50–120 range, depending on story category:
- Developer tools / infrastructure: $80–120 (highest intent, closest to LinkedIn senior tech)
- General tech/startup: $50–80
- Non-technical/adjacent: $30–50

### Step 3: Build the AEV Model

```python
def advertising_equivalent_value(
    rank_position,          # 1–30
    hours_on_front_page,    # typically 2–20 hours
    story_category,         # 'dev_tools', 'general_tech', 'adjacent'
    include_longtail=True
):
    # Traffic model (fit to empirical data from Step 1)
    base_visitors = traffic_model(rank_position, hours_on_front_page)
    
    # Ad-blocker correction
    true_visitors = base_visitors * 1.4  # conservative 40% undercount
    
    # Long-tail aggregator reach
    aggregator_reach = true_visitors * 0.20 if include_longtail else 0
    total_reach = true_visitors + aggregator_reach
    
    # CPM equivalent by category
    cpm = {'dev_tools': 100, 'general_tech': 65, 'adjacent': 40}[story_category]
    
    # Impression value (pageviews, not just uniques)
    impressions = total_reach * 1.3  # ~1.3 pages per visitor on average
    impression_value = (impressions / 1000) * cpm
    
    # Influence multiplier: HN readers are early adopters who spread to peers
    # Conservative: each HN visitor influences 3 additional people
    # Aggressive: 10–20 (VC/founder tier)
    influence_multiplier = 3.0  # conservative
    influenced_reach = total_reach * influence_multiplier
    
    # Secondary CPM (lower, for downstream social/email spread)
    secondary_cpm = cpm * 0.3
    secondary_value = (influenced_reach / 1000) * secondary_cpm
    
    return {
        'direct_traffic': total_reach,
        'impression_value_usd': impression_value,
        'influenced_reach': influenced_reach,
        'secondary_value_usd': secondary_value,
        'total_aev_usd': impression_value + secondary_value
    }
```

### Step 4: Sensitivity Analysis

Run the model across a grid of scenarios and produce a results table:

| Scenario | Rank | Hours | Category | Direct AEV | w/ Influence |
|---|---|---|---|---|---|
| Best case | #1 | 20hr | dev_tools | ? | ? |
| Strong result | #3 | 12hr | dev_tools | ? | ? |
| Typical result | #10 | 6hr | general_tech | ? | ? |
| Marginal | #25 | 2hr | adjacent | ? | ? |

Also compute: **breakeven analysis** — what's the CPC equivalent? If a story at rank #5 drives 30,000 visitors, and developer CPC on LinkedIn is $8–15, the raw click-equivalent value is $240,000–$450,000. Compare this against display impression-based AEV to bound the estimate.

### Step 5: Validate Against Known Comparables

Cross-validate your AEV estimates against:
- Carbon Ads pricing (developer-specific ad network, public rates)
- A newsletter like TLDR or Hacker Newsletter (known CPM/sponsorship rates for developer audiences)
- Stack Overflow advertising rates (also developer audience, more comparable than LinkedIn)
- The sponsorship rate for a podcast like Software Engineering Daily

If your model's AEV is in a plausible range relative to these alternatives, it's well-calibrated.

---

## Deliverables

1. **Timing Analysis Report**: 
   - Prior studies comparison table
   - Replication results on current data
   - Improved model feature importances
   - Heatmap: P(front page) by hour-of-week (two versions: maximize probability vs. maximize reach)
   - Final recommendation: posting time by objective

2. **Advertising Value Report**:
   - Traffic prior table with sources
   - Audience profile summary with CPM calibration rationale
   - AEV model with sensitivity table
   - Breakeven analysis
   - Comparable benchmarks validation
   - Final estimate: range of AEV by scenario (low/mid/high)

3. **Combined Insight**:
   - Optimal posting time × AEV = **expected advertising value per submission**, as a function of hour-of-week and story type. This is the key synthesis: not just "when should I post" but "what is the expected dollar value of posting at time T vs. time T+6?"

---

## Methodological Notes & Caveats

- HN front-page placement is **not** a substitute for paid advertising in all respects. Paid ads have targeting, retargeting, and timing control. HN provides none of these but compensates with exceptionally high audience quality and zero direct cost.
- The influence multiplier is the most uncertain parameter in the model. It should be treated as a scenario variable, not a point estimate.
- YCombinator does not publish HN traffic statistics publicly. All traffic estimates are triangulated from self-reported anecdotes and are likely undercounts due to ad-blocker prevalence among the HN audience.
- The ranking algorithm is partially known from published Arc source code, but YC has stated it is continuously modified. Any model of the algorithm may become stale.
- Voting rings and rapid early upvotes trigger anti-gaming penalties. Do not use AEV estimates to justify coordinated upvoting — this will suppress the post.
- Story content quality dominates all timing and strategy effects. A weak story submitted at the optimal time will not outperform a strong story submitted at a suboptimal time.

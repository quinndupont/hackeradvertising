"""Phase 2: Advertising Equivalent Value model."""
from typing import Literal

StoryCategory = Literal["dev_tools", "general_tech", "adjacent"]


def traffic_model(rank_position: int, hours_on_front_page: float) -> float:
    """Base visitors from rank and hours. Fit to empirical priors."""
    # Priors: #1 50-100k, Top5 20-50k, Top10 10-30k, 11-30 3-10k
    # ~50 visitors/min while on front page (marcotm)
    rank_mult = {
        1: 75000, 2: 45000, 3: 35000, 4: 28000, 5: 22000,
        6: 18000, 7: 15000, 8: 13000, 9: 11000, 10: 10000,
    }
    if rank_position <= 10:
        base = rank_mult.get(rank_position, 10000)
    else:
        base = max(3000, 10000 - (rank_position - 10) * 500)
    # Scale by hours (diminishing: first hours matter most)
    hour_factor = min(hours_on_front_page / 8, 1.5)
    return base * hour_factor


def advertising_equivalent_value(
    rank_position: int,
    hours_on_front_page: float,
    story_category: StoryCategory,
    include_longtail: bool = True,
    influence_multiplier: float = 3.0,
    adblocker_correction: float = 1.4,
) -> dict:
    """Compute AEV for front-page placement. Set influence_multiplier=0 for direct-only."""
    base_visitors = traffic_model(rank_position, hours_on_front_page)
    true_visitors = base_visitors * adblocker_correction
    aggregator_reach = true_visitors * 0.20 if include_longtail else 0
    total_reach = true_visitors + aggregator_reach

    cpm = {"dev_tools": 100, "general_tech": 65, "adjacent": 40}[story_category]
    impressions = total_reach * 1.3
    impression_value = (impressions / 1000) * cpm

    influenced_reach = total_reach * influence_multiplier
    secondary_cpm = cpm * 0.3
    secondary_value = (influenced_reach / 1000) * secondary_cpm

    return {
        "direct_traffic": total_reach,
        "impression_value_usd": impression_value,
        "influenced_reach": influenced_reach,
        "secondary_value_usd": secondary_value,
        "total_aev_usd": impression_value + secondary_value,
    }


def sensitivity_table() -> list[dict]:
    """Produce AEV sensitivity table."""
    scenarios = [
        ("Best case", 1, 20, "dev_tools"),
        ("Strong result", 3, 12, "dev_tools"),
        ("Typical result", 10, 6, "general_tech"),
        ("Marginal", 25, 2, "adjacent"),
    ]
    rows = []
    for name, rank, hours, cat in scenarios:
        direct = advertising_equivalent_value(rank, hours, cat, influence_multiplier=0)
        direct_aev = direct["impression_value_usd"]
        full = advertising_equivalent_value(rank, hours, cat)
        rows.append({
            "Scenario": name,
            "Rank": f"#{rank}",
            "Hours": hours,
            "Category": cat,
            "Direct AEV": round(direct_aev, 0),
            "w/ Influence": round(full["total_aev_usd"], 0),
        })
    return rows


def breakeven_cpc_analysis(rank: int = 5, visitors: int = 30000) -> dict:
    """CPC equivalent: LinkedIn developer CPC $8-15."""
    low_cpc, high_cpc = 8, 15
    return {
        "visitors": visitors,
        "click_equivalent_low_usd": visitors * low_cpc,
        "click_equivalent_high_usd": visitors * high_cpc,
        "cpc_range": f"${low_cpc}-{high_cpc}",
    }

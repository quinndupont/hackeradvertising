"""Phase 2: Advertising value analysis pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from src.models.aev import (
    advertising_equivalent_value,
    sensitivity_table,
    breakeven_cpc_analysis,
)


def run_aev_analysis() -> None:
    """Run full Phase 2 pipeline."""
    print("--- AEV Sensitivity Table ---")
    rows = sensitivity_table()
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    print("\n--- Breakeven CPC Analysis ---")
    be = breakeven_cpc_analysis(rank=5, visitors=30000)
    print(f"Rank #5, 30k visitors: click-equivalent ${be['click_equivalent_low_usd']:,.0f}-${be['click_equivalent_high_usd']:,.0f}")

    print("\n--- AEV by Scenario (summary) ---")
    for row in rows:
        rank = int(str(row["Rank"]).replace("#", ""))
        aev = advertising_equivalent_value(rank, row["Hours"], row["Category"])
        print(f"{row['Scenario']}: ${aev['total_aev_usd']:,.0f} total AEV")


if __name__ == "__main__":
    run_aev_analysis()

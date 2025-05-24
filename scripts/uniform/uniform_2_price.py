import pandas as pd
import os

# Load supply info to get marginal costs
supply = pd.read_csv("data/supply_adjusted.csv")
supply["gen_id"] = supply["node"].astype(str) + "_" + supply["type"]

# Load demand data
demand = pd.read_csv("data/demand.csv")

# Scenario setup
scenarios = ["hs", "hw", "lwls"]
demand_levels = ["offpeak_demand", "average_demand", "peak_demand"]

EPSILON = 0.01  # tolerance to account for float imprecision

for scenario in scenarios:
    for level in demand_levels:
        print(f"\n--- Processing: {scenario} | {level} ---")

        dispatch_file = f"outputs/uniform_dispatch/dispatch_{scenario}_{level}.csv"
        if not os.path.exists(dispatch_file):
            print("⚠️ Missing dispatch file, skipping...")
            continue

        # Load dispatch results
        df = pd.read_csv(dispatch_file)
        df_gen = df[df["Category"] == "Generation"].copy()
        df_gen["gen_id"] = df_gen["Node"].astype(str) + "_" + df_gen["Type"]

        # Merge marginal costs from supply data
        df_merged = df_gen.merge(supply[["gen_id", "mc"]], on="gen_id", how="left")

        # Sort by marginal cost (ascending)
        df_sorted = df_merged.sort_values(by="mc").reset_index(drop=True)
        df_sorted["cumgen"] = df_sorted["Value"].cumsum()

        total_demand = demand[level].sum()

        # Identify clearing price: first generator where cumulative gen meets or exceeds demand
        df_above = df_sorted[df_sorted["cumgen"] >= total_demand - EPSILON]

        if df_above.empty:
            print(f"❌ No generator meets demand in: {scenario} | {level}")
            print(f"   Max cumulative generation: {df_sorted['cumgen'].max():.2f} MW")
            print(f"   Total demand: {total_demand:.2f} MW")
            continue

        clearing_row = df_above.iloc[0]
        clearing_price = clearing_row["mc"]

        print(f"✅ Clearing price: {clearing_price:.2f} €/MWh")

        # Calculate generator-level surplus
        df_sorted["ClearingPrice"] = clearing_price
        df_sorted["Surplus"] = (clearing_price - df_sorted["mc"]) * df_sorted["Value"]

        # Rename and tidy for output
        df_out = df_sorted[["Node", "Type", "Value", "mc", "ClearingPrice", "Surplus"]]
        df_out.columns = ["Node", "Type", "Generation", "MarginalCost", "ClearingPrice", "Surplus"]

        # === Add system-level totals ===
        total_paid = clearing_price * total_demand
        total_surplus = df_sorted["Surplus"].sum()

        print(f"💰 Total Paid Cost (initial): {total_paid:.2f} €")
        print(f"📈 Total Surplus: {total_surplus:.2f} €")

        system_rows = pd.DataFrame([
            {
                "Node": "System",
                "Type": "",
                "Generation": total_demand,
                "MarginalCost": "",
                "ClearingPrice": clearing_price,
                "Surplus": ""
            },
            {
                "Node": "System",
                "Type": "",
                "Generation": "",
                "MarginalCost": "",
                "ClearingPrice": "TotalPaid",
                "Surplus": total_paid
            },
            {
                "Node": "System",
                "Type": "",
                "Generation": "",
                "MarginalCost": "",
                "ClearingPrice": "TotalSurplus",
                "Surplus": total_surplus
            }
        ])

        # Append system summary to generator output
        df_out = pd.concat([df_out, system_rows], ignore_index=True)

        # Save to file
        os.makedirs("outputs/uniform_processed", exist_ok=True)
        df_out.to_csv(f"outputs/uniform_processed/results_{scenario}_{level}.csv", index=False)

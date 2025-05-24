import pandas as pd
import os

# Load supply info to get marginal costs
supply = pd.read_csv("data/supply_adjusted.csv")
supply["gen_id"] = supply["node"].astype(str) + "_" + supply["type"]

# Load demand data
demand = pd.read_csv("data/demand.csv")

# Scenario setup
scenario = "hs"
level = "peak_demand"
EPSILON = 0.01  # tolerance for float imprecision

print(f"\n--- Processing: {scenario} | {level} ---")

dispatch_file = f"outputs/sensitivity/uniform/dispatch_{scenario}_{level}.csv"
if not os.path.exists(dispatch_file):
    print("⚠️ Missing dispatch file, exiting...")
    exit()

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

# Identify clearing price
df_above = df_sorted[df_sorted["cumgen"] >= total_demand - EPSILON]

if df_above.empty:
    print(f"❌ No generator meets demand in: {scenario} | {level}")
    print(f"   Max cumulative generation: {df_sorted['cumgen'].max():.2f} MW")
    print(f"   Total demand: {total_demand:.2f} MW")
    exit()

clearing_row = df_above.iloc[0]
clearing_price = clearing_row["mc"]
total_paid = clearing_price * total_demand

print(f"✅ Clearing price: {clearing_price:.2f} €/MWh")

# Calculate surplus
df_sorted["ClearingPrice"] = clearing_price
df_sorted["Surplus"] = (clearing_price - df_sorted["mc"]) * df_sorted["Value"]
total_surplus = df_sorted["Surplus"].sum()

# Tidy output
df_out = df_sorted[["Node", "Type", "Value", "mc", "ClearingPrice", "Surplus"]]
df_out.columns = ["Node", "Type", "Generation", "MarginalCost", "ClearingPrice", "Surplus"]

# Append total paid and total surplus to output
summary_row = pd.DataFrame([{
    "Node": "TOTAL",
    "Type": "",
    "Generation": total_demand,
    "MarginalCost": "",
    "ClearingPrice": clearing_price,
    "Surplus": total_surplus
}])

df_out = pd.concat([df_out, summary_row], ignore_index=True)
df_out.to_csv(f"outputs/sensitivity/uniform/results_{scenario}_{level}.csv", index=False)

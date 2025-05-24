# script_d_redispatch.py
import pandas as pd
import os

# === Load static inputs ===
supply = pd.read_csv("data/supply_adjusted.csv")
demand = pd.read_csv("data/demand.csv")
lines = pd.read_csv("data/lines.csv")

supply["gen_id"] = supply["node"].astype(str) + "_" + supply["type"]
line_cap = {(row["from_node"], row["to_node"]): row["linecap"] for _, row in lines.iterrows()}

scenarios = ["hs", "hw", "lwls"]
demand_levels = ["offpeak_demand", "average_demand", "peak_demand"]
VRE = ["onshorewind", "offshorewind", "solar"]
STEP = 10
MAX_ITER = 1000

summary_rows = []

for scenario in scenarios:
    for level in demand_levels:
        print(f"\n--- Redispatch: {scenario} | {level} ---")

        vfile = f"outputs/uniform_violations/violations_{scenario}_{level.replace('_demand','')}.csv"
        dfile = f"outputs/uniform_dispatch/dispatch_{scenario}_{level}.csv"

        if not os.path.exists(vfile) or not os.path.exists(dfile):
            print("⚠️ Missing dispatch or violation file, skipping...")
            continue

        # === Load dispatch and prepare ===
        df = pd.read_csv(dfile)
        df = df[df["Category"] == "Generation"].copy()
        df["Node"] = df["Node"].astype(int)
        df["gen_id"] = df["Node"].astype(str) + "_" + df["Type"]
        df = df.merge(supply[["gen_id", "mc", "adjusted_capacity"]], on="gen_id", how="left")

        violations = pd.read_csv(vfile)
        exporting_nodes = set(violations["From"])
        importing_nodes = set(violations["To"])

        curtailment = 0
        redispatch_cost = 0

        for _ in range(MAX_ITER):
            changes = 0

            for node in exporting_nodes:
                vre_units = df[(df["Node"] == node) & (df["Type"].isin(VRE)) & (df["Value"] > 0)]
                vre_units = vre_units.sort_values("mc")
                for idx in vre_units.index:
                    reduce = min(STEP, df.at[idx, "Value"])
                    if reduce > 0:
                        df.at[idx, "Value"] -= reduce
                        curtailment += reduce
                        changes += 1
                        break

            for node in importing_nodes:
                conv_units = df[(df["Node"] == node) & (~df["Type"].isin(VRE))]
                conv_units = conv_units.sort_values("mc")
                for idx in conv_units.index:
                    room = df.at[idx, "adjusted_capacity"] - df.at[idx, "Value"]
                    increase = min(STEP, room)
                    if increase > 0:
                        df.at[idx, "Value"] += increase
                        redispatch_cost += increase * df.at[idx, "mc"]
                        changes += 1
                        break

            if changes == 0:
                break

        print(f"✅ Completed | Curtailment: {curtailment:.1f} MW | Redispatch Cost: {redispatch_cost:.2f} €")

        # === Save updated dispatch ===
        df_out = df[["Node", "Type", "Value"]].copy()
        df_out["Category"] = "Redispatch"
        df_out["Cost"] = df["mc"] * df["Value"]
        df_out.to_csv(f"outputs/uniform_redispatch/redispatch_{scenario}_{level}.csv", index=False)

        # === Economic Calculations ===
        adjusted_TEC = (df["Value"] * df["mc"]).sum()
        total_demand = demand[level].sum()
        
        result_file = f"outputs/uniform_processed/results_{scenario}_{level}.csv"
        if os.path.exists(result_file):
            result_df = pd.read_csv(result_file)
            clearing_prices = result_df["ClearingPrice"].dropna().unique()
            clearing_prices = [float(cp) for cp in clearing_prices if str(cp).replace('.', '', 1).isdigit()]
            if clearing_prices:
                clearing_price = clearing_prices[0]
            else:
                print(f"⚠️ No numeric clearing price found in {result_file}. Skipping...")
                continue
        else:
            print(f"⚠️ Clearing price file not found: {result_file}")
            continue

                # Load TPC (U1) from processed results
        init_paid = result_df[result_df["ClearingPrice"] == "TotalPaid"]["Surplus"].values
        if len(init_paid) == 0:
            print(f"⚠️ TotalPaid missing in {result_file}")
            continue
        tpc_u1 = float(init_paid[0])

        # Final Adjusted TPC and Surplus
        adjusted_TPC = tpc_u1 + redispatch_cost
        total_surplus = adjusted_TPC - adjusted_TEC

        marginal_cost_curtailment = (redispatch_cost / curtailment) if curtailment > 0 else ""

        # === Save to summary ===
        summary_rows.append({
            "Scenario": scenario,
            "DemandLevel": level,
            "Adjusted_TEC": round(adjusted_TEC, 2),
            "Adjusted_TPC": round(adjusted_TPC, 2),
            "Total_Surplus": round(total_surplus, 2),
            "Clearing_Price": round(clearing_price, 2),
            "Curtailment_MWh": curtailment,
            "Redispatch_Cost": round(redispatch_cost, 2),
            "Marginal_Cost_Curtailment": round(marginal_cost_curtailment, 2) if curtailment > 0 else ""
        })

# === Final Summary Output ===
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv("outputs/uniform_redispatch/summary_redispatch.csv", index=False)
print("\n📄 Redispatch summary saved to: outputs/redispatch_summary/summary_redispatch.csv")

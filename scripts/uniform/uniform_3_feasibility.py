import pandas as pd
import pyomo.environ as pyo
import os

# === Load static inputs ===
lines = pd.read_csv("data/lines.csv")
demand = pd.read_csv("data/demand.csv")

# Ensure node labels are consistent integers
lines["from_node"] = lines["from_node"].astype(int)
lines["to_node"] = lines["to_node"].astype(int)
demand["node"] = demand["node"].astype(int)

# Build line capacity dictionary
line_cap = {(row["from_node"], row["to_node"]): row["linecap"] for _, row in lines.iterrows()}
all_nodes = sorted(set(lines["from_node"]).union(set(lines["to_node"])))

scenarios = ["hs", "hw", "lwls"]
demand_levels = ["offpeak_demand", "average_demand", "peak_demand"]

for scenario in scenarios:
    for level in demand_levels:
        print(f"\n--- Feasibility Check: {scenario} | {level} ---")

        dispatch_file = f"outputs/uniform_dispatch/dispatch_{scenario}_{level}.csv"
        if not os.path.exists(dispatch_file):
            print("⚠️ Dispatch file missing, skipping...")
            continue

        # === Load dispatch results ===
        df = pd.read_csv(dispatch_file)
        df = df[df["Category"] == "Generation"].copy()  # Filter only generation rows
        df["Node"] = df["Node"].astype(int)             # Safe to cast now
        nodal_gen = df.groupby("Node")["Value"].sum().to_dict()

        # === Load nodal demand ===
        nodal_demand = dict(zip(demand["node"], demand[level]))

        # === Calculate net injections: Generation - Demand ===
        net_injection = {n: nodal_gen.get(n, 0) - nodal_demand.get(n, 0) for n in all_nodes}
        net_sum = sum(net_injection.values())
        print(f"🔍 Net injection balance: {net_sum:.4f} MW (should be ~0)")

        if abs(net_sum) > 1e-3:
            print("❌ Net injection imbalance too large. Skipping DC load flow.")
            continue
        else:
            # Correct minor imbalance if needed
            last_node = all_nodes[-1]
            net_injection[last_node] -= net_sum  # force balance

        # === Build DC Load Flow Model ===
        model = pyo.ConcreteModel()
        model.NODES = pyo.Set(initialize=all_nodes)
        model.LINES = pyo.Set(initialize=line_cap.keys(), dimen=2)

        model.theta = pyo.Var(model.NODES, domain=pyo.Reals)
        model.flow = pyo.Var(model.LINES, domain=pyo.Reals)

        # Slack bus: fix angle at first node
        slack_node = all_nodes[0]
        model.Slack = pyo.Constraint(expr=model.theta[slack_node] == 0)

        # DC flow: flow = angle difference
        def dc_flow_rule(m, i, j):
            return m.flow[(i, j)] == m.theta[i] - m.theta[j]
        model.DCFlow = pyo.Constraint(model.LINES, rule=dc_flow_rule)

        # Nodal power balance
        def nodal_balance_rule(m, n):
            inflow = sum(m.flow[(i, j)] for (i, j) in m.LINES if j == n)
            outflow = sum(m.flow[(i, j)] for (i, j) in m.LINES if i == n)
            return inflow - outflow == -net_injection[n]
        model.Balance = pyo.Constraint(model.NODES, rule=nodal_balance_rule)

        # Solve model
        solver = pyo.SolverFactory("glpk")
        results = solver.solve(model, tee=False)

        if results.solver.termination_condition != pyo.TerminationCondition.optimal:
            print("❌ Load flow model did not solve.")
            continue

                # === Check for violations ===
        violations = []
        for (i, j) in model.LINES:
            flow = pyo.value(model.flow[(i, j)])
            cap = line_cap[(i, j)]
            if abs(flow) > cap + 1e-3:
                violations.append({
                    "From": i,
                    "To": j,
                    "Flow": flow,
                    "Capacity": cap,
                    "Overload": abs(flow) - cap
                })

        if not violations:
            print("✅ No flow violations. Dispatch is feasible.")
        else:
            print(f"❗ {len(violations)} line violations detected.")
            for v in violations:
                print(f"  {v['From']} → {v['To']}: Flow = {v['Flow']:.1f} MW, Cap = {v['Capacity']} MW, Over = {v['Overload']:.1f} MW")

            # === Save violations to CSV ===
            df_v = pd.DataFrame(violations)
            os.makedirs("outputs/uniform_violations", exist_ok=True)
            safe_level = level.replace("_demand", "")  # e.g. "peak"
            filename = f"outputs/uniform_violations/violations_{scenario}_{safe_level}.csv"
            df_v.to_csv(filename, index=False)
            print(f"💾 Violations saved to: {filename}")

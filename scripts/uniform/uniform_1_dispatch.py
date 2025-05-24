import pandas as pd
import pyomo.environ as pyo
import os

# ========== 1. Load Data ==========
supply = pd.read_csv("data/supply_adjusted.csv")
demand = pd.read_csv("data/demand.csv")
weather = pd.read_csv("data/weatherprofiles.csv")

# ========== 2. Define Scenarios ==========
scenarios = ["hs", "hw", "lwls"]
demand_levels = ["offpeak_demand", "average_demand", "peak_demand"]
renewable_types = ["onshorewind", "offshorewind", "solar"]

# ========== 3. Loop Over All Scenario Combinations ==========
for scenario_name in scenarios:
    for demand_level in demand_levels:
        print(f"\n--- Solving Uniform Dispatch: {scenario_name} | {demand_level} ---")

        available_capacity = {}
        costs = {}
        for _, row in supply.iterrows():
            node = row["node"]
            tech = row["type"]
            base_cap = row["adjusted_capacity"]
            mc = row["mc"]

            if tech in renewable_types:
                prof = weather[(weather["scenario"] == scenario_name) & (weather["node"] == node)]
                multiplier = prof.iloc[0][f"{tech}_profile"] if not prof.empty else 0
            else:
                multiplier = 1

            cap = base_cap * multiplier
            available_capacity[(node, tech)] = cap
            costs[(node, tech)] = mc

        # Sum system-wide demand
        total_demand = demand[demand_level].sum()

        # ========== 4. Pyomo Model Setup ==========
        model = pyo.ConcreteModel()

        model.GENS = pyo.Set(initialize=available_capacity.keys(), dimen=2)
        model.p_gen = pyo.Var(model.GENS, domain=pyo.NonNegativeReals)

        def objective_rule(m):
            return sum(costs[g] * m.p_gen[g] for g in m.GENS)
        model.OBJ = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

        def demand_constraint(m):
            return sum(m.p_gen[g] for g in m.GENS) == total_demand
        model.DemandConstraint = pyo.Constraint(rule=demand_constraint)

        def gen_capacity_rule(m, n, tech):
            return m.p_gen[(n, tech)] <= available_capacity[(n, tech)]
        model.GenCapacity = pyo.Constraint(model.GENS, rule=gen_capacity_rule)

        solver = pyo.SolverFactory("glpk")
        results = solver.solve(model, tee=False)

        if results.solver.status != pyo.SolverStatus.ok or results.solver.termination_condition != pyo.TerminationCondition.optimal:
            print(f"WARNING: Solver failed for {scenario_name} | {demand_level}")

        # ========== 5. Output Dispatch ==========
        output = []
        for (n, t) in model.GENS:
            output.append({
                "Node": n,
                "Type": t,
                "Category": "Generation",
                "Value": pyo.value(model.p_gen[(n, t)])
            })

        output.append({
            "Node": "System",
            "Type": "",
            "Category": "TotalCost",
            "Value": pyo.value(model.OBJ)
        })

        df = pd.DataFrame(output)
        os.makedirs("outputs/uniform", exist_ok=True)
        df.to_csv(f"outputs/uniform_dispatch/dispatch_{scenario_name}_{demand_level}.csv", index=False)

total_demand = demand[demand_level].sum()
total_available = sum(available_capacity.values())

print(f"🧮 Demand: {total_demand:.1f} MW | Available Capacity: {total_available:.1f} MW")

# Optional: breakdown by tech
tech_sums = {}
for (n, t), cap in available_capacity.items():
    tech_sums[t] = tech_sums.get(t, 0) + cap
for t, total in tech_sums.items():
    print(f"  {t:<15}: {total:.1f} MW")

#note total system cost here is true economic cost of serving demand, not considering the price actually paid (but marginal cost)
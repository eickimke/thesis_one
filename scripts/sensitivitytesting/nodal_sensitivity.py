import pandas as pd
import pyomo.environ as pyo
import os

# ========== 1. Load Data ==========
supply = pd.read_csv("data/supply_adjusted.csv")
lines = pd.read_csv("data/lines_sensitivity.csv")
demand = pd.read_csv("data/demand.csv")
weather = pd.read_csv("data/weatherprofiles.csv")

# ========== 2. Scenario Setup ==========
scenario_name = "hs"
demand_level = "peak_demand"
renewable_types = ["onshorewind", "offshorewind", "solar"]

print(f"\n--- Solving: {scenario_name} | {demand_level} ---")

available_capacity = {}
costs = {}

# Adjust available capacity based on weather
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

# Line and demand inputs
line_cap = {(row["from_node"], row["to_node"]): row["linecap"] for _, row in lines.iterrows()}
nodal_demand = dict(zip(demand["node"], demand[demand_level]))

# ========== 3. Pyomo Model Setup ==========
model = pyo.ConcreteModel()
model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

model.NODES = pyo.Set(initialize=demand["node"].unique())
model.LINES = pyo.Set(initialize=line_cap.keys(), dimen=2)
model.GENS = pyo.Set(initialize=available_capacity.keys(), dimen=2)

model.p_gen = pyo.Var(model.GENS, domain=pyo.NonNegativeReals)
model.p_flow = pyo.Var(model.LINES, domain=pyo.Reals)
model.theta = pyo.Var(model.NODES, domain=pyo.Reals) 

# Objective: Minimize total system cost
def objective_rule(m):
    return sum(costs[g] * m.p_gen[g] for g in m.GENS)
model.OBJ = pyo.Objective(rule=objective_rule, sense=pyo.minimize)

# Nodal balance: gen + inflow - outflow = demand
def nodal_balance_rule(m, n):
    gen_sum = sum(m.p_gen[(n, tech)] for (node, tech) in m.GENS if node == n)
    inflow = sum(m.p_flow[(i, j)] for (i, j) in m.LINES if j == n)
    outflow = sum(m.p_flow[(i, j)] for (i, j) in m.LINES if i == n)
    return gen_sum + inflow - outflow == nodal_demand[n]
model.NodalBalance = pyo.Constraint(model.NODES, rule=nodal_balance_rule)

# Generator capacity limits
def gen_capacity_rule(m, n, tech):
    return m.p_gen[(n, tech)] <= available_capacity[(n, tech)]
model.GenCapacity = pyo.Constraint(model.GENS, rule=gen_capacity_rule)

# Line capacity limits
def line_capacity_rule_pos(m, i, j):
    return m.p_flow[(i, j)] <= line_cap[(i, j)]
def line_capacity_rule_neg(m, i, j):
    return m.p_flow[(i, j)] >= -line_cap[(i, j)]
model.LineCapacityPos = pyo.Constraint(model.LINES, rule=line_capacity_rule_pos)
model.LineCapacityNeg = pyo.Constraint(model.LINES, rule=line_capacity_rule_neg)

# DC Load Flow approximation
def dc_flow_rule(m, i, j):
    return m.p_flow[(i, j)] == m.theta[i] - m.theta[j]
model.DCFlow = pyo.Constraint(model.LINES, rule=dc_flow_rule)

# ========== 4. Solve ==========
solver = pyo.SolverFactory("glpk")
results = solver.solve(model, tee=False)

if results.solver.status != pyo.SolverStatus.ok or results.solver.termination_condition != pyo.TerminationCondition.optimal:
    print(f"WARNING: Solver failed for {scenario_name} | {demand_level}")

# ========== 5. Collect Outputs ==========
output = []

for (n, t) in model.GENS:
    gen_value = pyo.value(model.p_gen[(n, t)])
    lmp = model.dual.get(model.NodalBalance[n], 0)
    mc = costs[(n, t)]
    surplus = (lmp - mc) * gen_value

    output.append({"Node": n, "Type": t, "Category": "Generation", "Value": gen_value})
    output.append({"Node": n, "Type": t, "Category": "Surplus", "Value": surplus})

for (i, j) in model.LINES:
    flow = pyo.value(model.p_flow[(i, j)])
    output.append({"Node": i, "Type": f"to_{j}", "Category": "Flow", "Value": flow})

for n in model.NODES:
    theta_val = pyo.value(model.theta[n])
    lmp_val = model.dual.get(model.NodalBalance[n], None)
    output.append({"Node": n, "Type": "", "Category": "LMP", "Value": lmp_val})
    output.append({"Node": n, "Type": "", "Category": "Angle", "Value": theta_val})

# === Total Paid and Surplus ===
total_paid = sum(
    model.dual.get(model.NodalBalance[n], 0) * pyo.value(model.p_gen[(n, t)])
    for (n, t) in model.GENS
)

total_cost = pyo.value(model.OBJ)
total_surplus = total_paid - total_cost

output.append({"Node": "System", "Type": "", "Category": "TotalPaid", "Value": total_paid})
output.append({"Node": "System", "Type": "", "Category": "TotalSurplus", "Value": total_surplus})


output.append({"Node": "System", "Type": "", "Category": "TotalCost", "Value": pyo.value(model.OBJ)})

# Save results
df = pd.DataFrame(output)
os.makedirs("outputs/nodal", exist_ok=True)
df.to_csv(f"outputs/sensitivity/nodal/{scenario_name}_{demand_level}.csv", index=False)

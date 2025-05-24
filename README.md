# Nodal Pricing and Market Efficiency in the German Power System

This repository contains all model code, input data, and output results used in the master's thesis:

**“Locational Pricing for the Energy Transition: Evaluating Nodal Market Design in the German Power System”**

The thesis investigates whether locational marginal pricing can improve market efficiency and VRE integration in Germany compared to the current uniform pricing regime. A stylised 6-node Python model is used to simulate and compare dispatch outcomes across multiple scenarios.

---

## Repository Structure

```
/data/                → Input datasets (demand, weatherprofiles, adjusted generation capacities, line capacities, sensitivity testing lines)
/outputs/             → Model results by scenario and pricing regime
/scripts/             → Python scripts for running the model
/requirements.txt     → Python package dependencies
/README.md            → Project documentation (this file)
```

---

## Getting Started

### Prerequisites

- Python 3.10 or later
- GLPK (GNU Linear Programming Kit)

### Install Dependencies

To install required Python packages:

```bash
pip install -r requirements.txt
```

### GLPK Installation

GLPK is required to solve the optimisation problem via Pyomo. It must be installed separately and be available on your system path.

#### macOS:
```bash
brew install glpk
```

#### Windows:
```bash
choco install glpk
```

#### Linux (Debian/Ubuntu):
```bash
sudo apt-get install glpk-utils
```

---

## Running the Model

This project includes three main modelling tracks:
- **Nodal pricing simulation**
- **Uniform pricing simulation with redispatch**
- **Sensitivity testing for transmission capacities**

### Nodal Pricing

Run the nodal model using:

```bash
python scripts/nodal/nodalmodel.py
```

Results are saved to:

```
/outputs/nodal/
```

### Uniform Pricing (Stepwise)

The uniform model requires a step-by-step run of four scripts in order:

```bash
python scripts/uniform/uniform_1_dispatch.py     # Initial dispatch
python scripts/uniform/uniform_2_price.py     # Clearing Price Calculation
python scripts/uniform/uniform_3_feasibility.py     # DC Load Flow Model Feasibility Check
python scripts/uniform/uniform_4_redispatch.py     # Heuristic Redispatch
```

Each script builds on the previous step. Outputs are saved into the following directories:

```
/outputs/uniform_dispatch/
/outputs/uniform_violations/
/outputs/uniform_redispatch/
/outputs/uniform_processed/
```

### 📉 Sensitivity Testing

Sensitivity testing scripts are stored under `/scripts/sensitivitytesting/`.

- Nodal sensitivity test:
```bash
python scripts/sensitivitytesting/nodal_sensitivity.py
```

- Uniform sensitivity tests (run in order):
```bash
python scripts/sensitivitytesting/uniform_sens_1.py
python scripts/sensitivitytesting/uniform_sens_2.py
python scripts/sensitivitytesting/uniform_sens_3.py
python scripts/sensitivitytesting/uniform_sens_4.py
```

Results from sensitivity testing are saved in:

```
/outputs/sensitivity/
```

The main nodal and uniform scripts are structured as scenario loops and use predefined input files located in `/data/`. These can be adjusted directly to run alternative cases. The sensitivity scripts run single scenarios, which can similarly be customised by modifying the input data or parameters within each file.

---

## 📊 Results & Output Tables

The raw data underlying thesis Tables 6–18 (e.g. system cost, redispatch, generator surplus, LMPs) is available in:

```
/outputs/nodal/
/outputs/uniform_processed/
/outputs/sensitivity/
```

These outputs are structured by scenario. Tables used in the thesis were compiled manually from these raw results.

---

## 📂 Data Sources

Input data is drawn from public sources:

- **Renewables.Ninja**: Weather profiles 
    https://www.renewables.ninja 

- **SMARD.de** (Bundesnetzagentur): Net generation capacity (Kraftwerksliste)
  https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/Versorgungssicherheit/Erzeugungskapazitaeten/Kraftwerksliste/start.html

-**EWI Merit Order Tool**: Marginal cost estimates and capacity outage factors
    https://www.ewi.uni-koeln.de/de/publikationen/ewi-merit-order-tool-2023/ 

For full source documentation, see Chapter 4 of the thesis.

---

## 🗺 Geographic Plots

The Germany map outline used for visualisations is sourced from **Natural Earth** (public domain):  
https://www.naturalearthdata.com

Due to licensing caution, the file is not included. You may download a shapefile or GeoJSON from the above link and place it in `/scripts/graphs/`.

---

## 🧾 Citation

If using this repository or model in your own work, please cite the original thesis:

> [Imke Eickholt] (2025). *Locational Pricing for the Energy Transition: Evaluating Nodal Market Design in the German Power System.* [Lund University]. MSc Economics Masters Essay.

---

## 📬 Contact

Imke Eickholt 
eickimke@gmail.com
---

## 📄 License

This repository is shared for academic and educational purposes. Please contact the author for reuse or modification beyond non-commercial use.

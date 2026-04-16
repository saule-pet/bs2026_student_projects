# ⚛️ CERN Open Data Explorer

![CERN Open Data Explorer Hero](./assets/hero.png)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CERN Open Data](https://img.shields.io/badge/Data-opendata.cern.ch-blue)](https://opendata.cern.ch/)

**CERN Open Data Explorer** is a professional-grade interactive dashboard designed for the exploration and analysis of authentic particle physics datasets from the LHC (Large Hadron Collider). It bridges the gap between raw scientific data and intuitive visualization, enabling researchers and students to "rediscover" fundamental particles like the $J/\psi$, $\Upsilon$, and $Z$ bosons.

---

## 🚀 Key Features

*   **⚡ High-Performance Analysis**: Leveraging [Polars](https://pola.rs/) for lightning-fast columnar processing of millions of collision events.
*   **🌐 Real-time CERN Portal Integration**: Search and stream datasets directly from the `opendata.cern.ch` API.
*   **📊 Publication-Quality Graphics**: Integrated Matplotlib engine for generating high-DPI (300) histograms suitable for scientific publication.
*   **🧊 3D Event Visualization**: Native browser-based 3D momentum vector displays and event-by-event animations using Plotly.
*   **🕵️ Deep ROOT/DST Inspection**: Advanced diagnostic tools to peer into the nested structure of complex High Energy Physics (HEP) objects via [Uproot](https://uproot.readthedocs.io/).
*   **📝 LHCb Macro Generator**: Automated generation of DaVinci/Gaudi configuration code for CERN GRID processing.

---

## 🛠️ Technology Stack

| Component | Technology |
| :--- | :--- |
| **Frontend/Dashboard** | [Streamlit](https://streamlit.io/) |
| **Data Processing** | [Polars](https://pola.rs/), [NumPy](https://numpy.org/), [Awkward Array](https://awkward-array.org/) |
| **HEP Integration** | [Uproot 5](https://uproot.readthedocs.io/), XRootD |
| **Visualization** | [Plotly](https://plotly.com/), [Matplotlib](https://matplotlib.org/) |
| **Package Management** | [Pixi](https://pixi.sh/) |

---

## 🏁 Getting Started

### Prerequisites

*   [Pixi](https://pixi.sh/) (Conda-compatible package manager)
*   Python 3.11+

### Installation

Clone the repository and install dependencies using Pixi:

```bash
pixi install
```

### Running the Application

Launch the Streamlit dashboard:

```bash
pixi run streamlit run main.py
```

---

## 📂 Project Structure

```text
.
├── assets/             # Brand assets and images
├── data/               # Local cache for CERN datasets
├── pages/              # Streamlit dashboard modules
│   ├── 1_Analysis.py      # Core physics analysis engine
│   ├── 2_CernExplorer.py  # Portal search & streaming
│   └── 3_Macro_Generator.py # LHCb DaVinci code generation
├── scripts/            # Modular research tools
│   ├── analysis/          # Scientific plotting modules
│   ├── exploration/       # ROOT/DST deep inspection
│   └── davinci_macros/    # Gaudi/DaVinci templates
└── main.py             # Application entry point
```

---

## 🧪 Scientific Validation

The analysis logic follows standard HEP workflows for Dimuon resonance reconstruction. Invariant mass calculation ($M$) is performed using the relativistic 4-momentum formula:

$$M = \sqrt{(E_1+E_2)^2 - \|\vec{p}_1 + \vec{p}_2\|^2}$$

Validation against PDG (Particle Data Group) values is integrated into the "Publication Export" module.

## 👨‍🔬 Author

**Vytas Mulevicius**  
*Lead Developer & Physics Enthusiast*  
[GitHub Profile](https://github.com/VytasMule) | [LinkedIn](https://www.linkedin.com/in/vytasmule/)

---

## 🤝 Contributing

We welcome contributions from the particle physics and software engineering communities! Please see our `CONTRIBUTING.md` (coming soon) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

*   **CERN Open Data Group** for providing authentic LHC collision data.
*   **Scikit-HEP** developers for the amazing tools like Uproot and Awkward Array.
*   Academic institutions for supporting Open Science.

---

<p align="center">
  <i>Empowering the next generation of particle physicists.</i><br>
  <b>Open Science | Open Data | Open Progress</b>
</p>
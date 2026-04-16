import streamlit as st
from scripts.ui_utils import apply_branding

st.set_page_config(
    page_title="CERN Explorer | Home",
    page_icon="⚛️",
    layout="wide"
)

# Apply unified enterprise branding
apply_branding()

st.write("# ⚛️ CERN Open Data Explorer")

st.markdown(r"""
Welcome to the professional-grade portal for High Energy Physics exploration. 
This application provides researchers and students with direct access to authentic collision data 
released by the **CMS Experiment** at CERN.

---

### 🚀 Exploration Modules

| Module | Description |
| :--- | :--- |
| **⚛️ Analysis** | Perform invariant mass reconstruction and 3D momentum visualization. |
| **🔍 CERN Explorer** | Live search and streaming from the opendata.cern.ch API. |
| **📝 Macro Generator** | Export DaVinci/Gaudi processing macros for CERN GRID jobs. |

---

### 👈 Getting Started
To begin your interactive physics analysis, **select a module from the sidebar menu to the left.**

Using these tools, you can "rediscover" fundamental particles like the $J/\psi$, $\Upsilon$, and $Z$ bosons by analyzing dimuon pairs ($\mu^+\mu^-$) from Run 2011A.
""")


st.info("💡 **Navigation:** Use the sidebar on the left to switch between modules.")

# Sidebar Footer
# Credits are now handled by apply_branding()

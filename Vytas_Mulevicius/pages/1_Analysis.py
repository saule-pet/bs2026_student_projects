import streamlit as st
import polars as pl
import numpy as np
import plotly.graph_objects as go
import os
from scripts.download_data import get_datasets, download_dataset
from scripts.analysis.plot_mass import generate_publication_plot
from scripts.exploration.inspect_root import get_root_structure, get_branch_details
from scripts.ui_utils import apply_branding

st.set_page_config(page_title="CERN Explorer | Analysis", page_icon="⚛️", layout="wide")

# Apply unified enterprise branding
apply_branding()

# Select Dataset
st.sidebar.header("Dataset Selection")

# Scan data directory for files
if not os.path.exists('data'):
    os.makedirs('data', exist_ok=True)

available_files = sorted([f for f in os.listdir('data') if f.endswith(('.csv', '.root'))])

# Metadata for known datasets
known_metadata = {
    "Jpsimumu_Run2011A.csv": {"display": "J/ψ → μμ (2011A)", "min": 2.0, "max": 5.0, "mass": 3.096, "name": "J/ψ"},
    "Zmumu_Run2011A.csv": {"display": "Z → μμ (2011A)", "min": 70.0, "max": 110.0, "mass": 91.1876, "name": "Z"},
    "Ymumu_Run2011A.csv": {"display": "Υ → μμ (2011A)", "min": 8.0, "max": 12.0, "mass": 9.460, "name": "Υ"},
    "Wenu.csv": {"display": "W → eν (Electron)", "min": 0.0, "max": 120.0, "mass": 80.38, "name": "W"},
    "Wmunu.csv": {"display": "W → μν (Muon)", "min": 0.0, "max": 120.0, "mass": 80.38, "name": "W"}
}

# Build selection list
display_options = []
file_map = {}

for f in available_files:
    label = known_metadata[f]["display"] if f in known_metadata else f"📦 Custom: {f}"
    display_options.append(label)
    file_map[label] = f

data_source = st.sidebar.radio("Data Source", ["Local Storage", "Remote Stream (XRootD/HTTP)"])

if data_source == "Local Storage":
    if not available_files:
        st.warning("📂 No datasets found. Go to the **Explorer** page to download data!")
        st.stop()
        
    dataset_choice = st.sidebar.selectbox("Choose a local dataset", display_options)
    selected_file = file_map[dataset_choice]
else:
    # Support for streaming from session state if coming from Explorer page
    initial_url = st.session_state.get('stream_url', "")
    selected_file = st.sidebar.text_input("Enter ROOT/CSV URL", value=initial_url, placeholder="root://eospublic.cern.ch//eos/...")
    if not selected_file:
        st.info("💡 **Tip:** Go to the **Explorer** page and click 'Stream' on a dataset, or paste a URL here.")
        st.stop()

# Extract metadata
is_root = selected_file.lower().split('?')[0].endswith('.root') or selected_file.startswith('root://')
fname_for_meta = selected_file.split('/')[-1].split('?')[0]
default_particle = fname_for_meta.replace('.root', '').replace('.csv', '').split('_')[0]

if fname_for_meta in known_metadata:
    mdata = known_metadata[fname_for_meta]
    default_min, default_max, expected_mass, particle_name = mdata["min"], mdata["max"], mdata["mass"], mdata["name"]
else:
    default_min, default_max, expected_mass, particle_name = 0.0, 120.0, 0.0, default_particle

st.title(f"{particle_name} Physical Analysis")
if data_source == "Remote Stream (XRootD/HTTP)":
    st.caption(f"🌐 Streaming from: `{selected_file}`")
st.markdown(f"""
Exploring authentic CERN Open Data. For CSVs, we use Polars for speed. 
For **ROOT/DST** files, we use **Uproot** to extract columnar data directly into the analysis pipeline.
""")

# Check if data exists
if data_source == "Local Storage":
    data_path = f'data/{selected_file}'
    if not os.path.exists(data_path):
        st.warning(f"⚠️ Dataset **{selected_file}** not found locally.")
        if st.button("Download Required Datasets", type="primary"):
            datasets = get_datasets()
            os.makedirs('data', exist_ok=True)
            with st.status("Downloading datasets from CERN...", expanded=True) as status:
                for filename, url in datasets.items():
                    st.write(f"Downloading {filename}...")
                    download_dataset(url, os.path.join('data', filename))
                status.update(label="✅ Download complete!", state="complete", expanded=False)
            st.success("Data downloaded successfully! Refreshing...")
            st.rerun()
        st.stop()

# Load Data
@st.cache_data
def load_data(path):
    if path.lower().split('?')[0].endswith('.csv'):
        return pl.read_csv(path)
    elif path.lower().split('?')[0].endswith('.root') or path.startswith('root://'):
        import uproot
        import awkward as ak
        with uproot.open(path) as f:
            # Recursively find all items that have 'arrays' (i.e. are Trees)
            all_trees = [k for k, v in f.items(recursive=True) if hasattr(v, "arrays")]
            
            if not all_trees:
                st.error(f"No TTree found in {path}")
                st.stop()
            
            # Prefer trees that match common naming conventions (Events, DecayTree, mini, tree)
            # This handles cases like 'JpsiTuple/DecayTree' correctly.
            tree_name = next((k for k in all_trees if any(p in k for p in ('Events', 'DecayTree', 'mini', 'tree'))), all_trees[0])
            
            st.info(f"📍 Loading tree: `{tree_name}`")
            tree = f[tree_name]
            
            # Convert to Arrow Table first (most robust path to Polars)
            ak_array = tree.arrays()
            arrow_table = ak.to_arrow_table(ak_array, extensionarray=False)
            return pl.from_arrow(arrow_table)

with st.spinner(f"Loading {selected_file}..."):
    # Ensure local files are loaded from the 'data/' directory
    path_to_load = f"data/{selected_file}" if data_source == "Local Storage" else selected_file
    df = load_data(path_to_load)

# --- NEW: Data Diagnostics ---
with st.expander("🔍 Raw Data Diagnostic Inspect"):
    st.write(f"Total Events: {len(df)}")
    st.write("Column Names:", df.columns)
    st.dataframe(df.head(5))
# -----------------------------

st.sidebar.header("Plot Settings")
bins = st.sidebar.slider("Number of Bins", min_value=10, max_value=500, value=200, step=10)
mass_range = st.sidebar.slider(
    "Invariant mass range [GeV/c²]", 
    min_value=float(default_min - 10), max_value=float(default_max + 10), 
    value=(default_min, default_max), step=0.1
)

# Advanced filtering features
st.sidebar.header("Kinematic Cuts")
pt_min = st.sidebar.slider("Minimum Muon pT [GeV/c]", 0.0, 50.0, 0.0, 0.5)
eta_max = st.sidebar.slider("Maximum Muon |η|", 0.0, 3.0, 2.4, 0.1)
require_opposite_charge = st.sidebar.checkbox("Require Opposite Charge (Q1 + Q2 = 0)", value=True)

# --- NEW: Advanced File Diagnostic Tool ---
st.sidebar.markdown("---")
st.sidebar.header("🛠️ File Tools")
if st.sidebar.checkbox("Show Deep File Inspector"):
    st.subheader("🕵️ Deep ROOT/CSV Inspector")
    path_to_inspect = f"data/{selected_file}" if data_source == "Local Storage" else selected_file
    
    if is_root:
        struct = get_root_structure(path_to_inspect)
        if "error" in struct:
             st.error(struct["error"])
        else:
            tree_to_inspect = st.selectbox("Select Tree to explore branches", list(struct.keys()))
            if tree_to_inspect:
                details = get_branch_details(path_to_inspect, tree_to_inspect)
                st.write(f"**Found {len(details)} branches in `{tree_to_inspect}`:**")
                st.dataframe(details)
    else:
        st.info("Directly inspecting CSV schema via Polars:")
        st.write(df.schema)

# Calculate Invariant Mass and apply cuts dynamically based on available columns
cols = df.columns

# Heuristic mapping for different experiment formats
# CMS: pt1, pt2, eta1, eta2...
# ATLAS: lep_pt, lep_eta, lep_phi (usually jagged lists)
# LHCb: muplus_PX, muminus_PX, Bplus_MM...

if 'muplus_PX' in cols and 'muminus_PX' in cols:
    st.info("💡 **Format Detected:** LHCb NTuple. Mapping particle branches...")
    with st.spinner("Refactoring LHCb columnar data..."):
        # Map muons safely (LHCb is in MeV, we want GeV)
        mapping = {
            'muplus_PX': 'px1', 'muplus_PY': 'py1', 'muplus_PZ': 'pz1', 'muplus_PT': 'pt1',
            'muminus_PX': 'px2', 'muminus_PY': 'py2', 'muminus_PZ': 'pz2', 'muminus_PT': 'pt2'
        }
        for old_name, new_name in mapping.items():
            if old_name in df.columns:
                df = df.with_columns((pl.col(old_name) / 1000.0).alias(new_name))
        
        # Ensure we have Energies for Cartesian mass calculation
        if 'muplus_PE' in cols:
            df = df.with_columns((pl.col('muplus_PE') / 1000.0).alias('E1'))
        if 'muminus_PE' in cols:
            df = df.with_columns((pl.col('muminus_PE') / 1000.0).alias('E2'))
        
        if 'E1' not in df.columns or 'E2' not in df.columns:
            m_mu = 0.105658
            # Values are already in GeV now if they were aliased above
            if 'E1' not in df.columns:
                df = df.with_columns(((pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2 + m_mu**2).sqrt()).alias('E1'))
            if 'E2' not in df.columns:
                df = df.with_columns(((pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2 + m_mu**2).sqrt()).alias('E2'))
            
        # Calculate Eta if missing (standard LHCb tuples don't always have it)
        if 'eta1' not in df.columns:
            df = df.with_columns([
                (pl.col('pz1') / (pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2).sqrt()).clip(-0.999, 0.999).arctanh().alias('eta1'),
                (pl.col('pz2') / (pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2).sqrt()).clip(-0.999, 0.999).arctanh().alias('eta2')
            ])
        
        # Charge mapping if exists
        if 'muplus_ID' in cols:
             # In PDG, mu- is 13, mu+ is -13. So muplus_ID -13, muminus_ID 13.
             df = df.with_columns([
                 pl.col('muplus_ID').alias('Q1'),
                 pl.col('muminus_ID').alias('Q2')
             ])
        
        # If the file has a parent mass (like Bplus_MM), rename it to Calculated_M to bypass manual math
        # but only if it's the target particle.
        parent_mass_col = next((c for c in cols if c.endswith(('_MM', '_M')) and not any(p in c for p in ('muplus', 'muminus', 'Kplus'))), None)
        if parent_mass_col:
            st.success(f"💎 **High Precision Branch Found:** Using `{parent_mass_col}` (converted to GeV) for mass distribution.")
            df = df.with_columns((pl.col(parent_mass_col) / 1000.0).alias('Calculated_M'))
            
        cols = df.columns

if 'lep_pt' in cols and 'lep_eta' in cols:
    # ATLAS Open Data format - extract first two leptons and convert MeV -> GeV
    with st.spinner("Extracting ATLAS leptons and converting MeV -> GeV..."):
        df = df.with_columns([
            (pl.col('lep_pt').list.get(0) / 1000.0).alias('pt1'),
            (pl.col('lep_pt').list.get(1) / 1000.0).alias('pt2'),
            pl.col('lep_eta').list.get(0).alias('eta1'),
            pl.col('lep_eta').list.get(1).alias('eta2'),
            pl.col('lep_phi').list.get(0).alias('phi1'),
            pl.col('lep_phi').list.get(1).alias('phi2'),
        ])
        if 'lep_E' in cols:
            df = df.with_columns([
                (pl.col('lep_E').list.get(0) / 1000.0).alias('E1'),
                (pl.col('lep_E').list.get(1) / 1000.0).alias('E2')
            ])
        if 'met_et' in cols:
            df = df.with_columns([
                (pl.col('met_et') / 1000.0).alias('met'),
                pl.col('met_phi').alias('met_phi_val')
            ])
        if 'lep_charge' in cols:
             df = df.with_columns([
                pl.col('lep_charge').list.get(0).alias('Q1'),
                pl.col('lep_charge').list.get(1).alias('Q2')
            ])
        # Update cols list after the mapping
        cols = df.columns
        # Clean up events that don't have at least two leptons (to avoid null math)
        df = df.drop_nulls(subset=['pt1', 'pt2'])

if 'E1' in cols and 'px1' in cols:
    # Cartesian Data
    df = df.with_columns([
        (pl.col('E1') + pl.col('E2')).alias('E_tot'),
        (pl.col('px1') + pl.col('px2')).alias('px_tot'),
        (pl.col('py1') + pl.col('py2')).alias('py_tot'),
        (pl.col('pz1') + pl.col('pz2')).alias('pz_tot')
    ])
    df = df.with_columns(
        ((pl.col('E_tot')**2 - (pl.col('px_tot')**2 + pl.col('py_tot')**2 + pl.col('pz_tot')**2)).clip(lower_bound=0).sqrt()).alias('Calculated_M')
    )
elif 'pt1' in cols and 'eta1' in cols:
    # Transverse Data
    m_mu = 0.105658
    df = df.with_columns([
        (pl.col('pt1') * pl.col('phi1').cos()).alias('px1'),
        (pl.col('pt1') * pl.col('phi1').sin()).alias('py1'),
        (pl.col('pt1') * pl.col('eta1').sinh()).alias('pz1'),
    ])
    df = df.with_columns(
        ((pl.col('px1')**2 + pl.col('py1')**2 + pl.col('pz1')**2 + m_mu**2).sqrt()).alias('E1')
    )
    
    df = df.with_columns([
        (pl.col('pt2') * pl.col('phi2').cos()).alias('px2'),
        (pl.col('pt2') * pl.col('phi2').sin()).alias('py2'),
        (pl.col('pt2') * pl.col('eta2').sinh()).alias('pz2'),
    ])
    df = df.with_columns(
        ((pl.col('px2')**2 + pl.col('py2')**2 + pl.col('pz2')**2 + m_mu**2).sqrt()).alias('E2')
    )
    
    df = df.with_columns([
        (pl.col('E1') + pl.col('E2')).alias('E_tot'),
        (pl.col('px1') + pl.col('px2')).alias('px_tot'),
        (pl.col('py1') + pl.col('py2')).alias('py_tot'),
        (pl.col('pz1') + pl.col('pz2')).alias('pz_tot')
    ])
    
    df = df.with_columns(
        ((pl.col('E_tot')**2 - (pl.col('px_tot')**2 + pl.col('py_tot')**2 + pl.col('pz_tot')**2)).clip(lower_bound=0).sqrt()).alias('Calculated_M')
    )
elif 'pt' in cols and 'MET' in cols:
    # Single Lepton + MET (W Boson)
    st.info("💡 **Format Detected:** Single-particle event with Missing Transverse Energy (MET). Calculating **Transverse Mass ($M_T$)**.")
    df = df.with_columns(
        ( (2 * pl.col('pt') * pl.col('MET') * (1 - (pl.col('phi') - pl.col('phiMET')).cos())).sqrt() ).alias('Calculated_M')
    )
else:
    # If M is already in the dataset, use it!
    if 'M' in cols:
        df = df.with_columns(pl.col('M').alias('Calculated_M'))
    else:
        st.error(f"Dataset columns {cols} are not recognized for invariant mass calculation.")
        st.stop()

# Auto-update label for MT
mass_label = "Transverse Mass ($M_T$)" if 'MET' in cols else "Invariant Mass"

# Apply Kinematic Filtering Cuts
filter_exprs = [
    (pl.col('Calculated_M') >= mass_range[0]) & (pl.col('Calculated_M') <= mass_range[1])
]

# Check for single vs multi particle for kinematic cuts
if 'pt1' in cols:
    filter_exprs.append((pl.col('pt1') >= pt_min) & (pl.col('pt2') >= pt_min))
    filter_exprs.append((pl.col('eta1').abs() <= eta_max) & (pl.col('eta2').abs() <= eta_max))
elif 'pt' in cols:
    filter_exprs.append(pl.col('pt') >= pt_min)
    filter_exprs.append(pl.col('eta').abs() <= eta_max)

if require_opposite_charge and 'Q1' in df.columns and 'Q2' in df.columns:
    filter_exprs.append(pl.col('Q1') != pl.col('Q2'))

# Apply all filters
for expr in filter_exprs:
    df = df.filter(expr)

# Materialize to pandas for easier downstream Plotly plotting within Streamlit right now
filtered_df = df.to_pandas()

# --- NEW: Data Diagnostics (Filtered) ---
with st.expander("🔍 Data Diagnostic Inspect", expanded=False):
    st.write(f"**Total Initial Events:** {len(df) + (len(df) - len(filtered_df) if 'filtered_df' in locals() else 0)}") # Rough estimate
    st.write(f"**Events Passing Filters:** {len(filtered_df)}")
    if len(filtered_df) > 0:
        st.write("Mapped Columns Preview (GeV):")
        cols_to_show = [c for c in ['pt1', 'pt2', 'eta1', 'eta2', 'Calculated_M'] if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_to_show].head(5))
    else:
        st.warning("⚠️ No events passed your current filters. Try loosening your Kinematic Cuts or widening the Mass Range in the sidebar.")
# -----------------------------

view_mode = st.radio("Select View:", ["Mass Histogram", "3D Event Display", "3D Event Animation"])

if view_mode == "Mass Histogram":
    st.subheader(f"Invariant Mass Distribution ({particle_name} → μμ)")
    
    # Create interactive Plotly figure
    counts, bin_edges = np.histogram(filtered_df['Calculated_M'], bins=bins, range=mass_range)
    
    fig = go.Figure()
    
    # Add histogram bars
    fig.add_trace(go.Bar(
        x=bin_edges[:-1],
        y=counts,
        width=np.diff(bin_edges),
        offset=0,
        marker_color='royalblue',
        marker_line_width=0,
        name='Events',
        hovertemplate=f"{mass_label}: %{{x:.3f}} - %{{customdata:.3f}} GeV/c²<br>Events: %{{y}}<extra></extra>",
        customdata=bin_edges[1:]
    ))
    
    # Add expected mass marker
    fig.add_vline(
        x=expected_mass, 
        line_width=2, 
        line_dash='dash', 
        line_color='red'
    )
    
    # Add a dummy scatter trace for the legend entry of the expected mass
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color='red', width=2, dash='dash'),
        name=f'{particle_name} Mass ({expected_mass:.3f} GeV/c²)'
    ))
    
    # Update layout
    fig.update_layout(
        title=f'{mass_label} of Events ({particle_name})',
        xaxis_title=f'{mass_label} [GeV/c²]',
        yaxis_title='Number of Events',
        bargap=0,
        hovermode='x unified',
        template='plotly_white',
        height=600,
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    
    st.plotly_chart(fig, width='stretch')
    
    # --- NEW: Publication Quality Plot Export ---
    st.markdown("---")
    st.subheader("🎓 Publication Export")
    st.caption("Generate a high-DPI static plot using Matplotlib (legacy engine integration).")
    if st.button("Generate Publication-Ready Plot"):
        with st.spinner("Rendering high-res PNG..."):
            plot_buf = generate_publication_plot(
                filtered_df, 
                particle_name=particle_name, 
                expected_mass=expected_mass,
                mass_range=mass_range
            )
            st.image(plot_buf, caption=f"High-Res {particle_name} Histogram (300 DPI)")
            st.download_button(
                label="📥 Download PNG for Paper",
                data=plot_buf,
                file_name=f"{particle_name}_publication_plot.png",
                mime="image/png"
            )

elif view_mode == "3D Event Display":
    st.subheader("3D Momentum Visualization")
    st.markdown("View the 3D momentum vectors ($p_x, p_y, p_z$) of the two muons for a single physical event.")
    
    if not filtered_df.empty:
        # Use a slider to pick an event
        event_idx = st.slider("Select Event Index from Filtered Data", 0, len(filtered_df) - 1, 0, key='event_slider')
        event = filtered_df.iloc[event_idx]
        
        fig3d = go.Figure()
        
        # Determine strict bounds for symmetric 3D axes
        max_p = max(
            abs(event['px1']), abs(event['py1']), abs(event['pz1']),
            abs(event['px2']), abs(event['py2']), abs(event['pz2'])
        )
        # Avoid zero range if max_p is 0
        max_p = max_p if max_p > 0 else 1.0  
        
        # 1. Detector Geometry Overlay (Conceptual Cylinder for CMS Barrel)
        theta = np.linspace(0, 2*np.pi, 50)
        z_cyl = np.linspace(-max_p*1.2, max_p*1.2, 2)
        theta_grid, z_grid = np.meshgrid(theta, z_cyl)
        x_cyl = (max_p * 0.8) * np.cos(theta_grid)
        y_cyl = (max_p * 0.8) * np.sin(theta_grid)
        
        fig3d.add_trace(go.Surface(
            x=x_cyl, y=y_cyl, z=z_grid,
            opacity=0.1, colorscale=[[0, 'gray'], [1, 'gray']],
            showscale=False, hoverinfo='skip',
            name='CMS Barrel (Conceptual)'
        ))

        # Origin to Muon 1
        fig3d.add_trace(go.Scatter3d(
            x=[0, event['px1']], y=[0, event['py1']], z=[0, event['pz1']],
            mode='lines+markers', name='Muon 1',
            line=dict(color='royalblue', width=6),
            marker=dict(size=4, color='royalblue')
        ))
        
        # Origin to Muon 2
        fig3d.add_trace(go.Scatter3d(
            x=[0, event['px2']], y=[0, event['py2']], z=[0, event['pz2']],
            mode='lines+markers', name='Muon 2',
            line=dict(color='firebrick', width=6),
            marker=dict(size=4, color='firebrick')
        ))
        
        # 2. Parent Particle Momentum (Boost Vector)
        parent_px = event['px1'] + event['px2']
        parent_py = event['py1'] + event['py2']
        parent_pz = event['pz1'] + event['pz2']
        
        fig3d.add_trace(go.Scatter3d(
            x=[0, parent_px], y=[0, parent_py], z=[0, parent_pz],
            mode='lines+markers', name=f'{particle_name} Boost Vector',
            line=dict(color='darkgreen', width=8, dash='dash'),
            marker=dict(size=5, color='darkgreen')
        ))
        
        # Extend max_p if parent momentum is larger
        max_p = max(max_p, abs(parent_px), abs(parent_py), abs(parent_pz))
        
        fig3d.update_layout(
            scene=dict(
                xaxis=dict(title='px [GeV/c]', range=[-max_p, max_p]),
                yaxis=dict(title='py [GeV/c]', range=[-max_p, max_p]),
                zaxis=dict(title='pz [GeV/c]', range=[-max_p, max_p]),
                aspectmode='cube'
            ),
            margin=dict(l=0, r=0, b=0, t=30),
            height=600,
            template='plotly_white'
        )
        
        st.plotly_chart(fig3d, width='stretch')
        
        # --- Advanced Analytics ---
        st.markdown("### Physics Analytics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Calculated Mass", f"{event['Calculated_M']:.3f} GeV/c²")
            
        with col2:
            # 3. 3D Opening Angle
            p1_mag = np.sqrt(event['px1']**2 + event['py1']**2 + event['pz1']**2)
            p2_mag = np.sqrt(event['px2']**2 + event['py2']**2 + event['pz2']**2)
            dot_product = event['px1']*event['px2'] + event['py1']*event['py2'] + event['pz1']*event['pz2']
            cos_theta = np.clip(dot_product / (p1_mag * p2_mag), -1.0, 1.0)
            theta_deg = np.degrees(np.arccos(cos_theta))
            st.metric("3D Opening Angle (θ)", f"{theta_deg:.1f}°")
            
        with col3:
            # 4. Transverse Momentum / MET Surrogate
            pt_parent = np.sqrt(parent_px**2 + parent_py**2)
            st.metric("Pair Transverse Momentum ($p_T$)", f"{pt_parent:.2f} GeV/c")
        
        st.info("💡 **How to interpret:** The green dashed vector shows the momentum of the parent particle before decay (boost). The grey cylinder is a conceptual representation of the CMS inner detector. If the Pair $p_T$ is large, the rest of the event must have a large recoiling transverse momentum (origin of MET signatures).")
    else:
        st.warning("No events found in this mass range.")

elif view_mode == "3D Event Animation":
    st.subheader("3D Animation of Multiple Events")
    st.markdown("Watch how the kinematics of the collision change event by event natively in Streamlit!")
    
    if not filtered_df.empty:
        anim_events_count = st.slider("Number of Events to Animate", min_value=10, max_value=100, value=30, step=10, key='anim_slider')
        anim_events_count = min(len(filtered_df), anim_events_count)
        
        st.write(f"Animating the first {anim_events_count} events in the selected mass range...")
        subset_df = filtered_df.head(anim_events_count).copy()
        
        # Parent vectors
        subset_df['parent_px'] = subset_df['px1'] + subset_df['px2']
        subset_df['parent_py'] = subset_df['py1'] + subset_df['py2']
        subset_df['parent_pz'] = subset_df['pz1'] + subset_df['pz2']
        
        max_p = max([
            subset_df['px1'].abs().max(), subset_df['py1'].abs().max(), subset_df['pz1'].abs().max(),
            subset_df['px2'].abs().max(), subset_df['py2'].abs().max(), subset_df['pz2'].abs().max(),
            subset_df['parent_px'].abs().max(), subset_df['parent_py'].abs().max(), subset_df['parent_pz'].abs().max()
        ])
        max_p = max_p if max_p > 0 else 1.0
        
        fig_anim = go.Figure()
        
        # Static Cylinder
        theta = np.linspace(0, 2*np.pi, 50)
        z_cyl = np.linspace(-max_p*1.2, max_p*1.2, 2)
        theta_grid, z_grid = np.meshgrid(theta, z_cyl)
        x_cyl = (max_p * 0.8) * np.cos(theta_grid)
        y_cyl = (max_p * 0.8) * np.sin(theta_grid)
        
        fig_anim.add_trace(go.Surface(
            x=x_cyl, y=y_cyl, z=z_grid,
            opacity=0.1, colorscale=[[0, 'gray'], [1, 'gray']],
            showscale=False, hoverinfo='skip', name='CMS Barrel'
        ))
        
        # Initial traces (Event 0)
        ev0 = subset_df.iloc[0]
        fig_anim.add_trace(go.Scatter3d(
            x=[0, ev0['px1']], y=[0, ev0['py1']], z=[0, ev0['pz1']],
            mode='lines+markers', name='Muon 1', line=dict(color='royalblue', width=6), marker=dict(size=4)
        ))
        fig_anim.add_trace(go.Scatter3d(
            x=[0, ev0['px2']], y=[0, ev0['py2']], z=[0, ev0['pz2']],
            mode='lines+markers', name='Muon 2', line=dict(color='firebrick', width=6), marker=dict(size=4)
        ))
        fig_anim.add_trace(go.Scatter3d(
            x=[0, ev0['parent_px']], y=[0, ev0['parent_py']], z=[0, ev0['parent_pz']],
            mode='lines+markers', name=f'{particle_name} Boost', line=dict(color='darkgreen', width=8, dash='dash'), marker=dict(size=5)
        ))
        
        # Frames
        frames = []
        for i in range(anim_events_count):
            ev = subset_df.iloc[i]
            frames.append(go.Frame(
                data=[
                    go.Scatter3d(x=[0, ev['px1']], y=[0, ev['py1']], z=[0, ev['pz1']]),
                    go.Scatter3d(x=[0, ev['px2']], y=[0, ev['py2']], z=[0, ev['pz2']]),
                    go.Scatter3d(x=[0, ev['parent_px']], y=[0, ev['parent_py']], z=[0, ev['parent_pz']])
                ],
                traces=[1, 2, 3],
                name=f"frame{i}"
            ))
            
        fig_anim.frames = frames
        
        fig_anim.update_layout(
            updatemenus=[dict(
                type="buttons",
                showactive=False,
                y=-0.1, x=0, xanchor="left", yanchor="top",
                direction="left",
                buttons=[
                    dict(label="▶ Play",
                         method="animate",
                         args=[None, dict(frame=dict(duration=800, redraw=True), fromcurrent=True, transition=dict(duration=400))]),
                    dict(label="⏸ Pause",
                         method="animate",
                         args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))])
                ]
            )],
            scene=dict(
                xaxis=dict(title='px [GeV/c]', range=[-max_p, max_p]),
                yaxis=dict(title='py [GeV/c]', range=[-max_p, max_p]),
                zaxis=dict(title='pz [GeV/c]', range=[-max_p, max_p]),
                aspectmode='cube'
            ),
            margin=dict(l=0, r=0, b=0, t=30), height=600, template='plotly_white',
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        
        st.plotly_chart(fig_anim, width='stretch')
    else:
        st.warning("No events found to animate.")

st.subheader("Raw data preview")
# Show preview directly from Polars
preview_df = df.head(100).to_pandas()
preview_df.columns = [str(c) for c in preview_df.columns]
st.dataframe(preview_df)

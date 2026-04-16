import streamlit as st
import urllib.request
import json
import os
import pandas as pd
import math
from scripts.download_data import download_single_file
from scripts.ui_utils import apply_branding

st.set_page_config(page_title="CERN Explorer | Portal", page_icon="⚛️", layout="wide")

# Apply unified enterprise branding
apply_branding()

# Page-specific styling extensions
st.markdown("""
    <style>
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# Cache the API search to prevent flickering on reruns
@st.cache_data(ttl=3600)
def get_cern_data(query, only_csv=True):
    try:
        api_url = f"https://opendata.cern.ch/api/records/?q={query.replace(' ', '+')}&size=15"
        if only_csv:
            api_url += "&f=file_format:CSV&f=type:Dataset"
        
        req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=10)
        return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

def format_size(size_bytes):
    if not size_bytes or size_bytes == 0: return "Unknown Size"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

# Metadata for Quick Picks
QUICK_PICKS = {
    "⚛️ J/psi (Jpsimumu)": "Jpsimumu",
    "⚛️ Z Boson (Zmumu)": "Zmumu",
    "⚛️ Upsilon (Ymumu)": "Ymumu",
    "⚛️ DoubleMu (Mixed)": "DoubleMu"
}

# --- Callbacks ---
def set_search_query(q):
    st.session_state.search_query = q

def handle_preview(rec_id, fname, furl):
    st.session_state.active_preview_id = rec_id
    st.session_state.active_preview_fname = fname
    try:
        if fname.endswith('.csv'):
            st.session_state.preview_content = pd.read_csv(furl, nrows=20)
            st.session_state.preview_type = 'df'
        else:
            req_f = urllib.request.Request(furl, headers={'User-Agent': 'Mozilla/5.0'})
            st.session_state.preview_content = urllib.request.urlopen(req_f).read(1000).decode('utf-8')
            st.session_state.preview_type = 'text'
    except Exception as e:
        st.session_state.preview_error = str(e)

def stream_to_analysis(url):
    st.session_state.stream_url = url
    st.session_state.nav_to_analysis = True

# --- App UI ---
st.title("🔍 Explore CERN Open Data")
st.write("Search the live CERN Open Data portal for authentic particle physics datasets.")

# Initialize session state
if 'search_query' not in st.session_state:
    st.session_state.search_query = "Jpsimumu"
if 'active_preview_id' not in st.session_state:
    st.session_state.active_preview_id = None
if 'nav_to_analysis' not in st.session_state:
    st.session_state.nav_to_analysis = False

# Navigation Handler (handles redirect outside of callback for reliability)
if st.session_state.nav_to_analysis:
    st.session_state.nav_to_analysis = False
    st.switch_page("pages/1_Analysis.py")

col_search, col_filter = st.columns([3, 1])
with col_search:
    st.text_input("Enter search terms (e.g., 'Jpsimumu', 'DoubleMu', 'Run 2011')", 
                  key="search_query")

with col_filter:
    st.write("") # Padding
    only_csv = st.checkbox("Only CSV-compatible", value=True)

# Quick Search Buttons
st.write("🎯 **Quick Picks (Guaranteed CSVs):**")
qp_cols = st.columns(4)
for i, (label, query) in enumerate(QUICK_PICKS.items()):
    with qp_cols[i]:
        st.button(label, key=f"qp_{i}", on_click=set_search_query, args=(query,))

if st.session_state.search_query:
    result_data = get_cern_data(st.session_state.search_query, only_csv)
    
    if "error" in result_data:
        st.error(f"Error querying CERN API: {result_data['error']}")
    else:
        hits = result_data.get('hits', {}).get('hits', [])
        
        if not hits:
            st.warning("No datasets found for this search.")
        else:
            st.subheader(f"Found {len(hits)} matching records")
            
            for hit in hits:
                metadata = hit.get('metadata', {})
                title = metadata.get('title', 'Unknown Title')
                rec_id = hit.get('id')
                
                # Check if this record is currently being previewed
                is_active = st.session_state.active_preview_id == rec_id
                
                with st.expander(f"📚 {title} (ID: {rec_id})", expanded=is_active):
                    # --- Metadata Metrics ---
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Experiment", ", ".join(metadata.get('experiment', ['N/A'])))
                    with m2:
                        st.metric("Type", metadata.get('type', {}).get('secondary', ['Dataset'])[0])
                    with m3:
                        st.metric("Year", metadata.get('date_published', 'N/A'))
                    with m4:
                        st.metric("Run", ", ".join(metadata.get('run_period', ['N/A'])))
                    
                    st.markdown("---")
                    st.write(metadata.get('description', 'Detailed information for this record is available on the CERN Open Data portal.'))
                    
                    if 'methodology' in metadata:
                        with st.expander("🔬 Methodology & Selection Criteria"):
                            st.write(metadata['methodology'].get('description', ''), unsafe_allow_html=True)
                    
                    st.markdown(f"**Official Record:** [opendata.cern.ch/record/{rec_id}](https://opendata.cern.ch/record/{rec_id})")
                    
                    # File handling
                    files = metadata.get('_files', [])
                    compatible = [f for f in files if f.get('key', '').lower().endswith(('.csv', '.txt', '.json'))]
                    root_files = [f for f in files if f.get('key', '').lower().endswith('.root')]
                    
                    if compatible:
                        st.info(f"📊 Found {len(compatible)} compatible data files:")
                        for f in compatible:
                            fname = f.get('key')
                            fsize = format_size(f.get('size'))
                            furl = f"https://opendata.cern.ch/record/{rec_id}/files/{fname}"
                            
                            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                            with c1:
                                st.markdown(f"- **{fname}** (`{fsize}`)")
                            with c2:
                                st.button("👁️ Preview", 
                                          key=f"pbtn_{rec_id}_{fname}", 
                                          on_click=handle_preview, 
                                          args=(rec_id, fname, furl))
                            with c3:
                                st.button("🌊 Stream", 
                                          key=f"strbtn_{rec_id}_{fname}",
                                          on_click=stream_to_analysis,
                                          args=(furl,))
                            with c4:
                                if os.path.exists(os.path.join('data', fname)):
                                    st.button("✅ Stored", key=f"dlbtn_{rec_id}_{fname}", disabled=True)
                                else:
                                    if st.button(f"📥 Fetch", key=f"dlbtn_{rec_id}_{fname}"):
                                        with st.spinner(f"Fetching {fname}..."):
                                            download_single_file(furl, fname)
                                        st.success(f"Downloaded! Refreshing...")
                                        st.rerun()
                            
                            # Show the preview ONLY if it matches this specific file
                            if is_active and st.session_state.get('active_preview_fname') == fname:
                                st.markdown("### 👁️ Data Preview")
                                if 'preview_error' in st.session_state:
                                    st.error(st.session_state.preview_error)
                                    del st.session_state.preview_error
                                elif st.session_state.get('preview_type') == 'df':
                                    st.dataframe(st.session_state.preview_content, width='stretch')
                                else:
                                    st.code(st.session_state.preview_content, language='text')
                    
                    if root_files:
                        st.divider()
                        st.markdown("⚛️ **ROOT/DST Files Detected**")
                        st.caption("These files contain complex physics objects. You can 'Peek' to see their internal structure.")
                        for f in root_files:
                            fname = f.get('key')
                            fsize = format_size(f.get('size'))
                            furl = f"https://opendata.cern.ch/record/{rec_id}/files/{fname}"
                            
                            rc1, rc2, rc3, rc4, rc5 = st.columns([3, 1, 1, 1, 1])
                            with rc1:
                                st.markdown(f"- `{fname}` (`{fsize}`)")
                            
                            with rc2:
                                if st.button("🔍 Peek", key=f"peek_{rec_id}_{fname}"):
                                    try:
                                        import uproot
                                        with st.spinner("Analyzing remote ROOT header..."):
                                            # Use a standard open - uproot 5 defaults are usually best but we wrap in a try
                                            with uproot.open(furl) as root_file:
                                                all_keys = root_file.keys()
                                                st.session_state.root_active_id = rec_id
                                                st.session_state.root_active_fname = fname
                                                st.session_state.root_keys = all_keys
                                                st.success(f"Successfully bridged to `{fname}`")
                                    except Exception as e:
                                        st.error(f"Network error peeking ROOT file: {e}")
                                        st.info("💡 **Tip:** This large file might require a local download for full inspection.")
                            
                            with rc3:
                                st.button("🌊 Stream", 
                                          key=f"strr_{rec_id}_{fname}",
                                          on_click=stream_to_analysis,
                                          args=(furl,))

                            with rc4:
                                if os.path.exists(os.path.join('data', fname)):
                                    st.button("✅ Stored", key=f"dlr_{rec_id}_{fname}", disabled=True)
                                else:
                                    if st.button(f"📥 Fetch", key=f"dlr_{rec_id}_{fname}"):
                                        with st.spinner(f"Fetching ROOT file {fname}..."):
                                            download_single_file(furl, fname)
                                        st.success(f"Downloaded! Refreshing...")
                                        st.rerun()
                            
                            with rc5:
                                # Provide XRootD suggestion if user wants to use root:// instead of https://
                                # Most CERN Open Data is on eospublic.cern.ch
                                st.button("🔗 XRootD", 
                                          key=f"xrdb_{rec_id}_{fname}", 
                                          help="Copy XRootD path for high-speed streaming",
                                          on_click=lambda u=furl: st.toast(f"XRootD Suggestion: root://eospublic.cern.ch//eos/opendata/{u.split('files/')[-1]}", icon="⚛️"))
                            
                            # If this file is the active ROOT preview, show the structure below
                            if st.session_state.get('root_active_id') == rec_id and st.session_state.get('root_active_fname') == fname:
                                with st.container():
                                    st.markdown("---")
                                    st.write("**Found Trees/Directories:**")
                                    all_keys = st.session_state.root_keys
                                    st.write(all_keys)
                                    
                                    selected_tree = st.selectbox("Select a Tree to inspect branches", ["(Select)"] + all_keys, key=f"tsel_{rec_id}_{fname}")
                                    if selected_tree != "(Select)":
                                        try:
                                            import uproot
                                            with st.spinner(f"Reading branches from `{selected_tree}`..."):
                                                # Use the direct URL to peek inside
                                                with uproot.open(furl) as root_file:
                                                    tree = root_file[selected_tree]
                                                    st.write(f"**Branches in `{selected_tree}`:**")
                                                    st.json(tree.keys())
                                        except Exception as e:
                                            st.error(f"Could not read branches: {e}")

                    if not compatible and not root_files:
                        all_formats = metadata.get('distribution', {}).get('formats', [])
                        format_str = ", ".join(all_formats).upper() if all_formats else "ROOT/DST"
                        st.warning(f"⚠️ This dataset uses **{format_str}** format, which is not supported for direct browser preview.")

st.info("💡 **Navigation:** Use the sidebar on the left to head back to the 'Analysis' module with your own local data.")

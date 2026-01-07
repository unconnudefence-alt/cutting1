import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from rectpack import newPacker, PackingMode, PackingBin, SORT_AREA
import uuid
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="OptiCut Pro | Enterprise Nesting",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. PROFESSIONAL CSS STYLING (The "International" Look) ---
st.markdown("""
    <style>
    /* Global Font & Background */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Header Styling */
    h1, h2, h3 {
        color: #0f172a;
        font-weight: 600;
    }
    
    /* Card Styling for Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* Custom Button Styling */
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 6px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Table Header Styling */
    thead tr th:first-child { display:none }
    tbody th { display:none }
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE ---
if 'job_list' not in st.session_state:
    st.session_state.job_list = []
if 'optimization_result' not in st.session_state:
    st.session_state.optimization_result = None

# --- 4. CORE LOGIC ---

def add_item(shape, dims, qty, rot):
    """Adds items to the job queue with unique IDs."""
    new_items = []
    color_map = {'Rectangle': '#3B82F6', 'Square': '#10B981', 'Circle': '#F59E0B', 'Triangle': '#8B5CF6'}
    
    for _ in range(int(qty)):
        uid = str(uuid.uuid4())[:8]
        
        # Bounding Box Logic
        if shape in ['Rectangle', 'Square']:
            w, h = dims['w'], dims['h']
            area = w * h
        elif shape == 'Circle':
            w, h = dims['r']*2, dims['r']*2
            area = 3.14159 * (dims['r']**2)
        elif shape == 'Triangle':
            w, h = dims['b'], dims['h']
            area = 0.5 * dims['b'] * dims['h']

        new_items.append({
            'id': uid,
            'type': shape,
            'dims': dims,
            'w': w, 'h': h, # Bounding box
            'area': area,
            'allow_rotation': rot,
            'color': color_map.get(shape, '#666')
        })
    
    st.session_state.job_list.extend(new_items)

def solve_nesting(bin_w, bin_h, items):
    """
    Solves the packing problem. 
    Returns: Packed items list, Statistics, Unplaced items
    """
    packer = newPacker(mode=PackingMode.Offline, rotation=True, sort_algo=SORT_AREA)
    packer.add_bin(bin_w, bin_h)
    
    for item in items:
        packer.add_rect(item['w'], item['h'], rid=item['id'])
    
    start_time = time.time()
    packer.pack()
    elapsed = time.time() - start_time
    
    packed_results = []
    placed_ids = set()
    used_area = 0
    
    if len(packer) > 0:
        abin = packer[0] # Single bin optimization
        for rect in abin:
            rid = rect.rid
            original = next((x for x in items if x['id'] == rid), None)
            
            if original:
                placed_ids.add(rid)
                
                # Check rotation
                is_rotated = False
                if original['w'] != rect.width: 
                    is_rotated = True
                
                packed_results.append({
                    'id': rid,
                    'type': original['type'],
                    'x': rect.x,
                    'y': rect.y,
                    'w_box': rect.width,
                    'h_box': rect.height,
                    'rotation': 90 if is_rotated else 0,
                    'color': original['color'],
                    'dims': original['dims']
                })
                used_area += original['area']

    return {
        'placed': packed_results,
        'unplaced_count': len(items) - len(placed_ids),
        'efficiency': (used_area / (bin_w * bin_h)) * 100,
        'waste': 100 - ((used_area / (bin_w * bin_h)) * 100),
        'time': elapsed
    }

def plot_interactive_nesting(bin_w, bin_h, placed_items):
    """
    Creates a professional Plotly interactive chart.
    """
    fig = go.Figure()

    # 1. Draw Raw Material Board
    fig.add_shape(
        type="rect", x0=0, y0=0, x1=bin_w, y1=bin_h,
        line=dict(color="#334155", width=3),
        fillcolor="#f1f5f9", layer="below"
    )

    # 2. Draw Items
    for item in placed_items:
        x, y = item['x'], item['y']
        w, h = item['w_box'], item['h_box']
        
        # Hover Text
        hover_info = f"ID: {item['id']}<br>Type: {item['type']}<br>Pos: ({x}, {y})<br>Rot: {item['rotation']}°"
        
        if item['type'] in ['Rectangle', 'Square']:
            fig.add_trace(go.Scatter(
                x=[x, x+w, x+w, x, x],
                y=[y, y, y+h, y+h, y],
                fill="toself",
                fillcolor=item['color'],
                line=dict(color="white", width=1),
                mode='lines',
                name=item['type'],
                text=hover_info,
                hoverinfo='text',
                showlegend=False,
                opacity=0.9
            ))
            
        elif item['type'] == 'Circle':
            # Plotly shapes for circles are cleaner
            r = w / 2
            fig.add_shape(
                type="circle",
                x0=x, y0=y, x1=x+w, y1=y+h,
                line_color="white", fillcolor=item['color'],
                opacity=0.9
            )
            # Invisible scatter for hover tooltip
            fig.add_trace(go.Scatter(
                x=[x+r], y=[y+r], mode='markers',
                marker=dict(size=w, color='rgba(0,0,0,0)'),
                text=hover_info, hoverinfo='text', showlegend=False
            ))

        elif item['type'] == 'Triangle':
            # Draw triangle inside the bounding box
            # Simple Right Angle for demo
            fig.add_trace(go.Scatter(
                x=[x, x+w, x, x],
                y=[y, y, y+h, y],
                fill="toself",
                fillcolor=item['color'],
                line=dict(color="white", width=1),
                text=hover_info, hoverinfo='text',
                showlegend=False,
                opacity=0.9
            ))

    # 3. Chart Layout
    fig.update_layout(
        title=dict(text=f"Material Dimensions: {bin_w} x {bin_h} mm", font=dict(size=14, color="#64748b")),
        xaxis=dict(title="Width (mm)", range=[-10, bin_w+10], showgrid=True, gridcolor='#e2e8f0'),
        yaxis=dict(title="Height (mm)", range=[-10, bin_h+10], showgrid=True, gridcolor='#e2e8f0', scaleanchor="x", scaleratio=1),
        plot_bgcolor='white',
        margin=dict(l=20, r=20, t=40, b=20),
        height=600,
        dragmode='pan'
    )
    
    return fig

# --- 5. UI LAYOUT ---

# Sidebar: Project Settings
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2684/2684005.png", width=60)
    st.title("OptiCut Pro")
    st.markdown("---")
    
    st.subheader("1. Raw Material")
    col1, col2 = st.columns(2)
    rm_w = col1.number_input("Width (mm)", value=2440, step=10)
    rm_h = col2.number_input("Height (mm)", value=1220, step=10)
    
    st.markdown("---")
    st.subheader("2. Job Management")
    if st.button("🗑️ Reset All Data", type="secondary"):
        st.session_state.job_list = []
        st.session_state.optimization_result = None
        st.rerun()

    st.markdown("---")
    st.info("**Instructions:** define your material size, add shapes via the tabs on the right, and click Optimize.")

# Main Area
col_main_1, col_main_2 = st.columns([1, 2.5])

with col_main_1:
    st.subheader("🛠️ Input Shapes")
    
    tab1, tab2, tab3 = st.tabs(["Rect/Square", "Circle", "Triangle"])
    
    with tab1:
        st.markdown("##### Rectangle / Square")
        r_type = st.radio("Type", ["Rectangle", "Square"], horizontal=True, label_visibility="collapsed")
        c1, c2 = st.columns(2)
        if r_type == "Rectangle":
            w = c1.number_input("Width", 10, 2000, 400)
            h = c2.number_input("Height", 10, 2000, 300)
            dims = {'w': w, 'h': h}
        else:
            s = c1.number_input("Side", 10, 2000, 300)
            dims = {'w': s, 'h': s}
            
        qty = st.number_input("Qty", 1, 100, 5, key="q1")
        rot = st.checkbox("Allow Rotation", True, key="rot1")
        if st.button("Add Shape", key="btn1"):
            add_item(r_type, dims, qty, rot)
            st.toast(f"Added {qty} {r_type}s", icon="✅")

    with tab2:
        st.markdown("##### Circle")
        r = st.number_input("Radius (mm)", 10, 1000, 150)
        qty = st.number_input("Qty", 1, 100, 3, key="q2")
        if st.button("Add Shape", key="btn2"):
            add_item("Circle", {'r': r}, qty, False)
            st.toast(f"Added {qty} Circles", icon="✅")

    with tab3:
        st.markdown("##### Triangle")
        c1, c2 = st.columns(2)
        b = c1.number_input("Base", 10, 2000, 300)
        h = c2.number_input("Height", 10, 2000, 400)
        qty = st.number_input("Qty", 1, 100, 2, key="q3")
        rot = st.checkbox("Allow Rotation", True, key="rot3")
        if st.button("Add Shape", key="btn3"):
            add_item("Triangle", {'b': b, 'h': h}, qty, rot)
            st.toast(f"Added {qty} Triangles", icon="✅")

    # List Preview
    if st.session_state.job_list:
        st.markdown("### Job Queue")
        df_preview = pd.DataFrame(st.session_state.job_list)
        st.dataframe(
            df_preview[['type', 'dims', 'allow_rotation']].tail(5), 
            use_container_width=True, 
            hide_index=True
        )
        st.caption(f"Total Items: {len(st.session_state.job_list)}")
        
        if st.button("🚀 EXECUTE OPTIMIZATION", type="primary"):
            with st.spinner("Analyzing geometry and minimizing waste..."):
                time.sleep(0.5) # UX Delay for feel
                res = solve_nesting(rm_w, rm_h, st.session_state.job_list)
                st.session_state.optimization_result = res

with col_main_2:
    if st.session_state.optimization_result:
        res = st.session_state.optimization_result
        
        # 1. KPI Cards
        st.subheader("📊 Optimization Report")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Utilization", f"{res['efficiency']:.1f}%", delta_color="normal")
        k2.metric("Waste Rate", f"{res['waste']:.1f}%", delta_color="inverse")
        k3.metric("Unplaced Items", res['unplaced_count'], delta_color="inverse" if res['unplaced_count']>0 else "off")
        k4.metric("Process Time", f"{res['time']:.3f}s")
        
        # 2. Plotly Visualization
        st.markdown("### Cutting Layout")
        fig = plot_interactive_nesting(rm_w, rm_h, res['placed'])
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        
        # 3. Detailed Data & Export
        with st.expander("📂 View Detailed Cutting List & Export"):
            df_res = pd.DataFrame(res['placed'])
            if not df_res.empty:
                # Format for display
                display_df = df_res[['id', 'type', 'x', 'y', 'rotation', 'w_box', 'h_box']].copy()
                st.dataframe(display_df, use_container_width=True)
                
                # CSV Export
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CNC Data (CSV)",
                    data=csv,
                    file_name='opticut_job_result.csv',
                    mime='text/csv',
                )
            else:
                st.warning("No items were placed. Check dimensions.")
                
    else:
        # Empty State Placeholder
        st.markdown("""
        <div style="text-align: center; padding: 50px; color: #94a3b8; border: 2px dashed #e2e8f0; border-radius: 10px; margin-top: 20px;">
            <h3>Ready to Optimize</h3>
            <p>Add shapes from the left panel and click 'Execute Optimization' to see the magic.</p>
        </div>
        """, unsafe_allow_html=True)
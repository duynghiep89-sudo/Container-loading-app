import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- CSS ĐỂ CHỈ IN PHẦN KẾT QUẢ ---
st.markdown("""
    <style>
    @media print {
        section[data-testid="stSidebar"], .stButton, .stDownloadButton, 
        footer, header, .stTabs, div[data-testid="stExpander"], div.stDataFrame {
            display: none !important;
        }
        .main .block-container { padding-top: 1rem !important; }
    }
    </style>
""", unsafe_allow_html=True)

# --- KHỞI TẠO BỘ NHỚ TẠM (SESSION STATE) CHO DANH MỤC SKU ---
if 'sku_library' not in st.session_state:
    st.session_state.sku_library = pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight'])

# --- HÀM TẠO FILE CSV MẪU ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- HÀM VẼ 3D NÂNG CAO ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts, container_type):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    
    fig.add_trace(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers', marker=dict(color='white'), name=f"📦 CONTAINER: {container_type}"))

    added_to_legend = set()
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d_item = [float(p) for p in item.get_dimension()]
        color = sku_colors.get(item.name, '#808080')
        show_legend = item.name not in added_to_legend
        if show_legend: added_to_legend.add(item.name)

        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w], y=[y, y+h, y+h, y, y, y+h, y+h, y], z=[z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1, flatshading=True, name=f"{item.name} ({sku_counts.get(item.name)} kiện)", showlegend=show_legend
        ))
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=3), showlegend=False, hoverinfo='none'
        ))

    fig.update_layout(
        scene=dict(xaxis=dict(range=[-100, L+100]), yaxis=dict(range=[-100, W+100]), zaxis=dict(range=[-100, H+100]), aspectmode='data',
                   camera=dict(eye=dict(x=1.8, y=1.8, z=1.2), center=dict(x=0.2, y=0, z=-0.3))),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.7)", font=dict(size=16)),
        margin=dict(l=0, r=0, b=0, t=0), height=800
    )
    return fig

# --- GIAO DIỆN CHÍNH ---
st.title("🚚 Loading Map - GESIN")

cont_data = {
    "40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000], "45HC": [13556, 2352, 2698, 28000]
}

with st.sidebar:
    st.header("⚙️ Cấu hình")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    specs = cont_data[c_choice]
    L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-30, specs[3]
    st.success(f"📌 {c_choice}: {L}x{W}x{H} mm")

tab_calc, tab_library = st.tabs(["🚀 Tính toán đóng hàng", "📖 Danh mục SKU (Master Data)"])

# --- TAB 2: QUẢN LÝ DANH MỤC SKU ---
with tab_library:
    st.subheader("Quản lý thư viện thông số mặt hàng")
    col_lib1, col_lib2 = st.columns([1, 2])
    with col_lib1:
        lib_file = st.file_uploader("Nạp danh mục từ CSV", type="csv")
        if lib_file:
            st.session_state.sku_library = pd.read_csv(lib_file)
            st.rerun()
    with col_lib2:
        st.session_state.sku_library = st.data_editor(st.session_state.sku_library, num_rows="dynamic", key="lib_editor")

# --- TAB 1: TÍNH TOÁN ---
with tab_calc:
    st.subheader("Lập phương án đóng hàng")
    # Lấy danh sách SKU hiện có trong thư viện để làm gợi ý
    available_skus = st.session_state.sku_library['SKU'].unique().tolist()
    
    manual_entry = st.data_editor(
        pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity']),
        num_rows="dynamic",
        column_config={
            # BIẾN CỘT SKU THÀNH SELECTBOX ĐỂ GỢI Ý (Auto-complete)
            "SKU": st.column_config.SelectboxColumn("Chọn SKU", options=available_skus, required=True),
            "Quantity": st.column_config.NumberColumn("Số lượng", default=1)
        },
        key="calc_editor"
    )
    
    # Tự động điền thông số khi SKU được chọn
    if not manual_entry.empty:
        lib = st.session_state.sku_library
        for i, row in manual_entry.iterrows():
            if row['SKU'] in lib['SKU'].values:
                sku_data = lib[lib['SKU'] == row['SKU']].iloc[0]
                # Chỉ điền nếu các ô thông số đang trống
                if pd.isna(row['Width']) or row['Width'] == 0:
                    manual_entry.at[i, 'Width'] = sku_data['Width']
                    manual_entry.at[i, 'Height'] = sku_data['Height']
                    manual_entry.at[i, 'Depth'] = sku_data['Depth']
                    manual_entry.at[i, 'Weight'] = sku_data['Weight']

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        calc_df = manual_entry.dropna(subset=['SKU'])
        if not calc_df.empty:
            total_cbm = sum((r['Width']/1000 * r['Height']/1000 * r['Depth']/1000 * r['Quantity']) for _, r in calc_df.iterrows())
            with st.spinner('🛠️ Đang xử lý...'):
                packer = Packer()
                packer.add_bin(Bin(c_choice, L, W, H, M))
                palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf', '#E15F99']
                sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(calc_df['SKU'].unique())}
                sku_counts = calc_df.groupby('SKU')['Quantity'].sum().to_dict()

                for _, row in calc_df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))
                packer.pack()
                
                st.info(f"📊 Container: {c_choice} | Tổng hàng: {total_cbm:.3f} m³")
                st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, sku_counts, c_choice), use_container_width=True)
                st.components.v1.html("""
                    <script>function printPage() { window.parent.print(); }</script>
                    <button onclick="printPage()" style="background-color: #ff4b4b; color: white; padding: 15px 32px; border: none; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer;">
                        🖨️ XUẤT FILE PDF CHO KHO
                    </button>
                """, height=100)

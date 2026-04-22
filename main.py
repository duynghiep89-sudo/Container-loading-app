import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- CSS IN ẤN ---
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

# --- HÀM VẼ 3D ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)
    # Sàn và vách
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.2, showlegend=False))

    added_to_legend = set()
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d_item = [float(p) for p in item.get_dimension()]
        color = sku_colors.get(item.name, '#808080')
        show_in_legend = item.name not in added_to_legend
        if show_in_legend: added_to_legend.add(item.name)
        
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1, flatshading=True, name=f"{item.name}", showlegend=show_in_legend
        ))
        # Viền đen
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=2), showlegend=False, hoverinfo='none'
        ))
    fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30), height=700)
    return fig

# --- CẤU HÌNH CONTAINER ---
cont_data = {
    "40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000], "Tùy chỉnh": [6000, 2300, 2300, 20000]
}

# --- QUẢN LÝ MASTER DATA SKU ---
DB_FILE = "master_sku_list.csv"
if os.path.exists(DB_FILE):
    master_df = pd.read_csv(DB_FILE)
else:
    master_df = pd.DataFrame({'SKU': ['SOFA_A', 'TABLE_B'], 'Width': [850.0, 1000.0], 'Height': [900.0, 750.0], 'Depth': [2100.0, 1600.0], 'Weight': [75.0, 45.0]})

with st.sidebar:
    st.header("⚙️ Thiết lập")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    specs = cont_data[c_choice]
    L, W, H, M = (specs[0]-20, specs[1]-20, specs[2]-30, specs[3]) if c_choice != "Tùy chỉnh" else (specs[0], specs[1], specs[2], specs[3])
    
    st.divider()
    st.subheader("🗂️ Danh mục SKU")
    edited_master = st.data_editor(master_df, num_rows="dynamic", key="master_editor")
    if st.button("💾 LƯU DANH MỤC"):
        edited_master.to_csv(DB_FILE, index=False)
        st.success("Đã lưu database!")

# --- NHẬP HÀNG HÓA ---
st.subheader("📋 Danh sách đóng hàng")
sku_options = edited_master['SKU'].dropna().unique().tolist()

tab1, tab2 = st.tabs(["📂 Tải file CSV", "✍️ Nhập đơn hàng"])

input_df = pd.DataFrame()

with tab1:
    up_file = st.file_uploader("Upload CSV đơn hàng", type="csv")
    if up_file: input_df = pd.read_csv(up_file)

with tab2:
    manual_input = st.data_editor(
        pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity']),
        num_rows="dynamic",
        column_config={
            "SKU": st.column_config.SelectboxColumn("Mã SKU", options=sku_options, required=True),
            "Quantity": st.column_config.NumberColumn("SL", min_value=1, default=1),
            "Width": "Rộng (Tự điền)", "Height": "Cao (Tự điền)", "Depth": "Dài (Tự điền)", "Weight": "Nặng"
        },
        key="order_input"
    )
    if not manual_input.empty:
        input_df = pd.concat([input_df, manual_input], ignore_index=True)

# --- XỬ LÝ VÀ TÍNH TOÁN ---
if st.button("🚀 BẮT ĐẦU TÍNH TOÁN", use_container_width=True):
    if input_df.empty or input_df['SKU'].dropna().empty:
        st.error("Vui lòng nhập hàng hóa!")
    else:
        # Bước cực kỳ quan trọng: Duyệt lại data để đảm bảo lấy thông số mới nhất từ Master DB
        processed_data = []
        master_dict = edited_master.set_index('SKU').to_dict('index')

        for _, row in input_df.dropna(subset=['SKU']).iterrows():
            sku = row['SKU']
            qty = row['Quantity']
            
            # Nếu người dùng không nhập kích thước (hoặc nhập sai), lấy từ Master DB
            if sku in master_dict:
                m_info = master_dict[sku]
                w = float(row['Width']) if pd.notna(row['Width']) and row['Width'] != 0 else m_info['Width']
                h = float(row['Height']) if pd.notna(row['Height']) and row['Height'] != 0 else m_info['Height']
                d = float(row['Depth']) if pd.notna(row['Depth']) and row['Depth'] != 0 else m_info['Depth']
                wg = float(row['Weight']) if pd.notna(row['Weight']) and row['Weight'] != 0 else m_info['Weight']
                processed_data.append({'SKU': sku, 'Width': w, 'Height': h, 'Depth': d, 'Weight': wg, 'Quantity': int(qty)})

        final_df = pd.DataFrame(processed_data)
        
        if final_df.empty:
            st.error("Dữ liệu không hợp lệ.")
        else:
            st.write("Dữ liệu sau khi khớp danh mục:")
            st.dataframe(final_df, use_container_width=True)

            # Thuật toán đóng hàng
            packer = Packer()
            packer.add_bin(Bin(c_choice, L, W, H, M))
            
            # Tạo màu sắc
            unique_skus = final_df['SKU'].unique()
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
            sku_colors = {sku: colors[i % len(colors)] for i, sku in enumerate(unique_skus)}
            sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()

            for _, row in final_df.iterrows():
                for _ in range(int(row['Quantity'])):
                    packer.add_item(Item(row['SKU'], float(row['Depth']), float(row['Width']), float(row['Height']), float(row['Weight'])))
            
            packer.pack()
            
            # Hiển thị
            st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, sku_counts), use_container_width=True)
            
            st.components.v1.html("""
                <script>function printPage() { window.parent.print(); }</script>
                <button onclick="printPage()" style="background-color:#ff4b4b; color:white; padding:15px; border:none; border-radius:8px; width:100%; font-weight:bold; cursor:pointer;">
                    🖨️ XUẤT FILE PDF CHO KHO
                </button>
            """, height=100)

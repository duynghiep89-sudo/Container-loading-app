import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- ĐƯỜNG DẪN MẶC ĐỊNH ---
DEFAULT_PATH = r"G:\Customs\13. Share\06. ITEM PACKING\DMSKU.csv"

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

# --- HÀM HỖ TRỢ VẼ ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)
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
            color=color, opacity=1, flatshading=True, 
            name=f"{item.name} ({sku_counts.get(item.name)} kiện)", 
            showlegend=show_in_legend
        ))
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=3), showlegend=False, hoverinfo='none'
        ))

    fig.update_layout(
        scene=dict(xaxis=dict(title='Dài'), yaxis=dict(title='Rộng'), zaxis=dict(title='Cao'), 
                   aspectmode='data', camera=dict(eye=dict(x=1.8, y=1.8, z=1.2), center=dict(x=0.2, y=-0.2, z=-0.3))),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.7)"),
        margin=dict(l=0, r=0, b=0, t=30), height=800 
    )
    return fig

# --- LOGIC CẬP NHẬT SKU (TRỌNG TÂM FIX) ---
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity'])

def on_manual_change():
    # Lấy dữ liệu thay đổi từ Widget
    change_info = st.session_state.manual_input
    # Làm việc trên bản sao của DataFrame hiện tại
    df = st.session_state.manual_df.copy()

    # 1. Xử lý sửa ô (Chọn SKU hoặc sửa số)
    for row_idx_str, edits in change_info.get("edited_rows", {}).items():
        idx = int(row_idx_str)
        for col, val in edits.items():
            df.at[idx, col] = val
            # Nếu cột bị sửa là SKU, nạp ngay dữ liệu Master
            if col == "SKU" and val in edited_master['SKU'].values:
                m_row = edited_master[edited_master['SKU'] == val].iloc[0]
                df.at[idx, 'Width'] = m_row['Width']
                df.at[idx, 'Height'] = m_row['Height']
                df.at[idx, 'Depth'] = m_row['Depth']
                df.at[idx, 'Weight'] = m_row['Weight']
                df.at[idx, 'Quantity'] = 1

    # 2. Xử lý thêm dòng mới
    for new_row_data in change_info.get("added_rows", []):
        new_entry = {'SKU': None, 'Width': 0, 'Height': 0, 'Depth': 0, 'Weight': 0, 'Quantity': 1}
        if "SKU" in new_row_data:
            s_val = new_row_data["SKU"]
            if s_val in edited_master['SKU'].values:
                m_row = edited_master[edited_master['SKU'] == s_val].iloc[0]
                new_entry.update({'SKU': s_val, 'Width': m_row['Width'], 'Height': m_row['Height'], 
                                  'Depth': m_row['Depth'], 'Weight': m_row['Weight']})
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

    # 3. Xử lý xóa dòng
    if change_info.get("deleted_rows"):
        df = df.drop(change_info["deleted_rows"]).reset_index(drop=True)

    # Cập nhật lại session_state chính thức
    st.session_state.manual_df = df

# --- GIAO DIỆN SIDEBAR & MASTER SKU ---
with st.sidebar:
    st.header("⚙️ Cấu hình Phương tiện")
    cont_data = {"40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000], "20GP": [5898, 2352, 2393, 28000], "Tùy chỉnh": [0,0,0,0]}
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    if c_choice == "Tùy chỉnh":
        L, W, H, M = st.number_input("Dài"), st.number_input("Rộng"), st.number_input("Cao"), st.number_input("Tải trọng")
    else:
        s = cont_data[c_choice]
        L, W, H, M = s[0]-20, s[1]-20, s[2]-30, s[3]

    st.divider()
    st.header("🗂️ Danh mục SKU")
    
    # Bẫy lỗi đọc file Local
    m_df = pd.DataFrame()
    if os.path.exists(DEFAULT_PATH):
        try:
            m_df = pd.read_csv(DEFAULT_PATH)
            st.caption(f"✅ Đã nhận diện Master tại ổ G")
        except: pass
    
    u_file = st.file_uploader("Hoặc tải file CSV mới", type="csv")
    if u_file: m_df = pd.read_csv(u_file)
    elif m_df.empty: m_df = pd.DataFrame({'SKU':['A','B'], 'Width':[100,200], 'Height':[100,200], 'Depth':[100,200], 'Weight':[10,20]})
    
    edited_master = st.data_editor(m_df, num_rows="dynamic", key="master_editor")

# --- PHẦN NHẬP ĐƠN HÀNG ---
st.title("🚚 Loading Map - GESIN")
tab1, tab2 = st.tabs(["📂 File CSV", "✍️ Nhập tay"])
final_df = pd.DataFrame()

with tab2:
    sku_list = edited_master['SKU'].dropna().unique().tolist()
    st.data_editor(st.session_state.manual_df, num_rows="dynamic", key="manual_input", 
                   on_change=on_manual_change,
                   column_config={"SKU": st.column_config.SelectboxColumn("SKU", options=sku_list, required=True)})
    
    if not st.session_state.manual_df.empty:
        final_df = st.session_state.manual_df.dropna(subset=['SKU'])

# --- TÍNH TOÁN ---
if not final_df.empty and st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
    packer = Packer()
    packer.add_bin(Bin(c_choice, L, W, H, M))
    sku_colors = {s: c for s, c in zip(final_df['SKU'].unique(), ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'])}
    sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()

    for _, row in final_df.iterrows():
        for _ in range(int(row['Quantity'])):
            packer.add_item(Item(str(row['SKU']), float(row['Depth']), float(row['Width']), float(row['Height']), float(row['Weight'])))
    
    packer.pack()
    st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, sku_counts), use_container_width=True)

import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- CSS CHO GIAO DIỆN IN ---
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

# --- HÀM HỖ TRỢ ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    
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
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=2), showlegend=False, hoverinfo='none'
        ))
    fig.update_layout(scene=dict(aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30), height=700)
    return fig

# --- QUẢN LÝ DỮ LIỆU ---
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity'])

def on_editor_change():
    """Hàm callback xử lý ngay khi người dùng thao tác trên bảng"""
    state = st.session_state.manual_input  # Lấy trạng thái thay đổi từ key của editor
    df = st.session_state.manual_df
    
    # 1. Xử lý sửa ô (chọn SKU)
    for edit in state.get("edited_rows", {}):
        idx = int(edit)
        if "SKU" in state["edited_rows"][edit]:
            new_sku = state["edited_rows"][edit]["SKU"]
            # Lấy thông số từ Master nạp vào df
            master_row = edited_master[edited_master['SKU'] == new_sku]
            if not master_row.empty:
                df.at[idx, 'SKU'] = new_sku
                df.at[idx, 'Width'] = master_row.iloc[0]['Width']
                df.at[idx, 'Height'] = master_row.iloc[0]['Height']
                df.at[idx, 'Depth'] = master_row.iloc[0]['Depth']
                df.at[idx, 'Weight'] = master_row.iloc[0]['Weight']
                df.at[idx, 'Quantity'] = 1
        else:
            # Nếu sửa các cột khác thì cập nhật giá trị đó
            for col, val in state["edited_rows"][edit].items():
                df.at[idx, col] = val

    # 2. Xử lý thêm dòng mới
    for row in state.get("added_rows", {}):
        new_row = {'SKU': None, 'Width': 0, 'Height': 0, 'Depth': 0, 'Weight': 0, 'Quantity': 1}
        if "SKU" in row:
            new_sku = row["SKU"]
            master_row = edited_master[edited_master['SKU'] == new_sku]
            if not master_row.empty:
                new_row.update({
                    'SKU': new_sku,
                    'Width': master_row.iloc[0]['Width'],
                    'Height': master_row.iloc[0]['Height'],
                    'Depth': master_row.iloc[0]['Depth'],
                    'Weight': master_row.iloc[0]['Weight']
                })
        st.session_state.manual_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # 3. Xử lý xóa dòng
    if state.get("deleted_rows"):
        st.session_state.manual_df = df.drop(state["deleted_rows"]).reset_index(drop=True)

# --- GIAO DIỆN CHÍNH ---
st.title("🚚 Loading Map - GESIN")

cont_data = {
    "40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000], "45HC": [13556, 2352, 2698, 28000],
    "Tùy chỉnh": [0, 0, 0, 0]
}

with st.sidebar:
    st.header("⚙️ Cấu hình Phương tiện")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    if c_choice == "Tùy chỉnh":
        L, W, H, M = st.number_input("Dài"), st.number_input("Rộng"), st.number_input("Cao"), st.number_input("Tải trọng")
    else:
        specs = cont_data[c_choice]
        L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-30, specs[3]
        st.write(f"Lọt lòng: {L}x{W}x{H}")

    st.divider()
    st.header("🗂️ Danh mục SKU Master")
    master_file = st.file_uploader("Tải Master SKU", type="csv")
    if master_file: master_sku_df = pd.read_csv(master_file)
    else: master_sku_df = pd.DataFrame({'SKU': ['THD-6F2561-BKSV-13VN', 'THD-6F2561-AMBZ-13VN'], 'Width': [950, 630], 'Height': [765, 315], 'Depth': [1230, 645], 'Weight': [203, 37]})
    edited_master = st.data_editor(master_sku_df, num_rows="dynamic", key="master_editor")

# --- NHẬP HÀNG HÓA ---
tab1, tab2 = st.tabs(["📂 Tải CSV", "✍️ Nhập tay"])
final_df = pd.DataFrame()

with tab1:
    up = st.file_uploader("Chọn file đơn hàng", type="csv")
    if up: final_df = pd.read_csv(up)

with tab2:
    sku_list = edited_master['SKU'].dropna().unique().tolist()
    column_config = {
        "SKU": st.column_config.SelectboxColumn("Mã hàng (SKU)", options=sku_list, required=True),
        "Width": st.column_config.NumberColumn("Rộng"),
        "Height": st.column_config.NumberColumn("Cao"),
        "Depth": st.column_config.NumberColumn("Dài"),
        "Weight": st.column_config.NumberColumn("Nặng"),
        "Quantity": st.column_config.NumberColumn("Số lượng", min_value=1)
    }
    
    # Sử dụng on_change để bắt sự kiện thay đổi ngay lập tức
    st.data_editor(
        st.session_state.manual_df,
        column_config=column_config,
        num_rows="dynamic",
        key="manual_input",
        on_change=on_editor_change
    )
    
    if not st.session_state.manual_df.empty:
        clean = st.session_state.manual_df.dropna(subset=['SKU', 'Width'])
        final_df = pd.concat([final_df, clean], ignore_index=True) if not final_df.empty else clean

# --- TÍNH TOÁN ---
if not final_df.empty:
    st.subheader("Dữ liệu tổng hợp:")
    st.dataframe(final_df, use_container_width=True)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        with st.spinner('Đang tính toán...'):
            packer = Packer()
            packer.add_bin(Bin(c_choice, L, W, H, M))
            sku_colors = {sku: c for sku, c in zip(final_df['SKU'].unique(), ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'])}
            
            for _, row in final_df.iterrows():
                for _ in range(int(row['Quantity'])):
                    packer.add_item(Item(row['SKU'], float(row['Width']), float(row['Height']), float(row['Depth']), float(row['Weight'])))
            
            packer.pack()
            st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, {}), use_container_width=True)

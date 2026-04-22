import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- ĐOẠN 1: CSS ĐỂ CHỈ IN PHẦN KẾT QUẢ ---
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
            color=color, opacity=1, flatshading=True, name=f"{item.name} ({sku_counts.get(item.name)} kiện)", showlegend=show_in_legend
        ))
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=3), showlegend=False, hoverinfo='none'
        ))
    fig.update_layout(scene=dict(xaxis=dict(title='Dài'), yaxis=dict(title='Rộng'), zaxis=dict(title='Cao'), aspectmode='data'), margin=dict(l=0, r=0, b=0, t=30), height=800)
    return fig

# --- QUẢN LÝ DATABASE SKU (LƯU FILE) ---
DB_FILE = "master_sku_list.csv"

with st.sidebar:
    st.header("⚙️ Cấu hình Phương tiện")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    specs = cont_data[c_choice]
    L, W, H, M = (specs[0]-20, specs[1]-20, specs[2]-30, specs[3]) if c_choice != "Tùy chỉnh" else (6000, 2300, 2300, 15000)

    st.divider()
    st.header("🗂️ Danh mục SKU Hệ thống")
    
    # Load DB từ file hoặc tạo mới
    if os.path.exists(DB_FILE):
        master_df = pd.read_csv(DB_FILE)
    else:
        master_df = pd.DataFrame({'SKU': ['SOFA_A'], 'Width': [850.0], 'Height': [900.0], 'Depth': [2100.0], 'Weight': [75.0]})

    edited_master = st.data_editor(master_df, num_rows="dynamic", key="master_db")
    
    if st.button("💾 LƯU DANH MỤC VĨNH VIỄN"):
        edited_master.to_csv(DB_FILE, index=False)
        st.success("Đã lưu database!")

# --- PHẦN NHẬP DỮ LIỆU HÀNG HÓA ---
st.subheader("📋 Nhập danh sách hàng hóa")
tab1, tab2 = st.tabs(["📂 Tải file CSV", "✍️ Nhập tay trực tiếp"])

final_df = pd.DataFrame()

with tab1:
    uploaded_file = st.file_uploader("Kéo thả file CSV đơn hàng", type="csv")
    if uploaded_file:
        final_df = pd.read_csv(uploaded_file)

with tab2:
    sku_list = edited_master['SKU'].dropna().unique().tolist()
    
    # Khởi tạo session state cho bảng nhập tay và bộ theo dõi SKU cũ
    if "manual_df" not in st.session_state:
        st.session_state.manual_df = pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity'])
    if "previous_skus" not in st.session_state:
        st.session_state.previous_skus = {} # Lưu {index: SKU_value}

    manual_data = st.data_editor(
        st.session_state.manual_df, 
        num_rows="dynamic", 
        column_config={
            "SKU": st.column_config.SelectboxColumn("Mã hàng (SKU)", options=sku_list, required=True),
            "Quantity": st.column_config.NumberColumn("Số lượng", min_value=1, default=1)
        }, 
        key="manual_input"
    )

    # LOGIC: KIỂM TRA THAY ĐỔI SKU ĐỂ GHI ĐÈ THÔNG SỐ
    needs_rerun = False
    for index, row in manual_data.iterrows():
        current_sku = row['SKU']
        # Lấy SKU cũ của dòng này từ bộ nhớ đệm
        old_sku = st.session_state.previous_skus.get(index)

        # Nếu SKU hiện tại khác SKU cũ (bao gồm cả việc chọn lần đầu)
        if pd.notna(current_sku) and current_sku != old_sku:
            if current_sku in sku_list:
                # Tìm dữ liệu mới từ Master DB
                master_row = edited_master[edited_master['SKU'] == current_sku].iloc[0]
                manual_data.at[index, 'Width'] = master_row['Width']
                manual_data.at[index, 'Height'] = master_row['Height']
                manual_data.at[index, 'Depth'] = master_row['Depth']
                manual_data.at[index, 'Weight'] = master_row['Weight']
                # Cập nhật lại bộ nhớ đệm SKU cũ
                st.session_state.previous_skus[index] = current_sku
                needs_rerun = True

    if needs_rerun:
        st.session_state.manual_df = manual_data
        st.rerun()

    if not manual_data.empty:
        clean_manual = manual_data.dropna(subset=['SKU', 'Width', 'Height', 'Depth'])
        if not clean_manual.empty:
            final_df = pd.concat([final_df, clean_manual], ignore_index=True) if not final_df.empty else clean_manual

# --- TÍNH TOÁN VÀ HIỂN THỊ ---
if not final_df.empty:
    st.write("Dữ liệu tổng hợp:")
    st.dataframe(final_df, use_container_width=True)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        # Ép kiểu an toàn
        for col in ['Width', 'Height', 'Depth', 'Weight', 'Quantity']:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
        
        final_df = final_df[(final_df['Width'] > 0) & (final_df['Height'] > 0) & (final_df['Depth'] > 0)]

        if not final_df.empty:
            with st.spinner('🛠️ Đang tính toán...'):
                packer = Packer()
                packer.add_bin(Bin(c_choice, L, W, H, M))
                sku_colors = {sku: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'][i % 5] for i, sku in enumerate(final_df['SKU'].unique())}
                sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()

                for _, row in final_df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_item(Item(str(row['SKU']), float(row['Depth']), float(row['Width']), float(row['Height']), float(row['Weight'])))
                
                packer.pack()
                st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, sku_counts), use_container_width=True)
                
                st.components.v1.html("""
                    <script>function printPage() { window.parent.print(); }</script>
                    <button onclick="printPage()" style="background-color: #ff4b4b; color: white; padding: 15px; border: none; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer;">
                        🖨️ XUẤT FILE PDF CHO KHO
                    </button>
                """, height=800)

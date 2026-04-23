import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- ĐOẠN 1: CSS ĐỂ CHỈ IN PHẦN KẾT QUẢ ---
st.markdown("""
    <style>
    @media print {
        section[data-testid="stSidebar"], 
        .stButton, 
        .stDownloadButton, 
        footer, 
        header, 
        .stTabs,
        div[data-testid="stExpander"],
        div.stDataFrame {
            display: none !important;
        }
        .main .block-container {
            padding-top: 1rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# --- HÀM HỖ TRỢ ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)

    # Sàn gỗ & Tường
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
        scene=dict(
            xaxis=dict(title='Dài', range=[-100, L+100]),
            yaxis=dict(title='Rộng', range=[-100, W+100]),
            zaxis=dict(title='Cao', range=[-100, H+100]),
            aspectmode='data',
            camera=dict(eye=dict(x=1.8, y=1.8, z=1.2), center=dict(x=0.2, y=-0.2, z=-0.3))
        ),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.7)", font=dict(size=16)),
        margin=dict(l=0, r=0, b=0, t=30), height=800 
    )
    return fig

# --- QUẢN LÝ DỮ LIỆU ---
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity'])

def on_manual_change():
    state = st.session_state.manual_input
    df = st.session_state.manual_df
    
    for index_str, changes in state.get("edited_rows", {}).items():
        idx = int(index_str)
        if "SKU" in changes:
            new_sku = changes["SKU"]
            master_match = edited_master[edited_master['SKU'] == new_sku]
            if not master_match.empty:
                df.at[idx, 'SKU'] = new_sku
                df.at[idx, 'Width'] = master_match.iloc[0]['Width']
                df.at[idx, 'Height'] = master_match.iloc[0]['Height']
                df.at[idx, 'Depth'] = master_match.iloc[0]['Depth']
                df.at[idx, 'Weight'] = master_match.iloc[0]['Weight']
                df.at[idx, 'Quantity'] = 1
        else:
            for col, val in changes.items():
                df.at[idx, col] = val

    for row_data in state.get("added_rows", {}):
        new_row = {'SKU': None, 'Width': 0, 'Height': 0, 'Depth': 0, 'Weight': 0, 'Quantity': 1}
        if "SKU" in row_data:
            sku_val = row_data["SKU"]
            master_match = edited_master[edited_master['SKU'] == sku_val]
            if not master_match.empty:
                new_row.update({
                    'SKU': sku_val, 'Width': master_match.iloc[0]['Width'],
                    'Height': master_match.iloc[0]['Height'], 'Depth': master_match.iloc[0]['Depth'],
                    'Weight': master_match.iloc[0]['Weight']
                })
        st.session_state.manual_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    if state.get("deleted_rows"):
        st.session_state.manual_df = df.drop(state["deleted_rows"]).reset_index(drop=True)

# --- GIAO DIỆN CHÍNH ---
st.title("🚚 Loading Map - GESIN")

cont_data = {
    "40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000], "45HC": [13556, 2352, 2698, 28000],
    "40RF (Lạnh)": [11590, 2290, 2250, 27000], "20RF (Lạnh)": [5450, 2290, 2260, 24000],
    "Tùy chỉnh": [0, 0, 0, 0]
}

with st.sidebar:
    st.header("⚙️ Cấu hình Phương tiện")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    if c_choice == "Tùy chỉnh":
        L, W, H, M = st.number_input("Dài (mm)", value=6000), st.number_input("Rộng (mm)", value=2300), st.number_input("Cao (mm)", value=2300), st.number_input("Tải trọng (kg)", value=15000)
    else:
        specs = cont_data[c_choice]
        L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-30, specs[3]
        st.success(f"📌 Thông số lọt lòng {c_choice}:")
        st.write(f"Dài: {L}mm | Rộng: {W}mm | Cao: {H}mm")

    st.divider()
    st.header("🗂️ Danh mục SKU Hệ thống")
    st.caption("Thư mục file: `\\\\10.5.4.9\\gesinvn\\Customs\\13. Share\\06. ITEM PACKING\\`")
    
    master_file = st.file_uploader("Tải DMSKU.csv từ máy tính/ổ mạng", type="csv")
    if master_file: 
        master_sku_df = pd.read_csv(master_file)
    else: 
        master_sku_df = pd.DataFrame({'SKU': ['SOFA_A', 'TABLE_B'], 'Width': [850.0, 1000.0], 'Height': [900.0, 750.0], 'Depth': [2100.0, 1600.0], 'Weight': [75.0, 45.0]})
    
    edited_master = st.data_editor(master_sku_df, num_rows="dynamic", key="master_editor")

# --- PHẦN NHẬP DỮ LIỆU ---
st.subheader("📋 Nhập danh sách hàng hóa")
tab1, tab2 = st.tabs(["📂 Tải file CSV", "✍️ Nhập tay trực tiếp"])

final_df = pd.DataFrame()

with tab1:
    uploaded_file = st.file_uploader("Kéo thả file CSV đơn hàng", type="csv")
    if uploaded_file: final_df = pd.read_csv(uploaded_file)

with tab2:
    sku_list = edited_master['SKU'].dropna().unique().tolist()
    column_config = {
        "SKU": st.column_config.SelectboxColumn("Mã hàng (SKU)", options=sku_list, required=True),
        "Width": st.column_config.NumberColumn("Rộng (mm)", format="%d"),
        "Height": st.column_config.NumberColumn("Cao (mm)", format="%d"),
        "Depth": st.column_config.NumberColumn("Dài/Sâu (mm)", format="%d"),
        "Weight": st.column_config.NumberColumn("Nặng (kg)", format="%d"),
        "Quantity": st.column_config.NumberColumn("Số lượng (Kiện)", format="%d", min_value=1, default=1)
    }
    
    st.data_editor(
        st.session_state.manual_df,
        num_rows="dynamic",
        column_config=column_config,
        key="manual_input",
        on_change=on_manual_change
    )
    
    if not st.session_state.manual_df.empty:
        clean_manual = st.session_state.manual_df.dropna(subset=['SKU', 'Width'])
        final_df = pd.concat([final_df, clean_manual], ignore_index=True) if not final_df.empty else clean_manual

# --- XỬ LÝ TÍNH TOÁN ---
if not final_df.empty:
    st.write("Dữ liệu tổng hợp để tính toán:")
    st.dataframe(final_df, use_container_width=True)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        for col in ['Width', 'Height', 'Depth', 'Weight', 'Quantity']:
            final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
        final_df = final_df[final_df['Width'] > 0]

        if not final_df.empty:
            total_cargo_cbm = sum((row['Width']/1000 * row['Height']/1000 * row['Depth']/1000 * row['Quantity']) for _, row in final_df.iterrows())
            with st.spinner('🛠️ Đang tính toán...'):
                packer = Packer()
                packer.add_bin(Bin(c_choice, L, W, H, M))
                palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf']
                sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(final_df['SKU'].unique())}
                sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()

                for _, row in final_df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_item(Item(str(row['SKU']), float(row['Depth']), float(row['Width']), float(row['Height']), float(row['Weight'])))
                
                try:
                    packer.pack()
                    selected_bin = packer.bins[0]
                    st.info(f"📊 Container: {c_choice} | Tổng hàng: {total_cargo_cbm:.3f} m³")
                    st.plotly_chart(draw_3d_loading(selected_bin, sku_colors, sku_counts), use_container_width=True)
                    st.components.v1.html("""
                        <script>function printPage() { window.parent.print(); }</script>
                        <button onclick="printPage()" style="background-color: #ff4b4b; color: white; padding: 15px 32px; border: none; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer;">
                            🖨️ XUẤT FILE PDF CHO KHO (CHỈ IN SƠ ĐỒ)
                        </button>""", height=100)
                except Exception as e:
                    st.error(f"Lỗi: {e}")

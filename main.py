import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(page_title="Gesin Container Optimizer", layout="wide")

# --- HÀM VẼ 3D (TỪ BƯỚC TRƯỚC) ---
def draw_3d_loading(bin_obj):
    fig = go.Figure()
    d, r, c = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    
    for i, item in enumerate(bin_obj.items):
        x, y, z = item.position
        w, h, d_item = item.get_dimension()
        color = colors[i % len(colors)]
        
        # Vẽ khối hộp cho mỗi kiện hàng
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            opacity=0.7, color=color, name=item.name
        ))

    fig.update_layout(
        scene=dict(xaxis_title='Dài', yaxis_title='Rộng', zaxis_title='Cao'),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    return fig

# --- GIAO DIỆN CHÍNH ---
st.title("📦 Tối ưu hóa đóng hàng - Duy Nghiệp Gesin")

with st.sidebar:
    st.header("1. Cài đặt Container")
    c_type = st.selectbox("Loại Container", ["40HC", "20DC"])
    # Thông số chuẩn trừ đi 20mm dung sai
    if c_type == "40HC":
        L, W, H, M = 12012, 2332, 2678, 28000
    else:
        L, W, H, M = 5878, 2332, 2373, 28000
    st.info(f"Kích thước lọt lòng sử dụng: {L}x{W}x{H} (mm)")

st.subheader("2. Tải lên Packing List (CSV)")
st.write("Mẫu file CSV cần có các cột: SKU, Width, Height, Depth, Weight, Quantity")
uploaded_file = st.file_uploader("Chọn file CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df) # Hiển thị bảng hàng hóa cho đồng nghiệp xem

    if st.button("🚀 BẮT ĐẦU XẾP HÀNG"):
        # KHỞI TẠO PACKER
        packer = Packer()
        container = Bin(c_type, L, W, H, M)
        packer.add_bin(container)

        # NẠP HÀNG TỪ FILE
        for _, row in df.iterrows():
            for _ in range(int(row['Quantity'])):
                packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))

        # TÍNH TOÁN
        packer.pack()
        
        # HIỂN THỊ KẾT QUẢ
        selected_bin = packer.bins[0]
        used_vol = float(selected_bin.get_total_volume())
        total_vol = float(selected_bin.volume)
        utilization = (used_vol / total_vol) * 100

        col1, col2 = st.columns(2)
        col1.metric("Kiện hàng đã xếp", f"{len(selected_bin.items)} / {len(packer.items)}")
        col2.metric("Tỷ lệ lấp đầy", f"{utilization:.2f} %")

        # VẼ SƠ ĐỒ 3D
        st.plotly_chart(draw_3d_loading(selected_bin), use_container_width=True)

import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Gesin Container Optimizer", layout="wide")

# --- HÀM VẼ 3D NÂNG CAO ---
def draw_3d_loading(bin_obj):
    fig = go.Figure()
    
    # Bảng màu đậm, rõ nét (Modern Palette)
    color_palette = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
    ]
    sku_colors = {}
    color_idx = 0

    d_max = float(bin_obj.width)
    r_max = float(bin_obj.height)
    c_max = float(bin_obj.depth)

    # 1. VẼ KHUNG CONTAINER (Hệ khung thép)
    # Vẽ các đường biên để tạo hình dáng container
    lines = [
        ([0, d_max], [0, 0], [0, 0]), ([0, d_max], [r_max, r_max], [0, 0]),
        ([0, d_max], [0, 0], [c_max, c_max]), ([0, d_max], [r_max, r_max], [c_max, c_max]),
        ([0, 0], [0, r_max], [0, 0]), ([d_max, d_max], [0, r_max], [0, 0]),
        ([0, 0], [0, r_max], [c_max, c_max]), ([d_max, d_max], [0, r_max], [c_max, c_max]),
        ([0, 0], [0, 0], [0, c_max]), ([d_max, d_max], [0, 0], [0, c_max]),
        ([0, 0], [r_max, r_max], [0, c_max]), ([d_max, d_max], [r_max, r_max], [0, c_max])
    ]
    
    for x_line, y_line, z_line in lines:
        fig.add_trace(go.Scatter3d(
            x=x_line, y=y_line, z=z_line,
            mode='lines', line=dict(color='black', width=4),
            showlegend=False, hoverinfo='none'
        ))

    # 2. VẼ KIỆN HÀNG (KHỐI ĐẶC)
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d_item = [float(p) for p in item.get_dimension()]
        
        if item.name not in sku_colors:
            sku_colors[item.name] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
        color = sku_colors[item.name]

        # Vẽ khối đặc với đường viền đen (Line) xung quanh mỗi kiện
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            opacity=1, 
            color=color,
            name=f"SKU: {item.name}",
            flatshading=True
        ))

    # CẤU HÌNH KHÔNG GIAN
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Chiều Dài (x)', range=[0, d_max], showbackground=True, backgroundcolor="rgb(230, 230, 230)"),
            yaxis=dict(title='Chiều Rộng (y)', range=[0, r_max], showbackground=True, backgroundcolor="rgb(200, 200, 200)"),
            zaxis=dict(title='Chiều Cao (z)', range=[0, c_max], showbackground=True, backgroundcolor="rgb(220, 220, 220)"),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    return fig

# --- GIAO DIỆN CHÍNH ---
st.title("🚢 Hệ thống Mô phỏng Đóng Container - Duy Nghiệp")

with st.sidebar:
    st.header("1. Cấu hình Container")
    c_type = st.selectbox("Chọn loại Container", ["40HC", "20DC"])
    # Thiết lập kích thước chuẩn lọt lòng
    L, W, H, M = (12012, 2332, 2678, 28000) if c_type == "40HC" else (5878, 2332, 2373, 28000)
    st.success(f"Đang sử dụng: {c_type}")
    st.write(f"Dài: {L} mm | Rộng: {W} mm | Cao: {H} mm")

st.subheader("2. Dữ liệu Hàng hóa (CSV)")
uploaded_file = st.file_uploader("Tải file Packing List của bạn lên đây", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Danh sách hàng hóa nhận được:")
    st.dataframe(df, height=150)

    if st.button("▶️ BẮT ĐẦU MÔ PHỎNG"):
        with st.spinner('Máy tính đang tìm phương án xếp tối ưu...'):
            packer = Packer()
            container = Bin(c_type, L, W, H, M)
            packer.add_bin(container)

            for _, row in df.iterrows():
                for _ in range(int(row['Quantity'])):
                    packer.add_item(Item(row['SKU'], row['Width'], row['Height'], row['Depth'], row['Weight']))

            packer.pack()
            selected_bin = packer.bins[0]
            
            # Tính chỉ số hiệu quả
            total_item_vol = sum(float(i.get_dimension()[0]) * float(i.get_dimension()[1]) * float(i.get_dimension()[2]) for i in selected_bin.items)
            utilization = (total_item_vol / (L*W*H)) * 100

            # Hiển thị chỉ số
            c1, c2, c3 = st.columns(3)
            c1.metric("Tổng số kiện", f"{len(selected_bin.items)} / {len(packer.items)}")
            c2.metric("Hiệu suất lấp đầy", f"{utilization:.2f} %")
            c3.metric("Không gian trống", f"{(100 - utilization):.2f} %")

            # Hiển thị sơ đồ 3D
            st.plotly_chart(draw_3d_loading(selected_bin), use_container_width=True)

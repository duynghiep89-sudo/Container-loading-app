import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Gesin Container Optimizer Pro", layout="wide")

def draw_3d_loading(bin_obj):
    fig = go.Figure()
    L = float(bin_obj.width)
    W = float(bin_obj.height)
    H = float(bin_obj.depth)

    # 1. VẼ ĐÁY CONTAINER (Màu gỗ)
    fig.add_trace(go.Mesh3d(
        x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0],
        color='#A52A2A', opacity=0.8, name='Sàn Container'
    ))

    # 2. VẼ TƯỜNG & TRẦN (Màu xám thép - trong suốt nhẹ để nhìn xuyên thấu)
    # Vách trái
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='lightgray', opacity=0.2, showlegend=False))
    # Vách phải
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='lightgray', opacity=0.2, showlegend=False))
    # Vách trong cùng (đáy cont)
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.3, showlegend=False))

    # 3. VẼ CÁC KIỆN HÀNG
    color_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf']
    sku_colors = {}
    color_idx = 0

    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d = [float(p) for p in item.get_dimension()]
        
        if item.name not in sku_colors:
            sku_colors[item.name] = color_palette[color_idx % len(color_palette)]
            color_idx += 1
        
        # Vẽ khối đặc
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d, z+d, z+d, z+d],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=sku_colors[item.name], opacity=1.0, # ĐẶC 100%
            flatshading=True, name=item.name
        ))
        
        # Vẽ ĐƯỜNG VIỀN ĐEN cho từng kiện hàng (Quan trọng để nhìn rõ như ảnh mẫu)
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d, z+d, z+d, z+d, z, z+d, z+d, z+d, z+d, z, z],
            mode='lines', line=dict(color='black', width=2), showlegend=False, hoverinfo='none'
        ))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Dài', range=[0, L]),
            yaxis=dict(title='Rộng', range=[0, W]),
            zaxis=dict(title='Cao', range=[0, H]),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )
    return fig

# --- GIAO DIỆN STREAMLIT ---
st.title("🚢 Gesin Container Loading Simulator")
st.write("Giải pháp đóng hàng chuyên nghiệp cho Duy Nghiệp")

with st.sidebar:
    st.header("Cấu hình")
    c_type = st.selectbox("Loại Cont", ["40HC", "20DC"])
    L, W, H, M = (12012, 2332, 2678, 28000) if c_type == "40HC" else (5878, 2332, 2373, 28000)

uploaded_file = st.file_uploader("Nạp file Packing List (CSV)", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    if st.button("🚀 Xếp hàng & Mô phỏng 3D"):
        packer = Packer()
        packer.add_bin(Bin(c_type, L, W, H, M))
        for _, row in df.iterrows():
            for _ in range(int(row['Quantity'])):
                packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))
        
        packer.pack()
        selected_bin = packer.bins[0]
        
        # Chỉ số hiệu quả
        vol_total = L * W * H
        vol_used = sum(float(i.get_dimension()[0])*float(i.get_dimension()[1])*float(i.get_dimension()[2]) for i in selected_bin.items)
        
        st.success(f"Hiệu suất lấp đầy: {(vol_used/vol_total)*100:.2f}%")
        st.plotly_chart(draw_3d_loading(selected_bin), use_container_width=True)

import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Gesin Container Loading Pro", layout="wide")

def draw_3d_loading(bin_obj, sku_colors):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)

    # 1. VẼ ĐÁY CONTAINER (Màu sàn gỗ)
    fig.add_trace(go.Mesh3d(
        x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0],
        color='#8B4513', opacity=1, name='Sàn gỗ', showlegend=False
    ))

    # 2. VẼ TƯỜNG (Trong suốt để nhìn xuyên thấu)
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.2, showlegend=False))

    # 3. VẼ CÁC KIỆN HÀNG
    added_to_legend = set()
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d = [float(p) for p in item.get_dimension()]
        color = sku_colors.get(item.name, '#808080')
        
        # Chỉ hiện tên SKU 1 lần trong bảng chú thích
        show_in_legend = False
        if item.name not in added_to_legend:
            show_in_legend = True
            added_to_legend.add(item.name)

        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d, z+d, z+d, z+d],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1, flatshading=True,
            name=item.name, showlegend=show_in_legend
        ))
        
        # Đường viền đen sắc nét
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d, z+d, z+d, z+d, z, z+d, z+d, z+d, z+d, z, z],
            mode='lines', line=dict(color='black', width=2), showlegend=False, hoverinfo='none'
        ))

    # CẤU HÌNH BẢNG CHÚ THÍCH GÓC DƯỚI BÊN TRÁI
    fig.update_layout(
        scene=dict(xaxis_title='Dài', yaxis_title='Rộng', zaxis_title='Cao', aspectmode='data'),
        legend=dict(
            orientation="v",
            yanchor="bottom", y=0.01,
            xanchor="left", x=0.01,
            bgcolor="rgba(255, 255, 255, 0.5)"
        ),
        margin=dict(l=0, r=0, b=0, t=30)
    )
    return fig

# --- GIAO DIỆN CHÍNH ---
st.title("🚢 Hệ thống Xếp hàng Ưu tiên - Duy Nghiệp Gesin")

with st.sidebar:
    st.header("Cấu hình")
    c_type = st.selectbox("Loại Container", ["40HC", "20DC"])
    L, W, H, M = (12012, 2332, 2678, 28000) if c_type == "40HC" else (5878, 2332, 2373, 28000)
    
uploaded_file = st.file_uploader("Nạp file CSV hàng hóa", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # Chọn SKU ưu tiên
    sku_list = df['SKU'].unique().tolist()
    priority_sku = st.multiselect("Chọn SKU ưu tiên xếp trước (Sắp xếp theo thứ tự chọn)", sku_list)

    if st.button("🚀 BẮT ĐẦU XẾP HÀNG"):
        packer = Packer()
        packer.add_bin(Bin(c_type, L, W, H, M))

        # THUẬT TOÁN ƯU TIÊN: Sắp xếp lại DataFrame theo danh sách ưu tiên
        df['priority'] = df['SKU'].apply(lambda x: priority_sku.index(x) if x in priority_sku else 999)
        df = df.sort_values(by='priority')

        # Gán màu cố định cho SKU
        palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(sku_list)}

        for _, row in df.iterrows():
            for _ in range(int(row['Quantity'])):
                packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))

        packer.pack()
        selected_bin = packer.bins[0]
        
        # Chỉ số
        vol_total = L * W * H
        vol_used = sum(float(i.get_dimension()[0])*float(i.get_dimension()[1])*float(i.get_dimension()[2]) for i in selected_bin.items)
        
        st.success(f"Hiệu suất lấp đầy: {(vol_used/vol_total)*100:.2f}% | Tổng số kiện: {len(selected_bin.items)}")
        st.plotly_chart(draw_3d_loading(selected_bin, sku_colors), use_container_width=True)

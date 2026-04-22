import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- HÀM TẠO FILE CSV MẪU ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- HÀM VẼ 3D ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)

    # 1. Sàn gỗ
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    # 2. Tường
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.2, showlegend=False))

    added_to_legend = set()
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d = [float(p) for p in item.get_dimension()]
        color = sku_colors.get(item.name, '#808080')
        show_in_legend = item.name not in added_to_legend
        if show_in_legend: added_to_legend.add(item.name)

        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d, z+d, z+d, z+d],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1, flatshading=True, name=f"{item.name} ({sku_counts.get(item.name)} kiện)", showlegend=show_in_legend
        ))
        # Viền đen sắc nét
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d, z+d, z+d, z+d, z, z+d, z+d, z+d, z+d, z, z],
            mode='lines', line=dict(color='black', width=2), showlegend=False, hoverinfo='none'
        ))

    fig.update_layout(scene=dict(aspectmode='data'), legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01), margin=dict(l=0, r=0, b=0, t=0))
    return fig

# --- GIAO DIỆN CHÍNH ---
st.title("🚚 Loading Map - GESIN")

# Danh mục kích thước tiêu chuẩn (Dài, Rộng, Cao, Tải trọng)
cont_data = {
    "40HC": [12032, 2352, 2698, 28000],
    "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000],
    "45HC": [13556, 2352, 2698, 28000],
    "40RF": [11590, 2290, 2250, 27000],
    "20RF": [5450, 2290, 2260, 24000],
    "Tùy chỉnh": [0, 0, 0, 0]
}

with st.sidebar:
    st.header("⚙️ Cấu hình Phương tiện")
    c_choice = st.selectbox("Chọn loại Container", list(cont_data.keys()))
    
    if c_choice == "Tùy chỉnh":
        L = st.number_input("Dài (mm)", 6000)
        W = st.number_input("Rộng (mm)", 2300)
        H = st.number_input("Cao (mm)", 2300)
        M = st.number_input("Tải trọng (kg)", 15000)
    else:
        specs = cont_data[c_choice]
        # Hệ thống tự động trừ 20mm dung sai lọt lòng để an toàn khi đóng hàng thực tế
        L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-20, specs[3]
        
        # HIỂN THỊ THÔNG SỐ ĐỂ KIỂM TRA CHÉO (Yêu cầu mới của Duy Nghiệp)
        st.success(f"📌 Thông số sử dụng cho {c_choice}:")
        st.write(f"**Dài:** {L} mm")
        st.write(f"**Rộng:** {W} mm")
        st.write(f"**Cao:** {H} mm")
        st.write(f"**Tải trọng:** {M:,} kg")
        st.caption("*(Đã trừ 20mm dung sai lọt lòng)*")
    
    st.divider()
    template_df = pd.DataFrame({'SKU': ['TABLE_A', 'CHAIR_B'], 'Width': [800, 500], 'Height': [750, 900], 'Depth': [1200, 500], 'Weight': [40, 15], 'Quantity': [10, 20]})
    st.download_button(label="📥 Tải file CSV mẫu", data=convert_df_to_csv(template_df), file_name='template_gesin.csv', mime='text/csv')

st.subheader("📋 Nhập liệu hàng hóa")
uploaded_file = st.file_uploader("Chọn file CSV đã điền dữ liệu", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("Bảng kiểm tra dữ liệu đầu vào:")
    st.table(df)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        # KIỂM TRA CBM (Dùng đơn vị Mét để chính xác tuyệt đối)
        total_cargo_cbm = sum(((row['Width']/1000) * (row['Height']/1000) * (row['Depth']/1000) * row['Quantity']) for _, row in df.iterrows())
        vessel_cbm = (L/1000) * (W/1000) * (H/1000)
        
        st.info(f"📊 Tổng CBM hàng hóa: **{total_cargo_cbm:.3f} m³** | Dung tích xe: **{vessel_cbm:.3f} m³**")
        
        if total_cargo_cbm > vessel_cbm:
            st.error(f"❌ DỪNG TÍNH TOÁN: Hàng hóa ({total_cargo_cbm:.2f} m³) lớn hơn dung tích xe ({vessel_cbm:.2f} m³).")
        else:
            with st.spinner('🛠️ Đang tính toán sơ đồ...'):
                df = df.sort_values(by='SKU')
                sku_counts = df.groupby('SKU')['Quantity'].sum().to_dict()
                
                packer = Packer()
                packer.add_bin(Bin(c_choice, L, W, H, M))

                palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf', '#E15F99', '#222A2A']
                sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(df['SKU'].unique())}

                for _, row in df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))

                packer.pack()
                selected_bin = packer.bins[0]
                
                if len(selected_bin.items) < len(packer.items):
                    st.warning(f"⚠️ Cảnh báo: Chỉ xếp được {len(selected_bin.items)}/{len(packer.items)} kiện.")
                else:
                    st.success(f"✅ Đã xếp đủ toàn bộ hàng vào phương tiện!")

                st.plotly_chart(draw_3d_loading(selected_bin, sku_colors, sku_counts), use_container_width=True)

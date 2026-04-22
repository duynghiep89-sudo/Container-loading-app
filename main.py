import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- HÀM TẠO FILE CSV MẪU ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- HÀM VẼ 3D TỐI ƯU DIỆN TÍCH ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)

    # 1. Sàn gỗ
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    
    # 2. Tường thép giả lập (Mờ hơn nữa để tập trung vào hàng)
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))

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
            mode='lines', line=dict(color='black', width=1.5), showlegend=False, hoverinfo='none'
        ))

    fig.update_layout(
        scene=dict(xaxis_title='Dài', yaxis_title='Rộng', zaxis_title='Cao', aspectmode='data'),
        # Đưa chú thích xuống dưới để mở rộng diện tích hiển thị 3D
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, bgcolor="rgba(255, 255, 255, 0.5)"),
        margin=dict(l=0, r=0, b=0, t=0),
        height=700 # Tăng chiều cao khung hình 3D
    )
    return fig

# --- GIAO DIỆN CHÍNH ---
st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🚚 Loading Map - GESIN</h1>", unsafe_allow_html=True)

cont_data = {
    "40HC": [12032, 2352, 2698, 28000], "40DC": [12032, 2352, 2393, 28000],
    "20GP": [5898, 2352, 2393, 28000], "45HC": [13556, 2352, 2698, 28000],
    "40RF": [11590, 2290, 2250, 27000], "20RF": [5450, 2290, 2260, 24000],
    "Tùy chỉnh": [0, 0, 0, 0]
}

with st.sidebar:
    st.header("⚙️ Cấu hình")
    c_choice = st.selectbox("Chọn phương tiện", list(cont_data.keys()))
    if c_choice == "Tùy chỉnh":
        L, W, H, M = st.number_input("Dài", value=6000), st.number_input("Rộng", value=2300), st.number_input("Cao", value=2300), st.number_input("Tải", value=15000)
    else:
        specs = cont_data[c_choice]
        L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-30, specs[3]
        st.success(f"📌 {c_choice}: {L}x{W}x{H} mm")
    
    st.divider()
    template_df = pd.DataFrame({'SKU': ['TABLE_A', 'CHAIR_B'], 'Width': [800, 500], 'Height': [750, 900], 'Depth': [1200, 500], 'Weight': [40, 15], 'Quantity': [10, 20]})
    st.download_button(label="📥 Tải file mẫu CSV", data=convert_df_to_csv(template_df), file_name='template_gesin.csv', mime='text/csv')

st.subheader("📋 Nhập danh sách hàng hóa")
tab1, tab2 = st.tabs(["📂 Tải CSV", "✍️ Nhập tay"])
final_df = pd.DataFrame()

with tab1:
    uploaded_file = st.file_uploader("Kéo thả file CSV", type="csv")
    if uploaded_file: final_df = pd.read_csv(uploaded_file)
with tab2:
    manual_data = st.data_editor(pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity']), num_rows="dynamic", key="manual_input")
    if not manual_data.empty and manual_data.dropna(subset=['SKU']).shape[0] > 0:
        clean_manual = manual_data.dropna(subset=['SKU'])
        final_df = pd.concat([final_df, clean_manual], ignore_index=True) if not final_df.empty else clean_manual

if not final_df.empty:
    with st.expander("🔍 Xem bảng dữ liệu chi tiết"):
        st.dataframe(final_df, use_container_width=True, hide_index=True)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        total_cargo_cbm = sum((row['Width']/1000 * row['Height']/1000 * row['Depth']/1000 * row['Quantity']) for _, row in final_df.iterrows())
        vessel_cbm = (L/1000 * W/1000 * H/1000)
        
        if total_cargo_cbm > vessel_cbm:
            st.error(f"❌ VƯỢT DUNG TÍCH: Hàng ({total_cargo_cbm:.2f} m³) > Xe ({vessel_cbm:.2f} m³).")
        else:
            with st.spinner('🛠️ Đang tính toán...'):
                final_df = final_df.sort_values(by='SKU')
                sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()
                packer = Packer()
                packer.add_bin(Bin(c_choice, L, W, H, M))
                palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf', '#E15F99', '#222A2A']
                sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(final_df['SKU'].unique())}

                for _, row in final_df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))
                packer.pack()
                selected_bin = packer.bins[0]

                # --- HIỂN THỊ KẾT QUẢ RỘNG TOÀN MÀN HÌNH ---
                st.divider()
                st.subheader("📍 PHƯƠNG ÁN ĐÓNG HÀNG")
                
                # Hiển thị biểu đồ 3D lớn ở giữa
                st.plotly_chart(draw_3d_loading(selected_bin, sku_colors, sku_counts), use_container_width=True)
                
                # Hiển thị thông số phụ ở dưới biểu đồ
                c1, c2, c3 = st.columns(3)
                c1.metric("Tổng CBM hàng", f"{total_cargo_cbm:.3f} m³")
                c2.metric("Số kiện đã xếp", f"{len(selected_bin.items)} / {len(packer.items)}")
                c3.metric("Hiệu suất lấp đầy", f"{(sum(float(i.get_dimension()[0])*float(i.get_dimension()[1])*float(i.get_dimension()[2]) for i in selected_bin.items)/(L*W*H))*100:.2f} %")

                # NÚT XUẤT PDF SỬ DỤNG JAVASCRIPT ĐỂ FIX LỖI KHÔNG IN ĐƯỢC
                st.divider()
                st.write("👉 *Hãy xoay góc nhìn 3D phù hợp nhất trước khi nhấn nút bên dưới:*")
                
                # Sử dụng HTML/JS để kích hoạt lệnh in trực tiếp từ cửa sổ cha
                st.components.v1.html(
                    """
                    <html>
                    <body>
                    <button onclick="parent.window.print()" style="
                        background-color: #ff4b4b; 
                        color: white; 
                        padding: 15px 32px; 
                        text-align: center; 
                        text-decoration: none; 
                        display: inline-block; 
                        font-size: 16px; 
                        margin: 4px 2px; 
                        cursor: pointer; 
                        border: none; 
                        border-radius: 8px; 
                        width: 100%;
                        font-weight: bold;
                    ">
                        🖨️ XUẤT FILE PDF / IN BÁO CÁO
                    </button>
                    </body>
                    </html>
                    """,
                    height=100,
                )

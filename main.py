import streamlit as st
import pandas as pd
from py3dbp import Packer, Bin, Item
import plotly.graph_objects as go

st.set_page_config(page_title="Loading Map - GESIN", layout="wide")

# --- HÀM TẠO FILE CSV MẪU ---
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

# --- HÀM VẼ 3D TỐI ƯU GÓC NHÌN & ĐƯỜNG VIỀN ---
def draw_3d_loading(bin_obj, sku_colors, sku_counts, container_type):
    fig = go.Figure()
    L, W, H = float(bin_obj.width), float(bin_obj.height), float(bin_obj.depth)

    # 1. Sàn gỗ
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], color='#8B4513', opacity=1, showlegend=False))
    
    # 2. Tường thép giả lập (Mờ để tập trung vào hàng)
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[0, 0, 0, 0], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, L, L, 0], y=[W, W, W, W], z=[0, 0, H, H], color='gray', opacity=0.05, showlegend=False))
    fig.add_trace(go.Mesh3d(x=[0, 0, 0, 0], y=[0, W, W, 0], z=[0, 0, H, H], color='gray', opacity=0.1, showlegend=False))

    # Dòng tiêu đề Container trong Legend (Ghi chú)
    fig.add_trace(go.Scatter3d(x=[None], y=[None], z=[None], mode='markers', 
                               marker=dict(color='white'), name=f"📦 CONTAINER: {container_type}"))

    added_to_legend = set()
    for item in bin_obj.items:
        x, y, z = [float(p) for p in item.position]
        w, h, d_item = [float(p) for p in item.get_dimension()]
        color = sku_colors.get(item.name, '#808080')
        
        show_in_legend = item.name not in added_to_legend
        if show_in_legend: added_to_legend.add(item.name)

        # Vẽ khối hàng đặc
        fig.add_trace(go.Mesh3d(
            x=[x, x, x+w, x+w, x, x, x+w, x+w],
            y=[y, y+h, y+h, y, y, y+h, y+h, y],
            z=[z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=color, opacity=1, flatshading=True, 
            name=f"{item.name} ({sku_counts.get(item.name)} kiện)", 
            showlegend=show_in_legend
        ))
        
        # ĐƯỜNG VIỀN NGĂN CÁCH SẮC NÉT (Width=3 theo yêu cầu)
        fig.add_trace(go.Scatter3d(
            x=[x, x+w, x+w, x, x, x, x+w, x+w, x, x, x, x, x+w, x+w, x+w, x+w],
            y=[y, y, y+h, y+h, y, y, y, y+h, y+h, y+h, y, y+h, y+h, y, y, y+h],
            z=[z, z, z, z, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z+d_item, z+d_item, z+d_item, z+d_item, z, z],
            mode='lines', line=dict(color='black', width=3), showlegend=False, hoverinfo='none'
        ))

    # CẤU HÌNH CAMERA: ƯU TIÊN GÓC DƯỚI & KHÔNG MẤT HÌNH
    fig.update_layout(
        scene=dict(
            xaxis=dict(title='Dài', range=[-100, L+100]),
            yaxis=dict(title='Rộng', range=[-100, W+100]),
            zaxis=dict(title='Cao', range=[-100, H+100]),
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.2), # Góc nhìn xéo từ trên xuống
                center=dict(x=0.2, y=0, z=-0.3) # Dịch tiêu điểm xuống sàn và hướng ra cửa
            )
        ),
        legend=dict(
            yanchor="top", y=0.99, 
            xanchor="left", x=0.01, 
            bgcolor="rgba(255, 255, 255, 0.7)",
            font=dict(size=16) # Cỡ chữ SKU lớn dễ đọc
        ),
        margin=dict(l=0, r=0, b=0, t=0),
        height=900 # Khung hình đủ lớn để quan sát
    )
    return fig

# --- GIAO DIỆN STREAMLIT ---
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
        L = st.number_input("Dài (mm)", value=6000)
        W = st.number_input("Rộng (mm)", value=2300)
        H = st.number_input("Cao (mm)", value=2300)
        M = st.number_input("Tải trọng (kg)", value=15000)
    else:
        specs = cont_data[c_choice]
        # Trừ dung sai biên và 3cm trần an toàn theo yêu cầu của Duy Nghiệp
        L, W, H, M = specs[0]-20, specs[1]-20, specs[2]-30, specs[3]
        st.success(f"📌 {c_choice}: {L}x{W}x{H} mm")
    
    st.divider()
    template_df = pd.DataFrame({'SKU': ['TABLE_A', 'CHAIR_B'], 'Width': [800, 500], 'Height': [750, 900], 'Depth': [1200, 500], 'Weight': [40, 15], 'Quantity': [10, 20]})
    st.download_button(label="📥 Tải file mẫu CSV", data=convert_df_to_csv(template_df), file_name='template_gesin.csv', mime='text/csv')

st.subheader("📋 Nhập danh sách hàng hóa")
tab1, tab2 = st.tabs(["📂 Tải file CSV", "✍️ Nhập tay trực tiếp"])
final_df = pd.DataFrame()

with tab1:
    uploaded_file = st.file_uploader("Kéo thả file CSV", type="csv")
    if uploaded_file: final_df = pd.read_csv(uploaded_file)
with tab2:
    column_config = {"SKU": st.column_config.TextColumn("Mã hàng (SKU)", required=True), "Quantity": st.column_config.NumberColumn("Số lượng", default=1)}
    manual_data = st.data_editor(pd.DataFrame(columns=['SKU', 'Width', 'Height', 'Depth', 'Weight', 'Quantity']), num_rows="dynamic", column_config=column_config, key="manual_input")
    if not manual_data.empty and manual_data.dropna(subset=['SKU']).shape[0] > 0:
        clean_manual = manual_data.dropna(subset=['SKU'])
        final_df = pd.concat([final_df, clean_manual], ignore_index=True) if not final_df.empty else clean_manual

if not final_df.empty:
    st.write("Dữ liệu tổng hợp:")
    st.dataframe(final_df, use_container_width=True)

    if st.button("🚀 BẮT ĐẦU TÍNH TOÁN"):
        # TÍNH TOÁN CBM CHUẨN XÁC
        total_cargo_cbm = sum((row['Width']/1000 * row['Height']/1000 * row['Depth']/1000 * row['Quantity']) for _, row in final_df.iterrows())
        vessel_cbm = (L/1000 * W/1000 * H/1000)
        
        with st.spinner('🛠️ Đang tính toán phương án tối ưu...'):
            sku_counts = final_df.groupby('SKU')['Quantity'].sum().to_dict()
            packer = Packer()
            packer.add_bin(Bin(c_choice, L, W, H, M))
            palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#bcbd22', '#17becf', '#E15F99', '#222A2A']
            sku_colors = {sku: palette[i % len(palette)] for i, sku in enumerate(final_df['SKU'].unique())}

            for _, row in final_df.iterrows():
                for _ in range(int(row['Quantity'])):
                    packer.add_item(Item(row['SKU'], row['Depth'], row['Width'], row['Height'], row['Weight']))
            packer.pack()
            
            # HIỂN THỊ THÔNG TIN KẾT QUẢ
            st.info(f"📊 Tổng hàng: {total_cargo_cbm:.3f} m³ | Dung tích xe: {vessel_cbm:.3f} m³")
            st.plotly_chart(draw_3d_loading(packer.bins[0], sku_colors, sku_counts, c_choice), use_container_width=True)

            # NÚT IN FIX LỖI TRÌNH DUYỆT
            st.components.v1.html(
                """
                <script>function printPage() { window.parent.print(); }</script>
                <button onclick="printPage()" style="
                    background-color: #ff4b4b; color: white; padding: 15px 32px; 
                    border: none; border-radius: 8px; width: 100%; font-weight: bold; cursor: pointer;
                ">
                    🖨️ XUẤT FILE PDF / IN BÁO CÁO CHO KHO
                </button>
                """,
                height=100,
            )

import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Cotizador mayorista", layout="wide")

# -----------------------------
# SESSION STATE
# -----------------------------
if "pedido" not in st.session_state:
    st.session_state.pedido = []

# -----------------------------
# CARGA DE DATOS
# -----------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("catalogo.xlsx", header=0, skiprows=[1])
    df.columns = df.columns.str.strip().str.upper()
    return df

df_original = load_data()
df = df_original.copy()

# -----------------------------
# HEADER
# -----------------------------
col_logo, col_title = st.columns([1,4])

with col_logo:
    try:
        st.image("logo.png", width=120)
    except:
        pass

with col_title:
    st.title("Cotizador mayorista")
    st.subheader("Snacks y alimentos")

# -----------------------------
# MODO CLIENTE NUEVO
# -----------------------------
if st.checkbox("Modo cliente nuevo"):
    st.info("""
👋 **Bienvenido al cotizador mayorista**

1. Selecciona tipo de compra  
2. Filtra productos por marca o categoría  
3. Ingresa cantidades  
4. Revisa el resumen  
5. Descarga tu cotización  

💡 A mayor volumen, mejor eficiencia logística
""")

# -----------------------------
# DATOS CLIENTE
# -----------------------------
st.subheader("Datos del cliente")
col1, col2, col3 = st.columns(3)
cliente = col1.text_input("Nombre empresa")
pais = col2.text_input("País destino")
email = col3.text_input("Email")
fecha = datetime.now().strftime("%Y-%m-%d")

st.divider()

# -----------------------------
# TIPO PEDIDO
# -----------------------------
pedido_tipo = st.radio("Tipo de pedido:", ["Cajas sueltas", "Pallet consolidado", "Contenedor"])
MOQ_val = 1 if pedido_tipo != "Contenedor" else 25
MOQ_label = "1 Caja" if MOQ_val == 1 else "25 Cajas"
st.info(f"MOQ por producto: {MOQ_label}")

st.divider()

# -----------------------------
# FILTROS
# -----------------------------
st.subheader("Filtros")
colf1, colf2, colf3 = st.columns(3)

search = colf1.text_input("Buscar producto")

marcas = ["Todas"] + sorted(df_original['MARCA'].dropna().unique().tolist())
marca_sel = colf2.selectbox("Marca", marcas)

categorias = ["Todas"] + sorted(df_original['CATEGORÍA'].dropna().unique().tolist())
categoria_sel = colf3.selectbox("Categoría", categorias)

if search:
    df = df[df['PRODUCTO'].astype(str).str.contains(search, case=False, na=False)]

if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

if categoria_sel != "Todas":
    df = df[df['CATEGORÍA'] == categoria_sel]

st.write(f"Productos mostrados: {len(df)}")

st.divider()

# -----------------------------
# CATALOGO AGRUPADO
# -----------------------------
for marca in sorted(df['MARCA'].dropna().unique()):
    df_marca = df[df['MARCA'] == marca]

    with st.expander(f"{marca}", expanded=False):

        cols = st.columns([3,2,2,2,2,2,2])
        headers = ["Producto","Marca","Presentación","Presentaciones por caja","MOQ","Precio Caja (USD)","Cantidad"]
        for col, h in zip(cols, headers):
            col.markdown(f"**{h}**")

        for i, row in df_marca.iterrows():

            producto = row.get('PRODUCTO', '')
            marca_val = row.get('MARCA', '')
            presentacion = row.get('PRESENTACIÓN', '')
            und_caja = row.get('PRESENTACIONES POR CAJA', '')

            precio_raw = row.get('PRECIO EXW CAJA USD', 0)
            try:
                precio = float(str(precio_raw).replace("USD","").replace(",",".").strip())
            except:
                precio = 0

            cols = st.columns([3,2,2,2,2,2,2])
            cols[0].write(producto)
            cols[1].write(marca_val)
            cols[2].write(presentacion)
            cols[3].write(und_caja)
            cols[4].write(MOQ_label)
            cols[5].write(f"USD {precio:,.2f}")

            cantidad = cols[6].number_input("", min_value=0, step=MOQ_val, key=f"qty_{i}")

            if cantidad > 0:
                st.success("✔ Agregado al pedido")

                cantidad_label = f"{cantidad} Caja" if cantidad == 1 else f"{cantidad} Cajas"

                item = {
                    "Producto": producto,
                    "Marca": marca_val,
                    "Cantidad": cantidad_label,
                    "Precio": precio,
                    "Total": cantidad * precio
                }

                existe = False
                for idx, p in enumerate(st.session_state.pedido):
                    if p["Producto"] == producto:
                        st.session_state.pedido[idx] = item
                        existe = True
                        break

                if not existe:
                    st.session_state.pedido.append(item)

st.divider()

# -----------------------------
# FUNCION PDF
# -----------------------------
def generar_pdf(df, total_cajas, total_valor, tipo_envio):

    file_path = "cotizacion.pdf"
    doc = SimpleDocTemplate(file_path, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)

    elements = []
    styles = getSampleStyleSheet()

    wrap_style = ParagraphStyle(name='wrap', fontSize=8, leading=9)

    def campo(label, valor):
        valor = valor if valor else "______________________"
        return Paragraph(f"<b>{label}:</b> {valor}", styles['Normal'])

    try:
        elements.append(Image("logo.png", width=100, height=50))
    except:
        pass

    elements.append(Paragraph("Cotización", styles['Title']))
    elements.append(Spacer(1,12))

    elements.append(campo("Cliente", cliente))
    elements.append(campo("País", pais))
    elements.append(campo("Email", email))
    elements.append(campo("Fecha", fecha))

    elements.append(Spacer(1,12))

    data = [["Producto","Marca","Cantidad","Precio","Total"]]

    for _, row in df.iterrows():
        data.append([
            Paragraph(str(row['Producto']), wrap_style),
            row['Marca'],
            row['Cantidad'],
            f"USD {row['Precio']:,.2f}",
            f"USD {row['Total']:,.2f}"
        ])

    table = Table(data, colWidths=[150,100,90,90,90])

    table.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),colors.grey),
        ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
        ('GRID',(0,0),(-1,-1),1,colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1,12))

    totales_data = [
        ["", f"Total cajas: {total_cajas} Cajas"],
        ["", f"Total USD: USD {total_valor:,.2f}"],
        ["", f"Envío: {tipo_envio}"]
    ]

    totales_table = Table(totales_data, colWidths=[300,200])
    totales_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold')
    ]))

    elements.append(totales_table)

    doc.build(elements)
    return file_path

# -----------------------------
# FUNCION EXCEL
# -----------------------------
def generar_excel(df, cliente, pais, email, total_cajas, total_valor, tipo_envio):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        df_export = df.copy()
        df_export["Precio"] = df_export["Precio"].apply(lambda x: f"USD {x:,.2f}")
        df_export["Total"] = df_export["Total"].apply(lambda x: f"USD {x:,.2f}")

        df_export.to_excel(writer, index=False, sheet_name='Pedido')

        resumen = pd.DataFrame({
            "Campo": ["Cliente","País","Email","Total cajas","Total USD","Tipo de envío"],
            "Valor": [
                cliente, pais, email,
                total_cajas,
                f"USD {total_valor:,.2f}",
                tipo_envio
            ]
        })

        resumen.to_excel(writer, index=False, sheet_name='Resumen')

    output.seek(0)
    return output

# -----------------------------
# RESUMEN
# -----------------------------
st.subheader("Resumen del pedido")

if st.session_state.pedido:

    pedido_df = pd.DataFrame(st.session_state.pedido)

    total_cajas = sum([int(str(x).split()[0]) for x in pedido_df["Cantidad"]])
    total_valor = pedido_df["Total"].sum()
    pallets = total_cajas / 36

    if pedido_tipo == "Cajas sueltas":
        tipo_envio = "Carga suelta / Courier"
    elif pedido_tipo == "Pallet consolidado":
        tipo_envio = "No cumple mínimo" if total_cajas < 80 else f"{round(pallets,1)} pallets"
    else:
        tipo_envio = "Contenedor"

    pedido_df_display = pedido_df.copy()
    pedido_df_display["Precio"] = pedido_df_display["Precio"].apply(lambda x: f"USD {x:,.2f}")
    pedido_df_display["Total"] = pedido_df_display["Total"].apply(lambda x: f"USD {x:,.2f}")

    st.dataframe(pedido_df_display, use_container_width=True)

    st.metric("Total cajas", f"{total_cajas} Cajas")
    st.metric("Total USD", f"USD {total_valor:,.2f}")
    st.metric("Pallets estimados", round(pallets,2))

    st.success(f"Tipo de envío sugerido: {tipo_envio}")

    pdf_file = generar_pdf(pedido_df, total_cajas, total_valor, tipo_envio)
    excel_file = generar_excel(pedido_df, cliente, pais, email, total_cajas, total_valor, tipo_envio)

    col1, col2 = st.columns(2)

    with col1:
        with open(pdf_file, "rb") as f:
            st.download_button("📄 Descargar PDF", f, file_name="cotizacion.pdf")

    with col2:
        st.download_button(
            "📊 Descargar Excel",
            data=excel_file,
            file_name="pedido.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Aún no has agregado productos")

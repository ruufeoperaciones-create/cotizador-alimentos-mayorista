import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

st.set_page_config(page_title="Cotizador mayorista", layout="wide")

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
pedido_tipo = st.radio(
    "Tipo de pedido:",
    ["Cajas sueltas", "Pallet consolidado", "Contenedor"]
)

MOQ_val = 1 if pedido_tipo != "Contenedor" else 25
MOQ_label = "1 Caja" if MOQ_val == 1 else "25 Cajas"

st.info(f"MOQ por producto: {MOQ_label}")

st.divider()

# -----------------------------
# FILTROS
# -----------------------------
st.subheader("Filtros")

colf1, colf2 = st.columns(2)

with colf1:
    search = st.text_input("Buscar producto")

with colf2:
    marcas = ["Todas"] + sorted(df_original['MARCA'].dropna().unique().tolist())
    marca_sel = st.selectbox("Filtrar por marca", marcas)

if search:
    df = df[df['PRODUCTO'].astype(str).str.contains(search, case=False, na=False)]

if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

st.write(f"Productos mostrados: {len(df)}")

st.divider()

# -----------------------------
# ENCABEZADOS
# -----------------------------
cols = st.columns([3,2,2,2,2,2,2])
headers = [
    "Producto",
    "Marca",
    "Presentación",
    "Presentaciones por caja",
    "MOQ",
    "Precio Caja (USD)",
    "Cantidad"
]

for col, h in zip(cols, headers):
    col.markdown(f"**{h}**")

# Usar session_state para persistencia
if "pedido" not in st.session_state:
    st.session_state.pedido = []

pedido = st.session_state.pedido

# -----------------------------
# LISTADO
# -----------------------------
for i, row in df.iterrows():
    cols = st.columns([3,2,2,2,2,2,2])

    producto = row.get('PRODUCTO', '')
    marca = row.get('MARCA', '')
    presentacion = row.get('PRESENTACIÓN', '')
    und_caja = row.get('PRESENTACIONES POR CAJA', '')
    precio = float(row.get('PRECIO EXW CAJA USD', 0))

    cols[0].write(producto)
    cols[1].write(marca)
    cols[2].write(presentacion)
    cols[3].write(und_caja)
    cols[4].write(MOQ_label)
    cols[5].write(f"USD {precio:,.2f}")

    cantidad = cols[6].number_input(
        "",
        min_value=0,
        step=MOQ_val,
        key=f"qty_{i}"
    )

    if pedido_tipo == "Contenedor" and cantidad > 0 and cantidad < 25:
        st.warning("MOQ 25 cajas requerido")

    if cantidad > 0:
        cantidad_label = f"{cantidad} Caja" if cantidad == 1 else f"{cantidad} Cajas"
        item = {
            "Producto": producto,
            "Marca": marca,
            "Cantidad": cantidad_label,
            "Precio": precio,
            "Total": cantidad * precio
        }

        # Evitar duplicados (actualiza si ya existe)
        existe = False
        for i, p in enumerate(st.session_state.pedido):
            if p["Producto"] == producto:
                st.session_state.pedido[i] = item
                existe = True
                break
        if not existe:
            st.session_state.pedido.append(item)

st.divider()

# -----------------------------
# RESULTADOS
# -----------------------------
st.subheader("Resumen del pedido")

if pedido:
    pedido_df = pd.DataFrame(pedido)

    total_cajas = sum([int(str(x).split()[0]) for x in pedido_df["Cantidad"]])
    total_valor = pedido_df["Total"].sum()
    pallets = total_cajas / 36

    if pedido_tipo == "Cajas sueltas":
        tipo_envio = "Carga suelta / Courier"
    elif pedido_tipo == "Pallet consolidado":
        tipo_envio = "No cumple mínimo" if total_cajas < 80 else f"{round(pallets,1)} pallets"
    else:
        if pallets <= 11:
            tipo_envio = "Contenedor 20FT"
        elif pallets <= 24:
            tipo_envio = "Contenedor 40FT"
        else:
            tipo_envio = "Más de un contenedor"

    pedido_df_display = pedido_df.copy()
    pedido_df_display["Precio"] = pedido_df_display["Precio"].apply(lambda x: f"USD {x:,.2f}")
    pedido_df_display["Total"] = pedido_df_display["Total"].apply(lambda x: f"USD {x:,.2f}")

    st.dataframe(pedido_df_display, use_container_width=True)

    st.metric("Total cajas", f"{total_cajas} Cajas")
    st.metric("Total USD", f"USD {total_valor:,.2f}")
    st.metric("Pallets estimados", round(pallets,2))

    st.success(f"Tipo de envío sugerido: {tipo_envio}")

    # -----------------------------
    # PDF
    # -----------------------------
    def generar_pdf(df, total_cajas, total_valor, tipo_envio):
        file_path = "cotizacion.pdf"
        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        try:
            elements.append(Image("logo.png", width=100, height=50))
        except:
            pass

        elements.append(Paragraph("Cotización", styles['Title']))
        elements.append(Spacer(1,12))

        elements.append(Paragraph(f"Cliente: {cliente}", styles['Normal']))
        elements.append(Paragraph(f"País: {pais}", styles['Normal']))
        elements.append(Paragraph(f"Email: {email}", styles['Normal']))
        elements.append(Paragraph(f"Fecha: {fecha}", styles['Normal']))
        elements.append(Spacer(1,12))

        data = [["Producto","Marca","Cantidad","Precio","Total"]]

        for _, row in df.iterrows():
            data.append([
                row['Producto'],
                row['Marca'],
                row['Cantidad'],
                f"USD {row['Precio']:,.2f}",
                f"USD {row['Total']:,.2f}"
            ])

        # Anchos corregidos (SIN ERROR)
        col_widths = [150, 100, 90, 90, 90]
        table = Table(data, colWidths=col_widths)

        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.grey),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('GRID',(0,0),(-1,-1),1,colors.black)
        ]))

        elements.append(table)
        elements.append(Spacer(1,12))
        elements.append(Paragraph(f"Total cajas: {total_cajas} Cajas", styles['Normal']))
        elements.append(Paragraph(f"Total USD: USD {total_valor:,.2f}", styles['Normal']))
        elements.append(Paragraph(f"Envío: {tipo_envio}", styles['Normal']))

        doc.build(elements)
        return file_path

    pdf_file = generar_pdf(pedido_df, total_cajas, total_valor, tipo_envio)

    with open(pdf_file, "rb") as f:
        st.download_button("Descargar cotización PDF", f, file_name="cotizacion.pdf")

else:
    st.info("Aún no has agregado productos")

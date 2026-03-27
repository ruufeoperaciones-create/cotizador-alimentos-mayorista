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
2. Filtra productos  
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

marcas = ["Todas"] + sorted(df_original['MARCA'].dropna().unique())
marca_sel = colf2.selectbox("Marca", marcas)

categorias = ["Todas"] + sorted(df_original['CATEGORÍA'].dropna().unique())
categoria_sel = colf3.selectbox("Categoría", categorias)

if search:
    df = df[df['PRODUCTO'].astype(str).str.contains(search, case=False)]

if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

if categoria_sel != "Todas":
    df = df[df['CATEGORÍA'] == categoria_sel]

# -----------------------------
# CATALOGO
# -----------------------------
for marca in sorted(df['MARCA'].dropna().unique()):
    df_marca = df[df['MARCA'] == marca]

    with st.expander(marca):
        for i, row in df_marca.iterrows():

            producto = row.get('PRODUCTO', '')
            precio_raw = row.get('PRECIO EXW CAJA USD', 0)

            try:
                precio = float(str(precio_raw).replace("USD", "").replace(",", "."))
            except:
                precio = 0

            col1, col2, col3 = st.columns([4,2,2])

            col1.write(producto)
            col2.write(f"USD {precio:,.2f}")

            cantidad = col3.number_input("Cantidad", min_value=0, step=MOQ_val, key=f"qty_{i}")

            if cantidad > 0:
                item = {
                    "Producto": producto,
                    "Marca": marca,
                    "Cantidad": f"{cantidad} Caja" if cantidad == 1 else f"{cantidad} Cajas",
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
        valor = valor if valor else "____________________"
        return Paragraph(f"<b>{label}:</b> {valor}", styles['Normal'])

    elements.append(Paragraph("Cotización", styles['Title']))
    elements.append(Spacer(1,10))

    elements.append(campo("Cliente", cliente))
    elements.append(campo("País", pais))
    elements.append(campo("Email", email))
    elements.append(campo("Fecha", fecha))
    elements.append(Spacer(1,10))

    data = [["Producto","Marca","Cantidad","Precio","Total"]]

    for _, row in df.iterrows():
        data.append([
            Paragraph(str(row['Producto']), wrap_style),
            row['Marca'],
            row['Cantidad'],
            f"USD {row['Precio']:,.2f}",
            f"USD {row['Total']:,.2f}"
        ])

    table = Table(data, colWidths=[150,100,80,80,80])
    table.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),1,colors.black),
        ('BACKGROUND',(0,0),(-1,0),colors.grey)
    ]))

    elements.append(table)
    elements.append(Spacer(1,10))

    totales = [
        ["", f"Total cajas: {total_cajas}"],
        ["", f"Total USD: {total_valor:,.2f}"],
        ["", f"Envío: {tipo_envio}"]
    ]

    t = Table(totales, colWidths=[300,200])
    t.setStyle(TableStyle([('ALIGN',(1,0),(-1,-1),'RIGHT')]))

    elements.append(t)

    doc.build(elements)
    return file_path

# -----------------------------
# FUNCION EXCEL
# -----------------------------
def generar_excel(df, cliente, pais, email, total_cajas, total_valor, tipo_envio):
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export = df.copy()
        df_export.to_excel(writer, index=False, sheet_name='Pedido')

        resumen = pd.DataFrame({
            "Campo": ["Cliente","País","Email","Total cajas","Total USD","Tipo de envío"],
            "Valor": [cliente,pais,email,total_cajas,total_valor,tipo_envio]
        })

        resumen.to_excel(writer, index=False, sheet_name='Resumen')

    output.seek(0)
    return output

# -----------------------------
# RESUMEN
# -----------------------------
if st.session_state.pedido:

    pedido_df = pd.DataFrame(st.session_state.pedido)

    total_cajas = sum([int(x.split()[0]) for x in pedido_df["Cantidad"]])
    total_valor = pedido_df["Total"].sum()
    pallets = total_cajas / 36

    if pedido_tipo == "Cajas sueltas":
        tipo_envio = "Courier"
    elif pedido_tipo == "Pallet consolidado":
        tipo_envio = f"{round(pallets,1)} pallets"
    else:
        tipo_envio = "Contenedor"

    st.dataframe(pedido_df)

    st.metric("Total cajas", total_cajas)
    st.metric("Total USD", f"{total_valor:,.2f}")

    st.success(f"Envío sugerido: {tipo_envio}")

    pdf_file = generar_pdf(pedido_df, total_cajas, total_valor, tipo_envio)
    excel_file = generar_excel(pedido_df, cliente, pais, email, total_cajas, total_valor, tipo_envio)

    col1, col2 = st.columns(2)

    with col1:
        with open(pdf_file, "rb") as f:
            st.download_button("📄 Descargar PDF", f, file_name="cotizacion.pdf")

    with col2:
        st.download_button("📊 Descargar Excel", excel_file, file_name="pedido.xlsx")

else:
    st.info("Aún no has agregado productos")

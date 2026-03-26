import streamlit as st
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

st.set_page_config(page_title="Cotizador mayorista", layout="wide")

# -----------------------------
# SESSION STATE
# -----------------------------
if "pedido" not in st.session_state:
    st.session_state.pedido = []

if "show_tutorial" not in st.session_state:
    st.session_state.show_tutorial = False

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
    👋 Bienvenido:
    1. Selecciona tipo de pedido
    2. Usa filtros para encontrar productos
    3. Ingresa cantidades
    4. Revisa resumen abajo
    5. Descarga tu cotización
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

with colf1:
    search = st.text_input("Buscar producto")

with colf2:
    marcas = ["Todas"] + sorted(df_original['MARCA'].dropna().unique().tolist())
    marca_sel = st.selectbox("Marca", marcas)

with colf3:
    categorias = ["Todas"] + sorted(df_original['CATEGORÍA'].dropna().unique().tolist()) if 'CATEGORÍA' in df_original.columns else ["Todas"]
    categoria_sel = st.selectbox("Categoría", categorias)

# Aplicar filtros
if search:
    df = df[df['PRODUCTO'].astype(str).str.contains(search, case=False, na=False)]

if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

if categoria_sel != "Todas" and 'CATEGORÍA' in df.columns:
    df = df[df['CATEGORÍA'] == categoria_sel]

st.write(f"Productos mostrados: {len(df)}")

# Botones navegación
col_nav1, col_nav2 = st.columns(2)
with col_nav1:
    if st.button("⬆ Volver arriba"):
        st.markdown("#")
with col_nav2:
    if st.button("✅ Finalizar pedido"):
        st.markdown("## Resumen del pedido")

st.divider()

# -----------------------------
# AGRUPAR POR MARCA
# -----------------------------
pedido = st.session_state.pedido

for marca in sorted(df['MARCA'].dropna().unique()):
    df_marca = df[df['MARCA'] == marca]

    with st.expander(f"{marca}", expanded=False):
        cols = st.columns([3,2,2,2,2,2,2])
        headers = ["Producto","Marca","Presentación","Presentaciones por caja","MOQ","Precio Caja (USD)","Cantidad"]
        for col, h in zip(cols, headers):
            col.markdown(f"**{h}**")

        for i, row in df_marca.iterrows():
            cols = st.columns([3,2,2,2,2,2,2])

            producto = row.get('PRODUCTO', '')
            marca_val = row.get('MARCA', '')
            presentacion = row.get('PRESENTACIÓN', '')
            und_caja = row.get('PRESENTACIONES POR CAJA', '')
            precio = float(row.get('PRECIO EXW CAJA USD', 0))

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
# RESUMEN
# -----------------------------
st.subheader("Resumen del pedido")

if st.session_state.pedido:
    pedido_df = pd.DataFrame(st.session_state.pedido)

    total_cajas = sum([int(str(x).split()[0]) for x in pedido_df["Cantidad"]])
    total_valor = pedido_df["Total"].sum()
    pallets = total_cajas / 36

    pedido_df_display = pedido_df.copy()
    pedido_df_display["Precio"] = pedido_df_display["Precio"].apply(lambda x: f"USD {x:,.2f}")
    pedido_df_display["Total"] = pedido_df_display["Total"].apply(lambda x: f"USD {x:,.2f}")

    st.dataframe(pedido_df_display, use_container_width=True)

    st.metric("Total cajas", f"{total_cajas} Cajas")
    st.metric("Total USD", f"USD {total_valor:,.2f}")
    st.metric("Pallets estimados", round(pallets,2))

else:
    st.info("Aún no has agregado productos")

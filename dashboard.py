import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import base64
import datetime
from fpdf import FPDF
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA --
st.set_page_config(
    page_title="FerroVixia - Monitorización", 
    page_icon="paginita.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.logo("logo_ferrovixia.png", icon_image="logo_ferrovixia_pequeno.png")
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Convertimos tu logo
try:
    logo_base64 = get_base64("logo_ferrovixia.png")
except:
    logo_base64 = "" # Por si el archivo no existe aún

color_fondo = "#7d192a"  
color_secundario = "#7d192a92"
color_texto = "#FFFFFF" 

html_header = f"""
<style>
/* 1. Ocultar Header de Streamlit */
[data-testid="stHeader"] {{
    display: none !important;
}}

.block-container {{
    padding-top: 0rem !important;
}}

div[data-baseweb="tab-list"] {{
    width: 100% !important;
    display: flex !important;
}}

/* Hacer que cada botón (pestaña) crezca exactamente lo mismo */
button[data-baseweb="tab"] {{
    flex: 1 !important;
}}

/* Centrar el texto dentro de la pestaña */
button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p {{
    margin: auto !important;
    text-align: center !important;
    font-size: 18px !important; /* Puedes cambiar el tamaño si quieres que destaquen más */
}}

button[data-baseweb="tab"][aria-selected="true"] {{
    background-color: {color_secundario} !important;
}}

/* Ponemos el texto en blanco y negrita para que se lea bien sobre el fondo oscuro */
button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p {{
    color: white !important;
}}

/* 2. Banner con Flexbox */
.banner-ferrovixia {{
    background-color: {color_fondo}; 
    padding: 15px 25px; 
    margin-bottom: 1px;
    margin-left: -5rem;
    margin-right: -5rem;
    margin-top: -1rem;
    display: flex;
    align-items: center;
    justify-content: center; /* Centra el texto */
    position: relative; /* Para poder fijar el logo a la izquierda */
    min-height: 100px;
}}

.logo-container {{
    position: absolute;
    left: 6rem; /* Ajusta según lo lejos que lo quieras del borde */
}}

.logo-img {{
    height: 70px; /* Ajusta el tamaño de tu logo */
}}

.texto-banner {{
    text-align: center;
}}

@media (max-width: 768px) {{
    .banner-ferrovixia {{
        margin-left: -1rem;
        margin-right: -1rem;
        flex-direction: column; /* En móvil el logo se pone arriba y el texto abajo */
    }}
    .logo-container {{
        position: static;
        margin-bottom: 10px;
    }}
}}
</style>

<div class="banner-ferrovixia">
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}" class="logo-img">
    </div>
    <div class="texto-banner">
        <h1 style="color: {color_texto}; margin: 0; font-size: 2.5rem; font-weight: bold;">FerroVixía</h1>
        <p style="color: {color_texto}; margin: 0; opacity: 0.9; font-size: 1.1rem; margin-top: 5px;">
            Sistema de Monitorización da Infraestrutura Ferroviaria
        </p>
    </div>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)

hide_st_style = """
            <style>
          
            [data-testid="stStandardToolbar"] {
                display: none !important;
            }
            
           
            [data-testid="stAppDeployButton"] {
                display: none !important;
            }

          
            footer {
                visibility: hidden;
            }

         
            header {
                background-color: rgba(0,0,0,0);
                pointer-events: none; 
            }

            [data-testid="stSidebarCollapseButton"], 
            [data-testid="stHeader"] button {
                pointer-events: auto !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

def crear_pdf_informe(df_alertas, nombre_trayecto):
    pdf = FPDF()
    pdf.add_page()
   
    # Título (en color granate)
    pdf.set_font("helvetica", "B", 20)
    pdf.set_text_color(125, 25, 42) # Granate FerroVixia
    pdf.cell(0, 15, "Informe Ejecutivo de Inspeccion", border=0, align="C", new_x="LMARGIN", new_y="NEXT")
    
    # --- DATOS GENERALES ---
    pdf.set_font("helvetica", "", 12)
    pdf.set_text_color(0, 0, 0)
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    
    pdf.cell(0, 8, f"Fecha de generacion: {fecha_hoy}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Trayecto analizado: {nombre_trayecto}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"Total de alertas a revisar: {len(df_alertas)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5) # Salto de línea
    
    # --- TABLA DE ALERTAS ---
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(125, 25, 42) # Fondo encabezado granate
    pdf.set_text_color(255, 255, 255) # Texto blanco
    
    # Anchura de las columnas de la tabla
    col_w = [25, 40, 40, 40, 45]
    headers = ["ID Punto", "Latitud", "Longitud", "Acel. Max (g)", "Nivel"]
    
    # Imprimir encabezados
    for i in range(len(headers)):
        pdf.cell(col_w[i], 8, headers[i], border=1, align="C", fill=True)
    pdf.ln()
    
    # Filas de datos
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(240, 240, 240) # Gris clarito para las filas pares
    
    fill = False
    for index, row in df_alertas.iterrows():
        # Extraemos los datos previniendo que cambien los nombres de las columnas
        id_punto = str(row.get('ID_Punto', '-'))
        lat = str(round(row.get('Latitud', row.get('latitud', 0)), 6))
        lon = str(round(row.get('Longitud', row.get('longitud', 0)), 6))
        acel = str(round(row.get('Aceleracion_Max', row.get('aceleracion_ms2', 0)), 2))
        nivel = str(row.get('Nivel', row.get('nivel_gravedad', '-')))
        
        pdf.cell(col_w[0], 8, id_punto, border=1, align="C", fill=fill)
        pdf.cell(col_w[1], 8, lat, border=1, align="C", fill=fill)
        pdf.cell(col_w[2], 8, lon, border=1, align="C", fill=fill)
        pdf.cell(col_w[3], 8, acel, border=1, align="C", fill=fill)
        pdf.cell(col_w[4], 8, nivel, border=1, align="C", fill=fill)
        pdf.ln()
        
        fill = not fill # Alternar el color de fondo para la siguiente fila
        
    # Devolvemos el PDF en formato binario listo para descargar
    return bytes(pdf.output())

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
   
    if not url or not key:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass # Si falla porque no existe el archivo, no hace nada y sigue
            
   
    if not url or not key:
        st.error(" Faltan las credenciales de Supabase. Revisa las variables en Azure.")
        st.stop()
        
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES DE BASE DE DATOS ---
@st.cache_data(ttl=60) # Refresca la lista cada minuto
def obtener_tablas_disponibles():
    try:
        # Llamamos a la función SQL que creamos en Supabase
        response = supabase.rpc("obtener_tablas_resultado_nuevo").execute()
        
        # Extraemos solo los nombres en una lista limpia
        if response.data:
            return [fila['table_name'] for fila in response.data]
        return []
    except Exception as e:
        st.error("Error ao obter as táboas.")
        return []

@st.cache_data(ttl=60)
def obtener_datos_tabla(nombre_tabla):
    # Nos conectamos dinámicamente a la tabla que elija el usuario
    response = supabase.table(nombre_tabla).select("*").execute()
    return pd.DataFrame(response.data)

@st.cache_data(ttl=3600) # Cacheamos por 1 hora para no saturar la BBDD
def obtener_trayectoria_base(nombre_tabla_resultados):
    # Extraemos el nombre del trayecto (ej: 'pontevedra_vigo_ida_resultados' -> 'pontevedra_vigo_ida')
    nombre_limpio = nombre_tabla_resultados.replace("nuevo_", "").replace("_resultados", "")
    
    response = supabase.table("trayectorias_base_gps")\
        .select("latitud, longitud")\
        .eq("nombre_trayecto", nombre_limpio)\
        .order("orden")\
        .execute()
        
    return pd.DataFrame(response.data)

# --- INTERFAZ DE USUARIO ---
lista_tablas = obtener_tablas_disponibles()

tablas_a_ignorar = {"nuevo_vilagarcia_pontevedra_ida_resultados", "nuevo_coruna_santiago_ida_resultados"}
lista_tablas = [tabla for tabla in lista_tablas if tabla not in tablas_a_ignorar]
    
if not lista_tablas:
    st.info("No se atoparon táboas rematadas en '_resultados' na base de datos.")
    st.stop()


nombres_bonitos = {tabla: tabla.replace("nuevo_", "").replace("_resultados", "").replace("_", " ").title() for tabla in lista_tablas}
# --- DICCIONARIO DE TRAYECTOS ---
diccionario_trayectos = {
    "nuevo_pontevedra_vigo_ida_resultados": "Vigo - Pontevedra",
    "nuevo_pontevedra_vigo_vuelta_resultados": "Pontevedra - Vigo",
    #"nuevo_vilagarcia_pontevedra_ida_resultados": "Pontevedra - Vilagarcía",
    "nuevo_vilagarcia_pontevedra_vuelta_resultados": "Vilagarcía - Pontevedra",
    "nuevo_santiago_vilagarcia_ida_resultados": "Vilagarcía - Santiago",
    "nuevo_santiago_vilagarcia_vuelta_resultados": "Santiago - Vilagarcía",
    #"nuevo_coruna_santiago_ida_resultados": "Santiago - Coruña",
    "nuevo_coruna_santiago_vuelta_resultados": "Coruña - Santiago"
}

# --- PANEL LATERAL (FILTROS Y CONTROLES) ---

# --- NAVEGACIÓN PRINCIPAL CON PESTAÑAS ---
# Esto va en el cuerpo principal del script (sin tabular a la derecha)
tab1, tab2 = st.tabs(["MONITORIZACIÓN", "O PROXECTO"])

# --- CONTENIDO DE LA PESTAÑA 1 ---
with tab1:
    col_titulo, col_selector = st.columns([2.5, 1])
    
    with col_titulo:
        st.title("Visualización de traxectos")
        st.markdown("**Análisis de vibracións e infraestructura no tramo seleccionado.**")

    with col_selector:
        # Añadimos un par de saltos de línea invisibles para empujar el selector hacia abajo
        # y que quede perfectamente alineado con el título (que por defecto tiene margen arriba)
        st.write("")
        st.write("")
        
        def resetear_punto_ruta():
            st.session_state.punto_seleccionado = "Todos"
            
        # 2. Añadimos el 'key' y el 'on_change' al selector principal
        tabla_seleccionada = st.selectbox(
            "Selecciona o traxecto:", 
            options=lista_tablas,
            format_func=lambda x: diccionario_trayectos.get(x, x),
            key="selector_ruta_principal",
            on_change=resetear_punto_ruta  # <-- La magia ocurre aquí
        )
    
    nombre_amigable = diccionario_trayectos.get(tabla_seleccionada, tabla_seleccionada)

# Cargar datos de la tabla elegida
    with st.spinner(f"Descargando datos de {nombre_amigable}..."):
        df_ruta = obtener_datos_tabla(tabla_seleccionada)

    # --- NUEVO: FUNCIÓN CACHEADA PARA MATEMÁTICAS ---
    @st.cache_data
    def procesar_datos_mapa(df_original):
        # Hacemos una copia para no romper el original
        df_proc = df_original.copy()
        
        # 1. Aseguramos numéricos
        cols_a_promediar = ['Latitud', 'Longitud', 'Aceleracion_Max', 'Velocidad_kmh', 'f_CWT', 'f_WVD', 'Lambda']
        for col in cols_a_promediar:
            if col in df_proc.columns:
                df_proc[col] = pd.to_numeric(df_proc[col], errors='coerce')

        if 'Velocidad_kmh' in df_proc.columns:
            df_proc['Velocidad_kmh'] = df_proc['Velocidad_kmh'].replace(0.0, np.nan)
        if 'Lambda' in df_proc.columns:
            df_proc['Lambda'] = df_proc['Lambda'].replace(0.0, np.nan)
            
        # 2. Agrupación (Groupby)
        df_agrupado = df_proc.groupby('ID_Punto').agg({
            'Latitud': 'mean',           
            'Longitud': 'mean',          
            'Nivel': 'first',            
            'Aceleracion_Max': 'mean',    
            'Velocidad_kmh': 'mean',
            'f_CWT': 'mean',
            'f_WVD': 'mean',
            'Lambda': 'mean',
            'Archivo': 'count'           
        }).reset_index()

        df_agrupado.rename(columns={'Archivo': 'Num_Viajes'}, inplace=True)
        
        columnas_metricas = ['Aceleracion_Max', 'Velocidad_kmh', 'f_CWT', 'f_WVD', 'Lambda']
        columnas_existentes = [c for c in columnas_metricas if c in df_agrupado.columns]
        df_agrupado[columnas_existentes] = df_agrupado[columnas_existentes].round(2)
        
        return df_agrupado

    # --- PROCESAMIENTO DE DATOS ---
    st.divider()

    if not df_ruta.empty:
        # Llamamos a la función mágica (solo calculará la primera vez)
        df_mapa = procesar_datos_mapa(df_ruta)

        # (Aseguramos que la memoria interna exista antes de pintar nada)
        if 'punto_seleccionado' not in st.session_state:
            st.session_state.punto_seleccionado = "Todos"

        # --- 🛠️ LA MAGIA ANTIPARPADEO ---
        # Leemos el clic directamente de la memoria de Streamlit ANTES de dibujar el mapa
        if "mapa_interactivo_ferrovixia" in st.session_state:
            estado_mapa = st.session_state["mapa_interactivo_ferrovixia"]
            if estado_mapa and "selection" in estado_mapa:
                pts = estado_mapa["selection"].get("points", [])
                if pts:
                    st.session_state.punto_seleccionado = str(pts[0]["customdata"])
        # ----------------------------------------

        st.header(f"{nombre_amigable}")

        # --- CREAMOS LAS DOS COLUMNAS EN PARALELO ---
        # El 60% del ancho para el mapa (1.5) y el 40% para los datos (1)
        col_mapa, col_datos = st.columns([1.5, 1], gap="large")

        # ==========================================
        # COLUMNA IZQUIERDA: EL MAPA
        # ==========================================
        with col_mapa:
            st.subheader("Mapa de Impactos")
            
            estilo_mapa = st.radio(
                "Tipo de mapa:", 
                ["Rueiro", "Satélite"], 
                horizontal=True
            )

            df_base = obtener_trayectoria_base(tabla_seleccionada) 
            fig_mapa = go.Figure()

            # --- CAPA 1: RUTA BASE ---
            if not df_base.empty:
                fig_mapa.add_trace(go.Scattermap(
                    lat=df_base['latitud'], lon=df_base['longitud'],
                    mode='lines',
                    line=dict(width=3, color='rgba(0, 80, 200, 0.7)'), 
                    name='Traxecto completo', hoverinfo='skip' 
                ))
            else:
                st.toast("Aviso: Non se atopou traxectoria base para dibuxar a liña.", icon="⚠️")
            

            color_map = {
                'AVISO LEVE': 'yellow', 'ALERTA': 'orange',
                'INTERVENCION': 'red', 'INTERVENCION INMEDIATA': 'darkred' 
            }

            # --- CAPAS DE PUNTOS ---
            for gravedad, color in color_map.items():
                df_filtrado = df_mapa[df_mapa['Nivel'] == gravedad].copy() 
                
                if not df_filtrado.empty:
                    indices_seleccionados = []
                    if st.session_state.punto_seleccionado != "Todos":
                        coincidencias = df_filtrado['ID_Punto'].astype(str) == st.session_state.punto_seleccionado
                        if coincidencias.any():
                            indices_seleccionados = df_filtrado.reset_index(drop=True).index[coincidencias].tolist()

                    fig_mapa.add_trace(go.Scattermap(
                        lat=df_filtrado['Latitud'], lon=df_filtrado['Longitud'],
                        mode='markers', customdata=df_filtrado['ID_Punto'].astype(str), 
                        marker=dict(size=14, color=color, opacity=0.85), 
                        selected=dict(marker=dict(color='#AE66DB', size=20, opacity=1)), 
                        unselected=dict(marker=dict(opacity=0.85)), 
                        selectedpoints=indices_seleccionados if indices_seleccionados else None,
                        name=gravedad, 
                        text=(
                            "<b>Punto ID: " + df_filtrado['ID_Punto'].astype(str) + "</b><br>" +
                            "Nivel: " + df_filtrado['Nivel'] + "<br>" +
                            "Acel. Máx: " + df_filtrado['Aceleracion_Max'].astype(str) + " g<br>" +
                            "Vel. Media: " + df_filtrado['Velocidad_kmh'].astype(str) + " km/h<br>" +
                            "Viajes analizados: " + df_filtrado['Num_Viajes'].astype(str)
                        ),
                        hoverinfo="text"
                    ))

            # 1. Calculamos dinámicamente dónde centrar el mapa y el nivel de zoom
            if st.session_state.punto_seleccionado != "Todos":
                # Buscamos las coordenadas exactas de ese punto en el dataframe
                df_punto = df_mapa[df_mapa['ID_Punto'].astype(str) == st.session_state.punto_seleccionado]
                
                if not df_punto.empty:
                    centro_lat = df_punto['Latitud'].iloc[0]
                    centro_lon = df_punto['Longitud'].iloc[0]
                    nivel_zoom = 17 # Un zoom cercano para ver el detalle de la vía
                    
                    # MAGIA PLOTLY: Al cambiar el revision_id, forzamos a Plotly a viajar a este nuevo centro
                    revision_id = f"{tabla_seleccionada}_{st.session_state.punto_seleccionado}"
            else:
                # Vista general de la ruta si está seleccionado "Todos"
                centro_lat = df_ruta['Latitud'].dropna().mean() if 'Latitud' in df_ruta.columns else 0
                centro_lon = df_ruta['Longitud'].dropna().mean() if 'Longitud' in df_ruta.columns else 0
                nivel_zoom = 12
                
                # MAGIA PLOTLY: Si es la vista general, usamos el ID estático de la ruta. 
                # Así, si el usuario explora libremente con el ratón, el mapa no le hace un reset molesto.
                revision_id = tabla_seleccionada 

            # Mantenemos tu leyenda tal cual
            config_leyenda = dict(
                title=dict(text='Nivel de Gravidade', font=dict(size=14, color="black")), 
                font=dict(size=12, color="black"), itemsizing='constant', 
                bgcolor="rgba(255, 255, 255, 0.85)", bordercolor="black", borderwidth=1,
                yanchor="top", y=0.95, xanchor="right", x=0.99
            )

            # 2. Actualizamos el mapa pasándole nuestras variables dinámicas (nivel_zoom)
            if estilo_mapa == "Rueiro":
                fig_mapa.update_layout(
                    uirevision=revision_id, map_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0},
                    map=dict(uirevision=revision_id, center=dict(lat=centro_lat, lon=centro_lon), zoom=nivel_zoom),
                    height=600, legend=config_leyenda 
                )
            else:
                fig_mapa.update_layout(
                    uirevision=revision_id, map_style="white-bg", margin={"r":0,"t":0,"l":0,"b":0},
                    map=dict(
                        uirevision=revision_id,
                        center=dict(lat=centro_lat, lon=centro_lon), zoom=nivel_zoom,
                        layers=[
                            dict(sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], below="traces"),
                            dict(sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"], below="traces")
                        ]
                    ),
                    height=600, legend=config_leyenda 
                )

            if estilo_mapa == "Rueiro":
                fig_mapa.update_layout(
                    uirevision=revision_id, map_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0},
                    map=dict(uirevision=revision_id, center=dict(lat=centro_lat, lon=centro_lon), zoom=12),
                    height=600, legend=config_leyenda 
                )
            else:
                fig_mapa.update_layout(
                    uirevision=revision_id, map_style="white-bg", margin={"r":0,"t":0,"l":0,"b":0},
                    map=dict(
                        uirevision=revision_id,
                        center=dict(lat=centro_lat, lon=centro_lon), zoom=12,
                        layers=[
                            dict(sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"], below="traces"),
                            dict(sourcetype="raster", source=["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"], below="traces")
                        ]
                    ),
                    height=600, legend=config_leyenda 
                )
            
            st.plotly_chart(
                fig_mapa, width='stretch', on_select="rerun", key="mapa_interactivo_ferrovixia"
            )

        # ==========================================
        # COLUMNA DERECHA: LOS DATOS Y MÉTRICAS
        # ==========================================
        with col_datos:
            st.subheader(f"Resumo do traxecto")
            
            col_gravedad = 'Nivel' if 'Nivel' in df_ruta.columns else 'nivel_gravedad'
            col_vel = 'velocidad_kmh' if 'velocidad_kmh' in df_ruta.columns else 'Velocidad_kmh'

            total_puntos_unicos = len(df_mapa)
            puntos_criticos = len(df_mapa[df_mapa[col_gravedad].isin(['INTERVENCION', 'INTERVENCION INMEDIATA'])])
            vel_media = df_mapa[col_vel].mean() if col_vel in df_mapa.columns else 0.0
            
            # Usamos 3 columnas pequeñas dentro de la columna de datos para las métricas
            # He acortado ligeramente los títulos para que quepan bien al estar a un lado
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Pts", total_puntos_unicos)
            m2.metric("Críticos", puntos_criticos, delta_color="inverse")
            m3.metric("Km/h", f"{vel_media:.1f}")
            
            st.caption("Baseámonos nos umbrais que emprega [ADIF](https://contrataciondelestado.es/wps/wcm/connect/PLACE_es/Site/area/docAccCmpnt?srv=cmpnt&cmpntname=GetDocumentsById&source=library&DocumentIdParam=c14b78f2-0046-4060-b2a8-fd6cf7800ee6), pero é importante aclarar que ao tratarse dun prototipo académico, precisa dunha calibración máis exhaustiva.")
           
            st.divider()

            st.subheader("Análise detallada")
            st.write("Selecciona un punto no mapa ou aquí:")
            
            lista_puntos = ["Todos"] + df_mapa['ID_Punto'].astype(str).tolist()

            # 1. Asegurarnos de que el punto en memoria sigue existiendo en la lista actual
            if st.session_state.punto_seleccionado not in lista_puntos:
                st.session_state.punto_seleccionado = "Todos"

            # 2. Función "callback" que se ejecutará solo cuando el usuario toque el selectbox
            def sincronizar_selector():
                # El selectbox guardará su valor temporal en "selector_widget"
                # Lo pasamos a nuestra variable global "punto_seleccionado"
                st.session_state.punto_seleccionado = st.session_state.selector_widget

            # 3. El Selectbox nativo
            st.selectbox(
                "ID do punto a analizar:",
                options=lista_puntos,
                index=lista_puntos.index(st.session_state.punto_seleccionado),
                key="selector_widget",         # Asignamos una clave interna de Streamlit
                on_change=sincronizar_selector # Le decimos que ejecute la función al cambiar
            )

            if st.session_state.punto_seleccionado != "Todos":
                df_detalle = df_ruta[df_ruta['ID_Punto'].astype(str) == st.session_state.punto_seleccionado]
                
                if not df_detalle.empty:
                    st.write(f"**Historial de viaxes** ({len(df_detalle)} viaxes)")
                    
                    columnas_mostrar = ['Archivo', 'Velocidad_kmh', 'Aceleracion_Max', 'Nivel']
                    columnas_existentes = [col for col in columnas_mostrar if col in df_detalle.columns]
                    
                    df_mostrar = df_detalle[columnas_existentes].copy()
                    
                    if 'Archivo' in df_mostrar.columns:
                        df_mostrar['Archivo'] = (df_mostrar['Archivo']
                            .str.replace('Resultados_movil2_', '')
                            .str.replace('Resultados_movil_', '')
                            .str.replace('Resultados_M5_', '')
                            .str.replace('.mat', '')
                        )
                        
                    nomes_novos = {
                        'Archivo': 'Arquivo',
                        'Velocidad_kmh': 'Velocidade (km/h)',
                        'Aceleracion_Max': 'Aceleración Máx (g)',
                        'Nivel': 'Nivel' 
                    }
                    df_mostrar = df_mostrar.rename(columns=nomes_novos)
                    
                    st.dataframe(
                        df_mostrar, 
                        width='stretch',
                        hide_index=True 
                    )
            else:
                st.info("Fai clic nun punto para ver o seu historial.")

        # ==========================================
        # ZONA INFERIOR (ANCHO COMPLETO)
        # ==========================================
        st.divider()
        with st.expander("Ver datos crudos completos da tabla"):
          
            df_crudos = df_ruta.copy()
            
            if 'Archivo' in df_crudos.columns:
                df_crudos['Archivo'] = (df_crudos['Archivo']
                    .str.replace('Resultados_movil2_', '')
                    .str.replace('Resultados_movil_', '')
                    .str.replace('Resultados_M5_', '')
                    .str.replace('.mat', '')
                )

            nomes_galego_crudos = {
                'Archivo': 'Arquivo',
                'Velocidad_kmh': 'Velocidade (km/h)',
                'Aceleracion_Max': 'Aceleración Máx (g)',
                'Latitud': 'Latitude',
                'Longitud': 'Lonxitude'
            }
            df_crudos = df_crudos.rename(columns=nomes_galego_crudos)
            
            st.dataframe(df_crudos, width='stretch')


        # --- DESCARGA DE DOCUMENTOS ---
        st.divider()
        st.subheader("Exportar Informe de Mantemento")
        
        # Filtramos la tabla para quedarnos solo con las alertas importantes
        col_gravedad = 'Nivel' if 'Nivel' in df_ruta.columns else 'nivel_gravedad'
        df_informe = df_ruta[df_ruta[col_gravedad].isin(['INTERVENCION', 'INTERVENCION INMEDIATA', 'ALERTA'])]
        
        if not df_informe.empty:
            col1_btn, col2_btn = st.columns(2)
            
            # BOTÓN 1: EL CSV TRADICIONAL
            with col1_btn:
                csv_informe = df_informe.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar Datos (CSV)",
                    data=csv_informe,
                    file_name=f"Datos_{tabla_seleccionada}.csv",
                    mime="text/csv",
                    width='stretch'
                )
                
            # BOTÓN 2: EL NUEVO INFORME PDF
            with col2_btn:
                pdf_bytes = crear_pdf_informe(df_informe, nombres_bonitos.get(tabla_seleccionada, tabla_seleccionada))
                st.download_button(
                    label="Descargar Informe (PDF)",
                    data=pdf_bytes,
                    file_name=f"Informe_Mantenimiento_{tabla_seleccionada}.pdf",
                    mime="application/pdf",
                    type="primary", # Lo marcamos como principal para que destaque en granate/rojo
                    width='stretch'
                )
        else:
            st.success("Este traxecto non ten baches que requiran intervención.")

    # Esta es la pareja del 'if not df_ruta.empty:' de arriba
    else:
        st.warning(f"La tabla {tabla_seleccionada} está vacía o no tiene coordenadas válidas.")

with tab2:
    st.title("Sobre FerroVixia")

    st.markdown("""
    ### A NOSA PROPOSTA
    FerroVixía transforma os trens comerciais en sensores activos capaces de detectar anomalías nas vías. Mediante dispositivos IoT e procesamento dixital das sinais, 
    o prototipo distingue elementos fixos, como cambios de agulla, de defectos xeométricos. A información recóllese nunha base de datos na nube 
    e exponse nunha interface web que facilita o mantemento preditivo e mellora a seguridade ferroviaria.
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.info("#### A NOSA MISIÓN\nMonitorización continua, versátil e xeolocalizada das vías de tren.")
    with col_b:
        st.success("#### A TECNOLOXÍA\nInternet das Cousas (IoT), procesamento de sinais (CWT, WVD), detección de anomalías, Smart Data")

    st.subheader(" O PASO A PASO")
    # Puedes usar un diagrama simple o una lista de pasos
    st.write("""
    1. **Captura:** Dispositivos M5Stack instalados a bordo do tren recollen datos de aceleración e posición.
    2. **Procesado:** Coa ferramenta MATLAB aplicamos as técnicas de procesamento de sinal (CWT, WVD) para filtrar a información.
    3. **Almacenamento:** Os resultados filtrados almacénanse na nosa base de datos Supabase.
    4. **Visualización:** Esta interfaz web na nube presenta a información das viaxes de forma interactiva.
    """)
    
# --- PIE DE PÁGINA (FOOTER) ---
st.divider() # Línea sutil de separación

# Creamos 3 columnas: [Texto Nombres | Texto Contacto | Logos Universidad]
f1, f2, f3 = st.columns([2, 2, 1])

with f1:
    st.markdown("**O equipo:**")
    st.write("Eva Deibe de Bernardo")
    st.write("Marcos López Míguez")
    st.write("Manuela Outeiro Otero")
    st.write("Adriana Pazos Lorenzo")
    st.write("Uxía Veiras Suárez")
    
with f2:
    st.markdown("**Contacto:**")
    st.write("📧 ferrovixia@gmail.com")
    st.write("📍 Escola de Enxeñaría de Telecomunicación, Vigo")

# with f3:
    # width='stretch'
    # st.image("logo_universidad.png", width='stretch')

# Nota de copyright opcional al final
st.caption("© 2026 Proxecto FerroVixia - Monitorización Ferroviaria")

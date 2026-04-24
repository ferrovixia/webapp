import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="FerroVixia - Monitorización", 
    page_icon="paginita.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.logo("logo_ferrovixia.png", icon_image="logo_ferrovixia_pequeno.png")

color_fondo = "#7d192a"  
color_texto = "#FFFFFF" 

html_header = f"""
<style>
/* 1. Ocultar EXACTAMENTE el bloque HTML que me has pasado (Header completo) */
[data-testid="stHeader"] {{
    display: none !important;
}}

/* 2. Quitar el padding superior que mete Streamlit por defecto en la página */
.block-container {{
    padding-top: 0rem !important;
}}

/* 3. Clase personalizada para expandir tu franja */
.banner-ferrovixia {{
    background-color: {color_fondo}; 
    padding: 25px; 
    text-align: center; 
    margin-bottom: 25px;
    
    /* Márgenes laterales negativos para ocupar todo el ancho */
    margin-left: -5rem;
    margin-right: -5rem;
    
    /* Margen superior normalizado porque ya no hay header de Streamlit */
    margin-top: -1rem; 
}}

/* 4. Ajuste automático para que en móviles no se rompa */
@media (max-width: 768px) {{
    .banner-ferrovixia {{
        margin-left: -1rem;
        margin-right: -1rem;
        margin-top: -1rem;
    }}
}}
</style>

<div class="banner-ferrovixia">
    <h1 style="color: {color_texto}; margin: 0; font-size: 2.5rem; font-weight: bold;">FerroVixía</h1>
    <p style="color: {color_texto}; margin: 0; opacity: 0.9; font-size: 1.1rem; margin-top: 5px;">
        Sistema de Monitorización Ferroviaria
    </p>
</div>
"""
st.markdown(html_header, unsafe_allow_html=True)

hide_st_style = """
            <style>
            /* 1. Oculta el menú de la derecha (los 3 puntos) sin romper el header */
            [data-testid="stStandardToolbar"] {
                display: none !important;
            }
            
            /* 2. Oculta el botón de 'Deploy' si aparece */
            [data-testid="stAppDeployButton"] {
                display: none !important;
            }

            /* 3. Oculta el pie de página */
            footer {
                visibility: hidden;
            }

            /* 4. Asegura que el header no bloquee los clics */
            header {
                background-color: rgba(0,0,0,0);
                pointer-events: none; /* Esto hace que el header sea 'transparente' a los clics */
            }

            /* 5. PERO permite que el botón de la barra lateral sí reciba clics */
            [data-testid="stSidebarCollapseButton"], 
            [data-testid="stHeader"] button {
                pointer-events: auto !important;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)



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
        st.error("🚨 Faltan las credenciales de Supabase. Revisa las variables en Azure.")
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
        st.error("Error al obtener las tablas. ¿Creaste la función SQL en Supabase?")
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

if not lista_tablas:
    st.info("No se han encontrado tablas terminadas en '_resultados' en la base de datos.")
    st.stop()


nombres_bonitos = {tabla: tabla.replace("nuevo_", "").replace("_resultados", "").replace("_", " ").title() for tabla in lista_tablas}
# --- DICCIONARIO DE TRAYECTOS ---
diccionario_trayectos = {
    "nuevo_pontevedra_vigo_ida_resultados": "Vigo - Pontevedra",
    "nuevo_pontevedra_vigo_vuelta_resultados": "Pontevedra - Vigo",
    "nuevo_vilagarcia_pontevedra_ida_resultados": "Pontevedra - Vilagarcía",
    "nuevo_vilagarcia_pontevedra_vuelta_resultados": "Vilagarcía - Pontevedra",
    "nuevo_santiago_vilagarcia_ida_resultados": "Vilagarcía - Santiago",
    "nuevo_santiago_vilagarcia_vuelta_resultados": "Santiago - Vilagarcía",
    "nuevo_coruna_santiago_ida_resultados": "Santiago - Coruña",
    "nuevo_coruna_santiago_vuelta_resultados": "Coruña - Santiago"
}

# --- PANEL LATERAL (FILTROS Y CONTROLES) ---

# --- NAVEGACIÓN PRINCIPAL CON PESTAÑAS ---
# Esto va en el cuerpo principal del script (sin tabular a la derecha)
tab1, tab2 = st.tabs(["📊 Monitorización", "📋 Sobre el Proyecto"])

# --- CONTENIDO DE LA PESTAÑA 1 ---
with tab1:
    st.title(f"🗺️ Visualización de trayectos")
    st.markdown("**Análisis de vibraciones e infraestructura en el tramo seleccionado.**")

    col_sel1, col_sel2 = st.columns(2)
    with col_sel1:
        tabla_seleccionada = st.selectbox(
            "🛤️ Selecciona el trayecto:", 
            options=lista_tablas,
            format_func=lambda x: diccionario_trayectos.get(x, x)
        )
    with col_sel2:
        estilo_mapa = st.radio("🗺️ Tipo de mapa:", ["Callejero", "Satélite"], horizontal=True)
    
    nombre_amigable = diccionario_trayectos.get(tabla_seleccionada, tabla_seleccionada)
    st.title(f"🗺️ {nombre_amigable}")

    st.divider()
    # Cargar datos de la tabla elegida
    with st.spinner(f"📡 Descargando datos de {nombre_amigable}..."):
        df_ruta = obtener_datos_tabla(tabla_seleccionada)

    # Verificamos que la tabla tenga datos antes de intentar pintar nada
    # --- PROCESAMIENTO DE DATOS: AGRUPACIÓN SOLO POR ID_PUNTO ---

    if not df_ruta.empty:
        # 1. Aseguramos que las columnas sean numéricas antes de la media
        cols_a_promediar = ['Latitud', 'Longitud', 'Aceleracion_Max', 'Velocidad_kmh', 'f_CWT', 'f_WVD', 'Lambda']
        for col in cols_a_promediar:
            if col in df_ruta.columns:
                df_ruta[col] = pd.to_numeric(df_ruta[col], errors='coerce')

        # (Opcional, si aplicaste lo de los ceros en los M5)
        import numpy as np
        df_ruta['Velocidad_kmh'] = df_ruta['Velocidad_kmh'].replace(0.0, np.nan)
        df_ruta['Lambda'] = df_ruta['Lambda'].replace(0.0, np.nan)

        # 2. Agrupamos solo por ID_Punto
        df_mapa = df_ruta.groupby('ID_Punto').agg({
            'Latitud': 'mean',           # Conserva todos los decimales
            'Longitud': 'mean',          # Conserva todos los decimales
            'Nivel': 'first',            
            'Aceleracion_Max': 'mean',    
            'Velocidad_kmh': 'mean',
            'f_CWT': 'mean',
            'f_WVD': 'mean',
            'Lambda': 'mean',
            'Archivo': 'count'           
        }).reset_index()

        # Renombramos
        df_mapa.rename(columns={'Archivo': 'Num_Viajes'}, inplace=True)
        
        # 3. REDONDEAMOS SOLO LAS MÉTRICAS (Respetando el GPS)
        columnas_metricas = ['Aceleracion_Max', 'Velocidad_kmh', 'f_CWT', 'f_WVD', 'Lambda']
        df_mapa[columnas_metricas] = df_mapa[columnas_metricas].round(2)

        # --- MÉTRICAS RÁPIDAS ---
        st.subheader(f"Resumen de: {nombre_amigable}")
        
        col_gravedad = 'Nivel' if 'Nivel' in df_ruta.columns else 'nivel_gravedad'
        col_vel = 'velocidad_kmh' if 'velocidad_kmh' in df_ruta.columns else 'Velocidad_kmh'
        col_acel = 'aceleracion_ms2' if 'aceleracion_ms2' in df_ruta.columns else 'Aceleracion_ms2'
        col_lat = 'latitud' if 'latitud' in df_ruta.columns else 'Latitud'
        col_lon = 'longitud' if 'longitud' in df_ruta.columns else 'Longitud'

        total_puntos = len(df_ruta)
        graves = len(df_ruta[df_ruta[col_gravedad].isin(['INTERVENCION', 'INTERVENCION INMEDIATA'])])
        vel_media = df_ruta[col_vel].mean() if col_vel in df_ruta.columns else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Alertas Registradas", total_puntos)
        m2.metric("Puntos Críticos (Intervención)", graves)
        m3.metric("Velocidad Media (km/h)", f"{vel_media:.1f}")
        
        # --- MAPA ---
        st.subheader("Mapa de Impactos")
        
        estilo_mapa = st.radio(
            "Tipo de mapa:", 
            ["Callejero", "Satélite"], 
            horizontal=True
        )

        df_base = obtener_trayectoria_base(tabla_seleccionada) # trayectoria base 
        
        fig_mapa = go.Figure()

        # dibujar capa 1: ruta base
        if not df_base.empty:
            fig_mapa.add_trace(go.Scattermap(
                lat=df_base['latitud'],
                lon=df_base['longitud'],
                mode='lines',
                line=dict(width=3, color='rgba(0, 80, 200, 0.7)'), # Azul corporativo semi-transparente
                name='Trayecto completo',
                hoverinfo='skip' # Que no moleste al pasar el ratón
            ))
        else:
            st.toast("Aviso: No se encontró la trayectoria base para dibujar la línea.", icon="⚠️")
        
        # Mapear colores según la gravedad
    # Mapear colores según la gravedad
        color_map = {
            'AVISO LEVE': 'yellow',
            'ALERTA': 'orange',
            'INTERVENCION': 'red',
            'INTERVENCION INMEDIATA': 'darkred' # He actualizado esto según tu CSV
        }
        
        # Para leyenda avisos: iterar sobre cada nivel de gravedad
        for gravedad, color in color_map.items():
            # ATENCIÓN: Ahora filtramos df_mapa, no df_ruta
            df_filtrado = df_mapa[df_mapa['Nivel'] == gravedad] 
            
            if not df_filtrado.empty:
                fig_mapa.add_trace(go.Scattermap(
                    lat=df_filtrado['Latitud'], 
                    lon=df_filtrado['Longitud'],
                    mode='markers', 
                    marker=dict(size=14, color=color, opacity=0.8), 
                    name=gravedad, 
                    # Actualizamos el texto que se ve al hacer hover:
                    text=(
                        "<b>Punto ID: " + df_filtrado['ID_Punto'].astype(str) + "</b><br>" +
                        "Nivel: " + df_filtrado['Nivel'] + "<br>" +
                        "Acel. Máx: " + df_filtrado['Aceleracion_Max'].astype(str) + " g<br>" +
                        "Vel. Media: " + df_filtrado['Velocidad_kmh'].astype(str) + " km/h<br>" +
                        "Viajes analizados: " + df_filtrado['Num_Viajes'].astype(str)
                    ),
                    hoverinfo="text"
                ))

        # Configuración del mapa
        centro_lat = df_ruta[col_lat].mean()
        centro_lon = df_ruta[col_lon].mean()
        
        config_leyenda = dict(
            title=dict(text='Nivel de Gravedad', font=dict(size=16, color="black")), 
            font=dict(size=14, color="black"), 
            itemsizing='constant', 
            bgcolor="rgba(255, 255, 255, 0.85)", 
            bordercolor="black",
            borderwidth=1,
            yanchor="top",
            y=0.95, 
            xanchor="right",
            x=0.99
        )
        
        if estilo_mapa == "Callejero":
            fig_mapa.update_layout(
                map_style="open-street-map",
                margin={"r":0,"t":0,"l":0,"b":0},
                map=dict(center=dict(lat=centro_lat, lon=centro_lon), zoom=12),
                height=600,
                legend=config_leyenda 
            )
        else:
            fig_mapa.update_layout(
                map_style="white-bg", 
                margin={"r":0,"t":0,"l":0,"b":0},
                map=dict(
                    center=dict(lat=centro_lat, lon=centro_lon), 
                    zoom=12,
                    layers=[
                        dict(
                            sourcetype="raster",
                            source=["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                            below="traces"
                        ),
                        dict(
                            sourcetype="raster",
                            source=["https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"],
                            below="traces"
                        )
                    ]
                ),
                height=600,
                legend=config_leyenda 
            )
        
        st.plotly_chart(fig_mapa, width="stretch")
        
        # --- SECCIÓN DE DESGLOSE POR PUNTO ---
        st.divider()
        st.subheader("🔍 Análisis detallado por Punto")
        st.write("Selecciona un punto en el mapa (por su ID) para ver los datos de todos los trenes que han pasado por él.")
        
        # Selector de Punto
        punto_seleccionado = st.selectbox(
            "ID del Punto a analizar:",
            options=df_mapa['ID_Punto'].sort_values()
        )
        
        # Filtramos el dataframe ORIGINAL (el que tiene todos los archivos separados)
        df_detalle = df_ruta[df_ruta['ID_Punto'] == punto_seleccionado]
        
        if not df_detalle.empty:
            st.write(f"**Historial de viajes para el Punto {punto_seleccionado}** ({len(df_detalle)} viajes registrados)")
            
            # Mostramos la tabla limpia solo con las columnas de interés
            columnas_mostrar = ['Archivo', 'Velocidad_kmh', 'Aceleracion_Max', 'f_CWT', 'f_WVD', 'Lambda']
            
            # Usamos dataframe para que el usuario pueda ordenar por columnas (ej. ver la vel más alta)
            st.dataframe(
                df_detalle[columnas_mostrar], 
                width='stretch',
                hide_index=True # Oculta el número de fila por defecto que no aporta nada
            )
        
        with st.expander("Ver datos crudos de la tabla"):
            st.dataframe(df_ruta)

        # --- DESCARGA DE DOCUMENTO ---
        
        st.divider()
        st.subheader("📥 Exportar Parte de Trabajo")
        
        df_informe = df_ruta[df_ruta[col_gravedad].isin(['INTERVENCION', 'INTERVENCION INMEDIATA', 'ALERTA'])]
        
        if not df_informe.empty:
            csv_informe = df_informe.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Descargar Informe de Mantenimiento (CSV)",
                data=csv_informe,
                file_name=f"Parte_Mantenimiento_{tabla_seleccionada}.csv",
                mime="text/csv",
                type="primary" 
            )
        else:
            st.success("¡Buenas noticias! Este trayecto no tiene baches que requieran intervención.")

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
    st.write("Marcos López Miguel")
    st.write("Manuela Outeiro Otero")
    st.write("Adriana Pazos Lorenzo")
    st.write("Uxía Veiras Suárez")
    
with f2:
    st.markdown("**Contacto:**")
    st.write("📧 ferrovixia@gmail.com")
    st.write("📍 Escola de Enxeñaría de Telecomunicación, Vigo")

# with f3:
    # use_container_width=True 
    # st.image("logo_universidad.png", use_container_width=True)

# Nota de copyright opcional al final
st.caption("© 2026 Proyecto FerroVixia - Monitorización Ferroviaria")
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Dashboard Histórico de Vías", layout="wide")
st.title("🗺️ Histórico de Vibraciones por Trayecto")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES DE BASE DE DATOS ---
@st.cache_data(ttl=60) # Refresca la lista cada minuto
def obtener_tablas_disponibles():
    try:
        # Llamamos a la función SQL que creamos en Supabase
        response = supabase.rpc("obtener_tablas_resultados").execute()
        
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

# --- INTERFAZ DE USUARIO ---
lista_tablas = obtener_tablas_disponibles()

if not lista_tablas:
    st.info("No se han encontrado tablas terminadas en '_resultados' en la base de datos.")
    st.stop()

# Selector de ruta (tabla)
col1, col2 = st.columns([1, 3])
with col1:
    # Formateamos el nombre de la tabla para que se lea mejor en el menú (ej: vigo_coruna_resultados -> Vigo Coruna)
    nombres_bonitos = {tabla: tabla.replace("_resultados", "").replace("_", " ").title() for tabla in lista_tablas}
    
    tabla_seleccionada = st.selectbox(
        "🛤️ Selecciona el trayecto a visualizar:", 
        options=lista_tablas,
        format_func=lambda x: nombres_bonitos[x]
    )

st.divider()

# Cargar datos de la tabla elegida
df_ruta = obtener_datos_tabla(tabla_seleccionada)

if not df_ruta.empty:
    # --- MÉTRICAS RÁPIDAS ---
    st.subheader(f"Resumen de: {nombres_bonitos[tabla_seleccionada]}")
    
    # Adaptamos los nombres de columnas a tu CSV (en minúsculas si así lo subes a Supabase)
    # IMPORTANTE: Asegúrate de que las columnas en Supabase coinciden con estos nombres
    col_gravedad = 'nivel_gravedad' if 'nivel_gravedad' in df_ruta.columns else 'Nivel_Gravedad'
    col_vel = 'velocidad_kmh' if 'velocidad_kmh' in df_ruta.columns else 'Velocidad_kmh'
    col_acel = 'aceleracion_ms2' if 'aceleracion_ms2' in df_ruta.columns else 'Aceleracion_ms2'
    col_lat = 'latitud' if 'latitud' in df_ruta.columns else 'Latitud'
    col_lon = 'longitud' if 'longitud' in df_ruta.columns else 'Longitud'

    total_puntos = len(df_ruta)
    graves = len(df_ruta[df_ruta[col_gravedad].isin(['INTERVENCION', 'INMEDIATA'])])
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
    
    fig_mapa = go.Figure()

    # Mapear colores según la gravedad
    color_map = {
        'AVISO LEVE': 'yellow',
        'ALERTA': 'orange',
        'INTERVENCION': 'red',
        'INMEDIATA': 'darkred'
    }
    
    colores_baches = df_ruta[col_gravedad].map(color_map).fillna('gray')

    # Para leyenda avisos:
        # iterar sobre cada nivel de gravedad
    for gravedad, color in color_map.items():
       
        df_filtrado = df_ruta[df_ruta[col_gravedad] == gravedad]
        
        if not df_filtrado.empty:
            fig_mapa.add_trace(go.Scattermapbox(
                lat=df_filtrado[col_lat], 
                lon=df_filtrado[col_lon],
                mode='markers', 
                marker=dict(size=14, color=color, opacity=0.8), 
                name=gravedad, 
                text=df_filtrado[col_gravedad] + "<br>Acel: " + df_filtrado[col_acel].astype(str) + " g",
                hoverinfo="text"
            ))

    # Configuración del mapa
    centro_lat = df_ruta[col_lat].mean()
    centro_lon = df_ruta[col_lon].mean()
    
    config_leyenda = dict(
        title=dict(text='Nivel de Gravedad', font=dict(size=16, color="black")), 
        font=dict(size=14, color="black"), # Texto de las categorías 
        itemsizing='constant', 
        bgcolor="rgba(255, 255, 255, 0.85)", # fondo blanco con 85% de opacidad para que contraste con el mapa
        bordercolor="black",
        borderwidth=1,
        yanchor="top",
        y=0.95, 
        xanchor="right",
        x=0.99
    )
    
    if estilo_mapa == "Callejero":
        fig_mapa.update_layout(
            mapbox_style="open-street-map", 
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox=dict(center=dict(lat=centro_lat, lon=centro_lon), zoom=12),
            height=600,
            legend=config_leyenda 
        )
    else:
        # Satélite usando Esri World Imagery
        fig_mapa.update_layout(
            mapbox_style="white-bg", 
            margin={"r":0,"t":0,"l":0,"b":0},
            mapbox=dict(
                center=dict(lat=centro_lat, lon=centro_lon), 
                zoom=12,
                layers=[
                    dict(
                        sourcetype="raster",
                        source=["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                        below="traces"
                    )
                ]
            ),
            height=600,
            legend=config_leyenda 
        )
    
    st.plotly_chart(fig_mapa, use_container_width=True)
    
    # --- TABLA DE DATOS ---
    with st.expander("Ver datos crudos de la tabla"):
        st.dataframe(df_ruta)

else:
    st.warning(f"La tabla {tabla_seleccionada} está vacía o no tiene coordenadas válidas.")
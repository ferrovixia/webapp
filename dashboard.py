import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client

# --- CONFIGURACIÓN DE PÁGINA --
st.set_page_config(
    page_title="FerroVixia - Monitorización", 
    page_icon="paginita.png", # Aquí pones el nombre exacto de tu imagen
    layout="wide",
    initial_sidebar_state="expanded"
)
st.logo("logo_ferrovixia.png", icon_image="logo_ferrovixia_pequeno.png")
# --- OCULTAR MARCAS DE STREAMLIT ---
# --- OCULTAR MARCAS DE STREAMLIT (CORREGIDO) ---
# --- OCULTAR MARCAS DE STREAMLIT (VERSIÓN BULLETPROOF) ---
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
    # 1. Intentamos leer de Azure (Variables de entorno)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # 2. Si no están en Azure, intentamos usar los secretos locales (para cuando pruebas en tu PC)
    if not url or not key:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass # Si falla porque no existe el archivo, no hace nada y sigue
            
    # 3. Si después de todo no hay claves, mostramos error
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
    nombre_limpio = nombre_tabla_resultados.replace("_resultados", "")
    
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

# Selector de ruta (tabla)
# --- PANEL LATERAL (FILTROS Y CONTROLES) ---
with st.sidebar:
    # --- LOGO CORPORATIVO (AJUSTA EL ANCHO AQUÍ) ---
    st.image("logo_ferrovixia.png", width=220) # Sube de 200 si lo quieres aún más grande
    
    st.subheader("⚙️ Panel de Control")
    
    # Formateamos el nombre de la tabla (ahora también oculta el "nuevo_")
    nombres_bonitos = {tabla: tabla.replace("nuevo_", "").replace("_resultados", "").replace("_", " ").title() for tabla in lista_tablas}
    
    tabla_seleccionada = st.selectbox(
        "🛤️ Selecciona el trayecto:", 
        options=lista_tablas,
        format_func=lambda x: nombres_bonitos[x]
    )
    
    st.divider()
    
    # Hemos movido aquí también el selector del mapa para tener todos los botones juntos
    estilo_mapa = st.radio(
        "🗺️ Tipo de mapa:", 
        ["Callejero", "Satélite"], 
        horizontal=False
    )
st.divider()

# --- NAVEGACIÓN PRINCIPAL CON PESTAÑAS ---
# Esto va en el cuerpo principal del script (sin tabular a la derecha)
tab1, tab2 = st.tabs(["📊 Monitorización", "📋 Sobre el Proyecto"])

# --- CONTENIDO DE LA PESTAÑA 1 ---
with tab1:
    st.title("🗺️ Histórico de Vibraciones por Trayecto")
    # Cargar datos de la tabla elegida
    with st.spinner(f"📡 Descargando datos de {nombres_bonitos[tabla_seleccionada]}..."):
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
        st.subheader(f"Resumen de: {nombres_bonitos[tabla_seleccionada]}")
        
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
        # Ahora esto está correctamente tabulado dentro del 'if not df_ruta.empty:'
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
    st.title("📖 Sobre FerroVixia")

    st.markdown("""
    ### 🚆 ¿Qué es FerroVixia?
    **FerroVixia** es un sistema inteligente de monitorización diseñado para mejorar la seguridad y el mantenimiento de las vías ferroviarias. 
    Mediante el análisis de vibraciones en tiempo real, detectamos anomalías y baches que podrían comprometer la infraestructura.
    """)

    col_a, col_b = st.columns(2)
    with col_a:
        st.info("#### 🎯 Objetivo\nVisualizar y analizar el estado de las vías mediante datos de acelerometría y GPS para una intervención predictiva.")
    with col_b:
        st.success("#### 🛠️ Tecnología\nStack moderno: Python 3.12, Streamlit, Supabase (PostgreSQL) y despliegue continuo en Azure.")

    st.subheader("⚙️ Funcionamiento del Pipeline")
    # Puedes usar un diagrama simple o una lista de pasos
    st.write("""
    1. **Captura:** Dispositivos M5Stack instalados en el tren recogen datos de aceleración y posición.
    2. **Procesado:** Un script en MATLAB filtra el ruido y calcula métricas de gravedad (CWT, WVD, Lambda).
    3. **Almacenamiento:** Los resultados se suben a nuestra base de datos Supabase.
    4. **Visualización:** Este Dashboard en la nube presenta la información de forma interactiva.
    """)
    
    # Podéis añadir aquí una imagen del hardware (M5Stack) o del equipo
    #st.image("hardware_setup.jpg", caption="Dispositivo de captura basado en M5Stack")


# --- PIE DE PÁGINA (FOOTER) ---
st.divider() # Línea sutil de separación

# Creamos 3 columnas: [Texto Nombres | Texto Contacto | Logos Universidad]
f1, f2, f3 = st.columns([2, 2, 1])

with f1:
    st.markdown("**Desarrollado por:**")
    st.write("👩‍💻 Nombre Ingeniera 1")
    st.write("👩‍💻 Nombre Ingeniera 2")

with f2:
    st.markdown("**Información de Contacto:**")
    st.write("📧 contacto@universidad.edu")
    st.write("📍 Escuela de Ingeniería, Vigo")

# with f3:
    # Aquí puedes poner el logo de la universidad
    # use_container_width=True hace que se ajuste al tamaño de la columna
    # st.image("logo_universidad.png", use_container_width=True)

# Nota de copyright opcional al final
st.caption("© 2026 Proyecto FerroVixia - Monitorización Ferroviaria en tiempo real")

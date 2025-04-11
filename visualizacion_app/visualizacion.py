import streamlit as st
import folium
from streamlit_folium import st_folium
from pymongo import MongoClient
import numpy as np
from scipy.interpolate import griddata
from folium.plugins import HeatMap
from branca.element import Template, MacroElement
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.colors as mcolors

# Conexión a MongoDB Atlas
uri = "mongodb+srv://balcarcelmar:20051413Mar@siatadatos.rkyypad.mongodb.net/datos_siata?retryWrites=true&w=majority&appName=SIATAdatos"
client = MongoClient(uri)
db = client["datos_siata"]
collection = db["datos_siata"]

# Obtener datos de sensores
datos = collection.find()
coordenadas = [
    (dato["coordinates"]["latitude"], dato["coordinates"]["longitude"], dato["value"], dato["location"])
    for dato in datos
]


def calcular_aqi_pm25(concentracion):
    """Convierte una concentración de PM2.5 a AQI usando los rangos EPA"""
    rangos = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for c_low, c_high, aqi_low, aqi_high in rangos:
        if c_low <= concentracion <= c_high:
            aqi = ((aqi_high - aqi_low) / (c_high - c_low)) * (concentracion - c_low) + aqi_low
            return round(aqi)
    return None  # fuera de rango

def color_por_aqi(aqi):
    if aqi <= 50:
        return "green"
    elif aqi <= 100:
        return "lightgreen"
    elif aqi <= 150:
        return "orange"
    elif aqi <= 200:
        return "red"
    elif aqi <= 300:
        return "purple"
    else:
        return "darkred"



# Extraer latitudes, longitudes y valores
latitudes, longitudes, valores, ubicaciones = zip(*coordenadas)

# Calcular AQI de cada valor (PM2.5 -> AQI)
aqis = [calcular_aqi_pm25(v) if calcular_aqi_pm25(v) is not None else 0 for v in valores]

# Crear una cuadrícula para interpolar
grid_lat, grid_lon = np.mgrid[
    min(latitudes):max(latitudes):100j,
    min(longitudes):max(longitudes):100j
]

# Interpolar usando valores AQI
grid_valores = griddata(
    (latitudes, longitudes), aqis, (grid_lat, grid_lon), method="cubic"
)

# Crear el mapa base centrado en Medellín
mapa_medellin = folium.Map(location=[6.2442, -75.5812], zoom_start=12)


# Cambia "valor" por AQI
aqis = [calcular_aqi_pm25(valor) for valor in valores]
grid_valores = griddata(
    (latitudes, longitudes), aqis, (grid_lat, grid_lon), method="cubic"
)
heat_data = [
    [grid_lat[i][j], grid_lon[i][j], grid_valores[i][j]]
    for i in range(grid_lat.shape[0]) for j in range(grid_lat.shape[1]) 
    if not np.isnan(grid_valores[i][j])
]

HeatMap(heat_data, radius=10).add_to(mapa_medellin)

# # Marcar puntos de sensores en el mapa
# for lat, lon, valor, ubicacion in coordenadas:
#     folium.Marker(
#         location=[lat, lon],
#         popup=f"Ubicación: {ubicacion}<br>Valor: {valor}",
#         icon=folium.Icon(color="blue", icon="info-sign")
#     ).add_to(mapa_medellin)

for lat, lon, valor, ubicacion in coordenadas:
    aqi = calcular_aqi_pm25(valor)
    if aqi is not None:
        color = color_por_aqi(aqi)
    else:
        color = "gray"  # Color neutro si no se puede calcular AQI

    folium.Marker(
        location=[lat, lon],
        popup=f"Ubicación: {ubicacion}<br>PM2.5: {valor}<br>AQI: {aqi if aqi is not None else 'No disponible'}",
        icon=folium.Icon(color=color, icon="info-sign")
    ).add_to(mapa_medellin)


# HTML para la leyenda
leyenda_html = """
{% macro html(this, kwargs) %}
<div style="
    position: fixed; 
    bottom: 50px; left: 50px; width: 180px; height: 250px; 
    background-color: white; 
    border:2px solid grey; z-index:9999; font-size:14px;
    padding: 10px;
    box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    color: black;
">
<b>AQI</b><br>
<i style="background:green;width:12px;height:12px;display:inline-block;"></i> Bueno (0-50)<br>
<i style="background:lightgreen;width:12px;height:12px;display:inline-block;"></i> Moderado (51-100)<br>
<i style="background:orange;width:12px;height:12px;display:inline-block;"></i> No saludable para sensibles (101-150)<br>
<i style="background:red;width:12px;height:12px;display:inline-block;"></i> No saludable (151-200)<br>
<i style="background:purple;width:12px;height:12px;display:inline-block;"></i> Muy no saludable (201-300)<br>
<i style="background:darkred;width:12px;height:12px;display:inline-block;"></i> Peligroso (301+)<br>
</div>
{% endmacro %}
"""

leyenda = MacroElement()
leyenda._template = Template(leyenda_html)
mapa_medellin.get_root().add_child(leyenda)


# Configuración inicial en Streamlit
st.set_page_config(page_title="Visualización Calidad del Aire", layout="wide")
st.title("Mapa de Calidad del Aire: Calidad del Aire en Medellín")

# Pestañas en Streamlit
tabs = st.tabs(["Mapa de calor", "Sensor vs Hora", "Ranking de sensores", "Acerca de"])

# Pestaña "Mapa de calor"
with tabs[0]:
    st.header("Mapa de Calidad del Aire")
    st.write("Distribución estimada basada en datos de sensores. Cada sensor tiene un color asociado de acuerdo a su estimación AQI.")

    # Mapa interactivo centrado
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st_folium(mapa_medellin, width="100%", height=800)

    # Mapa estático interpolado
    st.subheader("Mapa estático interpolado por hora")

    # Obtener todas las horas únicas de los datos
    datos_completos = list(collection.find())
    horas_disponibles = sorted(list(set(d["date"]["utc"][:13] for d in datos_completos)))
    hora_seleccionada = st.select_slider("Selecciona una hora (UTC)", options=horas_disponibles)

    # Filtrar datos por la hora seleccionada
    datos_filtrados = [
        d for d in datos_completos if d["date"]["utc"].startswith(hora_seleccionada)
    ]

    coordenadas = []
    for d in datos_filtrados:
        try:
            lat = d["coordinates"]["latitude"]
            lon = d["coordinates"]["longitude"]
            valor = d["value"]
            aqi = calcular_aqi_pm25(valor)
            if aqi is not None:
                coordenadas.append((lat, lon, aqi))
        except:
            continue

    if len(coordenadas) >= 3:
        latitudes, longitudes, aqis = zip(*coordenadas)

        grid_lat, grid_lon = np.mgrid[
            min(latitudes):max(latitudes):100j,
            min(longitudes):max(longitudes):100j
        ]
        grid_valores = griddata((latitudes, longitudes), aqis, (grid_lat, grid_lon), method='cubic')

        fig, ax = plt.subplots(figsize=(10, 8))

        # Rangos y colores AQI (EPA)
        niveles = [0, 50, 100, 150, 200, 300, 500]
        colores = ['green', 'yellow', 'orange', 'red', 'purple', 'maroon']

        # Crear un mapa de colores discreto
        cmap_aqi = mcolors.ListedColormap(colores)
        norm = mcolors.BoundaryNorm(niveles, cmap_aqi.N)

        # Colores AQI en degradado (del verde al rojo oscuro)
        colores_aqi = [
            (0.0, "green"),          # 0
            (50/500, "yellow"),      # 50
            (100/500, "orange"),     # 100
            (150/500, "red"),        # 150
            (200/500, "purple"),     # 200
            (300/500, "maroon"),     # 300
            (1.0, "maroon")          # 500
        ]

        # Crear colormap degradado
        cmap_aqi = mcolors.LinearSegmentedColormap.from_list("aqi_gradiente", colores_aqi)

        # Contour plot con degradado
        niveles_aqi = np.linspace(0, 500, 100)
        mapa = ax.contourf(grid_lon, grid_lat, grid_valores, levels=niveles_aqi, cmap=cmap_aqi, vmin=0, vmax=500)

        plt.colorbar(mapa, label='AQI', ax=ax)

        ax.scatter(longitudes, latitudes, c=aqis, cmap='RdYlGn_r', edgecolors='black')
        # Convertir la hora seleccionada UTC a datetime
        utc_dt = datetime.strptime(hora_seleccionada, "%Y-%m-%dT%H")
        local_dt = utc_dt - timedelta(hours=5)  # Colombia = UTC-5
        hora_local_str = local_dt.strftime("%Y-%m-%d %H:%M")

        # Título del gráfico con hora local
        ax.set_title(f"AQI interpolado - {hora_local_str} (hora local)")
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
    else:
        st.warning("No hay suficientes datos para generar el mapa en esta hora.")

#pestaña de graficas

with tabs[1]:
    st.header("Sensor vs Hora")
    st.write("Esta gráfica muestra el valor de la calidad del aire (AQI) de cada sensor hora a hora durante el día.")
    st.write("Selecciona el sensor del cual deseas ver la información.")

    # Obtener datos completos
    datos_completos = list(collection.find())

    # Lista de sensores únicos
    sensores = sorted(list(set(d["location"] for d in datos_completos)))
    sensor_seleccionado = st.selectbox("Selecciona un sensor", sensores)

    # Filtrar datos por sensor
    datos_sensor = [
        d for d in datos_completos
        if d["location"] == sensor_seleccionado and "value" in d and "date" in d
    ]

    # Extraer hora local y AQI
    registros = []
    for d in datos_sensor:
        try:
            valor = d["value"]
            aqi = calcular_aqi_pm25(valor)
            if aqi is None:
                continue
            utc_str = d["date"]["utc"]
            utc_dt = datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            local_dt = utc_dt - timedelta(hours=5)  # UTC-5 para Medellín
            hora = local_dt.strftime("%H:%M")
            registros.append((hora, aqi))
        except:
            continue

    if registros:
        registros.sort()
        horas, aqis = zip(*registros)

        import plotly.graph_objs as go

        fig = go.Figure()

        # Línea principal
        fig.add_trace(go.Scatter(
            x=horas,
            y=aqis,
            mode='lines+markers',
            marker=dict(color='blue'),
            name='AQI',
            hovertemplate='Hora: %{x}<br>AQI: %{y}<extra></extra>'
        ))

        # Zonas de color por rango AQI
        niveles = [0, 50, 100, 150, 200, 300, 500]
        colores = ['rgba(0,255,0,0.2)', 'rgba(255,255,0,0.2)', 'rgba(255,165,0,0.2)',
                   'rgba(255,0,0,0.2)', 'rgba(128,0,128,0.2)', 'rgba(128,0,0,0.2)']

        for i in range(len(niveles) - 1):
            fig.add_shape(
                type="rect",
                xref="paper", yref="y",
                x0=0, x1=1,
                y0=niveles[i], y1=niveles[i+1],
                fillcolor=colores[i],
                line=dict(width=0),
                layer='below'
            )
        # Calcular el máximo AQI y agregar un 10% de margen
        max_aqi = max(aqis)
        y_max = max_aqi * 1.1 if max_aqi < 500 else 510


        fig.update_layout(
            title=f"AQI por hora - {sensor_seleccionado} (hora local)",
            xaxis_title="Hora del día",
            yaxis_title="AQI",
            hovermode="x unified",
            height=550,
            plot_bgcolor='white',
            paper_bgcolor='#f9f9f9',
            font=dict(color='black'),

            xaxis=dict(
                showgrid=True,
                gridcolor='lightgray',
                tickfont=dict(color='black'),
                title=dict(font=dict(color='black'))
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='lightgray',
                range=[0, y_max],
                tickfont=dict(color='black'),
                title=dict(font=dict(color='black'))
            )

        )

        st.plotly_chart(fig, use_container_width=True)

        # Leyenda textual
        st.markdown("""
        **Rangos de AQI:**
        - 🟩 Bueno (0–50)  
        - 🟨 Moderado (51–100)  
        - 🟧 No saludable para sensibles (101–150)  
        - 🟥 No saludable (151–200)  
        - 🟪 Muy no saludable (201–300)  
        - 🟫 Peligroso (301+)  
        """)
    else:
        st.warning("No hay datos disponibles para este sensor.")

with tabs[2]:
    st.header("Ranking de Sensores por AQI promedio diario")
    st.write("Este ranking muestra los sensores ordenados según el promedio de AQI durante el día. Valores más altos indican peor calidad del aire.")

    # Obtener datos
    datos_completos = list(collection.find())

    # Agrupar por sensor
    sensores_dict = {}

    for d in datos_completos:
        try:
            location = d["location"]
            valor = d["value"]
            aqi = calcular_aqi_pm25(valor)
            if aqi is None:
                continue
            if location not in sensores_dict:
                sensores_dict[location] = []
            sensores_dict[location].append(aqi)
        except:
            continue

    # Calcular promedios
    ranking = []
    for sensor, aqis in sensores_dict.items():
        if len(aqis) >= 3:
            promedio = round(np.mean(aqis), 2)
            ranking.append((sensor, promedio))

    # Ordenar de mayor a menor
    ranking.sort(key=lambda x: x[1], reverse=True)

    # Mostrar tabla bonita
    import pandas as pd

    df = pd.DataFrame(ranking, columns=["Sensor", "AQI promedio"])

    # Clasificar
    def clasificar_aqi(aqi):
        if aqi <= 50:
            return "🟩 Bueno"
        elif aqi <= 100:
            return "🟨 Moderado"
        elif aqi <= 150:
            return "🟧 No saludable (sensibles)"
        elif aqi <= 200:
            return "🟥 No saludable"
        elif aqi <= 300:
            return "🟪 Muy no saludable"
        else:
            return "🟫 Peligroso"

    df["Clasificación"] = df["AQI promedio"].apply(clasificar_aqi)

    st.dataframe(df, use_container_width=True, height=600)



# Pestaña "Acerca de"
with tabs[3]:
    st.header("Acerca de")
    st.markdown("""
    Este proyecto presenta una visualización interactiva y descriptiva de la **calidad del aire en Medellín**, basada en datos recopilados de sensores urbanos y procesados en tiempo real.

    ### ¿Qué vas a encontrar?
    - Un **mapa interactivo** con interpolación espacial de los valores de AQI (Índice de Calidad del Aire), generado a partir de datos de sensores distribuidos en la ciudad.
    - Un **mapa estático interpolado por hora**, que permite explorar la evolución espacial del AQI a lo largo del día, filtrando por hora específica.
    - Una **gráfica AQI vs Hora** por sensor, que muestra cómo varía la calidad del aire a lo largo del día en una ubicación específica.
    - EL Ranking de los sensores con peor y mejor calidad.

    ### ¿De dónde provienen los datos?
    Los datos son extraídos desde una base de datos **MongoDB Atlas** que contiene registros de sensores del sistema **SIATA Medellín**, incluyendo:
    - Coordenadas geográficas de cada sensor
    - Tiempos en formato UTC
    - Concentraciones de contaminantes (PM2.5)
    - Conversión a **AQI** según los estándares de la **EPA (Environmental Protection Agency, EE.UU.)**

    ### ¿Qué tecnologías se están utilizando?
    - **Python** como lenguaje principal
    - **Streamlit** para la construcción del dashboard interactivo
    - **MongoDB Atlas** para almacenamiento de datos en la nube
    - **Folium** para mapas interactivos
    - **Matplotlib y Plotly** para visualizaciones estáticas y dinámicas
    - **Scipy y Numpy** para interpolación espacial
    - **AQI personalizado** usando rangos y colores definidos por normativas internacionales

    ### Objetivo
    Este sistema permite visualizar de forma clara, interactiva y técnica la situación de calidad del aire en Medellín, facilitando el análisis ambiental para ciudadanos, investigadores o autoridades.
    """)

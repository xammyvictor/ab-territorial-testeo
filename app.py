import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types
import time

# -------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------------------
st.set_page_config(
    page_title="Lab Territorial - Testeo y Validación",
    page_icon="🌱",
    layout="wide"
)

# Inicializar cliente Gemini
api_key = st.secrets.get("GEMINI_API_KEY")
client_ai = genai.Client(api_key=api_key) if api_key else None

# Conexión con Google Sheets vía gspread
@st.cache_resource
def obtener_conexion_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
        raise ValueError("No se encontró la configuración [connections.gsheets] en los Secrets.")
    
    gsheets_secrets = dict(st.secrets["connections"]["gsheets"])
    spreadsheet_url = gsheets_secrets.get("spreadsheet")
    
    if not spreadsheet_url:
        raise ValueError("Falta la URL de la hoja ('spreadsheet') en los Secrets.")
    
    campos_requeridos = [
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "auth_uri", "token_uri",
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    
    service_account_info = {k: gsheets_secrets[k] for k in campos_requeridos if k in gsheets_secrets}
    
    if "private_key" in service_account_info:
        service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
    
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    sh = gc.open_by_url(spreadsheet_url)
    return sh

try:
    sh = obtener_conexion_gsheet()
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# Estructura del proyecto según propuesta técnica (UNIMINUTO - IMCA)
ORGANIZACIONES_POR_MUNICIPIO = {
    "Florida": [
        "Asociación comunitaria indígena de la Rivera - ASOACIR",
        "Grupo de mujeres Nasa Uy Wesx Fxi'nxizas del Resguardo Triunfo Cristal Paez",
        "Asociación de usuarios para el distrito de riego - ASODIFLOR"
    ],
    "Pradera": [
        "Asociación Agropecuaria del Corregimiento La Feria - AGROFERIA",
        "Asociación de Mujeres Emprendedoras Rurales de Arenillo - ASOMERA"
    ],
    "Tuluá": [
        "Asociación de Agricultores Orgánicos de San Lorenzo - ASOAGROS",
        "Asociación de Escuelas Agroecológicas Sostenibles de San Rafael - ASEAS",
        "Asociación de Pequeños Caficultores de la Marina - ASOPECAM"
    ]
}

# Dimensiones técnicas vinculadas a preguntas sencillas y comunitarias
PREGUNTAS_COMUNITARIAS = {
    "Pertinencia": "¿Siente que este producto cuida y representa nuestras costumbres, tradiciones y la identidad del territorio?",
    "Funcionalidad": "¿Es fácil de usar, sirve para lo que se pensó y resuelve una necesidad real en el campo o en el hogar?",
    "Presentacion": "¿Le parece bonito, bien empacado, limpio y agradable a la vista?",
    "Diferenciacion": "¿Se nota diferente y especial frente a lo que se consigue en el mercado común?",
    "Potencial": "¿Cree que a la gente de afuera o del pueblo le gustaría comprarlo con frecuencia?",
    "Agregacion": "¿Siente que esta transformación le da más valor, orgullo y beneficio al trabajo campesino e indígena?"
}

CRITERIOS_TECNICOS = list(PREGUNTAS_COMUNITARIAS.keys())

def cargar_hoja(worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        valores = ws.get_all_values()
        if not valores or len(valores) <= 1:
            return pd.DataFrame()
        encabezados = [c.strip() for c in valores[0]]
        filas = valores[1:]
        return pd.DataFrame(filas, columns=encabezados)
    except Exception as e:
        st.error(f"Error al leer '{worksheet_name}': {e}")
        return pd.DataFrame()

# Barra lateral de navegación
st.sidebar.title("🌱 Lab Territorial")
st.sidebar.caption("Fase 4: Testeo Comunitario, Diálogo de Saberes e Innovación")
seccion = st.sidebar.radio("Navegación:", [
    "📝 Encuesta Comunitaria (Campo)",
    "📊 Panel Comparativo y Ganadores",
    "🤖 Diagnóstico IA y Ajustes"
])

# -------------------------------------------------------------
# 1. ENCUESTA COMUNITARIA (LENGUAJE SENCILLO PARA CAMPO)
# -------------------------------------------------------------
if seccion == "📝 Encuesta Comunitaria (Campo)":
    st.header("Validación Participativa y Diálogo de Saberes")
    st.write("Espacio comunitario para probar, valorar y enriquecer los frutos y propuestas del territorio.")

    with st.form("form_testeo", clear_on_submit=True):
        st.subheader("1. ¿De dónde viene y qué estamos conociendo?")
        col1, col2 = st.columns(2)
        with col1:
            muni = st.selectbox("Municipio / Territorio:", list(ORGANIZACIONES_POR_MUNICIPIO.keys()))
            org = st.selectbox("Organización / Colectivo:", ORGANIZACIONES_POR_MUNICIPIO[muni])
        with col2:
            prototipo = st.text_input("Nombre de la muestra o producto a valorar:")
            perfil = st.selectbox("¿Quién valora?:", [
                "Hermano/a de otra organización comunitaria",
                "Comprador / Visitante del territorio",
                "Acompañante técnico / Facilitador"
            ])

        st.subheader("2. ¿Cómo sentimos y valoramos esta propuesta?")
        st.caption("Puntaje del 1 al 5: (1: Nada de acuerdo / No me convence | 3: Regular / Puede mejorar | 5: Totalmente de acuerdo / ¡Excelente!)")
        
        califs = {}
        c_cols1, c_cols2 = st.columns(2)
        for idx, (clave, pregunta) in enumerate(PREGUNTAS_COMUNITARIAS.items()):
            col_target = c_cols1 if idx < 3 else c_cols2
            with col_target:
                califs[clave] = st.slider(f"**{pregunta}**", min_value=1, max_value=5, value=4)

        st.subheader("3. Oportunidad en el Mercado y Valor Justo")
        c_com1, c_com2 = st.columns(2)
        with c_com1:
            intencion = st.radio("¿Usted compraría o recomendaría este producto en su presentación final?", ["Sí", "Tal vez", "No"], horizontal=True)
        with c_com2:
            precio = st.number_input("¿Qué precio considera justo pagar por este producto? (COP):", min_value=0, step=500, value=10000)

        st.subheader("4. La Palabra de la Comunidad (Diálogo de Saberes)")
        cq1, cq2 = st.columns(2)
        with cq1:
            pos = st.text_area("¿Qué es lo más bonito, sabroso o valioso que tiene?:")
            dudas = st.text_area("¿Qué preguntas, dudas o inquietudes le deja el producto?:")
        with cq2:
            crit = st.text_area("¿Qué cosas no le gustaron o cree que están fallando?:")
            mejoras = st.text_area("¿Qué consejo o idea le da al colectivo para mejorar este fruto?:")

        submit = st.form_submit_button("Guardar Valoración en la Hoja de Trabajo")

        if submit:
            if not prototipo.strip():
                st.error("Por favor, ingrese el nombre del producto o propuesta a evaluar.")
            else:
                fila_a_insertar = [
                    muni,
                    org,
                    prototipo.strip(),
                    perfil,
                    califs["Pertinencia"],
                    califs["Funcionalidad"],
                    califs["Presentacion"],
                    califs["Diferenciacion"],
                    califs["Potencial"],
                    califs["Agregacion"],
                    intencion,
                    precio,
                    pos,
                    dudas,
                    crit,
                    mejoras
                ]
                try:
                    ws_encuestas = sh.worksheet("Encuestas")
                    ws_encuestas.append_row(fila_a_insertar)
                    st.success(f"¡Valoración registrada con éxito para '{prototipo}'!")
                except Exception as e:
                    st.error(f"Error al guardar en Google Sheets: {e}")

# -------------------------------------------------------------
# 2. PANEL DE CONTROL COMPARATIVO Y GANADORES
# -------------------------------------------------------------
elif seccion == "📊 Panel Comparativo y Ganadores":
    st.header("Panel de Resultados y Comparativo de Prototipos")
    if st.button("🔄 Actualizar datos desde Google Sheets"):
        st.rerun()

    df_enc = cargar_hoja("Encuestas")

    if df_enc.empty or 'Prototipo' not in df_enc.columns:
        st.warning("Aún no hay valoraciones registradas en Google Sheets.")
    else:
        # Filtros en barra lateral para analítica
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtros de Visualización")
        
        lista_municipios = ["Todos"] + list(df_enc["Municipio"].dropna().unique())
        filtro_muni = st.sidebar.selectbox("Filtrar por Municipio:", lista_municipios)
        
        df_filtrado_muni = df_enc.copy()
        if filtro_muni != "Todos":
            df_filtrado_muni = df_filtrado_muni[df_filtrado_muni["Municipio"] == filtro_muni]

        lista_prototipos = ["Todos"] + list(df_filtrado_muni["Prototipo"].dropna().unique())
        filtro_proto = st.sidebar.selectbox("Filtrar por Prototipo:", lista_prototipos)
        
        df_analisis = df_filtrado_muni.copy()
        if filtro_proto != "Todos":
            df_analisis = df_analisis[df_analisis["Prototipo"] == filtro_proto]

        # Métricas generales del filtro actual
        criterios_existentes = [c for c in CRITERIOS_TECNICOS if c in df_analisis.columns]
        
        total_eval = len(df_analisis)
        if criterios_existentes and total_eval > 0:
            ratings = df_analisis[criterios_existentes].apply(pd.to_numeric, errors='coerce').values.flatten()
            favorables = (ratings >= 4).sum()
            total_preg = len(ratings[~pd.isna(ratings)])
            favorabilidad = (favorables / total_preg) * 100 if total_preg > 0 else 0
            promedio_general = ratings[~pd.isna(ratings)].mean() if total_preg > 0 else 0
        else:
            favorabilidad = 0
            promedio_general = 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Encuestas Evaluadas", f"{total_eval}")
        with kpi2:
            st.metric("Promedio General (1 a 5)", f"{promedio_general:.2f} / 5.0")
        with kpi3:
            st.metric("Índice de Aceptación", f"{favorabilidad:.1f}%", delta=f"{favorabilidad - 70:.1f}% vs meta (70%)")
        with kpi4:
            st.metric("Variedad de Prototipos", f"{df_analisis['Prototipo'].nunique()}")

        st.divider()

        # SECCIÓN DE RANKING Y GANADORES (Calculado sobre el universo filtrado por municipio)
        st.subheader("🏆 Cuadro de Honor y Comparativo de Desempeño")
        st.write("Identificación de los prototipos con mayor aceptación e impacto según los saberes comunitarios.")

        # Calcular promedios por prototipo
        df_agrupado = df_filtrado_muni.copy()
        for c in criterios_existentes:
            df_agrupado[c] = pd.to_numeric(df_agrupado[c], errors='coerce')

        ranking = df_agrupado.groupby("Prototipo").agg(
            Evaluaciones=("Municipio", "count"),
            **{c: (c, "mean") for c in criterios_existentes}
        ).reset_index()

        ranking["Promedio_Final"] = ranking[criterios_existentes].mean(axis=1)
        ranking = ranking.sort_values(by="Promedio_Final", ascending=False).reset_index(drop=True)
        ranking["Lugar"] = ranking.index + 1

        # Identificar ganador
        if not ranking.empty:
            ganador = ranking.iloc[0]
            col_trofeo, col_podio = st.columns([1, 2])
            with col_trofeo:
                st.info(f"### 🥇 Prototipo Líder:\n**{ganador['Prototipo']}**\n\n⭐ **Calificación:** {ganador['Promedio_Final']:.2f} / 5.0\n\n👥 **Evaluaciones:** {int(ganador['Evaluaciones'])}")
            with col_podio:
                st.write("**Top de Prototipos Destacados**")
                st.dataframe(
                    ranking[["Lugar", "Prototipo", "Evaluaciones", "Promedio_Final"] + criterios_existentes].style.format({
                        "Promedio_Final": "{:.2f}",
                        **{c: "{:.2f}" for c in criterios_existentes}
                    }),
                    use_container_width=True
                )

            # Gráfica de barras comparativa entre prototipos
            st.write("#### 📊 Comparativa de Calificación Global entre Prototipos")
            fig_ranking = px.bar(
                ranking,
                x="Prototipo",
                y="Promedio_Final",
                text="Promedio_Final",
                color="Promedio_Final",
                color_continuous_scale="Greens",
                range_y=[1, 5],
                labels={"Promedio_Final": "Calificación Media (1-5)"}
            )
            fig_ranking.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig_ranking, use_container_width=True)

        st.divider()

        # Detalle de criterios técnicos
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Muestreo por Territorio")
            conteo_muni = df_filtrado_muni["Municipio"].value_counts().reset_index()
            conteo_muni.columns = ["Municipio", "Total"]
            fig_muni = px.bar(conteo_muni, x="Municipio", y="Total", color="Municipio", text="Total")
            st.plotly_chart(fig_muni, use_container_width=True)

        with col_g2:
            st.subheader("Balance por Dimensión Evaluada")
            promedios = df_analisis[criterios_existentes].apply(pd.to_numeric, errors='coerce').mean().reset_index()
            promedios.columns = ["Criterio", "Promedio"]
            fig_radar = px.line_polar(promedios, r="Promedio", theta="Criterio", line_close=True, range_r=[1, 5])
            st.plotly_chart(fig_radar, use_container_width=True)

# -------------------------------------------------------------
# 3. ASISTENTE IA PARA SÍNTESIS Y AJUSTES
# -------------------------------------------------------------
elif seccion == "🤖 Diagnóstico IA y Ajustes":
    st.header("Análisis con IA: Síntesis de Saberes y Oportunidades")
    st.write("Gemini procesa las evaluaciones comunitarias para redactar las mejoras orientadas a la apropiación y sostenibilidad.")

    if st.button("🔄 Actualizar datos desde Google Sheets"):
        st.rerun()

    df_enc = cargar_hoja("Encuestas")

    if df_enc.empty or 'Prototipo' not in df_enc.columns:
        st.warning("Se requieren evaluaciones previas para ejecutar el análisis de IA.")
    else:
        prototipos_disponibles = [p for p in df_enc["Prototipo"].unique() if str(p).strip()]
        proto_sel = st.selectbox("Seleccione el prototipo a sistematizar:", prototipos_disponibles)
        df_filtrado = df_enc[df_enc["Prototipo"] == proto_sel]

        criterios_existentes = [c for c in CRITERIOS_TECNICOS if c in df_filtrado.columns]
        promedio_proto = df_filtrado[criterios_existentes].apply(pd.to_numeric, errors='coerce').mean().to_dict() if criterios_existentes else {}
        
        comentarios_positivos = " | ".join(df_filtrado["Positivos"].dropna().astype(str).tolist()) if "Positivos" in df_filtrado.columns else ""
        comentarios_dudas = " | ".join(df_filtrado["Dudas"].dropna().astype(str).tolist()) if "Dudas" in df_filtrado.columns else ""
        comentarios_criticas = " | ".join(df_filtrado["Criticas"].dropna().astype(str).tolist()) if "Criticas" in df_filtrado.columns else ""
        comentarios_mejoras = " | ".join(df_filtrado["Mejoras"].dropna().astype(str).tolist()) if "Mejoras" in df_filtrado.columns else ""
        
        municipio_asoc = df_filtrado["Municipio"].iloc[0] if "Municipio" in df_filtrado.columns else "No definido"
        org_asoc = df_filtrado["Organizacion"].iloc[0] if "Organizacion" in df_filtrado.columns else "No definida"

        st.write(f"**Territorio:** {municipio_asoc} | **Organización:** {org_asoc}")
        st.write(f"**Número de testimonios y valoraciones:** {len(df_filtrado)}")

        if st.button("🚀 Analizar con IA y Generar Cuadro de Ajustes"):
            if not client_ai:
                st.error("No se ha configurado la variable GEMINI_API_KEY en los Secrets.")
            else:
                with st.spinner("Sintetizando aportes comunitarios con Gemini..."):
                    prompt = f"""
                    Eres un consultor experto en innovación agroecológica territorial, diálogo de saberes campesinos e indígenas para UNIMINUTO e IMCA.
                    Analiza la información de validación comunitaria:
                    - Prototipo: {proto_sel}
                    - Municipio: {municipio_asoc}
                    - Organización: {org_asoc}
                    - Promedios por dimensión (1-5): {promedio_proto}
                    - Aspectos destacados por la comunidad: {comentarios_positivos}
                    - Dudas o inquietudes de la comunidad: {comentarios_dudas}
                    - Críticas o aspectos a mejorar: {comentarios_criticas}
                    - Consejos comunitarios: {comentarios_mejoras}

                    Genera con enfoque respetuoso y pedagógico:
                    1. 3 Oportunidades de mejora concretas (en empaque, transformación, saberes ancestrales o comercialización justa).
                    2. Cuadro comparativo técnico para el informe final:
                       - "Versión Inicial del Prototipo" (resumen de lo probado)
                       - "Mejoras Priorizadas de la Comunidad" (mínimo 2 acuerdos clave)
                       - "Prototipo Ajustado / Versión Final" (propuesta enriquecida)
                    """

                    modelos_prioritarios = [
                        'gemini-2.0-flash',
                        'gemini-2.0-flash-lite',
                        'gemini-2.5-pro',
                        'gemini-3.8-flash'
                    ]

                    respuesta = None
                    ultimo_error = None

                    for nombre_modelo in modelos_prioritarios:
                        try:
                            respuesta = client_ai.models.generate_content(
                                model=nombre_modelo,
                                contents=prompt,
                                config=types.GenerateContentConfig(temperature=0.2)
                            )
                            if respuesta and hasattr(respuesta, 'text') and respuesta.text:
                                break
                        except Exception as e:
                            ultimo_error = e
                            time.sleep(2)
                            continue

                    if respuesta and hasattr(respuesta, 'text') and respuesta.text:
                        st.markdown("### 📋 Resultados del Diálogo Sistematizado con IA")
                        st.markdown(respuesta.text)
                    else:
                        st.error(f"Servicio saturado temporalmente. Intente de nuevo en segundos. Detalle: {ultimo_error}")

                    st.divider()
                    st.subheader("Guardar Ajuste Oficial en Google Sheets")
                    with st.form("form_confirmar_ajuste"):
                        v_ini = st.text_area("Versión Inicial probada en campo:", value=f"Prototipo de {proto_sel} probado en {municipio_asoc}.")
                        v_mej = st.text_area("Mejoras y acuerdos comunitarios:", value="Ajustes técnicos identificados en el diálogo de saberes e IA.")
                        v_fin = st.text_area("Prototipo Ajustado Final:", value="Versión con identidad territorial optimizada para ExpoViva.")
                        btn_guardar_bd = st.form_submit_button("Guardar en Pestaña 'Ajustes'")

                        if btn_guardar_bd:
                            fila_ajuste = [
                                municipio_asoc,
                                org_asoc,
                                proto_sel,
                                v_ini,
                                v_mej,
                                v_fin
                            ]
                            try:
                                ws_ajustes = sh.worksheet("Ajustes")
                                ws_ajustes.append_row(fila_ajuste)
                                st.success("Ajuste registrado oficialmente en la pestaña 'Ajustes' de Google Sheets.")
                            except Exception as err:
                                st.error(f"Error al guardar ajuste: {err}")

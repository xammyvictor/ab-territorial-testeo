import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from google import genai
from google.genai import types

# -------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# -------------------------------------------------------------
st.set_page_config(
    page_title="Lab Territorial - Testeo y Validación",
    page_icon="🌱",
    layout="wide"
)

# Inicializar cliente Gemini
api_key = st.secrets.get("GEMINI_API_KEY")
client_ai = genai.Client(api_key=api_key) if api_key else None

# Conexión nativa y segura con Google Sheets usando gspread
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

CRITERIOS = [
    "Pertinencia", "Funcionalidad", "Presentacion",
    "Diferenciacion", "Potencial", "Agregacion"
]

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

# Menú lateral
st.sidebar.title("🌱 Lab Territorial")
st.sidebar.caption("Fase 4: Testeo Comunitario, Validación y Apropiación")
seccion = st.sidebar.radio("Navegación:", [
    "📝 Encuesta de Validación (Campo)",
    "📊 Panel de Control e Indicadores",
    "🤖 Diagnóstico IA y Ajustes"
])

# -------------------------------------------------------------
# 1. ENCUESTA DE VALIDACIÓN (REGISTRO EN GOOGLE SHEETS)
# -------------------------------------------------------------
if seccion == "📝 Encuesta de Validación (Campo)":
    st.header("Formulario de Testeo y Diálogo de Saberes")
    st.write("Instrumento participativo de recolección en campo para validación comunitaria.")

    with st.form("form_testeo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            muni = st.selectbox("Municipio:", list(ORGANIZACIONES_POR_MUNICIPIO.keys()))
            org = st.selectbox("Organización:", ORGANIZACIONES_POR_MUNICIPIO[muni])
        with col2:
            prototipo = st.text_input("Nombre o código del prototipo evaluado:")
            perfil = st.selectbox("Evaluador:", [
                "Integrante de otra organización comunitaria",
                "Consumidor / Visitante territorial",
                "Facilitador / Equipo técnico"
            ])

        st.markdown("### Calificación de Criterios (Escala 1 a 5)")
        c_cols1, c_cols2 = st.columns(2)
        califs = {}
        for idx, crit in enumerate(CRITERIOS):
            c_target = c_cols1 if idx < 3 else c_cols2
            with c_target:
                califs[crit] = st.slider(f"{crit} territorial/técnica:", 1, 5, 4)

        c_com1, c_com2 = st.columns(2)
        with c_com1:
            intencion = st.radio("¿Compraría o comercializaría la versión final?", ["Sí", "Tal vez", "No"], horizontal=True)
        with c_com2:
            precio = st.number_input("Precio estimado razonable (COP):", min_value=0, step=500, value=12000)

        st.markdown("### Diálogo Cualitativo de Saberes")
        cq1, cq2 = st.columns(2)
        with cq1:
            pos = st.text_area("Fortalezas y aspectos valiosos destacados:")
            dudas = st.text_area("Dudas, inquietudes o vacíos del prototipo:")
        with cq2:
            crit = st.text_area("Críticas constructivas / Deficiencias detectadas:")
            mejoras = st.text_area("Recomendaciones e ideas de mejora comunitaria:")

        submit = st.form_submit_button("Guardar en Google Sheets")

        if submit:
            if not prototipo.strip():
                st.error("Ingrese el nombre del prototipo antes de guardar.")
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
                    st.success(f"Evaluación guardada exitosamente en la nube para '{prototipo}'.")
                except Exception as e:
                    st.error(f"Error al guardar en Google Sheets: {e}")

# -------------------------------------------------------------
# 2. PANEL DE CONTROL E INDICADORES
# -------------------------------------------------------------
elif seccion == "📊 Panel de Control e Indicadores":
    st.header("Métricas de Validación y Apropiación")
    if st.button("🔄 Actualizar datos desde Google Sheets"):
        st.rerun()

    df_enc = cargar_hoja("Encuestas")

    if df_enc.empty:
        st.warning("No hay encuestas almacenadas en Google Sheets todavía.")
    else:
        kpi1, kpi2, kpi3 = st.columns(3)
        total_eval = len(df_enc)
        
        # Validar y calcular favorabilidad (puntajes >= 4)
        criterios_existentes = [c for c in CRITERIOS if c in df_enc.columns]
        if criterios_existentes:
            ratings = df_enc[criterios_existentes].apply(pd.to_numeric, errors='coerce').values.flatten()
            favorables = (ratings >= 4).sum()
            total_preguntas = len(ratings[~pd.isna(ratings)])
            indice_favorabilidad = (favorables / total_preguntas) * 100 if total_preguntas > 0 else 0
        else:
            indice_favorabilidad = 0

        with kpi1:
            st.metric("Total Encuestas Aplicadas", f"{total_eval} / 60 meta")
        with kpi2:
            st.metric("Índice de Aceptación", f"{indice_favorabilidad:.1f}%", 
                      delta=f"{indice_favorabilidad - 70:.1f}% vs meta (70%)")
        with kpi3:
            total_prototipos = df_enc['Prototipo'].nunique() if 'Prototipo' in df_enc.columns else 0
            st.metric("Prototipos Evaluados", f"{total_prototipos} / 15")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if "Municipio" in df_enc.columns:
                st.subheader("Encuestas por Municipio (Meta: 20 c/u)")
                conteo_muni = df_enc["Municipio"].value_counts().reset_index()
                conteo_muni.columns = ["Municipio", "Total"]
                fig_bar = px.bar(conteo_muni, x="Municipio", y="Total", color="Municipio", text="Total")
                st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            if criterios_existentes:
                st.subheader("Promedio de Criterios Técnicos")
                promedios = df_enc[criterios_existentes].apply(pd.to_numeric, errors='coerce').mean().reset_index()
                promedios.columns = ["Criterio", "Promedio"]
                fig_radar = px.line_polar(promedios, r="Promedio", theta="Criterio", line_close=True, range_r=[1, 5])
                st.plotly_chart(fig_radar, use_container_width=True)

# -------------------------------------------------------------
# 3. ASISTENTE IA PARA DIÁLOGO Y GENERACIÓN DE AJUSTES
# -------------------------------------------------------------
elif seccion == "🤖 Diagnóstico IA y Ajustes":
    st.header("Análisis con IA: Síntesis de Saberes y Oportunidades")
    st.write("Gemini procesa las evaluaciones comunitarias y redacta los ajustes para el informe final.")

    if st.button("🔄 Actualizar datos desde Google Sheets"):
        st.rerun()

    df_enc = cargar_hoja("Encuestas")

    if df_enc.empty or 'Prototipo' not in df_enc.columns:
        st.warning("Se requieren encuestas previas en Google Sheets para ejecutar el análisis.")
    else:
        prototipos_disponibles = [p for p in df_enc["Prototipo"].unique() if str(p).strip()]
        proto_sel = st.selectbox("Seleccione el prototipo a evaluar:", prototipos_disponibles)
        df_filtrado = df_enc[df_enc["Prototipo"] == proto_sel]

        criterios_existentes = [c for c in CRITERIOS if c in df_filtrado.columns]
        promedio_proto = df_filtrado[criterios_existentes].apply(pd.to_numeric, errors='coerce').mean().to_dict() if criterios_existentes else {}
        
        comentarios_positivos = " | ".join(df_filtrado["Positivos"].dropna().astype(str).tolist()) if "Positivos" in df_filtrado.columns else ""
        comentarios_dudas = " | ".join(df_filtrado["Dudas"].dropna().astype(str).tolist()) if "Dudas" in df_filtrado.columns else ""
        comentarios_criticas = " | ".join(df_filtrado["Criticas"].dropna().astype(str).tolist()) if "Criticas" in df_filtrado.columns else ""
        comentarios_mejoras = " | ".join(df_filtrado["Mejoras"].dropna().astype(str).tolist()) if "Mejoras" in df_filtrado.columns else ""
        
        municipio_asoc = df_filtrado["Municipio"].iloc[0] if "Municipio" in df_filtrado.columns else "No definido"
        org_asoc = df_filtrado["Organizacion"].iloc[0] if "Organizacion" in df_filtrado.columns else "No definida"

        st.write(f"**Municipio:** {municipio_asoc} | **Organización:** {org_asoc}")
        st.write(f"**Número de evaluaciones registradas:** {len(df_filtrado)}")

        if st.button("🚀 Analizar con IA y Generar Propuesta de Ajuste"):
            if not client_ai:
                st.error("No se ha configurado la variable GEMINI_API_KEY en los Secrets.")
            else:
                with st.spinner("Procesando diálogo comunitario con Gemini..."):
                    prompt = f"""
                    Eres un consultor experto en innovación agroecológica territorial para UNIMINUTO e IMCA.
                    Analiza la siguiente información de testeo comunitario:
                    - Prototipo: {proto_sel}
                    - Municipio: {municipio_asoc}
                    - Organización: {org_asoc}
                    - Calificaciones promedio (1-5): {promedio_proto}
                    - Fortalezas destacadas: {comentarios_positivos}
                    - Dudas identificadas: {comentarios_dudas}
                    - Críticas observadas: {comentarios_criticas}
                    - Sugerencias comunitarias: {comentarios_mejoras}

                    Genera:
                    1. 3 Oportunidades de mejora concretas (empaque, transformación o diferenciación).
                    2. Cuadro comparativo técnico:
                       - Versión Inicial del Prototipo
                       - Mejoras Priorizadas de la Comunidad (mínimo 2 mejoras)
                       - Prototipo Ajustado / Versión Final
                    """
                    
                    # Lista de modelos compatibles para tolerancia a fallos 503/404
                    modelos_candidatos = [
                        'gemini-2.5-flash',
                        'gemini-2.0-flash',
                        'gemini-1.5-flash',
                        'gemini-3.8-flash'
                    ]
                    
                    respuesta = None
                    ultimo_error = None

                    for nombre_modelo in modelos_candidatos:
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
                            continue

                    if respuesta and hasattr(respuesta, 'text') and respuesta.text:
                        st.markdown("### 📋 Resultados del Diagnóstico IA")
                        st.markdown(respuesta.text)
                    else:
                        st.error(f"Servicio saturado temporalmente. Intente de nuevo en segundos. Detalle: {ultimo_error}")

                    st.divider()
                    st.subheader("Guardar Ajuste Oficial en Google Sheets")
                    with st.form("form_confirmar_ajuste"):
                        v_ini = st.text_area("Versión Inicial:", value=f"Prototipo de {proto_sel} probado en {municipio_asoc}.")
                        v_mej = st.text_area("Mejoras Incorporadas:", value="Ajustes técnicos identificados por la comunidad e IA.")
                        v_fin = st.text_area("Prototipo Ajustado Final:", value="Versión con identidad territorial optimizada.")
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

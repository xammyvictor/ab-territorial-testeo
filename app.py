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

# Diccionario de Preguntas del Bloque 2 (Desagregadas por atributos independientes)
PREGUNTAS_DETALLADAS = {
    "P1_Tradicion": "P1. Refleja y respeta las tradiciones y saberes de las comunidades de la región.",
    "P2_Origen_Territorial": "P2. Se reconoce con claridad que proviene del trabajo campesino o indígena del territorio.",
    "P3_Cumple_Proposito": "P3. Cumple adecuadamente con el propósito o función para la cual fue pensado.",
    "P4_Facil_Uso": "P4. Es cómodo, práctico y fácil de usar, manejar o consumir.",
    "P5_Soluciona_Necesidad": "P5. Ayuda a atender una necesidad real en el hogar, el campo o la comunidad.",
    "P6_Visual_Atractivo": "P6. El aspecto visual general y el diseño de la etiqueta son atractivos.",
    "P7_Empaque_Adecuado": "P7. El empaque protege bien el producto y es adecuado para su conservación y traslado.",
    "P8_Buena_Calidad": "P8. Transmite una sensación de higiene, esmero y buena calidad.",
    "P9_Diferenciacion": "P9. Se distingue con facilidad frente a alternativas comerciales convencionales.",
    "P10_Valor_Agregado": "P10. La transformación o acabado final aporta un valor adicional a la materia prima."
}

COLUMNAS_CRITERIOS = list(PREGUNTAS_DETALLADAS.keys())

OPCIONES_LIKERT = [
    "1 - Totalmente en desacuerdo",
    "2 - En desacuerdo",
    "3 - Ni de acuerdo ni en desacuerdo",
    "4 - De acuerdo",
    "5 - Totalmente de acuerdo"
]

def parsear_likert(texto_opcion):
    return int(texto_opcion.split(" - ")[0])

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
    "📊 Panel Comparativo y Ganadores",
    "🤖 Diagnóstico IA y Ajustes"
])

# -------------------------------------------------------------
# 1. ENCUESTA ORGANIZADA POR BLOQUES METODOLÓGICOS
# -------------------------------------------------------------
if seccion == "📝 Encuesta de Validación (Campo)":
    st.header("Formulario de Testeo Comunitario y Diálogo de Saberes")
    st.caption("Instrumento estandarizado por bloques independientes de valoración.")

    with st.form("form_testeo", clear_on_submit=True):
        # BLOQUE 1: CARACTERIZACIÓN
        st.subheader("Bloque 1: Caracterización de la Valoración y del Evaluador")
        col1, col2 = st.columns(2)
        with col1:
            muni = st.selectbox("Municipio / Territorio:", list(ORGANIZACIONES_POR_MUNICIPIO.keys()))
            org = st.selectbox("Organización responsable:", ORGANIZACIONES_POR_MUNICIPIO[muni])
            prototipo = st.text_input("Nombre o código del prototipo a evaluar:")
        with col2:
            perfil = st.selectbox("Perfil de quien evalúa:", [
                "Integrante de otra organización comunitaria / campesina / indígena",
                "Consumidor o habitante del territorio",
                "Acompañante técnico / Facilitador institucional"
            ])
            st.write("**Durante la valoración usted (marque todas las que apliquen):**")
            cb_obs = st.checkbox("Observó la presentación y empaque")
            cb_man = st.checkbox("Manipuló el producto con sus manos")
            cb_deg = st.checkbox("Degustó o probó el producto")
            cb_exp = st.checkbox("Recibió una explicación o relato del producto")

        st.divider()

        # BLOQUE 2: VALORACIÓN DE ATRIBUTOS DEL PRODUCTO
        st.subheader("Bloque 2: Valoración de Atributos del Prototipo")
        st.caption("Responda de forma independiente para cada afirmación (Escala homogénea de 1 a 5).")

        califs = {}

        st.markdown("#### A. Identidad Territorial y Saberes Locales")
        c1, c2 = st.columns(2)
        with c1:
            califs["P1_Tradicion"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P1_Tradicion"],
                OPCIONES_LIKERT, index=3, key="p1"
            ))
        with c2:
            califs["P2_Origen_Territorial"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P2_Origen_Territorial"],
                OPCIONES_LIKERT, index=3, key="p2"
            ))

        st.markdown("#### B. Funcionalidad, Uso y Utilidad Práctica")
        f1, f2, f3 = st.columns(3)
        with f1:
            califs["P3_Cumple_Proposito"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P3_Cumple_Proposito"],
                OPCIONES_LIKERT, index=3, key="p3"
            ))
        with f2:
            califs["P4_Facil_Uso"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P4_Facil_Uso"],
                OPCIONES_LIKERT, index=3, key="p4"
            ))
        with f3:
            califs["P5_Soluciona_Necesidad"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P5_Soluciona_Necesidad"],
                OPCIONES_LIKERT, index=3, key="p5"
            ))

        st.markdown("#### C. Presentación, Empaque y Calidad Percibida")
        p1, p2, p3 = st.columns(3)
        with p1:
            califs["P6_Visual_Atractivo"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P6_Visual_Atractivo"],
                OPCIONES_LIKERT, index=3, key="p6"
            ))
        with p2:
            califs["P7_Empaque_Adecuado"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P7_Empaque_Adecuado"],
                OPCIONES_LIKERT, index=3, key="p7"
            ))
        with p3:
            califs["P8_Buena_Calidad"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P8_Buena_Calidad"],
                OPCIONES_LIKERT, index=3, key="p8"
            ))

        st.markdown("#### D. Diferenciación y Agregación de Valor")
        d1, d2 = st.columns(2)
        with d1:
            califs["P9_Diferenciacion"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P9_Diferenciacion"],
                OPCIONES_LIKERT, index=3, key="p9"
            ))
        with d2:
            califs["P10_Valor_Agregado"] = parsear_likert(st.radio(
                PREGUNTAS_DETALLADAS["P10_Valor_Agregado"],
                OPCIONES_LIKERT, index=3, key="p10"
            ))

        st.divider()

        # BLOQUE 3: ACEPTACIÓN, INTENCIÓN DE COMPRA Y PRECIO
        st.subheader("Bloque 3: Aceptación, Intención de Compra y Valoración Económica")
        b3_col1, b3_col2, b3_col3 = st.columns(3)
        with b3_col1:
            intencion_compra = st.radio(
                "Si el producto estuviera a la venta, ¿qué tan probable sería que lo compre?",
                [
                    "1 - Definitivamente no lo compraría",
                    "2 - Probablemente no lo compraría",
                    "3 - Podría o no comprarlo",
                    "4 - Probablemente lo compraría",
                    "5 - Definitivamente lo compraría"
                ],
                index=3
            )
        with b3_col2:
            recomendacion = st.radio(
                "¿Recomendaría este producto a otras personas?",
                ["Sí", "Tal vez", "No"],
                horizontal=True
            )
        with b3_col3:
            precio = st.number_input(
                "Precio de venta justo y adecuado para esta presentación ($ COP):",
                min_value=0, step=500, value=12000
            )

        st.divider()

        # BLOQUE 4: DIÁLOGO DE SABERES Y RECOMENDACIONES
        st.subheader("Bloque 4: Diálogo de Saberes y Recomendaciones Comunitarias")
        dq1, dq2 = st.columns(2)
        with dq1:
            valioso = st.text_area("¿Qué es lo que más valora o destaca de este producto o propuesta?:")
            dudas = st.text_area("¿Qué preguntas, dudas o vacíos de información le genera el producto?:")
        with dq2:
            por_mejorar = st.text_area("¿Qué aspectos o características considera indispensables mejorar?:")
            recomendaciones = st.text_area("¿Qué recomendación práctica le daría al colectivo para fortalecer la iniciativa?:")

        submit = st.form_submit_button("Guardar Evaluación en Google Sheets")

        if submit:
            if not prototipo.strip():
                st.error("Por favor ingrese el nombre del prototipo antes de guardar.")
            else:
                interacciones = []
                if cb_obs: interacciones.append("Observó")
                if cb_man: interacciones.append("Manipuló")
                if cb_deg: interacciones.append("Degustó")
                if cb_exp: interacciones.append("Explicación")
                texto_interaccion = ", ".join(interacciones) if interacciones else "No especificada"

                fila_a_insertar = [
                    muni,
                    org,
                    prototipo.strip(),
                    perfil,
                    texto_interaccion,
                    califs["P1_Tradicion"],
                    califs["P2_Origen_Territorial"],
                    califs["P3_Cumple_Proposito"],
                    califs["P4_Facil_Uso"],
                    califs["P5_Soluciona_Necesidad"],
                    califs["P6_Visual_Atractivo"],
                    califs["P7_Empaque_Adecuado"],
                    califs["P8_Buena_Calidad"],
                    califs["P9_Diferenciacion"],
                    califs["P10_Valor_Agregado"],
                    intencion_compra,
                    recomendacion,
                    precio,
                    valioso,
                    dudas,
                    por_mejorar,
                    recomendaciones
                ]
                try:
                    ws_encuestas = sh.worksheet("Encuestas")
                    ws_encuestas.append_row(fila_a_insertar)
                    st.success(f"Evaluación guardada exitosamente para '{prototipo}'.")
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
        st.warning("Aún no hay evaluaciones registradas en Google Sheets.")
    else:
        # Filtros laterales
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtros de Consulta")

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

        criterios_presentes = [c for c in COLUMNAS_CRITERIOS if c in df_analisis.columns]

        # Métricas de avance
        total_eval = len(df_analisis)
        if criterios_presentes and total_eval > 0:
            ratings = df_analisis[criterios_presentes].apply(pd.to_numeric, errors='coerce').values.flatten()
            favorables = (ratings >= 4).sum()
            total_preg = len(ratings[~pd.isna(ratings)])
            favorabilidad = (favorables / total_preg) * 100 if total_preg > 0 else 0
            promedio_general = ratings[~pd.isna(ratings)].mean() if total_preg > 0 else 0
        else:
            favorabilidad = 0
            promedio_general = 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Total Evaluaciones", f"{total_eval}")
        with k2:
            st.metric("Promedio General (1-5)", f"{promedio_general:.2f} / 5.0")
        with k3:
            st.metric("Índice de Aceptación", f"{favorabilidad:.1f}%", delta=f"{favorabilidad - 70:.1f}% vs meta (70%)")
        with k4:
            st.metric("Variedad de Prototipos", f"{df_analisis['Prototipo'].nunique()}")

        st.divider()

        # CUADRO DE HONOR Y GANADORES
        st.subheader("🏆 Cuadro de Honor y Comparativo de Prototipos")
        st.caption("Calculado a partir de la ponderación de los 10 atributos específicos evaluados.")

        df_agrupado = df_filtrado_muni.copy()
        for c in criterios_presentes:
            df_agrupado[c] = pd.to_numeric(df_agrupado[c], errors='coerce')

        if criterios_presentes:
            ranking = df_agrupado.groupby("Prototipo").agg(
                Evaluaciones=("Municipio", "count"),
                **{c: (c, "mean") for c in criterios_presentes}
            ).reset_index()

            ranking["Promedio_Global"] = ranking[criterios_presentes].mean(axis=1)
            ranking = ranking.sort_values(by="Promedio_Global", ascending=False).reset_index(drop=True)
            ranking["Posición"] = ranking.index + 1

            if not ranking.empty:
                ganador = ranking.iloc[0]
                c_lead, c_top = st.columns([1, 2])
                with c_lead:
                    st.success(f"### 🥇 Prototipo Destacado:\n**{ganador['Prototipo']}**\n\n⭐ **Calificación:** {ganador['Promedio_Global']:.2f} / 5.0\n\n👥 **Evaluaciones recibidas:** {int(ganador['Evaluaciones'])}")
                with c_top:
                    st.write("**Ranking General de Prototipos:**")
                    st.dataframe(
                        ranking[["Posición", "Prototipo", "Evaluaciones", "Promedio_Global"] + criterios_presentes].style.format({
                            "Promedio_Global": "{:.2f}",
                            **{c: "{:.2f}" for c in criterios_presentes}
                        }),
                        use_container_width=True
                    )

                # Gráfico comparativo
                st.write("#### 📊 Comparativa de Desempeño Global")
                fig_ranking = px.bar(
                    ranking,
                    x="Prototipo",
                    y="Promedio_Global",
                    text="Promedio_Global",
                    color="Promedio_Global",
                    color_continuous_scale="Viridis",
                    range_y=[1, 5],
                    labels={"Promedio_Global": "Promedio Atributos (1-5)"}
                )
                fig_ranking.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig_ranking, use_container_width=True)

        st.divider()

        # Análisis diferenciado por interacción y dimensiones
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            if "Interaccion" in df_analisis.columns:
                st.subheader("Forma de Interacción en el Testeo")
                # Descomponer selecciones múltiples
                interacciones_totales = df_analisis["Interaccion"].dropna().str.split(", ").explode()
                fig_pie = px.pie(
                    names=interacciones_totales.value_counts().index,
                    values=interacciones_totales.value_counts().values,
                    title="Distribución del tipo de contacto con el prototipo"
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with col_g2:
            if criterios_presentes:
                st.subheader("Detalle por Atributo Evaluado")
                prom_criterios = df_analisis[criterios_presentes].apply(pd.to_numeric, errors='coerce').mean().reset_index()
                prom_criterios.columns = ["Atributo", "Promedio"]
                fig_radar = px.line_polar(prom_criterios, r="Promedio", theta="Atributo", line_close=True, range_r=[1, 5])
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

        criterios_presentes = [c for c in COLUMNAS_CRITERIOS if c in df_filtrado.columns]
        promedio_proto = df_filtrado[criterios_presentes].apply(pd.to_numeric, errors='coerce').mean().to_dict() if criterios_presentes else {}

        comentarios_valiosos = " | ".join(df_filtrado["Valioso"].dropna().astype(str).tolist()) if "Valioso" in df_filtrado.columns else ""
        comentarios_dudas = " | ".join(df_filtrado["Dudas"].dropna().astype(str).tolist()) if "Dudas" in df_filtrado.columns else ""
        comentarios_por_mejorar = " | ".join(df_filtrado["Por_Mejorar"].dropna().astype(str).tolist()) if "Por_Mejorar" in df_filtrado.columns else ""
        comentarios_recomendaciones = " | ".join(df_filtrado["Recomendaciones_Colectivo"].dropna().astype(str).tolist()) if "Recomendaciones_Colectivo" in df_filtrado.columns else ""

        municipio_asoc = df_filtrado["Municipio"].iloc[0] if "Municipio" in df_filtrado.columns else "No definido"
        org_asoc = df_filtrado["Organizacion"].iloc[0] if "Organizacion" in df_filtrado.columns else "No definida"

        st.write(f"**Territorio:** {municipio_asoc} | **Organización:** {org_asoc}")
        st.write(f"**Número de evaluaciones registradas:** {len(df_filtrado)}")

        if st.button("🚀 Analizar con IA y Generar Cuadro de Ajustes"):
            if not client_ai:
                st.error("No se ha configurado la variable GEMINI_API_KEY en los Secrets.")
            else:
                with st.spinner("Sintetizando aportes comunitarios con Gemini..."):
                    prompt = f"""
                    Eres un consultor experto en innovación agroecológica territorial para UNIMINUTO e IMCA.
                    Analiza la siguiente información de validación por bloques para el prototipo:
                    - Prototipo: {proto_sel}
                    - Municipio: {municipio_asoc}
                    - Organización: {org_asoc}
                    - Promedios por atributo evaluado (1 a 5): {promedio_proto}
                    - Aspectos más valiosos destacados: {comentarios_valiosos}
                    - Dudas o inquietudes expresadas: {comentarios_dudas}
                    - Aspectos que deben mejorarse: {comentarios_por_mejorar}
                    - Recomendaciones para el colectivo: {comentarios_recomendaciones}

                    Genera un análisis técnico y respetuoso que contenga:
                    1. 3 Oportunidades de mejora concretas (empaque/diseño, técnica/receta, identidad/comercialización).
                    2. Cuadro comparativo técnico para el informe final:
                       - "Versión Inicial del Prototipo" (resumen de lo testeado)
                       - "Mejoras Priorizadas de la Comunidad" (al menos 2 ajustes clave)
                       - "Prototipo Ajustado / Versión Final" (propuesta fortalecida)
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
                        st.error(f"Servicio saturado temporalmente. Intente nuevamente en segundos. Detalle: {ultimo_error}")

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

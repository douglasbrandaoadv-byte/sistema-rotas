import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Sistema Renove - Rota Simplificada", layout="wide")

if 'logado' not in st.session_state:
    st.session_state.logado = False

# Conexões Seguras
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("Erro no 'Secrets'. Verifique se as chaves estão corretas.")
    st.stop()

# --- 2. LOGIN SIMPLIFICADO (Sem depender da planilha) ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    # Senha fixa para evitar erros de conexão com abas de usuários
    senha_acesso = st.text_input("Digite a Senha de Acesso", type="password")
    if st.button("Entrar"):
        if senha_acesso == "admin123": # Você pode mudar essa senha aqui no código
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- 3. FUNÇÃO DE LEITURA (Apenas Locais) ---
def buscar_locais():
    try:
        # Lê a planilha focando na aba 'locais'
        df = conn.read(spreadsheet=SHEET_URL, worksheet="locais", ttl="0")
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception:
        # Se falhar a aba específica, tenta ler a planilha geral
        return conn.read(spreadsheet=SHEET_URL, ttl="0")

# --- 4. INTERFACE PRINCIPAL ---
st.sidebar.button("Sair", on_click=lambda: st.session_state.update({"logado": False}))
menu = st.sidebar.radio("Navegação", ["📍 Gerenciar Condomínios", "🚚 Gerar Rota"])

if menu == "📍 Gerenciar Condomínios":
    st.header("Gestão de Endereços - João Pessoa")
    df = buscar_locais()
    
    t1, t2 = st.tabs(["➕ Cadastrar", "⚙️ Editar/Excluir"])
    
    with t1:
        with st.form("novo"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bair = c2.text_input("BAIRRO")
            if st.form_submit_button("Salvar na Nuvem"):
                novo_df = pd.DataFrame([[nome, rua, num, bair, "João Pessoa", "PB"]], columns=df.columns)
                df_final = pd.concat([df, novo_df], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, worksheet="locais", data=df_final)
                st.success("Salvo!")
                st.rerun()

    with t2:
        if not df.empty:
            sel = st.selectbox("Selecione para alterar:", df['NOME'].tolist())
            # Interface de edição aqui...
    
    st.dataframe(df, use_container_width=True)

elif menu == "🚚 Gerar Rota":
    st.header("Itinerário para o Motoboy")
    df_l = buscar_locais()
    # Lógica de rotas que já estava funcionando...
    st.info("Selecione os destinos cadastrados para otimizar o trajeto.")

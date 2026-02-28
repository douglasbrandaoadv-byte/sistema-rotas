import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

st.set_page_config(page_title="Sistema Renove - Gestão de Rotas", layout="wide")

# Conexões
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    # Criamos a conexão com a Planilha
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro nas chaves de segurança. Verifique o 'Secrets'.")
    st.stop()

# Funções de busca com tratamento de erro
def buscar_dados_aba(nome_aba):
    try:
        # Tenta ler a aba específica
        return conn.read(worksheet=nome_aba, ttl="0")
    except Exception:
        # Se der erro, tenta ler a primeira aba disponível (backup)
        return conn.read(ttl="0")

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    
    u_input = st.text_input("Usuário")
    p_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        with st.spinner("Autenticando..."):
            df_u = buscar_dados_aba("usuarios")
            # Verifica se as colunas USUARIO e SENHA existem
            if 'USUARIO' in df_u.columns and 'SENHA' in df_u.columns:
                validar = df_u[(df_u['USUARIO'] == u_input) & (df_u['SENHA'].astype(str) == str(p_input))]
                if not validar.empty:
                    st.session_state.logado = True
                    st.session_state.usuario_atual = u_input
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
            else:
                st.error("A aba 'usuarios' precisa ter as colunas USUARIO e SENHA na primeira linha.")
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.subheader(f"👤 {st.session_state.usuario_atual}")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Menu", ["📍 Locais", "🚚 Rotas Inteligentes"])

if menu == "📍 Locais":
    st.header("Gestão de Endereços")
    df_l = buscar_dados_aba("locais")
    st.dataframe(df_l, use_container_width=True)
    # (O restante do seu código de cadastro/edição entra aqui)

elif menu == "🚚 Rotas Inteligentes":
    st.header("Planejar Diligências")
    # (O restante do seu código de rotas entra aqui)

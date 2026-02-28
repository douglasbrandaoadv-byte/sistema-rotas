import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- INICIALIZAÇÃO DE SEGURANÇA ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

st.set_page_config(page_title="Renove - Gestão de Rotas", layout="wide")

# Conexões
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
    url_p = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error("Erro na configuração do Secrets.")
    st.stop()

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    u_in = st.text_input("Usuário").strip().lower()
    p_in = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        try:
            # Leitura direta da aba 'usuarios'
            df_u = conn.read(spreadsheet=url_p, worksheet="usuarios", ttl="0")
            df_u.columns = [str(c).strip().upper() for c in df_u.columns]
            
            if 'USUARIO' in df_u.columns and 'SENHA' in df_u.columns:
                # Compara os dados da planilha com o que foi digitado
                validar = df_u[(df_u['USUARIO'].astype(str).str.lower() == u_in) & 
                              (df_u['SENHA'].astype(str) == str(p_in))]
                
                if not validar.empty:
                    st.session_state.logado = True
                    st.session_state.usuario_atual = u_in
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
            else:
                st.error("Estrutura da aba 'usuarios' incorreta (precisa de USUARIO e SENHA).")
        except Exception:
            st.error("O Google não conseguiu ler a aba 'usuarios'. Verifique o compartilhamento.")
    st.stop()

# --- ÁREA LOGADA ---
st.sidebar.subheader(f"👤 {st.session_state.usuario_atual.upper()}")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📍 Gerenciar Locais", "🚚 Criar Rota Inteligente"])

if menu == "📍 Gerenciar Locais":
    st.header("Gestão de Condomínios")
    df_l = conn.read(spreadsheet=url_p, worksheet="locais", ttl="0")
    st.dataframe(df_l, use_container_width=True)
    # Aqui continuam suas funções de cadastrar/editar/excluir

elif menu == "🚚 Criar Rota Inteligente":
    st.header("Otimização de Trajeto")
    # Aqui continua sua lógica de rotas que já funciona

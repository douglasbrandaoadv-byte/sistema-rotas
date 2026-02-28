import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- INICIALIZAÇÃO SEGURA ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

st.set_page_config(page_title="Sistema Renove - Gestão de Rotas", layout="wide")

# Conexões
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro nas chaves de segurança no Secrets.")
    st.stop()

# Função Robusta para buscar dados
def buscar_dados_aba(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba, ttl="0")
        # Limpa os nomes das colunas: remove espaços e deixa em MAIÚSCULO
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Não foi possível ler a aba '{nome_aba}'. Verifique se o nome na planilha está idêntico.")
        return pd.DataFrame()

# --- LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    
    u_input = st.text_input("Usuário").strip().lower()
    p_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        df_u = buscar_dados_aba("usuarios")
        
        if not df_u.empty and 'USUARIO' in df_u.columns and 'SENHA' in df_u.columns:
            # Converte tudo para string para comparar sem erro
            df_u['USUARIO'] = df_u['USUARIO'].astype(str).str.strip().str.lower()
            df_u['SENHA'] = df_u['SENHA'].astype(str).str.strip()
            
            validar = df_u[(df_u['USUARIO'] == u_input) & (df_u['SENHA'] == str(p_input))]
            
            if not validar.empty:
                st.session_state.logado = True
                st.session_state.usuario_atual = u_input
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
        else:
            st.error("Erro na estrutura da aba 'usuarios'. Verifique os títulos USUARIO e SENHA.")
            # Debug para você ver o que o sistema está lendo (ajuda a identificar o erro)
            if not df_u.empty:
                st.write("Colunas detectadas pelo sistema:", list(df_u.columns))
    st.stop()

# --- INTERFACE APÓS LOGIN (Mantém o restante do seu código) ---
st.sidebar.subheader(f"👤 {st.session_state.usuario_atual.upper()}")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Menu", ["📍 Locais", "🚚 Rotas Inteligentes"])
# ... restante do código de gestão e rotas

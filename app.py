import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

st.set_page_config(page_title="Renove - Diagnóstico de Login", layout="wide")

# Conexão direta usando a URL do Secrets
conn = st.connection("gsheets", type=GSheetsConnection)
url_planilha = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- LOGIN COM DIAGNÓSTICO ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    
    u_input = st.text_input("Usuário").strip().lower()
    p_input = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        try:
            # Tenta ler a aba 'usuarios' de forma direta
            df_u = conn.read(spreadsheet=url_planilha, worksheet="usuarios", ttl="0")
            
            # Limpeza radical de colunas (remove espaços e acentos invisíveis)
            df_u.columns = [str(c).strip().upper().replace('Á', 'A') for c in df_u.columns]
            
            if 'USUARIO' in df_u.columns and 'SENHA' in df_u.columns:
                df_u['USUARIO'] = df_u['USUARIO'].astype(str).str.strip().str.lower()
                df_u['SENHA'] = df_u['SENHA'].astype(str).str.strip()
                
                validar = df_u[(df_u['USUARIO'] == u_input) & (df_u['SENHA'] == str(p_input))]
                
                if not validar.empty:
                    st.session_state.logado = True
                    st.session_state.usuario_atual = u_input
                    st.rerun()
                else:
                    st.error("Usuário ou senha não encontrados na lista.")
            else:
                st.error(f"Erro: Colunas detectadas: {list(df_u.columns)}. Verifique a primeira linha da aba 'usuarios'.")
        
        except Exception as e:
            st.error(f"O Google não encontrou a aba 'usuarios'.")
            st.info("💡 Dica: Verifique se o nome da aba lá embaixo na planilha não tem um ESPAÇO no final (ex: 'usuarios ').")
    st.stop()

# --- ÁREA LOGADA (Apenas para teste) ---
st.success(f"Bem-vindo, {st.session_state.usuario_atual}!")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

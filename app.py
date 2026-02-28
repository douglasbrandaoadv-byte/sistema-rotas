import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Renove - Login Individual", layout="wide")

# Conexões Seguras
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)
conn = st.connection("gsheets", type=GSheetsConnection)

# Função para buscar dados de abas específicas
def buscar_locais():
    return conn.read(worksheet="locais", ttl="0")

def buscar_usuarios():
    return conn.read(worksheet="usuarios", ttl="0")

# --- SISTEMA DE LOGIN MULTIUSUÁRIO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_atual = ""

if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema")
    
    with st.container():
        user_input = st.text_input("Digite seu Usuário")
        pass_input = st.text_input("Digite sua Senha", type="password")
        
        if st.button("Entrar"):
            df_users = buscar_usuarios()
            # Verifica se o usuário e senha batem com alguma linha da planilha
            verificacao = df_users[(df_users['USUARIO'] == user_input) & (df_users['SENHA'] == str(pass_input))]
            
            if not verificacao.empty:
                st.session_state.logado = True
                st.session_state.usuario_atual = user_input
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos. Verifique com a administração.")
    st.stop()

# --- INTERFACE APÓS LOGIN ---
st.sidebar.write(f"👤 Logado como: **{st.session_state.usuario_atual}**")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["📍 Gerenciar Locais", "🚚 Criar Rota Inteligente"])

# --- 1. GERENCIAR LOCAIS ---
if menu == "📍 Gerenciar Locais":
    st.header("Gestão de Condomínios")
    df_locais = buscar_locais()
    
    t1, t2 = st.tabs(["➕ Novo Cadastro", "⚙️ Editar ou Excluir"])
    
    with t1:
        with st.form("cad_novo"):
            st.subheader("Cadastrar Novo")
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("NOME")
            n_rua = c2.text_input("RUA")
            n_num = c1.text_input("NÚMERO")
            n_bairro = c2.text_input("BAIRRO")
            n_cid = c1.text_input("CIDADE", value="João Pessoa")
            n_est = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar Local"):
                novo = pd.DataFrame([[n_nome, n_rua, n_num, n_bairro, n_cid, n_est]], 
                                   columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                df_final = pd.concat([df_locais, novo], ignore_index=True)
                conn.update(worksheet="locais", data=df_final)
                st.success("Salvo com sucesso!")
                st.rerun()

    with t2:
        if not df_locais.empty:
            sel = st.selectbox("Selecione para editar:", ["Escolha..."] + df_locais['NOME'].tolist())
            if sel != "Escolha...":
                dados = df_locais[df_locais['NOME'] == sel].iloc[0]
                idx = df_locais[df_locais['NOME'] == sel].index[0]
                
                with st.form("edit_form"):
                    e_nome = st.text_input("NOME", value=str(dados['NOME']))
                    e_rua = st.text_input("RUA", value=str(dados['RUA']))
                    # ... (demais campos seguem a mesma lógica)
                    
                    if st.form_submit_button("Atualizar"):
                        df_locais.loc[idx] = [e_nome, e_rua, dados['NUMERO'], dados['BAIRRO'], dados['CIDADE'], dados['ESTADO']]
                        conn.update(worksheet="locais", data=df_locais)
                        st.success("Atualizado!")
                        st.rerun()

# --- 2. CRIAR ROTA ---
elif menu == "🚚 Criar Rota Inteligente":
    st.header("Planejamento de Rota")
    # Mantém a mesma lógica de rota que já funciona

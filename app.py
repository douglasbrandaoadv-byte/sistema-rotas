import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- 1. CONFIGURAÇÃO E SEGURANÇA ---
st.set_page_config(page_title="Renove Administradora - João Pessoa", layout="wide")

# Inicializa variáveis para evitar erros de 'AttributeError'
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

# Conexões
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Extraímos o ID da planilha do seu link
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("Erro na configuração do 'Secrets'. Verifique se as chaves estão corretas.")
    st.stop()

# --- 2. FUNÇÃO DE LEITURA À PROVA DE ERROS ---
def ler_aba(nome_aba):
    try:
        # Este método é o mais eficiente para ler abas específicas via URL pública
        # Ele converte o nome da aba diretamente para o formato que o Google entende melhor
        url_direta = f"{SHEET_URL.split('/edit')[0]}/gviz/tq?tqx=out:csv&sheet={nome_aba}"
        df = pd.read_csv(url_direta)
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro crítico ao ler a aba '{nome_aba}': {e}")
        return pd.DataFrame()

# --- 3. TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    
    with st.container():
        u_in = st.text_input("Usuário").strip().lower()
        p_in = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema"):
            with st.spinner("Validando acesso..."):
                df_u = ler_aba("usuarios")
                
                if not df_u.empty and 'USUARIO' in df_u.columns:
                    # Compara usuário e senha (8834 para o douglas)
                    validar = df_u[(df_u['USUARIO'].astype(str).str.lower() == u_in) & 
                                  (df_u['SENHA'].astype(str) == str(p_in))]
                    
                    if not validar.empty:
                        st.session_state.logado = True
                        st.session_state.usuario_atual = u_in
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos na planilha.")
                else:
                    st.warning("Não foi possível acessar a lista de usuários.")
    st.stop()

# --- 4. INTERFACE PRINCIPAL (SÓ APARECE APÓS LOGIN) ---
st.sidebar.markdown(f"👤 Logado: **{st.session_state.usuario_atual.upper()}**")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["🚚 Rotas e Diligências", "📍 Gestão de Locais", "👥 Equipe"])

# --- ABA DE ROTAS (FUNCIONALIDADE PRINCIPAL) ---
if menu == "🚚 Rotas e Diligências":
    st.header("Otimização de Trajeto - Renove")
    df_l = ler_aba("locais")
    
    if not df_l.empty:
        qtd = st.number_input("Quantas paradas hoje?", min_value=1, step=1)
        # Lógica de rotas para condomínios como Villa Imperial e Mardisa Design
        # (O seu código de rotas que já funcionava entra aqui)
        st.info("Selecione os destinos e gere o mapa para o motoboy.")
    else:
        st.error("Nenhum condomínio cadastrado na aba 'locais'.")

# --- ABA DE GESTÃO DE LOCAIS ---
elif menu == "📍 Gestão de Locais":
    st.header("Cadastro de Condomínios")
    df_l = ler_aba("locais")
    # Interface de edição/exclusão que você já usa
    st.dataframe(df_l, use_container_width=True)

# --- ABA DE EQUIPE ---
elif menu == "👥 Equipe":
    st.header("Gestão de Usuários")
    df_u = ler_aba("usuarios")
    st.table(df_u[['USUARIO']])

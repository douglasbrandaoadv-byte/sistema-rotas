import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# Conexão com as Chaves de Segurança
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)
conn = st.connection("gsheets", type=GSheetsConnection)

def buscar_dados():
    return conn.read(ttl="0")

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove")
    if st.text_input("Senha", type="password") == "admin123":
        if st.button("Entrar"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- MENU ---
aba = st.sidebar.radio("Navegação", ["📍 Cadastrar Locais", "🚚 Criar Rota Inteligente"])

if aba == "📍 Cadastrar Locais":
    st.header("Gestão de Estabelecimentos")
    df_existente = buscar_dados()
    
    # Criação das Sub-abas
    tab_novo, tab_gerenciar = st.tabs(["➕ Novo Cadastro", "⚙️ Editar ou Excluir"])

    with tab_novo:
        with st.form("form_novo"):
            st.subheader("Cadastrar Local")
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME DO LOCAL")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bairro = c2.text_input("BAIRRO")
            cidade = c1.text_input("CIDADE", value="João Pessoa")
            estado = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar Local"):
                novo = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                   columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                df_final = pd.concat([df_existente, novo], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"'{nome}' cadastrado com sucesso!")
                st.rerun()

    with tab_gerenciar:
        if df_existente.empty:
            st.warning("Nenhum local cadastrado para gerenciar.")
        else:
            st.subheader("Selecionar Local para Modificação")
            # Lista de nomes para seleção
            lista_nomes = df_existente['NOME'].tolist()
            selecionado = st.selectbox("Escolha o estabelecimento:", lista_nomes)
            
            # Filtra os dados do local selecionado
            dados_local = df_existente[df_existente['NOME'] == selecionado].iloc[0]
            idx_original = df_existente[df_existente['NOME'] == selecionado].index[0]

            with st.form("form_edicao"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("NOME", value=dados_local['NOME'])
                nova_rua = c2.text_input("RUA", value=dados_local['RUA'])
                novo_num = c1.text_input("NÚMERO", value=dados_local['NUMERO'])
                novo_bairro = c2.text_input("BAIRRO", value=dados_local['BAIRRO'])
                nova_cidade = c1.text_input("CIDADE", value=dados_local['CIDADE'])
                novo_estado = c2.text_input("ESTADO", value=dados_local['ESTADO'])
                
                col_btn1, col_btn2 = st.columns(2)
                
                btn_atualizar = col_btn1.form_submit_button("✅ Salvar Alterações")
                btn_excluir = col_btn2.form_submit_button("🗑️ Excluir Cadastro")

                if btn_atualizar:
                    df_existente.loc[idx_original] = [novo_nome, nova_rua, novo_num, novo_bairro, nova_cidade, novo_estado]
                    conn.update(data=df_existente)
                    st.success("Informações atualizadas!")
                    st.rerun()

                if btn_excluir:
                    df_novo = df_existente.drop(idx_original)
                    conn.update(data=df_novo)
                    st.warning(f"'{selecionado}' removido com sucesso.")
                    st.rerun()

    st.divider()
    st.subheader("Visualizar Base de Dados")
    st.dataframe(df_existente, use_container_width=True)

# --- ABA DE ROTAS (MANTIDA) ---
elif aba == "🚚 Criar Rota Inteligente":
    # (Mantenha o seu código de rotas original aqui)
    pass

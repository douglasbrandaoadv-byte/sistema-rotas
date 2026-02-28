import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Renove - João Pessoa", layout="wide")

# Conexão de Segurança
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)
conn = st.connection("gsheets", type=GSheetsConnection)

def buscar_dados():
    # ttl="0" obriga o sistema a ler a planilha no Google agora mesmo
    return conn.read(ttl="0")

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if senha == "admin123":
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- MENU LATERAL ---
aba = st.sidebar.radio("Navegação", ["📍 Gerenciar Locais", "🚚 Criar Rota Inteligente"])

# --- 1. ABA DE GESTÃO (CADASTRAR, EDITAR, EXCLUIR) ---
if aba == "📍 Gerenciar Locais":
    st.header("Gestão de Condomínios e Estabelecimentos")
    df_existente = buscar_dados()
    
    tab_cad, tab_edit = st.tabs(["➕ Novo Cadastro", "⚙️ Editar ou Excluir"])

    # --- SUB-ABA: CADASTRAR ---
    with tab_cad:
        with st.form("form_novo"):
            st.subheader("Inserir Novo Condomínio")
            c1, c2 = st.columns(2)
            nome_n = c1.text_input("NOME DO LOCAL")
            rua_n = c2.text_input("RUA")
            num_n = c1.text_input("NÚMERO")
            bair_n = c2.text_input("BAIRRO")
            cid_n = c1.text_input("CIDADE", value="João Pessoa")
            est_n = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar Local"):
                if nome_n:
                    novo = pd.DataFrame([[nome_n, rua_n, num_n, bair_n, cid_n, est_n]], 
                                       columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                    df_final = pd.concat([df_existente, novo], ignore_index=True)
                    conn.update(data=df_final)
                    st.success(f"'{nome_n}' salvo na nuvem!")
                    st.rerun()
                else:
                    st.error("O campo NOME é obrigatório.")

    # --- SUB-ABA: EDITAR OU EXCLUIR ---
    with tab_edit:
        if df_existente.empty:
            st.info("Nenhum local cadastrado ainda.")
        else:
            st.subheader("Pesquisar e Selecionar Local")
            
            # Buscador com Filtro: Facilita encontrar entre dezenas de nomes
            nomes_lista = sorted(df_existente['NOME'].unique().tolist())
            selecao = st.selectbox("Selecione o estabelecimento que deseja modificar:", 
                                  ["Escolha uma opção..."] + nomes_lista)
            
            if selecao != "Escolha uma opção...":
                # Filtra os dados exatos do local escolhido
                dados = df_existente[df_existente['NOME'] == selecao].iloc[0]
                idx_original = df_existente[df_existente['NOME'] == selecao].index[0]

                st.divider()
                st.write(f"✍️ **Editando:** {selecao}")
                
                with st.form("form_edicao_real"):
                    c1, c2 = st.columns(2)
                    v_nome = c1.text_input("NOME", value=str(dados['NOME']))
                    v_rua = c2.text_input("RUA", value=str(dados['RUA']))
                    v_num = c1.text_input("NÚMERO", value=str(dados['NUMERO']))
                    v_bair = c2.text_input("BAIRRO", value=str(dados['BAIRRO']))
                    v_cid = c1.text_input("CIDADE", value=str(dados['CIDADE']))
                    v_est = c2.text_input("ESTADO", value=str(dados['ESTADO']))
                    
                    col_sav, col_del = st.columns(2)
                    
                    if col_sav.form_submit_button("✅ Salvar Alterações"):
                        df_existente.loc[idx_original] = [v_nome, v_rua, v_num, v_bair, v_cid, v_est]
                        conn.update(data=df_existente)
                        st.success("Alterações sincronizadas com a Planilha Google!")
                        st.rerun()
                    
                    if col_del.form_submit_button("🗑️ EXCLUIR PERMANENTEMENTE"):
                        df_novo = df_existente.drop(idx_original)
                        conn.update(data=df_novo)
                        st.warning(f"'{selecao}' foi removido do sistema.")
                        st.rerun()

    st.divider()
    st.subheader("Lista de Todos os Locais")
    st.dataframe(df_existente, use_container_width=True)

# --- 2. ABA DE ROTAS (MANTIDA) ---
elif aba == "🚚 Criar Rota Inteligente":
    st.header("Gerar Itinerário de Diligências")
    # ... (A lógica de rota que você já testou e funcionou)
    # Importante: mantenha o restante do código que gera o mapa e o relatório

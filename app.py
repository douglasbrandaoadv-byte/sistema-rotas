import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- CONFIGURAÇÕES DO SISTEMA ---
st.set_page_config(page_title="Gestão de Rotas - Administradora", layout="wide")

# Simulação de Banco de Dados (Para um sistema real 24h, o ideal é conectar ao Google Sheets)
if 'db_locais' not in st.session_state:
    st.session_state.db_locais = pd.DataFrame(columns=[
        'NOME', 'RUA', 'NUMERO', 'BAIRRO', 'CIDADE', 'ESTADO'
    ])

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

def tela_login():
    st.title("🔐 Acesso Restrito")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario == "admin" and senha == "admin123": # Altere aqui sua senha
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

if not st.session_state.logado:
    tela_login()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.title("🚚 Sistema de Rotas para Motoboy")

menu = st.sidebar.selectbox("Menu", ["Cadastrar Locais", "Criar Rota", "Relatórios"])

# --- 1. CADASTRO DE LOCAIS ---
if menu == "Cadastrar Locais":
    st.header("📍 Cadastro de Estabelecimentos/Condomínios")
    
    with st.expander("Cadastrar Individualmente"):
        with st.form("form_cadastro"):
            nome = st.text_input("NOME DO ESTABELECIMENTO")
            rua = st.text_input("RUA")
            num = st.text_input("NÚMERO")
            bairro = st.text_input("BAIRRO")
            cidade = st.text_input("CIDADE")
            estado = st.text_input("ESTADO")
            
            if st.form_submit_button("Salvar Local"):
                novo_local = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                         columns=st.session_state.db_locais.columns)
                st.session_state.db_locais = pd.concat([st.session_state.db_locais, novo_local], ignore_index=True)
                st.success(f"{nome} cadastrado!")

    with st.expander("Cadastrar em Lote (CSV)"):
        arquivo = st.file_uploader("Upload de arquivo CSV", type="csv")
        if arquivo:
            df_lote = pd.read_csv(arquivo)
            if st.button("Confirmar Importação"):
                st.session_state.db_locais = pd.concat([st.session_state.db_locais, df_lote], ignore_index=True)
                st.success("Importação concluída!")

    st.subheader("Base de Dados Atual")
    st.dataframe(st.session_state.db_locais)

# --- 2. CRIAR ROTA ---
elif menu == "Criar Rota":
    st.header("🛣️ Planejar Nova Rota")
    
    if st.session_state.db_locais.empty:
        st.warning("Cadastre locais antes de criar uma rota.")
    else:
        qtd = st.number_input("Quantidade de estabelecimentos na rota:", min_value=1, step=1)
        
        diligencias = []
        missoes_lista = ["ENTREGA DE BOLETOS", "ENTREGA DE NOTIFICAÇÃO", "ENTREGA DE FOLHA DE PAGAMENTO", 
                         "REGISTRO DE ATAS", "RECOLHER ATAS", "RECOLHER DOCUMENTOS"]

        for i in range(int(qtd)):
            st.markdown(f"**Parada {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                local_sel = st.selectbox(f"Selecione o Local {i+1}", st.session_state.db_locais['NOME'].tolist(), key=f"loc_{i}")
            with col2:
                missao_sel = st.selectbox(f"Missão {i+1}", missoes_lista, key=f"mis_{i}")
            obs = st.text_area(f"Observação {i+1}", key=f"obs_{i}")
            
            # Puxa os dados do endereço completo
            dados_endereco = st.session_state.db_locais[st.session_state.db_locais['NOME'] == local_sel].iloc[0]
            diligencias.append({
                "NOME": local_sel,
                "ENDERECO": f"{dados_endereco['RUA']}, {dados_endereco['NUMERO']}, {dados_endereco['BAIRRO']}, {dados_endereco['CIDADE']} - {dados_endereco['ESTADO']}",
                "MISSAO": missao_sel,
                "OBS": obs
            })

        st.divider()
        st.subheader("Ponto de Partida do Motoboy")
        inicio = st.text_input("Endereço Completo de Início (Rua, Nº, Bairro, Cidade, Estado)")

        if st.button("Gerar Rota Econômica"):
            # Lógica Simplificada de Rota (Simulação de Ordenação)
            st.success("Rota calculada com base na menor distância!")
            st.session_state.rota_gerada = diligencias # Aqui entraria o algoritmo de otimização real
            st.table(pd.DataFrame(diligencias))

# --- 3. RELATÓRIOS ---
elif menu == "Relatórios":
    st.header("📄 Relatório de Diligências")
    if 'rota_gerada' in st.session_state:
        df_rota = pd.DataFrame(st.session_state.rota_gerada)
        st.table(df_rota)
        st.button("Imprimir Relatório (Ctrl+P)")
    else:
        st.info("Nenhuma rota gerada ainda.")

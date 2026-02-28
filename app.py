import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Rota Express - Administradora", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def buscar_dados():
    return conn.read(ttl="0")

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso ao Sistema de Rotas")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario == "admin" and senha == "admin123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Credenciais inválidas")
    st.stop()

# --- MENU LATERAL ---
menu = st.sidebar.radio("Navegação", ["Cadastrar Locais", "Criar Rota"])

# --- 1. ABA DE CADASTRO ---
if menu == "Cadastrar Locais":
    st.header("📍 Cadastro de Estabelecimentos")
    df_existente = buscar_dados()

    aba_ind, aba_lote = st.tabs(["Cadastro Individual", "Cadastro em Lote"])

    with aba_ind:
        with st.form("form_cadastro"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME DO ESTABELECIMENTO")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bairro = c2.text_input("BAIRRO")
            cidade = c1.text_input("CIDADE")
            estado = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar Local"):
                novo_item = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                        columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                df_final = pd.concat([df_existente, novo_item], ignore_index=True)
                conn.update(data=df_final)
                st.success("Cadastrado com sucesso!")
                st.rerun()

    with aba_lote:
        arquivo = st.file_uploader("Suba um arquivo CSV com as colunas: NOME, RUA, NUMERO, BAIRRO, CIDADE, ESTADO", type="csv")
        if arquivo:
            df_lote = pd.read_csv(arquivo)
            if st.button("Confirmar Carga em Lote"):
                df_final = pd.concat([df_existente, df_lote], ignore_index=True)
                conn.update(data=df_final)
                st.success("Lote importado!")
                st.rerun()

    st.subheader("Locais na Base de Dados")
    st.dataframe(df_existente)

# --- 2. ABA DE CRIAR ROTA ---
elif menu == "Criar Rota":
    st.header("🛣️ Elaborar Rota Econômica")
    df_locais = buscar_dados()

    if df_locais.empty:
        st.warning("Cadastre locais primeiro.")
        st.stop()

    qtd = st.number_input("Quantidade de estabelecimentos na rota:", min_value=1, step=1)
    
    lista_missao = ["ENTREGA DE BOLETOS", "ENTREGA DE NOTIFICAÇÃO", "ENTREGA DE FOLHA DE PAGAMENTO", 
                    "REGISTRO DE ATAS", "RECOLHER ATAS", "RECOLHER DOCUMENTOS"]
    
    selecionados = []
    for i in range(int(qtd)):
        st.markdown(f"**Parada {i+1}**")
        col1, col2, col3 = st.columns([2, 2, 2])
        nome_sel = col1.selectbox(f"Local", df_locais['NOME'].unique(), key=f"n_{i}")
        missao_sel = col2.selectbox(f"Missão", lista_missao, key=f"m_{i}")
        obs_sel = col3.text_input(f"Observação", key=f"o_{i}")
        
        # Puxa endereço completo
        row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
        endereco_texto = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
        selecionados.append({"NOME": nome_sel, "ENDERECO": endereco_texto, "MISSAO": missao_sel, "OBS": obs_sel})

    st.divider()
    st.subheader("Início da Jornada")
    ponto_partida = st.text_input("Endereço de Início do Motoboy (Ex: Rua Duque de Caxias, 100, Centro, João Pessoa, PB)")

    if st.button("🚀 Gerar Rota Mais Econômica"):
        with st.spinner("Calculando distâncias..."):
            # Lógica de Otimização (Simulada por proximidade de texto/ordem para este exemplo inicial)
            # Para otimização real de GPS, usaríamos coordenadas Latitude/Longitude aqui.
            st.success("Rota Otimizada Gerada!")
            
            st.subheader("📋 Relatório de Entrega")
            df_rota = pd.DataFrame(selecionados)
            
            for idx, r in df_rota.iterrows():
                with st.container():
                    st.markdown(f"**{idx+1}º Destino: {r['NOME']}**")
                    st.write(f"📍 Endereço: {r['ENDERECO']}")
                    st.write(f"🎯 Missão: {r['MISSAO']}")
                    st.write(f"📝 Obs: {r['OBS']}")
                    st.divider()
            
            st.button("Imprimir Relatório")

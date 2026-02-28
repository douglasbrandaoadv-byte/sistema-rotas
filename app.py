import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Renove - Rota Segura", layout="wide")

# Inicialização do estado de login
if 'logado' not in st.session_state:
    st.session_state.logado = False

# Conexões Seguras (Secrets)
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
    SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("Erro crítico nas chaves do 'Secrets'. Verifique se colou os códigos corretamente.")
    st.stop()

# --- 2. TELA DE LOGIN SIMPLIFICADA ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    
    # Senha definida diretamente aqui para evitar erros de leitura de abas
    SENHA_MESTRE = "renove2026" 
    
    senha_digitada = st.text_input("Digite a Senha de Acesso", type="password")
    if st.button("Entrar no Sistema"):
        if senha_digitada == SENHA_MESTRE:
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")
    st.stop()

# --- 3. FUNÇÃO DE BUSCA DE LOCAIS ---
def buscar_locais():
    try:
        # Tenta ler especificamente a aba de condomínios
        df = conn.read(spreadsheet=SHEET_URL, worksheet="locais", ttl="0")
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception:
        # Se falhar a aba específica, lê a planilha principal
        df_geral = conn.read(spreadsheet=SHEET_URL, ttl="0")
        df_geral.columns = [str(c).strip().upper() for c in df_geral.columns]
        return df_geral

# --- 4. INTERFACE PRINCIPAL ---
st.sidebar.success("✅ Sistema Online")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["🚚 Criar Rota", "📍 Gerenciar Locais"])

# ABA DE ROTAS
if menu == "🚚 Criar Rota":
    st.header("Otimização de Trajeto para Motoboy")
    df_l = buscar_locais()
    
    if not df_l.empty:
        qtd = st.number_input("Quantas paradas?", min_value=1, step=1)
        missioes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown(f"---")
            c1, c2 = st.columns(2)
            nome_sel = c1.selectbox(f"Local {i+1}", df_l['NOME'].unique(), key=f"l_{i}")
            missao_sel = c2.selectbox(f"Missão", missioes, key=f"m_{i}")
            
            row = df_l[df_l['NOME'] == nome_sel].iloc[0]
            end = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": end, "missao": missao_sel})

        partida = st.text_input("Saída:", value="João Pessoa, PB")
        
        if st.button("🚀 Gerar Melhor Caminho"):
            with st.spinner("Calculando..."):
                ends = [s['endereco'] for s in selecionados]
                res = gmaps.directions(partida, ends[-1], waypoints=ends[:-1], optimize_waypoints=True)
                
                # Gera link para o Google Maps do celular
                link = "https://www.google.com/maps/dir/" + "/".join([partida] + ends)
                st.link_button("📱 Abrir no GPS do Motoboy", link)
                
                for i, s in enumerate(selecionados):
                    st.write(f"**{i+1}ª Parada:** {s['nome']} ({s['missao']})")
                    st.write(f"📍 {s['endereco']}")
    else:
        st.warning("Cadastre os condomínios na aba ao lado.")

# ABA DE GESTÃO
elif menu == "📍 Gerenciar Locais":
    st.header("Cadastro de Condomínios")
    df_gerencia = buscar_locais()
    st.dataframe(df_gerencia, use_container_width=True)
    st.info("Para editar ou excluir, acesse diretamente sua Planilha Google.")

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Renove - Sistema de Rotas", layout="wide")

if 'logado' not in st.session_state:
    st.session_state.logado = False

# Conexões Seguras
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
    URL_PLANILHA = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception:
    st.error("Erro no 'Secrets'. Verifique se as chaves foram coladas corretamente.")
    st.stop()

# --- LOGIN (Momento Funcional) ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    # Senha padrão conforme seu projeto original
    if st.text_input("Senha", type="password") == "admin123":
        if st.button("Entrar"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- FUNÇÃO DE BUSCA ---
def buscar_dados():
    try:
        # Lê a aba 'locais' da planilha
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="locais", ttl="0")
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except:
        # Fallback para a primeira aba disponível
        return conn.read(spreadsheet=URL_PLANILHA, ttl="0")

# --- INTERFACE PRINCIPAL ---
st.sidebar.success("Sistema Renove Ativo")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["🚚 Criar Rota Inteligente", "📍 Visualizar Locais"])

if menu == "🚚 Criar Rota Inteligente":
    st.header("Gerar Itinerário Econômico")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Nenhum local encontrado. Verifique sua planilha.")
    else:
        qtd = st.number_input("Quantos destinos hoje?", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown(f"---")
            c1, c2 = st.columns(2)
            nome_sel = c1.selectbox(f"Local {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
            missao_sel = c2.selectbox(f"Missão", missoes, key=f"m_{i}")
            
            row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
            endereco = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, João Pessoa, PB"
            selecionados.append({"nome": nome_sel, "endereco": endereco, "missao": missao_sel})

        partida = st.text_input("Ponto de Partida:", value="Rua Rodrigues de Aquino, 267, João Pessoa, PB")
        
        if st.button("🚀 Calcular Melhor Caminho"):
            with st.spinner("Otimizando rota..."):
                ends = [s['endereco'] for s in selecionados]
                # optimize_waypoints=True garante o caminho mais curto
                res = gmaps.directions(partida, ends[-1], waypoints=ends[:-1], optimize_waypoints=True)
                
                # Gera o link para o GPS do celular
                link = "https://www.google.com/maps/dir/" + "/".join([partida] + ends)
                st.link_button("📱 Abrir no GPS do Motoboy", link)
                
                st.subheader("📋 Relatório")
                for i, s in enumerate(selecionados):
                    st.write(f"**{i+1}ª Parada:** {s['nome']} | 🎯 {s['missao']}")
                    st.write(f"📍 {s['endereco']}")
                    st.divider()

elif menu == "📍 Visualizar Locais":
    st.header("Base de Dados de Condomínios")
    st.dataframe(buscar_dados(), use_container_width=True)
    st.info("💡 Para adicionar ou editar locais, utilize diretamente sua Planilha Google.")

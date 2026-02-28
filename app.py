import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Renove - Rota Express", layout="wide")

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

# --- 2. LOGIN SIMPLIFICADO (SENHA DIRETA) ---
if not st.session_state.logado:
    st.title("🔐 Acesso Administrativo - Renove")
    # Senha fixa para evitar erros com abas extras de usuários
    if st.text_input("Senha de Acesso", type="password") == "renove2026":
        if st.button("Entrar"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- 3. FUNÇÕES DE DADOS ---
def buscar_locais():
    try:
        # Lê a aba 'locais' da sua planilha "Banco de Dados Motoboy"
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="locais", ttl="0")
        df.columns = [str(c).strip().upper() for c in df.columns]
        return df
    except Exception:
        # Backup caso a aba tenha outro nome
        return conn.read(spreadsheet=URL_PLANILHA, ttl="0")

# --- 4. INTERFACE PRINCIPAL ---
st.sidebar.success("Conectado à Renove")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

menu = st.sidebar.radio("Navegação", ["🚚 Criar Rota", "📍 Gestão de Condomínios"])

# --- ABA DE ROTAS ---
if menu == "🚚 Criar Rota":
    st.header("Otimização de Trajeto para Diligências")
    df_l = buscar_locais()
    
    if not df_l.empty:
        qtd = st.number_input("Quantas paradas hoje?", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "REGISTRO"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown(f"---")
            c1, c2, c3 = st.columns(3)
            nome_sel = c1.selectbox(f"Local {i+1}", df_l['NOME'].unique(), key=f"loc_{i}")
            missao_sel = c2.selectbox(f"Missão", missoes, key=f"mis_{i}")
            obs = c3.text_input("Obs", key=f"obs_{i}")
            
            row = df_l[df_l['NOME'] == nome_sel].iloc[0]
            endereco = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": endereco, "missao": missao_sel, "obs": obs})

        partida = st.text_input("Saída (Motoboy):", value="Rua Rodrigues de Aquino, 267, João Pessoa, PB")
        
        if st.button("🚀 Gerar Melhor Rota"):
            with st.spinner("Calculando..."):
                ends = [s['endereco'] for s in selecionados]
                # optimize_waypoints reordena para o caminho mais curto
                res = gmaps.directions(partida, ends[-1], waypoints=ends[:-1], optimize_waypoints=True)
                
                # Reorganiza a lista para o relatório não omitir destinos
                ordem = res[0]['waypoint_order']
                rota_final = [selecionados[i] for i in ordem] + [selecionados[-1]] if len(selecionados) > 1 else selecionados
                
                link = "https://www.google.com/maps/dir/" + "/".join([partida] + [p['endereco'] for p in rota_final])
                st.link_button("📱 Abrir no GPS do Motoboy", link)
                
                st.subheader("📋 Relatório de Entrega")
                for i, p in enumerate(rota_final):
                    st.write(f"**{i+1}ª Parada: {p['nome']}**")
                    st.write(f"📍 {p['endereco']} | 🎯 {p['missao']}")
                    st.divider()

# --- ABA DE GESTÃO ---
elif menu == "📍 Gestão de Condomínios":
    st.header("Gerenciar Base de Dados")
    df_geral = buscar_locais()
    
    t1, t2 = st.tabs(["➕ Cadastrar Novo", "⚙️ Editar/Excluir"])
    
    with t1:
        with st.form("add"):
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("NOME")
            n_rua = c2.text_input("RUA")
            n_num = c1.text_input("NÚMERO")
            n_bair = c2.text_input("BAIRRO")
            if st.form_submit_button("Salvar Condomínio"):
                novo = pd.DataFrame([[n_nome, n_rua, n_num, n_bair, "João Pessoa", "PB"]], columns=df_geral.columns)
                df_up = pd.concat([df_geral, novo], ignore_index=True)
                conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_up)
                st.success("Salvo!")
                st.rerun()

    with t2:
        if not df_geral.empty:
            sel = st.selectbox("Selecione o local para modificar:", ["Selecione..."] + df_geral['NOME'].tolist())
            if sel != "Selecione...":
                dados = df_geral[df_geral['NOME'] == sel].iloc[0]
                idx = df_geral[df_geral['NOME'] == sel].index[0]
                with st.form("edit"):
                    e_rua = st.text_input("RUA", value=str(dados['RUA']))
                    e_num = st.text_input("NÚMERO", value=str(dados['NUMERO']))
                    if st.form_submit_button("Confirmar Alteração"):
                        df_geral.loc[idx, ['RUA', 'NUMERO']] = [e_rua, e_num]
                        conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_geral)
                        st.success("Atualizado!")
                        st.rerun()
                    if st.form_submit_button("🗑️ Excluir Permanente"):
                        df_del = df_geral.drop(idx)
                        conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_del)
                        st.warning("Excluído.")
                        st.rerun()
    st.dataframe(df_geral)

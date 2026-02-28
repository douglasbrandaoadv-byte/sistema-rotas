import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- 1. INICIALIZAÇÃO SEGURA (Evita o erro de AttributeError) ---
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_atual' not in st.session_state:
    st.session_state.usuario_atual = ""

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Renove - Gestão Total", layout="wide")

# Conexões
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)
conn = st.connection("gsheets", type=GSheetsConnection)

def buscar_locais():
    return conn.read(worksheet="locais", ttl="0")

def buscar_usuarios():
    return conn.read(worksheet="usuarios", ttl="0")

# --- 2. SISTEMA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    
    with st.container():
        user_input = st.text_input("Usuário")
        pass_input = st.text_input("Senha", type="password")
        
        if st.button("Entrar"):
            df_users = buscar_usuarios()
            # Validação na planilha de usuários
            validar = df_users[(df_users['USUARIO'] == user_input) & (df_users['SENHA'] == str(pass_input))]
            
            if not validar.empty:
                st.session_state.logado = True
                st.session_state.usuario_atual = user_input
                st.rerun()
            else:
                st.error("Dados incorretos. Verifique com o administrador.")
    st.stop()

# --- 3. INTERFACE PRINCIPAL ---
st.sidebar.write(f"👤 Logado como: **{st.session_state.usuario_atual}**")
if st.sidebar.button("Sair/Trocar Usuário"):
    st.session_state.logado = False
    st.session_state.usuario_atual = ""
    st.rerun()

# Definição das opções do menu
opcoes_menu = ["📍 Gerenciar Locais", "🚚 Criar Rota Inteligente"]

# Apenas o usuário 'admin' (ou seu nome) pode ver a gestão de usuários
if st.session_state.usuario_atual.lower() == 'admin':
    opcoes_menu.append("👥 Gerenciar Usuários")

aba = st.sidebar.radio("Navegação", opcoes_menu)

# --- ABA: GERENCIAR LOCAIS ---
if aba == "📍 Gerenciar Locais":
    st.header("Gestão de Condomínios e Estabelecimentos")
    df_locais = buscar_locais()
    
    tab_cad, tab_edit = st.tabs(["➕ Novo Cadastro", "⚙️ Editar ou Excluir"])

    with tab_cad:
        with st.form("form_novo"):
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("NOME DO LOCAL")
            n_rua = c2.text_input("RUA")
            n_num = c1.text_input("NÚMERO")
            n_bair = c2.text_input("BAIRRO")
            n_cid = c1.text_input("CIDADE", value="João Pessoa")
            n_est = c2.text_input("ESTADO", value="PB")
            if st.form_submit_button("Salvar Local"):
                novo = pd.DataFrame([[n_nome, n_rua, n_num, n_bair, n_cid, n_est]], columns=df_locais.columns)
                df_final = pd.concat([df_locais, novo], ignore_index=True)
                conn.update(worksheet="locais", data=df_final)
                st.success("Cadastrado!")
                st.rerun()

    with tab_edit:
        if not df_locais.empty:
            sel = st.selectbox("Escolha o local para modificar:", ["Selecione..."] + sorted(df_locais['NOME'].tolist()))
            if sel != "Selecione...":
                dados = df_locais[df_locais['NOME'] == sel].iloc[0]
                idx = df_locais[df_locais['NOME'] == sel].index[0]
                with st.form("edit_form"):
                    e_nome = st.text_input("NOME", value=str(dados['NOME']))
                    e_rua = st.text_input("RUA", value=str(dados['RUA']))
                    e_num = st.text_input("NÚMERO", value=str(dados['NUMERO']))
                    e_bair = st.text_input("BAIRRO", value=str(dados['BAIRRO']))
                    if st.form_submit_button("Atualizar"):
                        df_locais.loc[idx] = [e_nome, e_rua, e_num, e_bair, dados['CIDADE'], dados['ESTADO']]
                        conn.update(worksheet="locais", data=df_locais)
                        st.success("Atualizado!")
                        st.rerun()
                    if st.form_submit_button("🗑️ Excluir"):
                        df_novo = df_locais.drop(idx)
                        conn.update(worksheet="locais", data=df_novo)
                        st.warning("Excluído!")
                        st.rerun()

# --- ABA: CRIAR ROTA ---
elif aba == "🚚 Criar Rota Inteligente":
    st.header("Planejamento de Rota")
    df_locais = buscar_locais()
    qtd = st.number_input("Destinos:", min_value=1, step=1)
    miss_list = ["ENTREGA DE BOLETOS", "ENTREGA DE NOTIFICAÇÃO", "REGISTRO DE ATAS", "RECOLHER DOCUMENTOS"]
    
    sel_rota = []
    for i in range(int(qtd)):
        st.markdown(f"**Parada {i+1}**")
        c1, c2, c3 = st.columns(3)
        loc = c1.selectbox(f"Local", df_locais['NOME'].unique(), key=f"l{i}")
        mis = c2.selectbox(f"Missão", miss_list, key=f"m{i}")
        obs = c3.text_input(f"Observação", key=f"o{i}")
        row = df_locais[df_locais['NOME'] == loc].iloc[0]
        end = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
        sel_rota.append({"nome": loc, "endereco": end, "missao": mis, "obs": obs})

    partida = st.text_input("Início:", value="Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB")
    
    if st.button("🚀 Gerar Rota Econômica"):
        ends = [s['endereco'] for s in sel_rota]
        res = gmaps.directions(partida, ends[-1], waypoints=ends[:-1], optimize_waypoints=True)
        ordem = res[0]['waypoint_order']
        
        # Organiza a lista completa incluindo o destino final
        final = [sel_rota[i] for i in ordem] + [sel_rota[-1]] if len(sel_rota) > 1 else sel_rota
        
        st.success("Rota calculada!")
        link = "https://www.google.com/maps/dir/" + "/".join([partida] + [p['endereco'] for p in final])
        st.link_button("📱 Abrir no GPS do Motoboy", link)
        
        for i, p in enumerate(final):
            st.write(f"**{i+1}ª Parada: {p['nome']}** - {p['missao']}")
            st.write(f"📍 {p['endereco']} | 📝 {p['obs']}")
            st.divider()

# --- ABA: GERENCIAR USUÁRIOS (Admin apenas) ---
elif aba == "👥 Gerenciar Usuários":
    st.header("Controle de Acesso da Equipe")
    df_u = buscar_usuarios()
    
    with st.form("cad_user"):
        st.subheader("Novo Usuário")
        nu = st.text_input("Nome de Usuário")
        ns = st.text_input("Senha")
        if st.form_submit_button("Cadastrar Funcionário"):
            if nu and ns:
                nu_df = pd.DataFrame([[nu, ns]], columns=["USUARIO", "SENHA"])
                df_u_f = pd.concat([df_u, nu_df], ignore_index=True)
                conn.update(worksheet="usuarios", data=df_u_f)
                st.success("Usuário criado!")
                st.rerun()
    
    st.subheader("Equipe Cadastrada")
    st.table(df_u)
    if st.button("🗑️ Remover último usuário da lista"):
        df_u = df_u[:-1]
        conn.update(worksheet="usuarios", data=df_u)
        st.rerun()

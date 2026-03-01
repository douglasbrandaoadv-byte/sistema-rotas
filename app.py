import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# --- CONEXÃO BLINDADA ---
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    
    # Prevenção: Corrige as quebras de linha caso o servidor as leia como texto
    segredos = dict(st.secrets["connections"]["gsheets"])
    if "private_key" in segredos:
        segredos["private_key"] = segredos["private_key"].replace("\\n", "\n")
        
    conn = st.connection("gsheets", type=GSheetsConnection, **segredos)
except Exception as e:
    st.error(f"Erro na ligação ao servidor: {e}")
    st.stop()

def buscar_dados():
    try:
        return conn.read(worksheet="locais", ttl="0")
    except Exception as e:
        st.error(f"Falha ao descarregar base de dados: {e}")
        return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    if st.text_input("Palavra-passe", type="password") == "admin123":
        if st.button("Entrar no Sistema"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- MENU E INTERFACE ---
st.sidebar.success("✅ Conectado ao Google")
if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

aba = st.sidebar.radio("Navegação", ["📍 Gerir Estabelecimentos", "🚚 Gerar Rota Inteligente"])

if aba == "📍 Gerir Estabelecimentos":
    st.header("Base de Dados de Condomínios")
    df_existente = buscar_dados()
    
    tab_novo, tab_gerenciar = st.tabs(["➕ Cadastrar", "⚙️ Editar/Eliminar"])

    with tab_novo:
        with st.form("form_novo"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME DO LOCAL")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bairro = c2.text_input("BAIRRO")
            cidade = c1.text_input("CIDADE", value="João Pessoa")
            estado = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar no Banco de Dados"):
                if nome and rua:
                    novo = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                       columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                    df_final = pd.concat([df_existente, novo], ignore_index=True)
                    conn.update(worksheet="locais", data=df_final)
                    st.success(f"Condomínio '{nome}' guardado com sucesso!")
                    st.rerun()

    with tab_gerenciar:
        if df_existente.empty:
            st.info("Nenhum local registado ainda.")
        else:
            lista_nomes = df_existente['NOME'].tolist()
            selecionado = st.selectbox("Selecione o local:", lista_nomes)
            
            dados = df_existente[df_existente['NOME'] == selecionado].iloc[0]
            idx = df_existente[df_existente['NOME'] == selecionado].index[0]

            with st.form("form_edicao"):
                c1, c2 = st.columns(2)
                n_nome = c1.text_input("NOME", value=dados['NOME'])
                n_rua = c2.text_input("RUA", value=dados['RUA'])
                n_num = c1.text_input("NÚMERO", value=str(dados['NUMERO']))
                n_bair = c2.text_input("BAIRRO", value=dados['BAIRRO'])
                n_cid = c1.text_input("CIDADE", value=dados['CIDADE'])
                n_est = c2.text_input("ESTADO", value=dados['ESTADO'])
                
                b1, b2 = st.columns(2)
                if b1.form_submit_button("✅ Guardar Alteração"):
                    df_existente.loc[idx] = [n_nome, n_rua, n_num, n_bair, n_cid, n_est]
                    conn.update(worksheet="locais", data=df_existente)
                    st.success("Atualizado!")
                    st.rerun()

                if b2.form_submit_button("🗑️ Eliminar Permanente"):
                    df_existente = df_existente.drop(idx)
                    conn.update(worksheet="locais", data=df_existente)
                    st.warning("Registo removido.")
                    st.rerun()

    st.dataframe(df_existente, use_container_width=True)

elif aba == "🚚 Gerar Rota Inteligente":
    st.header("Otimização de Trajeto para Motoboy")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Efetue primeiro o registo dos condomínios na aba ao lado.")
    else:
        qtd = st.number_input("Destinos da diligência:", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            nome_sel = c1.selectbox(f"Parada {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
            missao_sel = c2.selectbox("Missão", missoes, key=f"m_{i}")
            obs = c3.text_input("Observações", key=f"o_{i}")
            
            row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
            end = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": end, "missao": missao_sel, "obs": obs})

        partida = st.text_input("Ponto de Partida:", value="João Pessoa, PB")

        if st.button("🚀 Calcular Rota"):
            with st.spinner("A conectar ao Google Maps..."):
                try:
                    ends = [s['endereco'] for s in selecionados]
                    res = gmaps.directions(partida, ends[-1], waypoints=ends[:-1], optimize_waypoints=True)
                    
                    ordem = res[0]['waypoint_order']
                    st.success("Caminho mais curto calculado com sucesso!")
                    
                    link = f"https://www.google.com/maps/dir//{partida}/" + "/".join([selecionados[i]['endereco'] for i in ordem])
                    st.link_button("📱 Abrir GPS", link)

                    for i, idx in enumerate(ordem):
                        item = selecionados[idx]
                        st.write(f"**{i+1}º - {item['nome']}** | {item['missao']}")
                        st.write(f"📍 {item['endereco']}")
                        st.divider()
                except Exception:
                    st.error("Falha ao gerar o mapa. Verifique se os endereços são válidos.")

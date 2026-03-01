import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps
import urllib.parse

st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# --- CONEXÃO DIRETA OFICIAL ---
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    URL_PLANILHA = st.secrets["URL_PLANILHA"]
    gmaps = googlemaps.Client(key=API_KEY)
    
    credenciais = dict(st.secrets["minhas_credenciais"])
    credenciais["private_key"] = credenciais["private_key"].replace("\\n", "\n")
    
    # A correção está aqui: os asteriscos (**) desempacotam o dicionário perfeitamente
    conn = st.connection("planilha_renove", type=GSheetsConnection, **credenciais)
except Exception as e:
    st.error(f"⚠️ Erro ao aceder às credenciais: {e}")
    st.stop()

def buscar_dados():
    try:
        return conn.read(spreadsheet=URL_PLANILHA, worksheet="locais", ttl="0")
    except Exception as e:
        st.warning("Planilha sem dados ou não acessível no momento.")
        return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])

# --- SISTEMA DE ACESSO ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    if st.text_input("Insira a Senha", type="password") == "admin123":
        if st.button("Entrar no Sistema"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.success("✅ Conectado à Base de Dados")
if st.sidebar.button("Terminar Sessão"):
    st.session_state.logado = False
    st.rerun()

aba = st.sidebar.radio("Navegação", ["📍 Gestão de Locais", "🚚 Gerar Itinerário"])

if aba == "📍 Gestão de Locais":
    st.header("Base de Dados de Condomínios")
    df_existente = buscar_dados()
    
    tab_novo, tab_gerenciar = st.tabs(["➕ Adicionar Local", "⚙️ Editar/Eliminar"])

    with tab_novo:
        with st.form("form_novo"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME DO LOCAL")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bairro = c2.text_input("BAIRRO")
            cidade = c1.text_input("CIDADE", value="João Pessoa")
            estado = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Guardar Local"):
                if nome and rua:
                    novo = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                       columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                    df_final = pd.concat([df_existente, novo], ignore_index=True)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_final)
                    st.success(f"Condomínio '{nome}' adicionado com sucesso!")
                    st.rerun()

    with tab_gerenciar:
        if df_existente.empty:
            st.info("A base de dados encontra-se vazia.")
        else:
            lista_nomes = df_existente['NOME'].tolist()
            selecionado = st.selectbox("Selecione o local para editar:", lista_nomes)
            
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
                if b1.form_submit_button("✅ Guardar Alterações"):
                    df_existente.loc[idx] = [n_nome, n_rua, n_num, n_bair, n_cid, n_est]
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_existente)
                    st.success("Informações atualizadas!")
                    st.rerun()

                if b2.form_submit_button("🗑️ Remover Registo"):
                    df_existente = df_existente.drop(idx)
                    conn.update(spreadsheet=URL_PLANILHA, worksheet="locais", data=df_existente)
                    st.warning("Condomínio removido da lista.")
                    st.rerun()

    st.dataframe(df_existente, use_container_width=True)

elif aba == "🚚 Gerar Itinerário":
    st.header("Cálculo de Rota Económica (Menor Distância)")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Adicione os condomínios na aba lateral antes de gerar rotas.")
    else:
        qtd = st.number_input("Número de diligências hoje:", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS", "FOLHA DE PAGAMENTO"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            nome_sel = c1.selectbox(f"Diligência {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
            missao_sel = c2.selectbox("Tarefa", missoes, key=f"m_{i}")
            obs = c3.text_input("Observações (Opcional)", key=f"o_{i}")
            
            row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
            end = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": end, "missao": missao_sel, "obs": obs})

        partida = st.text_input("Ponto de Partida (Onde o motoboy está agora):", value="João Pessoa, PB")
        
        # O Destino Final é cravado no código para fechar a rota
        destino_final_renove = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"

        if st.button("🚀 Otimizar Rota (Google Maps)"):
            with st.spinner("A calcular o caminho mais rápido e económico..."):
                try:
                    # Todos os locais selecionados são tratados como paradas no meio do caminho
                    waypoints = [s['endereco'] for s in selecionados]
                    
                    # O Google Maps recebe a Partida, o Destino Final Fixo, e reorganiza os Waypoints para a menor distância
                    res = gmaps.directions(partida, destino_final_renove, waypoints=waypoints, optimize_waypoints=True)
                    
                    ordem_otimizada = res[0]['waypoint_order']
                    rota_ordenada = [selecionados[i] for i in ordem_otimizada]
                    
                    st.success("Trajeto mais económico calculado com sucesso!")
                    
                    # Criação Segura do Link do GPS Universal
                    url_partida = urllib.parse.quote(partida)
                    url_paradas = "/".join([urllib.parse.quote(s['endereco']) for s in rota_ordenada])
                    url_destino = urllib.parse.quote(destino_final_renove)
                    
                    link = f"https://www.google.com/maps/dir/{url_partida}/{url_paradas}/{url_destino}"
                    
                    st.link_button("📱 Abrir Rota Direto no GPS do Motoboy", link)

                    st.subheader("📋 Relatório da Rota Inteligente")
                    st.info(f"🏍️ **INÍCIO (Partida):** {partida}")
                    
                    for i, item in enumerate(rota_ordenada):
                        st.write(f"**{i+1}ª Parada - {item['nome']}** | 🎯 {item['missao']}")
                        st.write(f"📍 {item['endereco']}")
                        if item['obs']:
                            st.caption(f"📝 Obs: {item['obs']}")
                        st.divider()
                    
                    st.success(f"🏁 **DESTINO FINAL:** Sede da Renove Administradora ({destino_final_renove})")
                        
                except Exception as e:
                    st.error("Falha ao traçar rota. Confirme se as ruas cadastradas existem no mapa e tente novamente.")

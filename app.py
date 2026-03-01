import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# Conexão com as Chaves de Segurança
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    gmaps = googlemaps.Client(key=API_KEY)
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro ao carregar as chaves de segurança. Verifique o painel Secrets.")
    st.stop()

# Função de busca protegida (aponta especificamente para a aba 'locais')
def buscar_dados():
    try:
        return conn.read(worksheet="locais", ttl="0")
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])

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
st.sidebar.success("Sistema Renove Ativo")
aba = st.sidebar.radio("Navegação", ["📍 Cadastrar Locais", "🚚 Criar Rota Inteligente"])

if aba == "📍 Cadastrar Locais":
    st.header("Gestão de Estabelecimentos")
    df_existente = buscar_dados()
    
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
                if nome and rua: # Prevenção de campos vazios
                    novo = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                       columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                    df_final = pd.concat([df_existente, novo], ignore_index=True)
                    # Força a atualização apenas na aba correta
                    conn.update(worksheet="locais", data=df_final)
                    st.success(f"'{nome}' cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.warning("Preencha ao menos o Nome e a Rua.")

    with tab_gerenciar:
        if df_existente.empty:
            st.warning("Nenhum local cadastrado para gerenciar.")
        else:
            st.subheader("Selecionar Local para Modificação")
            lista_nomes = df_existente['NOME'].tolist()
            selecionado = st.selectbox("Escolha o estabelecimento:", lista_nomes)
            
            dados_local = df_existente[df_existente['NOME'] == selecionado].iloc[0]
            idx_original = df_existente[df_existente['NOME'] == selecionado].index[0]

            with st.form("form_edicao"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("NOME", value=dados_local['NOME'])
                nova_rua = c2.text_input("RUA", value=dados_local['RUA'])
                novo_num = c1.text_input("NÚMERO", value=str(dados_local['NUMERO']))
                novo_bairro = c2.text_input("BAIRRO", value=dados_local['BAIRRO'])
                nova_cidade = c1.text_input("CIDADE", value=dados_local['CIDADE'])
                novo_estado = c2.text_input("ESTADO", value=dados_local['ESTADO'])
                
                col_btn1, col_btn2 = st.columns(2)
                btn_atualizar = col_btn1.form_submit_button("✅ Salvar Alterações")
                btn_excluir = col_btn2.form_submit_button("🗑️ Excluir Cadastro")

                if btn_atualizar:
                    df_existente.loc[idx_original] = [novo_nome, nova_rua, novo_num, novo_bairro, nova_cidade, novo_estado]
                    conn.update(worksheet="locais", data=df_existente)
                    st.success("Informações atualizadas!")
                    st.rerun()

                if btn_excluir:
                    df_novo = df_existente.drop(idx_original)
                    conn.update(worksheet="locais", data=df_novo)
                    st.warning(f"'{selecionado}' removido com sucesso.")
                    st.rerun()

    st.divider()
    st.subheader("Base de Dados Atual")
    st.dataframe(df_existente, use_container_width=True)

# --- ABA DE ROTAS ---
elif aba == "🚚 Criar Rota Inteligente":
    st.header("Gerar Itinerário Econômico")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Cadastre locais primeiro.")
    else:
        qtd = st.number_input("Quantos destinos hoje?", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "ENTREGA DE NOTIFICAÇÃO", "ENTREGA DE FOLHA DE PAGAMENTO", "REGISTRO DE ATAS", "RECOLHER ATAS", "RECOLHER DOCUMENTOS"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            nome_sel = col1.selectbox(f"Local {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
            missao_sel = col2.selectbox(f"Missão", missoes, key=f"m_{i}")
            obs = col3.text_input("Observação", key=f"o_{i}")
            
            row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
            endereco = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": endereco, "missao": missao_sel, "obs": obs})

        st.subheader("Ponto de Partida")
        partida = st.text_input("De onde o motoboy está saindo?", value="João Pessoa, PB")

        if st.button("🚀 Gerar Melhor Rota"):
            with st.spinner("Otimizando trajeto com Google Maps..."):
                try:
                    enderecos_lista = [s['endereco'] for s in selecionados]
                    resultado = gmaps.directions(partida, enderecos_lista[-1], waypoints=enderecos_lista[:-1], optimize_waypoints=True)
                    
                    ordem_otimizada = resultado[0]['waypoint_order']
                    
                    st.success("Rota calculada com a sequência mais curta!")
                    
                    link_final = f"https://www.google.com/maps/dir//{partida}/" + "/".join([selecionados[i]['endereco'] for i in ordem_otimizada])
                    st.link_button("📱 Abrir Rota no GPS do Motoboy", link_final)

                    st.subheader("📋 Relatório de Entrega")
                    for i, idx_original in enumerate(ordem_otimizada):
                        item = selecionados[idx_original]
                        st.markdown(f"**{i+1}ª Parada: {item['nome']}**")
                        st.write(f"📍 {item['endereco']}")
                        st.write(f"🎯 Missão: {item['missao']} | 📝 Obs: {item['obs']}")
                        st.divider()
                except Exception as e:
                    st.error("Erro ao gerar a rota. Verifique se os endereços estão corretos.")

import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import googlemaps

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# Conexão com as Chaves de Segurança
API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
gmaps = googlemaps.Client(key=API_KEY)
conn = st.connection("gsheets", type=GSheetsConnection)

def buscar_dados():
    # ttl="0" garante que ele sempre pegue o dado mais atual da planilha
    return conn.read(ttl="0")

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    senha = st.text_input("Senha do Sistema", type="password")
    if st.button("Entrar"):
        if senha == "admin123":
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- MENU ---
aba = st.sidebar.radio("Navegação", ["📍 Cadastrar e Gerenciar", "🚚 Criar Rota Inteligente"])

# --- 1. ABA DE CADASTRO E GERENCIAMENTO ---
if aba == "📍 Cadastrar e Gerenciar":
    st.header("Gestão de Condomínios e Estabelecimentos")
    df_existente = buscar_dados()
    
    aba_cad, aba_edit = st.tabs(["➕ Novo Cadastro", "⚙️ Editar ou Excluir"])

    # SUB-ABA: CADASTRAR NOVO
    with aba_cad:
        with st.form("form_novo"):
            st.subheader("Cadastrar Novo Local")
            c1, c2 = st.columns(2)
            nome = c1.text_input("NOME DO LOCAL")
            rua = c2.text_input("RUA")
            num = c1.text_input("NÚMERO")
            bairro = c2.text_input("BAIRRO")
            cidade = c1.text_input("CIDADE", value="João Pessoa")
            estado = c2.text_input("ESTADO", value="PB")
            
            if st.form_submit_button("Salvar Local"):
                novo = pd.DataFrame([[nome, rua, num, bairro, cidade, estado]], 
                                   columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
                df_final = pd.concat([df_existente, novo], ignore_index=True)
                conn.update(data=df_final)
                st.success(f"'{nome}' cadastrado com sucesso!")
                st.rerun()

    # SUB-ABA: EDITAR OU EXCLUIR
    with aba_edit:
        if df_existente.empty:
            st.info("Não há locais cadastrados para gerenciar.")
        else:
            st.subheader("Selecione um local para modificar")
            # Cria uma lista de nomes para escolher
            opcao_sel = st.selectbox("Escolha o estabelecimento:", df_existente['NOME'].tolist())
            
            # Localiza os dados atuais desse estabelecimento
            dados_atuais = df_existente[df_existente['NOME'] == opcao_sel].iloc[0]
            indice_original = df_existente[df_existente['NOME'] == opcao_sel].index[0]

            with st.form("form_edicao"):
                c1, c2 = st.columns(2)
                novo_nome = c1.text_input("NOME", value=dados_atuais['NOME'])
                nova_rua = c2.text_input("RUA", value=dados_atuais['RUA'])
                novo_num = c1.text_input("NÚMERO", value=dados_atuais['NUMERO'])
                novo_bairro = c2.text_input("BAIRRO", value=dados_atuais['BAIRRO'])
                nova_cidade = c1.text_input("CIDADE", value=dados_atuais['CIDADE'])
                novo_estado = c2.text_input("ESTADO", value=dados_atuais['ESTADO'])
                
                col_btn_edit, col_btn_del = st.columns(2)
                
                # BOTÃO ATUALIZAR
                if col_btn_edit.form_submit_button("✅ Salvar Alterações"):
                    df_existente.loc[indice_original] = [novo_nome, nova_rua, novo_num, novo_bairro, nova_cidade, novo_estado]
                    conn.update(data=df_existente)
                    st.success("Informações atualizadas!")
                    st.rerun()
                
                # BOTÃO EXCLUIR
                if col_btn_del.form_submit_button("🗑️ Excluir Cadastro"):
                    df_novo = df_existente.drop(indice_original)
                    conn.update(data=df_novo)
                    st.warning(f"'{opcao_sel}' foi removido do sistema.")
                    st.rerun()

    st.divider()
    st.subheader("Visualizar Todos os Locais")
    st.dataframe(df_existente)

# --- 2. ABA DE CRIAR ROTA ---
elif aba == "🚚 Criar Rota Inteligente":
    st.header("Gerar Itinerário Econômico")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Cadastre os locais primeiro.")
    else:
        qtd = st.number_input("Quantos destinos hoje?", min_value=1, step=1)
        missoes = ["ENTREGA DE BOLETOS", "ENTREGA DE NOTIFICAÇÃO", "ENTREGA DE FOLHA DE PAGAMENTO", "REGISTRO DE ATAS", "RECOLHER ATAS", "RECOLHER DOCUMENTOS"]
        
        selecionados = []
        for i in range(int(qtd)):
            st.markdown(f"---")
            col1, col2, col3 = st.columns(3)
            nome_sel = col1.selectbox(f"Local {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
            missao_sel = col2.selectbox(f"Missão {i+1}", missoes, key=f"m_{i}")
            obs = col3.text_input(f"Observação {i+1}", key=f"o_{i}")
            
            row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
            endereco = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
            selecionados.append({"nome": nome_sel, "endereco": endereco, "missao": missao_sel, "obs": obs})

        st.subheader("Ponto de Partida")
        partida = st.text_input("De onde o motoboy está saindo?", value="Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB")

        if st.button("🚀 Gerar Melhor Rota"):
            with st.spinner("Otimizando trajeto..."):
                enderecos_lista = [s['endereco'] for s in selecionados]
                resultado = gmaps.directions(partida, enderecos_lista[-1], waypoints=enderecos_lista[:-1], optimize_waypoints=True)
                
                ordem_otimizada = resultado[0]['waypoint_order']
                paradas_finais = [selecionados[i] for i in ordem_otimizada]
                if len(selecionados) > 1:
                    paradas_finais.append(selecionados[-1])
                elif len(selecionados) == 1:
                    paradas_finais = [selecionados[0]]

                link_final = "https://www.google.com/maps/dir/" + "/".join([partida] + [p['endereco'] for p in paradas_finais])
                st.link_button("📱 Abrir Rota no GPS", link_final)

                st.subheader("📋 Relatório de Entrega")
                for i, item in enumerate(paradas_finais):
                    st.markdown(f"**{i+1}ª Parada: {item['nome']}**")
                    st.write(f"📍 {item['endereco']}")
                    st.write(f"🎯 Missão: {item['missao']} | 📝 Obs: {item['obs']}")
                    st.divider()

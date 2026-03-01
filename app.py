import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import googlemaps
import urllib.parse
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# --- CONEXÃO OFICIAL GOOGLE (NATIVA E SEM BUGS) ---
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    URL_PLANILHA = st.secrets["URL_PLANILHA"]
    gmaps = googlemaps.Client(key=API_KEY)
    
    credenciais_dict = dict(st.secrets["credenciais_google"])
    credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
    
    gc = gspread.service_account_from_dict(credenciais_dict)
    planilha = gc.open_by_url(URL_PLANILHA)
    
    aba_banco = planilha.worksheet("locais")
    aba_historico = planilha.worksheet("historico_rotas")
    
except Exception as e:
    st.error(f"⚠️ Erro ao aceder ao sistema do Google: {e}")
    st.stop()

def buscar_dados():
    try:
        registos = aba_banco.get_all_records()
        if not registos:
            return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])
            
        df = pd.DataFrame(registos)
        df.columns = df.columns.str.upper() 
        return df
    except Exception as e:
        st.error(f"⚠️ Detalhe do bloqueio ao ler: {e}")
        return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])

def salvar_dados(df):
    aba_banco.clear()
    set_with_dataframe(aba_banco, df)

# --- SISTEMA DE ACESSO COM MEMÓRIA ANTI-REFRESH ---
if st.query_params.get("acesso") == "permitido":
    st.session_state.logado = True
elif 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    if st.text_input("Insira a Senha", type="password") == "admin123":
        if st.button("Entrar no Sistema"):
            st.session_state.logado = True
            st.query_params["acesso"] = "permitido"
            st.rerun()
    st.stop()

# --- INTERFACE PRINCIPAL ---
st.sidebar.success("✅ Conectado à Base de Dados")
if st.sidebar.button("Terminar Sessão"):
    st.session_state.logado = False
    st.query_params.clear()
    st.rerun()

aba = st.sidebar.radio("Navegação", ["📍 Gestão de Locais", "🚚 Gerar Itinerário", "📊 Relatórios de Rotas"])

if aba == "📍 Gestão de Locais":
    st.header("Base de Dados de Condomínios")
    df_existente = buscar_dados()
    
    tab_novo, tab_lote, tab_gerenciar = st.tabs(["➕ Adicionar Local", "📂 Cadastro em Lote", "⚙️ Editar/Eliminar"])

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
                    
                    with st.spinner("A guardar na Base de Dados..."):
                        salvar_dados(df_final)
                        
                    st.success(f"Condomínio '{nome}' adicionado com sucesso!")
                    st.rerun()

    with tab_lote:
        modo_lote = st.radio("Selecione o método de cadastro em lote:", 
                             ["📝 Preencher Planilha Online", "📁 Upload de Arquivo (Excel/CSV)"])
        
        if modo_lote == "📝 Preencher Planilha Online":
            st.info("💡 **Dica:** Preencha os dados diretamente na grade abaixo. Para adicionar mais linhas, basta clicar na última linha vazia ou no ícone de '+' que aparece no final.")
            
            df_template = pd.DataFrame(
                [["", "", "", "", "João Pessoa", "PB"]] * 5,
                columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"]
            )
            
            df_editado = st.data_editor(df_template, num_rows="dynamic")
            
            if st.button("🚀 Cadastrar Todos da Planilha"):
                df_valido = df_editado[df_editado["NOME"].str.strip() != ""]
                
                if not df_valido.empty:
                    df_final = pd.concat([df_existente, df_valido], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['NOME'], keep='last')
                    
                    with st.spinner("A enviar todos os registros para o banco de dados..."):
                        salvar_dados(df_final)
                    
                    st.success(f"✅ Sucesso! {len(df_valido)} locais cadastrados de uma só vez.")
                    st.rerun()
                else:
                    st.warning("⚠️ Preencha pelo menos o 'NOME' de um local válido na planilha antes de cadastrar.")

        else: 
            st.info("💡 **Dica:** A sua planilha deve conter as seguintes colunas exatas na primeira linha: **NOME, RUA, NUMERO, BAIRRO, CIDADE, ESTADO**")
            arquivo_up = st.file_uploader("Selecione a sua planilha (.csv ou .xlsx)", type=["csv", "xlsx"])
            
            if arquivo_up is not None:
                try:
                    if arquivo_up.name.endswith('.csv'):
                        df_lote = pd.read_csv(arquivo_up)
                    else:
                        df_lote = pd.read_excel(arquivo_up)
                    
                    df_lote.columns = df_lote.columns.str.upper().str.strip()
                    colunas_obrigatorias = ["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"]
                    
                    if all(col in df_lote.columns for col in colunas_obrigatorias):
                        st.write("🔎 **Pré-visualização dos dados:**")
                        st.dataframe(df_lote[colunas_obrigatorias].head(5))
                        
                        if st.button("🚀 Confirmar e Guardar Arquivo"):
                            df_final = pd.concat([df_existente, df_lote[colunas_obrigatorias]], ignore_index=True)
                            df_final = df_final.drop_duplicates(subset=['NOME'], keep='last')
                            
                            with st.spinner("A processar e a enviar tudo para o Google Sheets..."):
                                salvar_dados(df_final)
                            
                            st.success(f"✅ Sucesso! {len(df_lote)} locais importados de uma só vez.")
                            st.rerun()
                    else:
                        st.error("⚠️ ERRO: A sua planilha não contém as colunas corretas.")
                except Exception as e:
                    st.error(f"Erro ao ler o ficheiro: {e}")

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
                    with st.spinner("A atualizar no sistema..."):
                        salvar_dados(df_existente)
                    st.success("Informações atualizadas!")
                    st.rerun()

                if b2.form_submit_button("🗑️ Remover Registo"):
                    df_existente = df_existente.drop(idx)
                    with st.spinner("A remover do sistema..."):
                        salvar_dados(df_existente)
                    st.warning("Condomínio removido da lista.")
                    st.rerun()

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
        
        destino_final_renove = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"

        if st.button("🚀 Otimizar Rota (Google Maps)"):
            with st.spinner("A calcular o caminho mais rápido e económico..."):
                try:
                    waypoints = [s['endereco'] for s in selecionados]
                    res = gmaps.directions(partida, destino_final_renove, waypoints=waypoints, optimize_waypoints=True)
                    
                    ordem_otimizada = res[0]['waypoint_order']
                    rota_ordenada = [selecionados[i] for i in ordem_otimizada]
                    
                    # --- CÁLCULO DA QUILOMETRAGEM TOTAL ---
                    distancia_total_metros = 0
                    for leg in res[0]['legs']:
                        distancia_total_metros += leg['distance']['value']
                    
                    distancia_total_km = round(distancia_total_metros / 1000, 1)
                    distancia_texto = f"{distancia_total_km} km"
                    
                    st.success(f"Trajeto mais económico calculado com sucesso! (Distância total: {distancia_texto})")
                    
                    url_partida = urllib.parse.quote(partida)
                    url_paradas = "/".join([urllib.parse.quote(s['endereco']) for s in rota_ordenada])
                    url_destino = urllib.parse.quote(destino_final_renove)
                    
                    link = f"https://www.google.com/maps/dir/{url_partida}/{url_paradas}/{url_destino}"
                    
                    st.link_button("📱 Abrir Rota Direto no GPS do Motoboy", link)

                    st.subheader("📋 Relatório da Rota Inteligente")
                    st.info(f"🏍️ **INÍCIO (Partida):** {partida}")
                    
                    nomes_rota_historico = []
                    
                    for i, item in enumerate(rota_ordenada):
                        st.write(f"**{i+1}ª Parada - {item['nome']}** | 🎯 {item['missao']}")
                        st.write(f"📍 {item['endereco']}")
                        if item['obs']:
                            st.caption(f"📝 Obs: {item['obs']}")
                        st.divider()
                        nomes_rota_historico.append(item['nome'])
                    
                    st.success(f"🏁 **DESTINO FINAL:** Sede da Administradora ({destino_final_renove})")
                    nomes_rota_historico.append("Sede Renove")
                    
                    fuso_jp = pytz.timezone('America/Fortaleza')
                    agora = datetime.now(fuso_jp)
                    
                    linha_historico = [
                        agora.strftime("%d/%m/%Y"),           # DATA
                        agora.strftime("%H:%M"),              # HORA
                        partida,                              # PARTIDA
                        " ➔ ".join(nomes_rota_historico),     # ROTA COMPLETA
                        distancia_texto                       # KM TOTAL
                    ]
                    
                    try:
                        aba_historico.append_row(linha_historico)
                    except Exception as e:
                        st.warning("A rota foi gerada no ecrã, mas houve uma falha ao arquivar no histórico.")
                        
                except Exception as e:
                    st.error("Falha ao traçar rota. Confirme se as ruas cadastradas existem no mapa e tente novamente.")

elif aba == "📊 Relatórios de Rotas":
    st.header("Histórico de Rotas Geradas")
    
    try:
        dados_historico = aba_historico.get_all_records()
        
        if not dados_historico:
            st.info("Nenhuma rota foi gerada e gravada ainda.")
        else:
            df_hist = pd.DataFrame(dados_historico)
            
            # Filtro por Data
            if 'DATA' in df_hist.columns:
                datas_disponiveis = df_hist['DATA'].unique().tolist()
                datas_disponiveis.reverse() 
                
                data_selecionada = st.selectbox("📅 Selecione a Data para visualizar:", ["Todas as Datas"] + datas_disponiveis)
                
                if data_selecionada != "Todas as Datas":
                    df_hist = df_hist[df_hist['DATA'] == data_selecionada]
            
            # Exibe os dados (agora com a coluna KM TOTAL)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            if 'DATA' in df_hist.columns:
                csv = df_hist.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Descarregar Relatório em Excel (CSV)",
                    data=csv,
                    file_name=f"relatorio_rotas_{data_selecionada.replace('/', '-')}.csv" if data_selecionada != "Todas as Datas" else "relatorio_rotas_todas.csv",
                    mime="text/csv",
                )
            
    except Exception as e:
        st.error("⚠️ Ocorreu um erro ao ler o histórico. Certifique-se de que criou a aba 'historico_rotas' na sua folha de cálculo com os títulos exatos: DATA | HORA | PARTIDA | ROTA | KM TOTAL.")

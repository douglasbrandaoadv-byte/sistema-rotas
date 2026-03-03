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

# --- SISTEMA DE CACHE PARA PROTEGER CONTRA BLOQUEIOS DO GOOGLE ---
@st.cache_data(ttl=600, show_spinner=False)
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
    buscar_dados.clear() # Limpa a memória para forçar uma nova leitura atualizada

@st.cache_data(ttl=600, show_spinner=False)
def buscar_historico():
    try:
        return aba_historico.get_all_records()
    except Exception as e:
        return []

# --- SISTEMA DE ACESSO COM MEMÓRIA ANTI-REFRESH ---
if st.query_params.get("acesso") == "permitido":
    st.session_state.logado = True
elif 'logado' not in st.session_state:
    st.session_state.logado = False

if 'lote_key' not in st.session_state:
    st.session_state.lote_key = 0

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

# ==========================================================
# MENU 1: GESTÃO DE LOCAIS
# ==========================================================
if aba == "📍 Gestão de Locais":
    st.header("Base de Dados de Condomínios")
    df_existente = buscar_dados()
    
    tab_cadastrados, tab_novo, tab_lote = st.tabs([
        "🏢 Empreendimentos Cadastrados", 
        "➕ Adicionar Local", 
        "📂 Cadastro em Lote"
    ])

    with tab_cadastrados:
        st.subheader("Pesquisa e Gestão de Locais")
        
        if df_existente.empty:
            st.info("A base de dados encontra-se vazia.")
        else:
            termo_busca = st.text_input("🔍 Buscar Empreendimento (Digite o nome, rua ou bairro):", "").strip().lower()
            
            df_display = df_existente.copy()
            
            if termo_busca:
                mask = df_display.apply(lambda row: row.astype(str).str.lower().str.contains(termo_busca).any(), axis=1)
                df_display = df_display[mask]
                if df_display.empty:
                    st.warning("Nenhum local encontrado com este termo.")
            
            st.caption("💡 Marque a caixa ao lado do local para **Editar** ou **Excluir**.")
            df_display.insert(0, "SELECIONAR", False)
            
            df_editado = st.data_editor(
                df_display,
                column_config={"SELECIONAR": st.column_config.CheckboxColumn(required=True)},
                disabled=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"],
                hide_index=True,
                use_container_width=True,
                key="editor_locais_cadastrados"
            )
            
            selecionados = df_editado[df_editado["SELECIONAR"] == True]
            
            if not selecionados.empty:
                st.divider()
                
                if len(selecionados) == 1:
                    idx_real = selecionados.index[0] 
                    dados_originais = df_existente.loc[idx_real]
                    
                    st.write("### ✏️ Editar Informações do Local")
                    with st.form("form_edita_local"):
                        c1, c2 = st.columns(2)
                        n_nome = c1.text_input("NOME", value=dados_originais['NOME'])
                        n_rua = c2.text_input("RUA", value=dados_originais['RUA'])
                        n_num = c1.text_input("NÚMERO", value=str(dados_originais['NUMERO']))
                        n_bair = c2.text_input("BAIRRO", value=dados_originais['BAIRRO'])
                        n_cid = c1.text_input("CIDADE", value=dados_originais['CIDADE'])
                        n_est = c2.text_input("ESTADO", value=dados_originais['ESTADO'])
                        
                        col_salvar, col_vazia = st.columns([1, 3])
                        with col_salvar:
                            if st.form_submit_button("✅ Guardar Edição"):
                                df_existente.loc[idx_real] = [n_nome, n_rua, n_num, n_bair, n_cid, n_est]
                                with st.spinner("A atualizar no Google Sheets..."):
                                    salvar_dados(df_existente)
                                st.success("Local atualizado com sucesso!")
                                st.rerun()
                else:
                    st.info("⚠️ Para **Editar**, por favor selecione apenas um (1) local de cada vez.")
                
                st.write("### 🗑️ Exclusão")
                if st.button(f"Excluir {len(selecionados)} local(is) selecionado(s)", type="primary"):
                    indices_para_excluir = selecionados.index.tolist()
                    df_existente = df_existente.drop(indices_para_excluir)
                    with st.spinner("A remover do banco de dados..."):
                        salvar_dados(df_existente)
                    st.warning("Local(is) excluído(s) com sucesso.")
                    st.rerun()
            else:
                st.caption(f"📊 Total listado: {len(df_display)} empreendimento(s).")

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
            
            df_editado = st.data_editor(
                df_template, 
                num_rows="dynamic", 
                key=f"tabela_lote_{st.session_state.lote_key}"
            )
            
            if st.button("🚀 Cadastrar Todos da Planilha"):
                df_valido = df_editado[df_editado["NOME"].str.strip() != ""]
                
                if not df_valido.empty:
                    df_final = pd.concat([df_existente, df_valido], ignore_index=True)
                    df_final = df_final.drop_duplicates(subset=['NOME'], keep='last')
                    
                    with st.spinner("A enviar todos os registros para o banco de dados..."):
                        salvar_dados(df_final)
                    
                    st.success(f"✅ Sucesso! {len(df_valido)} locais cadastrados de uma só vez.")
                    st.session_state.lote_key += 1
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

# ==========================================================
# MENU 2: GERAR ITINERÁRIO
# ==========================================================
elif aba == "🚚 Gerar Itinerário":
    st.header("Cálculo de Rota e Gestão de Urgências")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Adicione os condomínios na aba lateral antes de gerar rotas.")
    else:
        if 'etapa_rota' not in st.session_state:
            st.session_state.etapa_rota = 0
            st.session_state.rota_provisoria = []
            st.session_state.partida = ""
            st.session_state.historico_salvo = False

        if st.session_state.etapa_rota == 0:
            qtd = st.number_input("Número de diligências hoje:", min_value=1, step=1)
            missoes = ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS", "FOLHA DE PAGAMENTO"]
            
            selecionados = []
            for i in range(int(qtd)):
                st.markdown("---")
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                nome_sel = c1.selectbox(f"Diligência {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
                missao_sel = c2.selectbox("Tarefa", missoes, key=f"m_{i}")
                obs = c3.text_input("Observações (Opcional)", key=f"o_{i}")
                urgente = c4.checkbox("🚨 URGÊNCIA", key=f"u_{i}")
                
                row = df_locais[df_locais['NOME'] == nome_sel].iloc[0]
                end = f"{row['RUA']}, {row['NUMERO']}, {row['BAIRRO']}, {row['CIDADE']}, {row['ESTADO']}"
                selecionados.append({"nome": nome_sel, "endereco": end, "missao": missao_sel, "obs": obs, "urgente": urgente})

            partida = st.text_input("Ponto de Partida (Onde o motoboy está agora):", value="João Pessoa, PB")
            destino_final_renove = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"

            if st.button("⚙️ Gerar Rota Provisória"):
                with st.spinner("A consultar o Google Maps para sugerir o caminho mais rápido..."):
                    try:
                        waypoints = [s['endereco'] for s in selecionados]
                        res = gmaps.directions(partida, destino_final_renove, waypoints=waypoints, optimize_waypoints=True)
                        
                        ordem_otimizada = res[0]['waypoint_order']
                        rota_ordenada = [selecionados[i] for i in ordem_otimizada]
                        
                        st.session_state.rota_provisoria = rota_ordenada
                        st.session_state.partida = partida
                        st.session_state.etapa_rota = 1
                        st.rerun()
                    except Exception as e:
                        st.error("Falha ao traçar rota. Confirme se as ruas cadastradas existem no mapa e tente novamente.")

        elif st.session_state.etapa_rota == 1:
            st.subheader("📋 Rota Provisória (Ajuste a Sequência se Necessário)")
            st.info("Esta é a sequência mais curta sugerida pelo GPS. **Use as setas ⬆️ e ⬇️ para subir ou descer um local e furar a fila, caso haja uma urgência.**")
            
            hc1, hc2, hc3, hc4, hc5 = st.columns([0.8, 1.2, 1, 3, 3])
            hc1.write("**ORDEM**")
            hc2.write("**AÇÃO**")
            hc3.write("**URGÊNCIA**")
            hc4.write("**LOCAL**")
            hc5.write("**ENDEREÇO**")
            st.markdown("---")
            
            for i, item in enumerate(st.session_state.rota_provisoria):
                c1, c2, c3, c4, c5 = st.columns([0.8, 1.2, 1, 3, 3])
                
                c1.markdown(f"<h4 style='margin-top:0px;'>{i+1}º</h4>", unsafe_allow_html=True)
                
                with c2:
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.button("⬆️", key=f"up_{i}", disabled=(i == 0), help="Subir"):
                            st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i-1] = \
                                st.session_state.rota_provisoria[i-1], st.session_state.rota_provisoria[i]
                            st.rerun()
                    with sc2:
                        if st.button("⬇️", key=f"down_{i}", disabled=(i == len(st.session_state.rota_provisoria) - 1), help="Descer"):
                            st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i+1] = \
                                st.session_state.rota_provisoria[i+1], st.session_state.rota_provisoria[i]
                            st.rerun()
                
                c3.write("🚨 SIM" if item["urgente"] else "")
                c4.write(f"{item['nome']}\n\n*(Tarefa: {item['missao']})*")
                c5.write(item["endereco"])
                
                st.markdown("---")
            
            st.write("") 
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar Sequência e Finalizar Rota", type="primary"):
                    with st.spinner("A consolidar a rota final e a calcular a distância exata..."):
                        st.session_state.rota_final = st.session_state.rota_provisoria.copy()
                        st.session_state.etapa_rota = 2
                        st.rerun()
            with c2:
                if st.button("⬅️ Cancelar e Voltar"):
                    st.session_state.etapa_rota = 0
                    st.rerun()

        elif st.session_state.etapa_rota == 2:
            destino_final_renove = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"
            partida = st.session_state.partida
            rota_final = st.session_state.rota_final
            
            try:
                waypoints = [s['endereco'] for s in rota_final]
                res = gmaps.directions(partida, destino_final_renove, waypoints=waypoints, optimize_waypoints=False)
                
                distancia_total_metros = 0
                for leg in res[0]['legs']:
                    distancia_total_metros += leg['distance']['value']
                
                distancia_total_km = round(distancia_total_metros / 1000, 1)
                distancia_texto = f"{distancia_total_km} km"
                
                st.success(f"🎉 Trajeto Oficial Finalizado com sucesso! (Distância total: {distancia_texto})")
                
                url_partida = urllib.parse.quote(partida)
                url_paradas = "/".join([urllib.parse.quote(s['endereco']) for s in rota_final])
                url_destino = urllib.parse.quote(destino_final_renove)
                
                link = f"https://www.google.com/maps/dir/{url_partida}/{url_paradas}/{url_destino}"
                
                st.link_button("📱 Abrir Rota Direta no GPS do Motoboy", link)

                st.subheader("📋 Relatório da Rota Oficial")
                st.info(f"🏍️ **INÍCIO (Partida):** {partida}")
                
                nomes_rota_historico = []
                
                for i, item in enumerate(rota_final):
                    tag_urgente = "🚨 **URGENTE** | " if item["urgente"] else ""
                    st.write(f"**{i+1}ª Parada - {item['nome']}** | {tag_urgente}🎯 {item['missao']}")
                    st.write(f"📍 {item['endereco']}")
                    if item['obs']:
                        st.caption(f"📝 Obs: {item['obs']}")
                    st.divider()
                    
                    nome_hist = f"🚨 {item['nome']}" if item["urgente"] else item['nome']
                    nomes_rota_historico.append(nome_hist)
                
                st.success(f"🏁 **DESTINO FINAL:** Sede da Administradora ({destino_final_renove})")
                nomes_rota_historico.append("Sede Renove")
                
                if not st.session_state.historico_salvo:
                    fuso_jp = pytz.timezone('America/Fortaleza')
                    agora = datetime.now(fuso_jp)
                    
                    linha_historico = [
                        agora.strftime("%d/%m/%Y"),
                        agora.strftime("%H:%M"),
                        partida,
                        " ➔ ".join(nomes_rota_historico),
                        distancia_texto
                    ]
                    
                    try:
                        aba_historico.append_row(linha_historico)
                        buscar_historico.clear() # Atualiza o cache do histórico
                        st.session_state.historico_salvo = True
                    except Exception as e:
                        st.warning("A rota foi gerada no ecrã, mas houve uma falha ao arquivar no histórico.")
                
                if st.button("🔄 Planejar Nova Rota"):
                    st.session_state.etapa_rota = 0
                    st.session_state.historico_salvo = False
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Falha ao processar rota final: {e}")

# ==========================================================
# MENU 3: RELATÓRIOS E GESTÃO DE HISTÓRICO
# ==========================================================
elif aba == "📊 Relatórios de Rotas":
    st.header("Histórico e Gestão de Rotas")
    
    try:
        dados_historico = buscar_historico()
        
        if not dados_historico:
            st.info("Nenhuma rota foi gerada e gravada ainda.")
        else:
            df_hist = pd.DataFrame(dados_historico)
            
            tab_geral, tab_agrupado, tab_edicao = st.tabs([
                "📋 Histórico Geral", 
                "📈 Relatório Agrupado", 
                "⚙️ Detalhar e Editar"
            ])
            
            # --- ABA 1: HISTÓRICO GERAL ---
            with tab_geral:
                if 'DATA' in df_hist.columns:
                    datas_disponiveis = df_hist['DATA'].unique().tolist()
                    datas_disponiveis.reverse() 
                    
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        data_selecionada = st.selectbox("📅 Filtrar tabela por Data:", ["Todas as Datas"] + datas_disponiveis)
                    
                    df_exibicao = df_hist.copy()
                    if data_selecionada != "Todas as Datas":
                        df_exibicao = df_exibicao[df_exibicao['DATA'] == data_selecionada]
                
                    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
                    
                    csv = df_exibicao.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descarregar Tabela em CSV",
                        data=csv,
                        file_name=f"relatorio_rotas_{data_selecionada.replace('/', '-')}.csv" if data_selecionada != "Todas as Datas" else "relatorio_rotas_todas.csv",
                        mime="text/csv",
                    )
            
            # --- ABA 2: RELATÓRIO AGRUPADO ---
            with tab_agrupado:
                st.info("💡 **Dica:** Marque as caixas na coluna 'SELECIONAR' para escolher rotas específicas. O sistema irá somar a quilometragem e mostrar os condomínios mais visitados nas rotas escolhidas.")
                
                df_selecao = df_hist.copy()
                df_selecao.insert(0, "SELECIONAR", False)
                
                df_editado = st.data_editor(
                    df_selecao,
                    column_config={"SELECIONAR": st.column_config.CheckboxColumn(required=True)},
                    disabled=["DATA", "HORA", "PARTIDA", "ROTA", "KM TOTAL"],
                    hide_index=True,
                    use_container_width=True,
                    key="editor_relatorio_agrupado"
                )
                
                rotas_selecionadas = df_editado[df_editado["SELECIONAR"] == True]
                
                if not rotas_selecionadas.empty:
                    st.divider()
                    st.subheader("📊 Resultados do Relatório")
                    
                    total_km = 0.0
                    todos_destinos = []
                    
                    for idx, row in rotas_selecionadas.iterrows():
                        km_val = row.get("KM TOTAL", "0")
                        try:
                            km_str = str(km_val).lower().replace('km', '').replace(',', '.').strip()
                            total_km += float(km_str)
                        except:
                            pass
                        
                        rota_val = row.get("ROTA", "")
                        pedacos = str(rota_val).split(" ➔ ")
                        for p in pedacos:
                            p_limpo = p.replace("🚨 ", "").strip()
                            if p_limpo and p_limpo != "Sede Renove" and p_limpo != row.get("PARTIDA", ""):
                                todos_destinos.append(p_limpo)
                    
                    c_res1, c_res2 = st.columns(2)
                    
                    c_res1.metric("🛣️ Quilometragem Total (Soma)", f"{total_km:.1f} km", f"{len(rotas_selecionadas)} rotas selecionadas")
                    
                    if todos_destinos:
                        contagem = pd.Series(todos_destinos).value_counts().reset_index()
                        contagem.columns = ["Condomínio / Local", "Qtd. de Visitas"]
                        c_res2.write("**🏆 Locais mais frequentes:**")
                        c_res2.dataframe(contagem, hide_index=True, use_container_width=True)

            # --- ABA 3: DETALHAR, EDITAR E EXCLUIR ---
            with tab_edicao:
                st.subheader("⚙️ Detalhar, Editar ou Excluir Rotas")
                
                termo_busca = st.text_input("🔍 Buscar Rota (Digite a Data ou o Nome do Local):", "").strip().lower()
                
                opcoes_rotas = []
                for idx, row in enumerate(dados_historico):
                    linha_sheets = idx + 2
                    
                    data_rota = str(row.get('DATA', '')).lower()
                    locais_rota = str(row.get('ROTA', '')).lower()
                    
                    if termo_busca in data_rota or termo_busca in locais_rota:
                        texto_resumo = f"{row.get('DATA', '')} às {row.get('HORA', '')} | {row.get('KM TOTAL', '')} | {str(row.get('ROTA', ''))[:60]}..."
                        opcoes_rotas.append((linha_sheets, texto_resumo, row))
                    
                opcoes_rotas.reverse()
                
                if not opcoes_rotas:
                    st.warning("Nenhuma rota encontrada com esse termo de busca.")
                else:
                    rota_selecionada = st.selectbox("Selecione a rota que deseja gerenciar:", opcoes_rotas, format_func=lambda x: x[1])
                    
                    if rota_selecionada:
                        linha_alvo, resumo, dados = rota_selecionada
                        
                        st.write("### 🔎 Detalhes da Rota")
                        c_detalhe1, c_detalhe2 = st.columns(2)
                        with c_detalhe1:
                            st.info(f"📅 **Data:** {dados.get('DATA', '')}\n\n"
                                    f"⏰ **Hora:** {dados.get('HORA', '')}\n\n"
                                    f"📍 **Partida:** {dados.get('PARTIDA', '')}\n\n"
                                    f"📏 **Distância:** {dados.get('KM TOTAL', '')}")
                        
                        with c_detalhe2:
                            st.success("**Ordem dos Destinos:**")
                            destinos = str(dados.get('ROTA', '')).split(" ➔ ")
                            for i, destino in enumerate(destinos):
                                st.write(f"{i+1}º ➔ {destino}")
                        
                        st.write("### 🛠️ Ações")
                        col_edit, col_del = st.columns(2)
                        
                        with col_edit:
                            with st.expander("✏️ Editar Informações desta Rota"):
                                with st.form("form_edita_rota"):
                                    n_data = st.text_input("Data", value=dados.get('DATA', ''))
                                    n_hora = st.text_input("Hora", value=dados.get('HORA', ''))
                                    n_partida = st.text_input("Partida", value=dados.get('PARTIDA', ''))
                                    n_rota = st.text_area("Rota (Mantenha a seta ' ➔ ' entre os locais)", value=dados.get('ROTA', ''))
                                    n_km = st.text_input("KM Total", value=dados.get('KM TOTAL', ''))
                                    
                                    if st.form_submit_button("Guardar Alterações"):
                                        try:
                                            aba_historico.update(f"A{linha_alvo}:E{linha_alvo}", [[n_data, n_hora, n_partida, n_rota, n_km]])
                                            buscar_historico.clear() # Limpa o cache após editar
                                            st.success("Rota atualizada com sucesso no banco de dados!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Erro ao atualizar: {e}")
                        
                        with col_del:
                            if st.button("🗑️ Excluir esta Rota Definitivamente", type="primary"):
                                try:
                                    aba_historico.delete_rows(linha_alvo)
                                    buscar_historico.clear() # Limpa o cache após apagar
                                    st.warning("A rota foi apagada do histórico.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro ao excluir: {e}")
            
    except Exception as e:
        st.error(f"⚠️ Ocorreu um erro ao ler o histórico. Verifique se a aba 'historico_rotas' possui as colunas exatas: DATA | HORA | PARTIDA | ROTA | KM TOTAL. Detalhe: {e}")

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

        # --- NOVA ETAPA 1 COM SETAS DE ORDENAÇÃO ---
        elif st.session_state.etapa_rota == 1:
            st.subheader("📋 Rota Provisória (Ajuste a Sequência se Necessário)")
            st.info("Esta é a sequência mais curta sugerida pelo GPS. **Use as setas ⬆️ e ⬇️ para subir ou descer um local e furar a fila, caso haja uma urgência.**")
            
            # Cabeçalhos da Tabela
            hc1, hc2, hc3, hc4, hc5 = st.columns([0.8, 1.2, 1, 3, 3])
            hc1.write("**ORDEM**")
            hc2.write("**AÇÃO**")
            hc3.write("**URGÊNCIA**")
            hc4.write("**LOCAL**")
            hc5.write("**ENDEREÇO**")
            st.markdown("---")
            
            # Renderiza cada local como uma linha com botões
            for i, item in enumerate(st.session_state.rota_provisoria):
                c1, c2, c3, c4, c5 = st.columns([0.8, 1.2, 1, 3, 3])
                
                # Número da Ordem
                c1.markdown(f"<h4 style='margin-top:0px;'>{i+1}º</h4>", unsafe_allow_html=True)
                
                # Botões de Setas
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
                
                # Dados do Local
                c3.write("🚨 SIM" if item["urgente"] else "")
                c4.write(f"{item['nome']}\n\n*(Tarefa: {item['missao']})*")
                c5.write(item["endereco"])
                
                st.markdown("---")
            
            st.write("") # Espaço em branco
            
            # Botões de Confirmação
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Confirmar Sequência e Finalizar Rota", type="primary"):
                    with st.spinner("A consolidar a rota final e a calcular a distância exata..."):
                        # Como as setas já ajustaram a ordem direto na memória, basta avançar
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
                        st.session_state.historico_salvo = True
                    except Exception as e:
                        st.warning("A rota foi gerada no ecrã, mas houve uma falha ao arquivar no histórico.")
                
                if st.button("🔄 Planejar Nova Rota"):
                    st.session_state.etapa_rota = 0
                    st.session_state.historico_salvo = False
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Falha ao processar rota final: {e}")

elif aba == "📊 Relatórios de Rotas":
    st.header("Histórico e Gestão de Rotas")
    
    try:
        dados_historico = aba_historico.get_all_records()
        
        if not dados_historico:
            st.info("Nenhuma rota foi gerada e gravada ainda.")
        else:
            df_hist = pd.DataFrame(dados_historico)
            
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
            
            st.divider()
            
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
                                        st.success("Rota atualizada com sucesso no banco de dados!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao atualizar: {e}")
                    
                    with col_del:
                        if st.button("🗑️ Excluir esta Rota Definitivamente", type="primary"):
                            try:
                                aba_historico.delete_rows(linha_alvo)
                                st.warning("A rota foi apagada do histórico.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir: {e}")
            
    except Exception as e:
        st.error(f"⚠️ Ocorreu um erro ao ler o histórico. Verifique se a aba 'historico_rotas' possui as colunas exatas: DATA | HORA | PARTIDA | ROTA | KM TOTAL. Detalhe: {e}")

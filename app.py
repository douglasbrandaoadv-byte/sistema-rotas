import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import googlemaps
import urllib.parse
from datetime import datetime
import pytz
import streamlit.components.v1 as components
import base64
import os

# Configuração de ecrã para ocupar toda a largura
st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide", page_icon="🏢")

# ==========================================================
# ESTILIZAÇÃO VISUAL (CSS) - PALETA RENOVE
# ==========================================================
COR_ESCURA = "#313753"  # Azul Marinho da Logo
COR_CLARA = "#4D648D"   # Azul Aço da Logo

st.markdown(f"""
<style>
    /* Cores dos Cabeçalhos */
    h1, h2, h3, h4, h5, h6 {{
        color: {COR_ESCURA} !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }}
    
    /* Fundo do Menu Lateral */
    [data-testid="stSidebar"] {{
        background-color: #f4f6f9;
        border-right: 2px solid {COR_CLARA};
    }}
    
    /* Cor principal de destaque (Métricas, links) */
    a {{ color: {COR_CLARA}; font-weight: bold; }}
    [data-testid="stMetricValue"] {{ color: {COR_ESCURA} !important; }}
    
    /* Personalização das Abas (Tabs) */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {{
        font-size: 16px;
        font-weight: 600;
        color: {COR_ESCURA};
    }}
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-bottom-color: {COR_CLARA} !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO OFICIAL GOOGLE ---
@st.cache_resource(show_spinner=False)
def conectar_google():
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    URL_PLANILHA = st.secrets["URL_PLANILHA"]
    cliente_gmaps = googlemaps.Client(key=API_KEY)
    
    credenciais_dict = dict(st.secrets["credenciais_google"])
    credenciais_dict["private_key"] = credenciais_dict["private_key"].replace("\\n", "\n")
    
    gc = gspread.service_account_from_dict(credenciais_dict)
    plan = gc.open_by_url(URL_PLANILHA)
    
    a_banco = plan.worksheet("locais")
    a_historico = plan.worksheet("historico_rotas")
    a_veiculo = plan.worksheet("historico_veiculo")
    
    return cliente_gmaps, a_banco, a_historico, a_veiculo

try:
    gmaps, aba_banco, aba_historico, aba_veiculo = conectar_google()
except Exception as e:
    st.error(f"⚠️ Erro ao aceder ao sistema do Google: {e}")
    st.stop()

# --- SISTEMA DE CACHE ---
@st.cache_data(ttl=600, show_spinner=False)
def buscar_dados():
    try:
        registos = aba_banco.get_all_records()
        df = pd.DataFrame(registos)
        df.columns = df.columns.str.upper() 
        return df
    except:
        return pd.DataFrame(columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"])

def salvar_dados(df):
    aba_banco.clear()
    set_with_dataframe(aba_banco, df)
    buscar_dados.clear()

@st.cache_data(ttl=600, show_spinner=False)
def buscar_historico():
    try: return aba_historico.get_all_records()
    except: return []

@st.cache_data(ttl=600, show_spinner=False)
def buscar_veiculo():
    try: return aba_veiculo.get_all_records()
    except: return []

# --- CONTROLO DE ACESSO ---
if st.query_params.get("acesso") == "permitido":
    st.session_state.logado = True
elif 'logado' not in st.session_state:
    st.session_state.logado = False

if 'lote_key' not in st.session_state: st.session_state.lote_key = 0

if not st.session_state.logado:
    st.markdown(f"<h1 style='text-align: center; color: {COR_ESCURA};'>🔐 Acesso Restrito</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try:
            st.image("Renove logo PNG.png", use_container_width=True)
        except:
            pass
        if st.text_input("Senha", type="password") == "admin123":
            if st.button("Entrar no Sistema", type="primary", use_container_width=True):
                st.session_state.logado = True
                st.query_params["acesso"] = "permitido"
                st.rerun()
    st.stop()

# ==========================================================
# MENU LATERAL - LOGOMARCA E NAVEGAÇÃO
# ==========================================================
if 'menu_atual' not in st.session_state:
    st.session_state.menu_atual = "📍 Gestão de Locais"

# Inserção da Logomarca no topo do menu lateral
try:
    st.sidebar.image("Renove logo PNG.png", use_container_width=True)
except Exception:
    st.sidebar.markdown(f"<h2 style='text-align: center; color: {COR_ESCURA};'>RENOVE<br><small style='font-size:12px;'>ADMINISTRADORA</small></h2>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**🧭 MENU DE NAVEGAÇÃO**")

opcoes_menu = [
    "📍 Gestão de Locais", 
    "🚚 Gerar Intinerário", 
    "📊 Relatórios de Rotas",
    "🏍️ Dados do Veículo",
    "📑 Relatório de Veículos"
]

for opcao in opcoes_menu:
    tipo_botao = "primary" if st.session_state.menu_atual == opcao else "secondary"
    if st.sidebar.button(opcao, use_container_width=True, type=tipo_botao):
        st.session_state.menu_atual = opcao
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Terminar Sessão (Limpar Cache)", use_container_width=True):
    st.session_state.logado = False
    st.query_params.clear()
    buscar_dados.clear()
    buscar_historico.clear()
    buscar_veiculo.clear()
    st.rerun()

aba = st.session_state.menu_atual

# ==========================================================
# 📍 GESTÃO DE LOCAIS
# ==========================================================
if aba == "📍 Gestão de Locais":
    st.markdown("<h1>Base de Dados de Condomínios</h1>", unsafe_allow_html=True)
    df_existente = buscar_dados()
    tab_cadastrados, tab_novo, tab_lote = st.tabs(["🏢 Empreendimentos Cadastrados", "➕ Adicionar Local", "📂 Cadastro em Lote"])

    with tab_cadastrados:
        st.info("💡 **Dica:** Utilize a caixa de pesquisa abaixo para encontrar um local. Marque a caixa ao lado do nome para **Editar** ou **Excluir**.")
        termo = st.text_input("🔍 Digite o nome, rua ou bairro para pesquisar:", "").strip().lower()
        df_display = df_existente.copy()
        
        if termo:
            mask = df_display.apply(lambda row: row.astype(str).str.lower().str.contains(termo).any(), axis=1)
            df_display = df_display[mask]
        
        df_display.insert(0, "SELECIONAR", False)
        df_editado = st.data_editor(
            df_display, 
            column_config={"SELECIONAR": st.column_config.CheckboxColumn(required=True)}, 
            disabled=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"], 
            hide_index=True, 
            use_container_width=True, 
            key="editor_locais"
        )
        sel = df_editado[df_editado["SELECIONAR"] == True]
        
        if not sel.empty:
            st.divider()
            if len(sel) == 1:
                idx = sel.index[0]
                d_orig = df_existente.loc[idx]
                st.subheader(f"✏️ Editando: {d_orig['NOME']}")
                with st.form("form_edita"):
                    c1, c2 = st.columns(2)
                    n_nome = c1.text_input("NOME DO LOCAL", value=d_orig['NOME'])
                    n_rua = c2.text_input("RUA", value=d_orig['RUA'])
                    n_num = c1.text_input("NÚMERO", value=str(d_orig['NUMERO']))
                    n_bair = c2.text_input("BAIRRO", value=d_orig['BAIRRO'])
                    n_cid = c1.text_input("CIDADE", value=d_orig['CIDADE'])
                    n_est = c2.text_input("ESTADO", value=d_orig['ESTADO'])
                    if st.form_submit_button("✅ Salvar Alterações", type="primary"):
                        df_existente.loc[idx] = [n_nome, n_rua, n_num, n_bair, n_cid, n_est]
                        salvar_dados(df_existente)
                        st.success("Informações atualizadas com sucesso!")
                        st.rerun()
            if st.button("🗑️ Excluir Selecionado(s) Definitivamente", type="secondary"):
                salvar_dados(df_existente.drop(sel.index.tolist()))
                st.rerun()

    with tab_novo:
        with st.form("novo"):
            c1, c2 = st.columns(2)
            n = c1.text_input("NOME DO LOCAL")
            r = c2.text_input("RUA")
            nu = c1.text_input("NÚMERO")
            b = c2.text_input("BAIRRO")
            if st.form_submit_button("Guardar Novo Local", type="primary"):
                salvar_dados(pd.concat([df_existente, pd.DataFrame([[n, r, nu, b, "João Pessoa", "PB"]], columns=df_existente.columns)], ignore_index=True))
                st.success("Local cadastrado!")
                st.rerun()

    with tab_lote:
        st.info("Preencha as linhas vazias e clique no botão abaixo para salvar vários locais de uma vez.")
        df_lote = st.data_editor(pd.DataFrame([["", "", "", "", "João Pessoa", "PB"]]*5, columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"]), num_rows="dynamic", key=f"lote_{st.session_state.lote_key}")
        if st.button("🚀 Cadastrar Lote em Massa", type="primary"):
            salvar_dados(pd.concat([df_existente, df_lote[df_lote["NOME"] != ""]], ignore_index=True))
            st.session_state.lote_key += 1
            st.success("Lote salvo com sucesso!")
            st.rerun()

# ==========================================================
# 🚚 GERAR INTINERÁRIO
# ==========================================================
elif aba == "🚚 Gerar Intinerário":
    st.markdown("<h1>Cálculo de Rota e Gestão de Urgências</h1>", unsafe_allow_html=True)
    df_locais = buscar_dados()
    if df_locais.empty: st.warning("Cadastre locais no menu 'Gestão de Locais' primeiro.")
    else:
        if 'etapa_rota' not in st.session_state:
            st.session_state.etapa_rota = 0
            st.session_state.rota_provisoria = []
            st.session_state.historico_salvo = False

        if st.session_state.etapa_rota == 0:
            qtd = st.number_input("Número de diligências hoje:", min_value=1, step=1)
            selecionados = []
            for i in range(int(qtd)):
                st.markdown(f"<h3 style='color:{COR_CLARA};'>Diligência {i+1}</h3>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                n_sel = c1.selectbox("Selecione o Local", df_locais['NOME'].unique(), key=f"l_{i}")
                m_sel = c2.selectbox("Tarefa", ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS", "FOLHA DE PAGAMENTO"], key=f"m_{i}")
                
                c3, c4 = st.columns([3, 1])
                obs = c3.text_input("Observações (Ex: Falar com portaria, deixar na caixa)", key=f"o_{i}")
                st.write("") 
                urg = c4.checkbox("🚨 MARCAR COMO URGENTE", key=f"u_{i}")
                
                r = df_locais[df_locais['NOME'] == n_sel].iloc[0]
                end = f"{r['RUA']}, {r['NUMERO']}, {r['BAIRRO']}, {r['CIDADE']}, {r['ESTADO']}"
                selecionados.append({"nome": n_sel, "endereco": end, "missao": m_sel, "obs": obs, "urgente": urg})
                st.divider()

            st.markdown("### Partida e Geração")
            partida = st.text_input("Ponto de Partida:", value="João Pessoa, PB")
            dest_final = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"

            if st.button("⚙️ Gerar Rota Provisória", type="primary", use_container_width=True):
                with st.spinner("Consultando GPS do Google..."):
                    try:
                        waypoints = [s['endereco'] for s in selecionados]
                        res = gmaps.directions(partida, dest_final, waypoints=waypoints, optimize_waypoints=True)
                        st.session_state.rota_provisoria = [selecionados[i] for i in res[0]['waypoint_order']]
                        st.session_state.partida = partida
                        st.session_state.etapa_rota = 1
                        st.rerun()
                    except Exception as e: st.error(f"Erro ao traçar rota: {e}")

        elif st.session_state.etapa_rota == 1:
            st.subheader("📋 Etapa de Ajuste")
            st.info("Utilize as setas para furar a fila se for necessário.")
            
            for i, item in enumerate(st.session_state.rota_provisoria):
                with st.container():
                    c1, c2, c3 = st.columns([1, 6, 2])
                    with c1:
                        st.markdown(f"<h2 style='color:{COR_CLARA};'>{i+1}º</h2>", unsafe_allow_html=True)
                        sc1, sc2 = st.columns(2)
                        if sc1.button("⬆️", key=f"u_{i}", disabled=(i==0)):
                            st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i-1] = st.session_state.rota_provisoria[i-1], st.session_state.rota_provisoria[i]
                            st.rerun()
                        if sc2.button("⬇️", key=f"d_{i}", disabled=(i==len(st.session_state.rota_provisoria)-1)):
                            st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i+1] = st.session_state.rota_provisoria[i+1], st.session_state.rota_provisoria[i]
                            st.rerun()
                    with c2:
                        st.markdown(f"**{'🚨 URGENTE: ' if item['urgente'] else ''}{item['nome']}**")
                        st.write(f"*{item['endereco']}*")
                        if item['obs']:
                            st.caption(f"📝 Obs: {item['obs']}")
                    with c3:
                        st.markdown(f"**Tarefa:**<br>{item['missao']}", unsafe_allow_html=True)
                st.divider()
            
            if st.button("✅ Confirmar Rota Oficial", type="primary", use_container_width=True):
                st.session_state.rota_final = st.session_state.rota_provisoria
                st.session_state.etapa_rota = 2
                st.rerun()

        elif st.session_state.etapa_rota == 2:
            try:
                rota = st.session_state.rota_final
                partida = st.session_state.partida
                dest_final = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"
                res = gmaps.directions(partida, dest_final, waypoints=[s['endereco'] for s in rota], optimize_waypoints=False)
                dist = f"{round(sum(l['distance']['value'] for l in res[0]['legs'])/1000, 1)} km"
                
                st.success(f"🏁 Rota Oficializada com Sucesso! Distância total: {dist}")
                st.link_button("📱 ABRIR ROTA NO GPS DO MOTOBOY", f"https://www.google.com/maps/dir/{urllib.parse.quote(partida)}/" + "/".join([urllib.parse.quote(s['endereco']) for s in rota]) + f"/{urllib.parse.quote(dest_final)}", use_container_width=True)

                st.subheader("📋 Relatório da Rota Oficial")
                
                fuso = pytz.timezone('America/Fortaleza')
                agora = datetime.now(fuso)
                
                # HTML DE IMPRESSÃO (Com as cores da Renove)
                html_imp = f"""<div style='font-family: Arial, sans-serif; font-size:16px; color:#000;'>
                <h2 style='color: {COR_ESCURA}; border-bottom: 2px solid {COR_CLARA}; padding-bottom:10px;'>ITINERÁRIO OFICIAL RENOVE</h2>
                <p><strong>Data:</strong> {agora.strftime('%d/%m/%Y às %H:%M')}<br>
                <strong>Partida:</strong> {partida}<br>
                <strong>KM Total Estimado:</strong> {dist}</p>
                <hr style='border:1px solid {COR_ESCURA};'>
                """
                
                obs_banco = []

                for i, item in enumerate(rota):
                    st.markdown(f"<h3 style='color:{COR_CLARA};'>{i+1}º - {item['nome']} {'🚨' if item['urgente'] else ''}</h3>", unsafe_allow_html=True)
                    st.write(f"**Tarefa:** {item['missao']} | **Endereço:** {item['endereco']}")
                    if item['obs']:
                        st.info(f"**Observação:** {item['obs']}")
                        obs_banco.append(f"[{item['nome']}] {item['obs']}")
                    st.divider()
                    
                    html_imp += f"""<p style='margin-bottom:15px; line-height:1.5;'>
                    <strong style='color:{COR_ESCURA};'>{i+1}º - {item['nome']}</strong> {'<strong style="color:red;">(URGENTE)</strong>' if item['urgente'] else ''}<br>
                    <strong>Tarefa:</strong> {item['missao']}<br>
                    <strong>Endereço:</strong> {item['endereco']}"""
                    
                    if item['obs']:
                        html_imp += f"<br><strong>Observação:</strong> <em>{item['obs']}</em>"
                    html_imp += "</p><hr style='border-top:1px dashed #ccc;'>"
                
                html_imp += f"<p style='color:{COR_ESCURA};'><strong>Destino Final:</strong> Sede da Administradora ({dest_final})</p></div>"
                
                b64 = base64.b64encode(html_imp.encode('utf-8')).decode('utf-8')

                col_n, col_i = st.columns(2)
                with col_n:
                    if st.button("🔄 Elaborar Nova Rota", use_container_width=True):
                        st.session_state.etapa_rota = 0
                        st.session_state.historico_salvo = False
                        st.rerun()
                with col_i:
                    components.html(f"""
                        <script>
                        function imp(){{
                            const h=decodeURIComponent(escape(window.atob('{b64}')));
                            const i=document.createElement('iframe');
                            i.style.display='none';
                            document.body.appendChild(i);
                            i.contentWindow.document.open();
                            i.contentWindow.document.write(h);
                            i.contentWindow.document.close();
                            setTimeout(()=>{{i.contentWindow.print();}}, 500);
                        }}
                        </script>
                        <button style='width:100%; height:42px; background-color:{COR_CLARA}; color:#ffffff; font-weight:bold; border-radius:8px; border:none; cursor:pointer;' onclick='imp()'>🖨️ IMPRIMIR ESTE RELATÓRIO</button>
                    """, height=50)

                if not st.session_state.historico_salvo:
                    str_obs_finais = " | ".join(obs_banco) if obs_banco else ""
                    linha_historico = [
                        agora.strftime("%d/%m/%Y"), 
                        agora.strftime("%H:%M"), 
                        partida, 
                        " ➔ ".join([f"🚨 {s['nome']}" if s['urgente'] else s['nome'] for s in rota]), 
                        dist,
                        str_obs_finais 
                    ]
                    aba_historico.append_row(linha_historico)
                    buscar_historico.clear()
                    st.session_state.historico_salvo = True
                    
            except Exception as e: st.error(f"Erro no fechamento da rota: {e}")

# ==========================================================
# 📊 RELATÓRIOS DE ROTAS
# ==========================================================
elif aba == "📊 Relatórios de Rotas":
    st.markdown("<h1>Gestão de Rotas Geradas</h1>", unsafe_allow_html=True)
    dados = buscar_historico()
    
    if len(dados) == 0: 
        st.info("Nenhuma rota registada.")
    else:
        df = pd.DataFrame(dados)
        
        if 'OBSERVAÇÕES' not in df.columns:
            df['OBSERVAÇÕES'] = ""
            
        t1, t2, t3 = st.tabs(["📋 Histórico Completo", "📈 Somatória e Agrupamentos", "⚙️ Detalhar, Editar e Imprimir"])
        
        with t1:
            st.markdown(f"<h3 style='color:{COR_CLARA};'>Visualização Geral</h3>", unsafe_allow_html=True)
            datas = df['DATA'].unique().tolist()[::-1]
            sel_data = st.selectbox("Filtrar Tabela por Data:", ["Todas as Datas"] + datas)
            df_v = df if sel_data == "Todas as Datas" else df[df['DATA'] == sel_data]
            st.dataframe(df_v, hide_index=True, use_container_width=True)
            
        with t2:
            st.markdown(f"<h3 style='color:{COR_CLARA};'>Cálculos por Seleção</h3>", unsafe_allow_html=True)
            st.caption("Marque as caixas das rotas que deseja somar.")
            df_sel = df.copy()
            df_sel.insert(0, "SELECIONAR", False)
            edit = st.data_editor(df_sel, hide_index=True, use_container_width=True, disabled=["DATA", "HORA", "PARTIDA", "ROTA", "KM TOTAL", "OBSERVAÇÕES"])
            
            selecionadas = edit[edit["SELECIONAR"] == True]
            if not selecionadas.empty:
                total_km = sum([float(str(k).replace('km','').replace(',','.').strip()) for k in selecionadas["KM TOTAL"] if k])
                st.metric("📏 Distância Total do Período Selecionado", f"{total_km:.1f} km")
        
        with t3:
            st.markdown(f"<h3 style='color:{COR_CLARA};'>Ferramentas Individuais da Rota</h3>", unsafe_allow_html=True)
            st.info("Selecione uma rota específica abaixo para visualizar detalhes, adicionar complementos ou imprimir a folha do percurso.")
            
            busca = st.text_input("🔍 Buscar por Local, Condomínio ou Data:").lower()
            opcoes = []
            for i, r in df.iterrows():
                resumo = f"Data: {r.get('DATA','')} | {r.get('KM TOTAL','')} | Locais: {str(r.get('ROTA',''))[:50]}..."
                if busca in str(r.to_dict()).lower():
                    opcoes.append((i, resumo, r))
            
            opcoes.reverse()
            
            if opcoes:
                sel = st.selectbox("Selecione a rota desejada:", opcoes, format_func=lambda x: x[1])
                idx_df, resumo, row_dados = sel
                idx_sheets = idx_df + 2 
                
                st.divider()
                st.markdown("#### Detalhamento e Edição")
                
                with st.form("form_editar_historico"):
                    c1, c2, c3 = st.columns([1, 1, 1])
                    n_data = c1.text_input("Data", value=str(row_dados.get('DATA', '')))
                    n_hora = c2.text_input("Hora", value=str(row_dados.get('HORA', '')))
                    n_km = c3.text_input("KM Total", value=str(row_dados.get('KM TOTAL', '')))
                    
                    n_partida = st.text_input("Partida", value=str(row_dados.get('PARTIDA', '')))
                    n_rota = st.text_area("Rota (Locais separados por ' ➔ ')", value=str(row_dados.get('ROTA', '')))
                    n_obs = st.text_area("Observações / Complementos", value=str(row_dados.get('OBSERVAÇÕES', '')), help="Adicione recados ou atualize o status dos locais.")
                    
                    col_s, col_d = st.columns(2)
                    with col_s:
                        if st.form_submit_button("💾 Salvar Alterações na Rota", type="primary", use_container_width=True):
                            try:
                                aba_historico.update(f"A{idx_sheets}:F{idx_sheets}", [[n_data, n_hora, n_partida, n_rota, n_km, n_obs]])
                                buscar_historico.clear()
                                st.success("Atualizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                    with col_d:
                        if st.form_submit_button("🗑️ Excluir Rota", use_container_width=True):
                            aba_historico.delete_rows(idx_sheets)
                            buscar_historico.clear()
                            st.rerun()
                
                st.markdown("#### Impressão Rápida")
                lista_locais = str(n_rota).split(" ➔ ")
                html_imp_hist = f"""<div style='font-family: Arial, sans-serif; font-size:16px; color:#000;'>
                <h2 style='color:{COR_ESCURA}; border-bottom: 2px solid {COR_CLARA}; padding-bottom:10px;'>ITINERÁRIO (REIMPRESSÃO)</h2>
                <p><strong>Data de Referência:</strong> {n_data} às {n_hora}<br>
                <strong>Partida:</strong> {n_partida}<br>
                <strong>KM Total:</strong> {n_km}</p>
                <hr style='border:1px solid {COR_ESCURA};'>
                """
                
                for idx_loc, loc in enumerate(lista_locais):
                    urg = "(URGENTE)" if "🚨" in loc else ""
                    nome_limpo = loc.replace("🚨 ", "")
                    html_imp_hist += f"<p style='margin-bottom:10px; line-height:1.5;'><strong style='color:{COR_ESCURA};'>{idx_loc+1}º - {nome_limpo}</strong> <strong style='color:red;'>{urg}</strong></p>"
                
                if n_obs:
                    html_imp_hist += f"<hr><p style='color:{COR_ESCURA};'><strong>OBSERVAÇÕES DA ROTA:</strong><br>{n_obs}</p>"
                
                html_imp_hist += "</div>"
                b64_hist = base64.b64encode(html_imp_hist.encode('utf-8')).decode('utf-8')
                
                components.html(f"""
                    <script>
                    function imp(){{
                        const h=decodeURIComponent(escape(window.atob('{b64_hist}')));
                        const i=document.createElement('iframe');
                        i.style.display='none';
                        document.body.appendChild(i);
                        i.contentWindow.document.open();
                        i.contentWindow.document.write(h);
                        i.contentWindow.document.close();
                        setTimeout(()=>{{i.contentWindow.print();}}, 500);
                    }}
                    </script>
                    <button style='width:100%; height:45px; background-color:{COR_CLARA}; color:#ffffff; font-weight:bold; border-radius:8px; border:none; cursor:pointer;' onclick='imp()'>🖨️ IMPRIMIR ESTA ROTA</button>
                """, height=50)

# ==========================================================
# 🏍️ DADOS DO VEÍCULO E RELATÓRIOS
# ==========================================================
elif aba == "🏍️ Dados do Veículo":
    st.markdown("<h1>Registo Diário da Frota</h1>", unsafe_allow_html=True)
    st.info("Preencha ao final do dia o uso e os gastos.")
    with st.form("veiculo"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Data do Registo", format="DD/MM/YYYY")
        km = c2.number_input("Odómetro (KM no painel)", min_value=0)
        
        st.write("---")
        abast = st.checkbox("Houve abastecimento neste dia?")
        v = st.number_input("Valor total do abastecimento (R$)", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("💾 Salvar Dados do Veículo", type="primary"):
            aba_veiculo.append_row([d.strftime("%d/%m/%Y"), km, "SIM" if abast else "NÃO", v])
            buscar_veiculo.clear()
            st.success("Dados da frota gravados com sucesso!")

elif aba == "📑 Relatório de Veículos":
    st.markdown("<h1>Gestão Financeira e de Rodagem</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color:{COR_CLARA};'>Cruzamento de Custos e Distância</h3>", unsafe_allow_html=True)
    periodo = st.date_input("Selecione o Período (Início e Fim):", [])
    
    if len(periodo) == 2:
        inicio, fim = periodo
        dados_v = buscar_veiculo()
        
        if len(dados_v) > 0:
            df_v = pd.DataFrame(dados_v)
            df_v['dt'] = pd.to_datetime(df_v['DATA'], format='%d/%m/%Y').dt.date
            filtrado = df_v[(df_v['dt'] >= inicio) & (df_v['dt'] <= fim)]
            
            c1, c2 = st.columns(2)
            gasto_total = sum(pd.to_numeric(filtrado['VALOR']))
            c1.metric("⛽ Gasto em Combustível no Período", f"R$ {gasto_total:.2f}")
            c2.metric("🗓️ Dias Registados", len(filtrado))
            
            st.markdown("#### Tabela de Abastecimentos Diários")
            st.dataframe(filtrado.drop(columns=['dt']), hide_index=True, use_container_width=True)
        else:
            st.warning("Não há informações de veículo para exibir neste período.")
    else:
        st.info("Selecione uma data inicial e uma data final no calendário acima para carregar o relatório.")

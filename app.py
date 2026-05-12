import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import googlemaps
import urllib.parse
import json
from datetime import datetime
import pytz
import streamlit.components.v1 as components
import base64

st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# --- CONEXÃO OFICIAL GOOGLE (BLINDADA) ---
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
    st.title("🔐 Acesso Restrito - Renove Administradora")
    if st.text_input("Senha", type="password") == "admin123":
        if st.button("Entrar"):
            st.session_state.logado = True
            st.query_params["acesso"] = "permitido"
            st.rerun()
    st.stop()

st.sidebar.success("✅ Conectado à Base de Dados")
if st.sidebar.button("Terminar Sessão"):
    st.session_state.logado = False
    st.query_params.clear()
    st.rerun()

aba = st.sidebar.radio("Navegação", [
    "📍 Gestão de Locais", 
    "🚚 Gerar Intinerário", 
    "📊 Relatórios de Rotas",
    "🏍️ Dados do Veículo",
    "📑 Relatório de Veículos"
])

# --- GESTÃO DE LOCAIS ---
if aba == "📍 Gestão de Locais":
    st.header("Base de Dados de Condomínios")
    df_existente = buscar_dados()
    tab_cadastrados, tab_novo, tab_lote = st.tabs(["🏢 Empreendimentos Cadastrados", "➕ Adicionar Local", "📂 Cadastro em Lote"])

    with tab_cadastrados:
        termo = st.text_input("🔍 Buscar Empreendimento:", "").strip().lower()
        df_display = df_existente.copy()
        if termo:
            mask = df_display.apply(lambda row: row.astype(str).str.lower().str.contains(termo).any(), axis=1)
            df_display = df_display[mask]
        
        df_display.insert(0, "SELECIONAR", False)
        df_editado = st.data_editor(df_display, column_config={"SELECIONAR": st.column_config.CheckboxColumn(required=True)}, disabled=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"], hide_index=True, use_container_width=True, key="editor_locais")
        sel = df_editado[df_editado["SELECIONAR"] == True]
        
        if not sel.empty:
            if len(sel) == 1:
                idx = sel.index[0]
                d_orig = df_existente.loc[idx]
                with st.form("form_edita"):
                    c1, c2 = st.columns(2)
                    n_nome = c1.text_input("NOME", value=d_orig['NOME'])
                    n_rua = c2.text_input("RUA", value=d_orig['RUA'])
                    n_num = c1.text_input("NÚMERO", value=str(d_orig['NUMERO']))
                    n_bair = c2.text_input("BAIRRO", value=d_orig['BAIRRO'])
                    n_cid = c1.text_input("CIDADE", value=d_orig['CIDADE'])
                    n_est = c2.text_input("ESTADO", value=d_orig['ESTADO'])
                    if st.form_submit_button("✅ Guardar"):
                        df_existente.loc[idx] = [n_nome, n_rua, n_num, n_bair, n_cid, n_est]
                        salvar_dados(df_existente)
                        st.rerun()
            if st.button("🗑️ Excluir Selecionado(s)", type="primary"):
                salvar_dados(df_existente.drop(sel.index.tolist()))
                st.rerun()

    with tab_novo:
        with st.form("novo"):
            c1, c2 = st.columns(2)
            n = c1.text_input("NOME")
            r = c2.text_input("RUA")
            nu = c1.text_input("NÚMERO")
            b = c2.text_input("BAIRRO")
            if st.form_submit_button("Guardar"):
                salvar_dados(pd.concat([df_existente, pd.DataFrame([[n, r, nu, b, "João Pessoa", "PB"]], columns=df_existente.columns)], ignore_index=True))
                st.rerun()

    with tab_lote:
        df_lote = st.data_editor(pd.DataFrame([["", "", "", "", "João Pessoa", "PB"]]*5, columns=["NOME", "RUA", "NUMERO", "BAIRRO", "CIDADE", "ESTADO"]), num_rows="dynamic", key=f"lote_{st.session_state.lote_key}")
        if st.button("🚀 Cadastrar"):
            salvar_dados(pd.concat([df_existente, df_lote[df_lote["NOME"] != ""]], ignore_index=True))
            st.session_state.lote_key += 1
            st.rerun()

# --- GERAR INTINERÁRIO ---
elif aba == "🚚 Gerar Intinerário":
    st.header("Cálculo de Rota e Gestão de Urgências")
    df_locais = buscar_dados()
    if df_locais.empty: st.warning("Cadastre locais primeiro.")
    else:
        if 'etapa_rota' not in st.session_state:
            st.session_state.etapa_rota = 0
            st.session_state.rota_provisoria = []
            st.session_state.historico_salvo = False

        if st.session_state.etapa_rota == 0:
            qtd = st.number_input("Número de diligências hoje:", min_value=1, step=1)
            selecionados = []
            for i in range(int(qtd)):
                st.markdown("---")
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                n_sel = c1.selectbox(f"Diligência {i+1}", df_locais['NOME'].unique(), key=f"l_{i}")
                m_sel = c2.selectbox("Tarefa", ["ENTREGA DE BOLETOS", "NOTIFICAÇÃO", "RECOLHER ATAS", "DOCUMENTOS", "FOLHA DE PAGAMENTO"], key=f"m_{i}")
                obs = c3.text_input("Obs", key=f"o_{i}")
                urg = c4.checkbox("🚨 URGÊNCIA", key=f"u_{i}")
                r = df_locais[df_locais['NOME'] == n_sel].iloc[0]
                end = f"{r['RUA']}, {r['NUMERO']}, {r['BAIRRO']}, {r['CIDADE']}, {r['ESTADO']}"
                selecionados.append({"nome": n_sel, "endereco": end, "missao": m_sel, "obs": obs, "urgente": urg})

            partida = st.text_input("Partida:", value="João Pessoa, PB")
            dest_final = "Rua Rodrigues de Aquino, 267, Centro, João Pessoa, PB"

            if st.button("⚙️ Gerar Rota Provisória"):
                try:
                    waypoints = [s['endereco'] for s in selecionados]
                    res = gmaps.directions(partida, dest_final, waypoints=waypoints, optimize_waypoints=True)
                    st.session_state.rota_provisoria = [selecionados[i] for i in res[0]['waypoint_order']]
                    st.session_state.partida = partida
                    st.session_state.etapa_rota = 1
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

        elif st.session_state.etapa_rota == 1:
            st.subheader("📋 Ajuste a Sequência (⬆️ ⬇️)")
            st.markdown("---")
            for i, item in enumerate(st.session_state.rota_provisoria):
                c1, c2, c3, c4 = st.columns([1, 1.5, 3, 4])
                c1.markdown(f"### {i+1}º")
                with c2:
                    sc1, sc2 = st.columns(2)
                    if sc1.button("⬆️", key=f"u_{i}", disabled=(i==0)):
                        st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i-1] = st.session_state.rota_provisoria[i-1], st.session_state.rota_provisoria[i]
                        st.rerun()
                    if sc2.button("⬇️", key=f"d_{i}", disabled=(i==len(st.session_state.rota_provisoria)-1)):
                        st.session_state.rota_provisoria[i], st.session_state.rota_provisoria[i+1] = st.session_state.rota_provisoria[i+1], st.session_state.rota_provisoria[i]
                        st.rerun()
                c3.markdown(f"**{'🚨 ' if item['urgente'] else ''}{item['nome']}**")
                c4.caption(item['endereco'])
                st.markdown("---")
            
            if st.button("✅ Confirmar Rota Oficial", type="primary"):
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
                
                st.success(f"Oficializado: {dist}")
                st.link_button("📱 Abrir GPS", f"https://www.google.com/maps/dir/{urllib.parse.quote(partida)}/" + "/".join([urllib.parse.quote(s['endereco']) for s in rota]) + f"/{urllib.parse.quote(dest_final)}")

                st.subheader("📋 Relatório da Rota Oficial")
                fuso = pytz.timezone('America/Fortaleza')
                agora = datetime.now(fuso)
                
                # HTML para Impressão Económica (com codificação correta)
                html_imp = f"""<div style='font-family:Arial; font-size:12px;'>
                <h2>INTINERÁRIO OFICIAL - {agora.strftime('%d/%m/%Y')}</h2>
                <p><strong>Partida:</strong> {partida}<br><strong>KM Total:</strong> {dist}</p><hr>"""
                
                for i, item in enumerate(rota):
                    st.write(f"**{i+1}º - {item['nome']}** {'🚨 URGENTE' if item['urgente'] else ''}")
                    st.write(f"🎯 {item['missao']} | 📍 {item['endereco']}")
                    st.divider()
                    html_imp += f"<p><strong>{i+1}º - {item['nome']}</strong> {'(URGENTE)' if item['urgente'] else ''}<br>Tarefa: {item['missao']}<br>Endereço: {item['endereco']}</p><hr>"
                
                html_imp += "</div>"
                b64 = base64.b64encode(html_imp.encode('utf-8')).decode('utf-8')

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Planejar Nova Rota", use_container_width=True):
                        st.session_state.etapa_rota = 0
                        st.session_state.historico_salvo = False
                        st.rerun()
                with col2:
                    components.html(f"""<script>function imp(){{const h=decodeURIComponent(escape(window.atob('{b64}')));const i=document.createElement('iframe');i.style.display='none';document.body.appendChild(i);i.contentWindow.document.write(h);i.contentWindow.document.close();i.contentWindow.print();}}</script><button style='width:100%; height:45px; border-radius:8px; border:1px solid #ccc; cursor:pointer' onclick='imp()'>🖨️ Imprimir Relatório</button>""", height=50)

                if not st.session_state.historico_salvo:
                    aba_historico.append_row([agora.strftime("%d/%m/%Y"), agora.strftime("%H:%M"), partida, " ➔ ".join([f"🚨 {s['nome']}" if s['urgente'] else s['nome'] for s in rota]), dist])
                    buscar_historico.clear()
                    st.session_state.historico_salvo = True
            except Exception as e: st.error(f"Erro: {e}")

# --- RELATÓRIO DE ROTAS ---
elif aba == "📊 Relatórios de Rotas":
    st.header("Histórico e Gestão de Rotas")
    dados = buscar_historico()
    if not dados: st.info("Nenhuma rota registada.")
    else:
        df = pd.DataFrame(dados)
        t1, t2, t3 = st.tabs(["📋 Histórico Geral", "📈 Relatório Agrupado", "⚙️ Detalhar e Editar"])
        
        with t1:
            datas = df['DATA'].unique().tolist()[::-1]
            sel_data = st.selectbox("Filtrar Data:", ["Todas"] + datas)
            df_v = df if sel_data == "Todas" else df[df['DATA'] == sel_data]
            st.dataframe(df_v, hide_index=True, use_container_width=True)
            
        with t2:
            st.caption("Selecione as rotas para somatória de KM:")
            df_sel = df.copy()
            df_sel.insert(0, "SELECIONAR", False)
            edit = st.data_editor(df_sel, hide_index=True, use_container_width=True)
            selecionadas = edit[edit["SELECIONAR"]]
            if not selecionadas.empty:
                total_km = sum([float(str(k).replace('km','').replace(',','.').strip()) for k in selecionadas["KM TOTAL"]])
                st.metric("Distância Total", f"{total_km:.1f} km")
        
        with t3:
            busca = st.text_input("Buscar por Local ou Data:").lower()
            opcoes = [f"{r['DATA']} - {r['ROTA'][:50]}..." for i, r in df.iterrows() if busca in str(r).lower()]
            if opcoes:
                sel_edit = st.selectbox("Escolha a rota:", opcoes)
                if st.button("🗑️ Excluir Rota"):
                    idx_del = opcoes.index(sel_edit) + 2
                    aba_historico.delete_rows(idx_del)
                    buscar_historico.clear()
                    st.rerun()

# --- DADOS DO VEÍCULO ---
elif aba == "🏍️ Dados do Veículo":
    st.header("Registo Diário")
    with st.form("veiculo"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Data", format="DD/MM/YYYY")
        km = c2.number_input("KM Inicial", min_value=0)
        abast = st.checkbox("Houve abastecimento?")
        v = st.number_input("Valor (R$)", min_value=0.0)
        if st.form_submit_button("Salvar"):
            aba_veiculo.append_row([d.strftime("%d/%m/%Y"), km, "SIM" if abast else "NÃO", v])
            buscar_veiculo.clear()
            st.success("Gravado!")

# --- RELATÓRIO DE VEÍCULOS ---
elif aba == "📑 Relatório de Veículos":
    st.header("Gestão de Frota e Custos")
    periodo = st.date_input("Selecione o Período:", [])
    if len(periodo) == 2:
        inicio, fim = periodo
        dados_v = buscar_veiculo()
        if dados_v:
            df_v = pd.DataFrame(dados_v)
            df_v['dt'] = pd.to_datetime(df_v['DATA'], format='%d/%m/%Y').dt.date
            filtrado = df_v[(df_v['dt'] >= inicio) & (df_v['dt'] <= fim)]
            st.metric("Gasto em Combustível", f"R$ {sum(pd.to_numeric(filtrado['VALOR'])):.2f}")
            st.dataframe(filtrado.drop(columns=['dt']), hide_index=True, use_container_width=True)

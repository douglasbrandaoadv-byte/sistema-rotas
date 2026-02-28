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
    return conn.read(ttl="0")

# --- SISTEMA DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Acesso Restrito - Renove Administradora")
    if st.text_input("Senha", type="password") == "admin123":
        if st.button("Entrar"):
            st.session_state.logado = True
            st.rerun()
    st.stop()

# --- MENU ---
aba = st.sidebar.radio("Navegação", ["📍 Cadastrar Locais", "🚚 Criar Rota Inteligente"])

if aba == "📍 Cadastrar Locais":
    st.header("Cadastro de Condomínios e Estabelecimentos")
    df_existente = buscar_dados()
    
    with st.form("form_novo"):
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
            st.success("Condomínio cadastrado na nuvem!")
            st.rerun()
    st.dataframe(df_existente)

elif aba == "🚚 Criar Rota Inteligente":
    st.header("Gerar Itinerário Econômico")
    df_locais = buscar_dados()
    
    if df_locais.empty:
        st.warning("Cadastre os condomínios primeiro.")
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
            with st.spinner("Calculando o melhor trajeto..."):
                enderecos_lista = [s['endereco'] for s in selecionados]
                
                # Google organiza as paradas intermediárias (optimize_waypoints=True)
                resultado = gmaps.directions(
                    partida, 
                    enderecos_lista[-1], 
                    waypoints=enderecos_lista[:-1], 
                    optimize_waypoints=True
                )
                
                ordem_otimizada = resultado[0]['waypoint_order']
                st.success("Rota calculada com a sequência mais curta!")

                # CRIAÇÃO DO RELATÓRIO COMPLETO (Waypoints + Destino Final)
                # 1. Pegamos os intermediários na ordem que o Google mandou
                paradas_finais = [selecionados[i] for i in ordem_otimizada]
                # 2. Adicionamos o último que definimos como destino final
                if len(selecionados) > 1:
                    paradas_finais.append(selecionados[-1])
                elif len(selecionados) == 1:
                    paradas_finais = [selecionados[0]]

                # Link para o Google Maps do celular
                lista_enderecos_rota = [partida] + [p['endereco'] for p in paradas_finais]
                link_final = "https://www.google.com/maps/dir/" + "/".join(lista_enderecos_rota)
                st.link_button("📱 Abrir Rota no GPS do Motoboy", link_final)

                st.subheader("📋 Relatório de Entrega")
                for i, item in enumerate(paradas_finais):
                    st.markdown(f"**{i+1}ª Parada: {item['nome']}**")
                    st.write(f"📍 {item['endereco']}")
                    st.write(f"🎯 Missão: {item['missao']} | 📝 Obs: {item['obs']}")
                    st.divider()

import streamlit as st
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import googlemaps
import urllib.parse
import json

st.set_page_config(page_title="Rota Inteligente - Renove", layout="wide")

# --- CONEXÃO OFICIAL GOOGLE (NATIVA E SEM BUGS) ---
try:
    API_KEY = st.secrets["GOOGLE_MAPS_API_KEY"]
    URL_PLANILHA = st.secrets["URL_PLANILHA"]
    gmaps = googlemaps.Client(key=API_KEY)
    
    # A CORREÇÃO ESTÁ AQUI: Lemos o JSON puro sem tentar forçar a conversão de quebras de linha
    credenciais_dict = json.loads(st.secrets["GOOGLE_JSON"])
    
    # Conectamos diretamente ao motor do Google
    gc = gspread.service_

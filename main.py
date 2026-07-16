import streamlit as st
import pandas as pd
import base64
import os
import io
import plotly.express as px  
from supabase import create_client, Client

# Configuração da página Streamlit (DEVE SER A PRIMEIRA LINHA DE CÓDIGO)
st.set_page_config(page_title="Plano de Ação - Administrativo", layout="wide")

# CONEXÃO DIRETA COM O SUPABASE
# Lembre-se de preencher com a URL e KEY corretas do seu projeto
SUPABASE_URL = "https://otlzkpjlzorxdhagqksf.supabase.co" 
SUPABASE_KEY = "sb_publishable_UtC2lBc6OwE0ZrWFpL7U9g_VuTjjjSw"

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Inicializa os estados da sessão de forma segura no topo
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'edit_item' not in st.session_state:
    st.session_state['edit_item'] = None

# Função para fazer upload de arquivos no Storage
def fazer_upload_storage(arquivo_upload):
    if arquivo_upload is not None:
        try:
            supabase = get_supabase_client()
            bytes_data = arquivo_upload.getvalue()
            nome_arquivo = f"{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_{arquivo_upload.name}"
            supabase.storage.from_("arquivos_acoes").upload(nome_arquivo, bytes_data)
            url_publica = supabase.storage.from_("arquivos_acoes").get_public_url(nome_arquivo)
            return url_publica
        except Exception as e:
            st.error(f"Erro ao subir arquivo: {e}")
            return None
    return None

# Função para salvar ou atualizar dados no Banco de Dados
def salvar_acao_no_banco(id_limpo, descricao, v_porque, v_onde, id_resp_final, prazo_str, v_como, v_quando, status, url_arq):
    try:
        supabase = get_supabase_client()
        dados_acao = {
            "descricao_acao": descricao,
            "porque": v_porque,
            "onde": v_onde,
            "id_responsavel": id_resp_final,
            "prazo": prazo_str,
            "como": v_como,
            "quando_detalhe": v_quando,
            "status": status,
            "url_arquivo": url_arq
        }
        
        if id_limpo and str(id_limpo).isdigit():
            supabase.table("Acoes").update(dados_acao).eq("id_acao", int(id_limpo)).execute()
        else:
            supabase.table("Acoes").insert(dados_acao).execute()
            
        return True, "Operação realizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar no Supabase: {str(e)}"


# --- TELA DE LOGIN FORMATO FORMULÁRIO (BLINDADO PARA NUVEM) ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.caption("📷 *[Insira o arquivo logo.png no seu GitHub]*")
            
        st.markdown("<h2 style='text-align: center;'>Acesso ao Sistema</h2>", unsafe_allow_html=True)
        
        with st.form(key="formulario_login"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            botao_enviar = st.form_submit_button("Entrar", use_container_width=True)
            
            if botao_enviar:
                if usuario_input.strip() == "admin" and senha_input.strip() == "123":
                    st.session_state['logado'] = True
                    st.success("Acesso concedido!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# ==============================================================================
# SISTEMA PRINCIPAL (SÓ CARREGA SE LOGADO)
# ==============================================================================

# --- PAINEL PRINCIPAL ---
col_tit, col_log = st.columns(2)
with col_tit:
    st.title("Plano de Ação-Administrativo")
with col_log:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("Sair (Logout)", use_container_width=True, key="btn_logout_final"):
        st.session_state['logado'] = False
        st.session_state['edit_item'] = None
        st.rerun()

# Buscar dados do banco Supabase de forma protegida
acoes = []
try:
    supabase = get_supabase_client()
    resposta = supabase.table("Acoes").select("*").order("prazo", desc=False).execute()
    acoes = resposta.data if hasattr(resposta, "data") else resposta.get('data', [])
except Exception as e:
    st.error(f"Erro ao carregar dados do Supabase: {e}")

# --- CONFIGURAÇÃO DE VALORES PADRÃO ---
valores_padrao = {
    "id": "", "descricao": "", "porque": "", "onde": "", 
    "como": "", "quando_detalhe": "", "status": "Não Iniciado", "id_responsavel": "1", "prazo": None, "url_arquivo": None
}

if st.session_state['edit_item']:
    item = st.session_state['edit_item']
    valores_padrao = {
        "id": str(item.get('id_acao', '')),
        "descricao": str(item.get('descricao_acao', '')),
        "porque": str(item.get('porque', '')) if item.get('porque') else "",
        "onde": str(item.get('onde', '')) if item.get('onde') else "",
        "id_responsavel": str(item.get('id_responsavel', '1')) if item.get('id_responsavel') else "1",
        "como": str(item.get('como', '')) if item.get('como') else "",
        "quando_detalhe": str(item.get('quando_detalhe', '')) if item.get('quando_detalhe') else "",
        "status": str(item.get('status', 'Não Iniciado')),
        "prazo": item.get('prazo'),
        "url_arquivo": item.get('url_arquivo')
    }

# --- INDICADORES GRÁFICOS E METRICAS ---
st.write("---")
st.subheader("📊 Painel de Monitoramento Geral")

total_acoes = len(acoes)
concluidas = 0
atrasadas = 0
hoje = pd.Timestamp.now().date()
status_contagem = {"Não Iniciado": 0, "Em Andamento": 0, "Concluído": 0}

if acoes:
    for a in acoes:
        status_texto = str(a.get('status', 'Não Iniciado')).strip().title()
        
        if "Andamento" in status_texto:
            status_contagem["Em Andamento"] += 1
        elif "Concluído" in status_texto or "Concluido" in status_texto:
            status_contagem["Concluído"] += 1
            concluidas += 1
        else:
            status_contagem["Não Iniciado"] += 1
            
        try:
            data_prazo = pd.to_datetime(a.get('prazo')).date()
            if data_prazo < hoje and "Concluid" not in status_texto:
                atrasadas += 1
        except:
            pass

taxa_conclusao = (concluidas / total_acoes * 100) if total_acoes > 0 else 0.0

m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📋 Total de Ações Registradas", value=f"{total_acoes} itens")
with m2:
    st.metric(label="✅ Taxa de Conclusão", value=f"{taxa_conclusao:.1f}%")
with m3:
    if atrasadas > 0:
        st.metric(label="🚨 Ações Críticas (Atrasadas)", value=f"{atrasadas} pendentes", delta="- Atenção urgente", delta_color="inverse")
    else:
        st.metric(label="🛡️ Prazos sob Controle", value="0 atrasos", delta="Em dia")

st.write("<br>", unsafe_allow_html=True)

# Gráfico Seguro usando Plotly Express
st.write("📊 **Progresso dos Planos de Ação**")

dados_barras = {
    "Status": ["Não Iniciado", "Em Andamento", "Concluído"],
    "Quantidade": [status_contagem["Não Iniciado"], status_contagem["Em Andamento"], status_contagem["Concluído"]]
}
df_barras_limpo = pd.DataFrame(dados_barras)

if df_barras_limpo["Quantidade"].sum() > 0:
    fig = px.bar(
        df_barras_limpo, 
        x="Status", 
        y="Quantidade", 
        color="Status",
        color_discrete_map={"Não Iniciado": "#ff9999", "Em Andamento": "#66b3ff", "Concluído": "#99ff99"}
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Cadastre ações para visualizar o gráfico de barras de monitoramento.")

# --- LISTAGEM DOS ITENS SALVOS COM FILTROS E EXCEL ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes:
    df_base = pd.DataFrame(acoes)
    colunas_necessarias = ["id_acao", "descricao_acao", "porque", "onde", "id_responsavel", "prazo", "como", "quando_detalhe", "status", "url_arquivo"]
    for col in colunas_necessarias:
        if col not in df_base.columns:
            df_base[col] = ""

    st.markdown("🔍 **Filtros de Busca**")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        opcoes_status = ["Todos"] + sorted(list(df_base["status"].unique()))
        status_filtrado = st.selectbox("Filtrar por Status:", opcoes_status, key="filtro_status_dinamico")
        
    with f_col2:
        opcoes_resp = ["Todos"] + sorted(list(df_base["id_responsavel"].astype(str).unique()))
        resp_filtrado = st.selectbox("Filtrar por ID do Responsável:", opcoes_resp, key="filtro_resp_dinamico")

    df_filtrado = df_base.copy()
    if status_filtrado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == status_filtrado]
    if resp_filtrado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["id_responsavel"].astype(str) == resp_filtrado]

    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        df_filtrado[colunas_necessarias].to_excel(writer, index=False, sheet_name='Planos de Ação')
    
    st.download_button(
        label="🟢 Baixar Lista Filtrada em Excel (.xlsx)",
        data=buffer_excel.getvalue(),
        file_name=f"plano_de_acao_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_download_excel_unico"
    )
    st.write("<br>", unsafe_allow_html=True)

    df_exibicao = df_filtrado[colunas_necessarias].copy()
    df_exibicao.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    
    st.write("**Ações de Gerenciamento:**")
    
    ids_disponiveis = [a for a in df_filtrado['id_acao']]
    
    # ESTRUTURA LINEAR REFEITA TOTALMENTE SEM CONFLITOS DE RECUO INDENTADO

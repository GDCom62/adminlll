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
        "id": str(item['id_acao']),
        "descricao": str(item['descricao_acao']),
        "porque": str(item['porque']) if item['porque'] else "",
        "onde": str(item['onde']) if item['onde'] else "",
        "id_responsavel": str(item['id_responsavel']) if item['id_responsavel'] else "1",
        "como": str(item['como']) if item['como'] else "",
        "quando_detalhe": str(item['quando_detalhe']) if item['quando_detalhe'] else "",
        "status": str(item['status']),
        "prazo": item['prazo'],
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
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("💡 Cadastre ações para visualizar o gráfico de barras de monitoramento.")

# --- LISTAGEM DOS ITENS SALVOS ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes:
    df_tabela = pd.DataFrame(acoes)
    colunas_necessarias = ["id_acao", "descricao_acao", "porque", "onde", "id_responsavel", "prazo", "como", "quando_detalhe", "status", "url_arquivo"]
    for col in colunas_necessarias:
        if col not in df_tabela.columns:
            df_tabela[col] = ""
            
    df_tabela = df_tabela[colunas_necessarias]
    df_tabela.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    
    st.write("**Ações de Gerenciamento:**")
    col_sel, col_btn_ed, col_btn_ex = st.columns(3)
    
    with col_sel:
        id_selecionado = st.selectbox("Selecione o ID de uma ação para modificar:", [a['id_acao'] for a in acoes], key="select_id_gerenciamento_unico")
    
    with col_btn_ed:
        if st.button("✏️ Editar Selecionado", use_container_width=True, key="btn_editar_item"):
            item_procurado = next((item for item in acoes if item["id_acao"] == id_selecionado), None)
            if item_procurado:
                st.session_state['edit_item'] = item_procurado
                st.rerun()
                
    with col_btn_ex:
        if st.button("🗑️ Excluir Selecionado", use_container_width=True, key="btn_excluir_item"):
            try:
                supabase = get_supabase_client()
                supabase.table("Acoes").delete().eq("id_acao", id_selecionado).execute()
                st.success(f"Ação ID #{id_selecionado} excluída!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")
else:
    st.info("Nenhuma ação cadastrada no sistema até o momento.")

# --- PAINEL OPERACIONAL DE CADASTRO E EDIÇÃO TOTALMENTE REESTRUTURADO ---
st.write("---")
st.subheader("📝 Painel: Registrar Informações")

if st.session_state['edit_item']:
    st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")

# Removidos os formulários internos "st.form" redundantes para evitar travamento de chaves
id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True, key="p_id")
descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"], key="p_desc")

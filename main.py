import streamlit as st
import pandas as pd
import base64
import os
import io
import plotly.express as px  # Biblioteca nativa e estável para o gráfico
from supabase import create_client, Client

# Configuração da página Streamlit (DEVE SER A PRIMEIRA LINHA DE CÓDIGO)
st.set_page_config(page_title="Plano de Ação - Administrativo", layout="wide")

# CONEXÃO DIRETA COM O SUPABASE
SUPABASE_URL = "https://supabase.co" 
SUPABASE_KEY = "sb_publishable_UtC2lBc6OwE0ZrWFpL7U9g_VuTjjjSw"

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNÇÃO ISOLADA PARA GERAR O RELATÓRIO PDF ---
def gerar_pdf_atualizado(dados_acoes):
    buffer_pdf = io.BytesIO()
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    
    doc = SimpleDocTemplate(buffer_pdf, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ADMINISTRATIVO", styles['Title']))
    elements.append(Spacer(1, 12))

    dados_pdf = [["ID", "Ação (What)", "Prazo", "Status", "Por que", "Onde", "Como", "Quando Det."]]
    for a in dados_acoes:
        dados_pdf.append([
            str(a.get('id_acao', '')), 
            str(a.get('descricao_acao', '')), 
            str(a.get('prazo', '')), 
            str(a.get('status', '')), 
            str(a.get('porque', '')), 
            str(a.get('onde', '')), 
            str(a.get('como', '')), 
            str(a.get('quando_detalhe', ''))
        ])

    # CORREÇÃO CRÍTICA DO PARÊNTESE: Larguras das 8 colunas definidas em pontos [fechando os colchetes]
    t = Table(dados_pdf, colWidths=[30, 150, 70, 80, 100, 80, 100, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer_pdf.seek(0)
    return buffer_pdf.getvalue()

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
        
        if id_limpo and id_limpo.isdigit():
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

# --- CONFIGURAÇÃO DE VALORES PADRÃO (MODO EDIÇÃO) ---
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
    
    if hasattr(resposta, "data"):
        acoes = resposta.data
    elif isinstance(resposta, dict) and "data" in resposta:
        acoes = resposta["data"]
except Exception as e:
    st.error(f"Erro ao carregar dados do Supabase: {e}")

# --- INDICADORES GRÁFICOS E METRICAS TURBINADAS ---
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
        elif "Concluido" in status_texto or "Concluído" in status_texto:
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

# Gráfico de Barras Nativo Estável
if total_acoes > 0:
    df_barras_limpo = pd.DataFrame({
        "Status": ["Não Iniciado", "Em Andamento", "Concluído"],
        "Quantidade": [status_contagem["Não Iniciado"], status_contagem["Em Andamento"], status_contagem["Concluído"]]
    }).set_index("Status")
    st.bar_chart(df_barras_limpo, y="Quantidade", color="#66b3ff")

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
    
    # Gerador de Relatório PDF Integrado (Agora sem erros de sintaxe)
    pdf_data = gerar_pdf_atualizado(acoes)
    st.download_button(
        label="📄 Gerar e Baixar Relatório (PDF)",
        data=pdf_data,
        file_name="Plano_Lavo_Levo.pdf",
        mime="application/pdf",
        key="btn_download_pdf_final",

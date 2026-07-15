import streamlit st as st
import pandas as pd
import base64
import os
import io
from datetime import datetime
from supabase import create_client, Client

# Configuração da página Streamlit (DEVE SER A PRIMEIRA LINHA DE CÓDIGO)
st.set_page_config(page_title="Plano de Ação - Administrativo", layout="wide")

# CONEXÃO DIRETA COM O SUPABASE
# Lembre-se de preencher com a URL e KEY corretas do seu projeto
SUPABASE_URL = "https://otlzkpjlzorxdhagqksf.supabase.co" 
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

    t = Table(dados_pdf, colWidths=[40, 150, 70, 70, 90, 80, 100, 100])
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

# Inicializa os estados de sessão de forma segura no topo
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# Função para fazer upload de arquivos no Storage do Supabase
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

# --- TELA DE LOGIN FORMATO BLINDADO ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.caption("📷 *[Insira o arquivo logo.png no seu GitHub]*")
            
        st.markdown("<h2 style='text-align: center;'>Acesso ao Sistema</h2>", unsafe_allow_html=True)
        
        with st.form(key="login_form_final"):
            usuario_input = st.text_input("Usuário")
            senha_input = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar", use_container_width=True)
            
            if botao_entrar:
                if usuario_input.strip() == "admin" and senha_input.strip() == "123":
                    st.session_state['logado'] = True
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
    st.stop()

# ==============================================================================
# SISTEMA PRINCIPAL (SÓ EXISTE SE ESTIVER LOGADO)
# ==============================================================================

# --- PAINEL PRINCIPAL COM BOTÃO DE LOGOUT ---
col_tit, col_log = st.columns(2)
with col_tit:
    st.title("Plano de Ação - Administrativo")
with col_log:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("Sair (Logout)", use_container_width=True, key="btn_logout_final"):
        st.session_state['logado'] = False
        st.rerun()

# 1. Buscar Ações de forma direta no Supabase
acoes = []
usuarios = []
try:
    supabase = get_supabase_client()
    resposta_acoes = supabase.table("Acoes").select("*").order("prazo", desc=False).execute()
    acoes = resposta_acoes.data if hasattr(resposta_acoes, "data") else []
except Exception as e:
    st.error(f"Erro ao carregar dados do Supabase (Tabela Acoes): {e}")

# 2. Tentar buscar usuários de forma segura (Se falhar, ativa o modo de texto manual)
modo_responsavel_manual = False
try:
    supabase = get_supabase_client()
    resposta_usuarios = supabase.table("usuarios").select("*").execute()
    usuarios = resposta_usuarios.data if hasattr(resposta_usuarios, "data") else []
except Exception:
    # Se der erro PGRST205, o aplicativo ativa o plano B automaticamente
    modo_responsavel_manual = True

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

# ==============================================================================
# FORMULÁRIO PARA SALVAR/EDITAR
# ==============================================================================
st.write("---")
st.subheader("Nova Ação / Editar Ação")

with st.form("form_acao", clear_on_submit=True):
    st.info("💡 Para criar um novo item, deixe o ID da Ação vazio. Para editar, digite o número do ID correspondente.")
    id_acao = st.text_input("ID da Ação (Somente números para editar)")
    descricao = st.text_input("O que (Ação) *")
    porque = st.text_input("Por que")
    onde = st.text_input("Onde")
    
    # Gerencia a exibição do campo de responsável baseado no banco
    dict_usuarios = {}
    if not modo_responsavel_manual and usuarios:
        for u in usuarios:
            dict_usuarios[u.get('nome', 'Sem Nome')] = u.get('id_usuario', '1')
        nome_resp = st.selectbox("Responsável (Quem) *", list(dict_usuarios.keys()))
    else:
        # PLANO B: Se a tabela não existir, vira um campo numérico simples (Evita o erro PGRST205)
        responsavel_manual_id = st.text_input("Código do Responsável (Digite o ID numérico do responsável) *", value="1")
    
    prazo = st.date_input("Prazo *", value=datetime.now().date())
    como = st.text_input("Como")
    quando_detalhe = st.text_input("Quando (Detalhe)")
    status = st.selectbox("Status", ["Não Iniciado", "Em Andamento", "Concluído"])
    arquivo_evidencia = st.file_uploader("Anexar evidência ou documento (Opcional)", type=["png", "jpg", "pdf", "docx"])
    
    submit = st.form_submit_button("Salvar Ação")
    
    if submit:
        id_limpo = id_acao.strip()
        if id_limpo != "" and not id_limpo.isdigit():
            st.error("Erro: O ID da Ação precisa ser um número inteiro válido (ex: 1, 5, 12).")
        elif not descricao:
            st.error("A descrição (O que) é obrigatória.")
        else:
            # Captura o ID correto do responsável dependendo do modo ativo
            if not modo_responsavel_manual and dict_usuarios:
                id_resp = str(dict_usuarios.get(nome_resp))
            else:
                id_resp = responsavel_manual_id.strip() if responsavel_manual_id.strip().isdigit() else "1"
            
            url_doc = None
            if arquivo_evidencia:
                url_doc = fazer_upload_storage(arquivo_evidencia)
                
            dados_acao = {
                "descricao_acao": descricao,
                "porque": porque,
                "onde": onde,
                "id_responsavel": id_resp,
                "prazo": prazo.strftime('%Y-%m-%d'),
                "como": como,
                "quando_detalhe": quando_detalhe,
                "status": status,
                "url_arquivo": url_doc
            }
            
            try:

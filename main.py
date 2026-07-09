import streamlit as st
import pandas as pd
import base64
import os
import io
from supabase import create_client, Client

# Configuração da página Streamlit (DEVE SER A PRIMEIRA LINHA)
st.set_page_config(page_title="Plano de Ação Lavo e Levo", layout="wide")

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

# --- BARRA LATERAL (SIDEBAR) COM FILTROS AVANÇADOS ---
st.sidebar.header("🔍 Filtros Avançados")

# Buscar dados do banco Supabase de forma protegida
acoes = []
try:
    supabase = get_supabase_client()
    resposta = supabase.table("Acoes").select("*").order("prazo", desc=False).execute()
    acoes = resposta.data
except Exception as e:
    st.error(f"Erro ao carregar dados do Supabase: {e}")

# Filtro de Status na Sidebar
filtro_status = st.sidebar.multiselect(
    "Filtrar por Status:", 
    ["Não Iniciado", "Em Andamento", "Concluído"], 
    default=["Não Iniciado", "Em Andamento", "Concluído"]
)

# Filtro de Responsável na Sidebar
responsáveis_disponiveis = sorted(list(set([str(a.get('id_responsavel', '1')) for a in acoes]))) if acoes else ["Todos"]
filtro_resp = st.sidebar.selectbox("Filtrar por ID do Responsável:", ["Todos"] + responsáveis_disponiveis)

# Aplicar os Filtros na lista de ações
acoes_filtradas = acoes
if acoes:
    if filtro_status:
        acoes_filtradas = [a for a in acoes_filtradas if str(a.get('status', 'Não Iniciado')).strip().title() in [s.title() for s in filtro_status]]
    if filtro_resp != "Todos":
        acoes_filtradas = [a for a in acoes_filtradas if str(a.get('id_responsavel', '1')) == filtro_resp]

# Botão de Logout na lateral
st.sidebar.write("---")
if st.sidebar.button("🚪 Sair do Sistema (Logout)", use_container_width=True):
    st.session_state['logado'] = False
    st.session_state['edit_item'] = None
    st.rerun()

# --- TÍTULO DO PAINEL PRINCIPAL ---
st.title("Plano de Ação Lavo e Levo")

# --- PAINEL DE MONITORAMENTO E MÉTRICAS ---
st.write("---")
st.subheader("📊 Painel de Monitoramento Geral")

# Dicionário de contagem criado corretamente no início do bloco
status_contagem = {"Não Iniciado": 0, "Em Andamento": 0, "Concluído": 0}
total_acoes = len(acoes_filtradas)
concluidas = 0
atrasadas = 0
hoje = pd.Timestamp.now().date()

if acoes_filtradas:
    for a in acoes_filtradas:
        status_texto = str(a.get('status', 'Não Iniciado')).strip().title()
        
        # Faz a contagem correta para o gráfico de barras
        if "Andamento" in status_texto:
            status_contagem["Em Andamento"] += 1
        elif "Concluido" in status_texto or "Concluído" in status_texto:
            status_contagem["Concluído"] += 1
            concluidas += 1
        else:
            status_contagem["Não Iniciado"] += 1
            
        # Calcula se está atrasado
        try:
            data_prazo = pd.to_datetime(a.get('prazo')).date()
            if data_prazo < hoje and "Concluid" not in status_texto:
                atrasadas += 1
        except:
            pass

taxa_conclusao = (concluidas / total_acoes * 100) if total_acoes > 0 else 0.0

# Exibição das Métricas em 3 colunas
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📋 Total de Ações Filtradas", value=f"{total_acoes} itens")
with m2:
    st.metric(label="✅ Taxa de Conclusão", value=f"{taxa_conclusao:.1f}%")
with m3:
    if atrasadas > 0:
        st.metric(label="🚨 Ações Críticas (Atrasadas)", value=f"{atrasadas} pendentes", delta="- Atenção urgente", delta_color="inverse")
    else:
        st.metric(label="🛡️ Prazos sob Controle", value="0 atrasos", delta="Em dia")

st.write("<br>", unsafe_allow_html=True)

# --- GRÁFICO DE BARRAS NATIVO E SEGURO ---
if total_acoes > 0:
    df_barras_limpo = pd.DataFrame({
        "Status": ["Não Iniciado", "Em Andamento", "Concluído"],
        "Quantidade": [status_contagem["Não Iniciado"], status_contagem["Em Andamento"], status_contagem["Concluído"]]
    })
    
    st.bar_chart(
        df_barras_limpo, 
        x="Status", 
        y="Quantidade", 
        color="Status",
        color_config={
            "Não Iniciado": "#ff9999",
            "Em Andamento": "#66b3ff",
            "Concluído": "#99ff99"
        }
    )
else:
    st.info("💡 Nenhuma ação corresponde aos filtros selecionados na barra lateral.")

# --- LISTAGEM DOS ITENS SALVOS ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes_filtradas:
    df_tabela = pd.DataFrame(acoes_filtradas)
    colunas_necessarias = ["id_acao", "descricao_acao", "porque", "onde", "id_responsavel", "prazo", "como", "quando_detalhe", "status", "url_arquivo"]
    for col in colunas_necessarias:
        if col not in df_tabela.columns:
            df_tabela[col] = ""
            
    df_tabela = df_tabela[colunas_necessarias]
    
    # Marcador de alerta visual de atraso na tabela
    prazos_com_alerta = []
    for _, linha in df_tabela.iterrows():
        try:
            data_prazo = pd.to_datetime(linha['prazo']).date()
            if data_prazo < hoje and str(linha['status']).strip().lower() != "concluído":
                prazos_com_alerta.append(f"🚨 {linha['prazo']} (Atrasado)")
            else:
                prazos_com_alerta.append(str(linha['prazo']))
        except:
            prazos_com_alerta.append(str(linha['prazo']))
            
    df_tabela['prazo'] = prazos_com_alerta
    df_tabela.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    
    # Relatório em Excel
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        df_tabela.to_excel(writer, index=False, sheet_name='Plano de Ação')
    
    st.download_button(
        label="📥 Baixar Relatório Filtrado (Excel)",
        data=buffer_excel.getvalue(),
        file_name="Plano_de_Acao_Lavo_Levo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        # df_tabela.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    
    # --- ÁREA DE EXPORTAÇÃO E DOWNLOADS ---
    col_down1, col_down2 = st.columns(2)
    
    with col_down1:
        # 1. Relatório em Excel (openpyxl)
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df_tabela.to_excel(writer, index=False, sheet_name='Plano de Ação')
        
        st.download_button(
            label="📥 Baixar Relatório Filtrado (Excel)",
            data=buffer_excel.getvalue(),
            file_name="Plano_de_Acao_Lavo_Levo.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_down2:
        # 2. Relatório em PDF (ReportLab) Reativado
        # Criamos uma função rápida interna para reconstruir o PDF com base nos filtros atuais
        def gerar_pdf_atualizado(dados_acoes):
            buffer_pdf = io.BytesIO()
            from reportlab.lib.pagesizes import landscape, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
            
            doc = SimpleDocTemplate(buffer_pdf, pagesize=landscape(A4))
            elements = []
            styles = getSampleStyleSheet()
            elements.append(Paragraph("PLANO DE AÇÃO ADMINISTRATIVO - LAVO E LEVO", styles['Title']))
            elements.append(Spacer(1, 12))

            # Cabeçalho estruturado do PDF
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

            # Configura larguras das colunas para caber na folha A4 em paisagem
            t = Table(dados_pdf, colWidths=[40, 160, 70, 80, 120, 100, 120, 100])
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

        # Renderiza o botão de download de PDF se houver registros
        pdf_data = gerar_pdf_atualizado(acoes_filtradas)
        st.download_button(
            label="📄 Gerar e Baixar Relatório (PDF)",
            data=pdf_data,
            file_name="Plano_Lavo_Levo.pdf",
            mime="application/pdf",
            key="btn_download_pdf_final",
            use_container_width=True
        )

    # Botões de Manutenção
    st.write("**Ações de Gerenciamento:**")
    col_sel, col_btn_ed, col_btn_ex = st.columns(3)
    
    with col_sel:
        id_selecionado = st.selectbox("Selecione o ID de uma ação para modificar:", [a['id_acao'] for a in acoes_filtradas], key="select_id_manutencao")
    
    with col_btn_ed:
        if st.button("✏️ Editar Selecionado", use_container_width=True):
            item_procurado = next((item for item in acoes if item["id_acao"] == id_selecionado), None)
            if item_procurado:
                st.session_state['edit_item'] = item_procurado
                st.rerun()
                

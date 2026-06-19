import streamlit as st
import sqlite3
import pandas as pd
import base64
import os
import io

# Bibliotecas para geração de PDF
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Configuração da página Streamlit
st.set_page_config(page_title="Plano de Ação Lavo e Levo", layout="wide")

# CONFIGURAÇÃO DO LOGIN FIXO
USUARIO_FIXO = "admin"
SENHA_FIXA = "123"

# CONEXÃO LOCAL COM SQLITE
def get_db_connection():
    conn = sqlite3.connect("banco_plano_acao_local.db")
    conn.row_factory = sqlite3.Row
    return conn

# Criação automática da tabela local se não existir
def inicializar_banco():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Acoes (
            id_acao INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao_acao TEXT NOT NULL,
            porque TEXT,
            onde TEXT,
            id_responsavel INTEGER,
            prazo TEXT,
            como TEXT,
            quando_detalhe TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

# Função para salvar ou atualizar dados no SQLite
def salvar_acao_no_banco(id_limpo, descricao, v_porque, v_onde, id_resp_final, prazo_str, v_como, v_quando, status):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if id_limpo and id_limpo.isdigit():
            # Query de Edição (UPDATE)
            query = """UPDATE Acoes SET 
                       descricao_acao=?, porque=?, onde=?, id_responsavel=?, 
                       prazo=?, como=?, quando_detalhe=?, status=? 
                       WHERE id_acao=?"""
            valores = (descricao, v_porque, v_onde, id_resp_final, prazo_str, v_como, v_quando, status, int(id_limpo))
            cursor.execute(query, valores)
        else:
            # Query de Criação (INSERT)
            query = """INSERT INTO Acoes 
                       (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
            valores = (descricao, v_porque, v_onde, id_resp_final, prazo_str, v_como, v_quando, status)
            cursor.execute(query, valores)
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Operação realizada com sucesso!"
    except Exception as e:
        return False, str(e)

# Função para gerar PDF
def gerar_pdf(acoes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ADMINISTRATIVO", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [["ID", "Ação (What)", "Prazo", "Status", "Por que", "Onde", "Como", "Quando Det."]]
    for a in acoes:
        data.append([
            str(a['id_acao']), str(a['descricao_acao']), str(a['prazo']), 
            str(a['status']), str(a['porque']), str(a['onde']), 
            str(a['como']), str(a['quando_detalhe'])
        ])

    # CORREÇÃO DEFINITIVA: Valores numéricos de larguras adicionados para não quebrar a compilação
    t = Table(data, colWidths=[40, 150, 70, 80, 120, 100, 120, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'edit_item' not in st.session_state:
    st.session_state['edit_item'] = None

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.caption("📷 *[Insira o arquivo logo.png no seu GitHub]*")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b2:
        st.markdown("<h2 style='text-align: center;'>Acesso ao Sistema</h2>", unsafe_allow_html=True)
        usuario = st.text_input("Usuário", key="login_user")
        senha = st.text_input("Senha", type="password", key="login_pass")
        
        if st.button("Entrar", use_container_width=True, key="btn_entrar"):
            if usuario == USUARIO_FIXO and senha == SENHA_FIXA:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# --- PAINEL PRINCIPAL ---
col_tit, col_log = st.columns(2)
with col_tit:
    st.title("Plano de Ação Lavo e Levo")
with col_log:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("Sair (Logout)", use_container_width=True, key="btn_logout"):
        st.session_state['logado'] = False
        st.session_state['edit_item'] = None
        st.rerun()

# Buscar dados do banco local SQLite
acoes = []
erro_banco = None
try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id_acao, descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status FROM Acoes ORDER BY prazo ASC")
    acoes = [dict(row) for row in cursor.fetchall()]
    conn.close()
except Exception as e:
    erro_banco = str(e)

if erro_banco:
    st.error(f"Erro ao carregar banco de dados: {erro_banco}")

# --- INDICADORES GRÁFICOS ---
st.write("---")
st.subheader("📊 Gráfico de Monitoramento de Status")

status_contagem = {"Não Iniciado": 0, "Em Andamento": 0, "Concluído": 0}
if acoes:
    for a in acoes:
        status_atual = a['status']
        if status_atual in status_contagem:
            status_contagem[status_atual] += 1

df_grafico = pd.DataFrame(list(status_contagem.items()), columns=["Status", "Quantidade"])
st.bar_chart(df_grafico, x="Status", y="Quantidade", color="#1f77b4")

if acoes:
    pdf_data = gerar_pdf(acoes)
    st.download_button(
        label="📄 Gerar e Baixar PDF",
        data=pdf_data,
        file_name="Plano_Lavo_Levo.pdf",
        mime="application/pdf",
        key="btn_download_pdf"
    )

# --- LISTAGEM DOS ITENS SALVOS ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes:
    df_tabela = pd.DataFrame(acoes)
    df_tabela.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status"]
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)
    
    st.write("**Ações de Gerenciamento:**")
    col_sel, col_btn_ed, col_btn_ex = st.columns(3)
    
    with col_sel:
        id_selecionado = st.selectbox("Selecione o ID de uma ação para modificar:", [a['id_acao'] for a in acoes], key="select_id_manutencao")
    
    with col_btn_ed:
        if st.button("✏️ Editar Selecionado", use_container_width=True, key="btn_editar_item"):
            item_procurado = next((item for item in acoes if item["id_acao"] == id_selecionado), None)
            if item_procurado:
                st.session_state['edit_item'] = item_procurado
                st.rerun()
                
    with col_btn_ex:
        if st.button("🗑️ Excluir Selecionado", use_container_width=True, key="btn_excluir_item"):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Acoes WHERE id_acao = ?", (id_selecionado,))
                conn.commit()
                conn.close()
                st.success(f"Ação ID #{id_selecionado} excluída com sucesso!")
                if st.session_state['edit_item'] and st.session_state['edit_item']['id_acao'] == id_selecionado:
                    st.session_state['edit_item'] = None
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")
else:
    st.info("Nenhuma ação cadastrada no sistema local até o momento.")

st.write("---")

# --- CONFIGURAÇÃO DE VALORES PADRÃO ---
valores_padrao = {
    "id": "", "descricao": "", "porque": "", "onde": "", 
    "como": "", "quando_detalhe": "", "status": "Não Iniciado", "id_responsavel": "1", "prazo": None
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
        "prazo": item['prazo']
    }
    st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")
    
    if st.button("❌ Cancelar Modo Edição e Voltar ao Novo Cadastro", use_container_width=True, key="btn_cancelar_edicao"):
        st.session_state['edit_item'] = None
        st.rerun()

# --- PAINEL OPERACIONAL ---
st.subheader("Painel: Registrar Informações")

id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True, key="input_id")
descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"], key="input_desc")
porque = st.text_input("Por que", value=valores_padrao["porque"], key="input_porque")
onde = st.text_input("Onde", value=valores_padrao["onde"], key="input_onde")
responsavel_id_input = st.text_input("Código do Responsável (ID)", value=valores_padrao["id_responsavel"], key="input_resp")

prazo_val = pd.to_datetime(valores_padrao["prazo"]).date() if valores_padrao["prazo"] else pd.Timestamp.now().date()
prazo = st.date_input("Prazo *", value=prazo_val, key="input_prazo")


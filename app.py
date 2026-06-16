import streamlit as st
import mysql.connector
from datetime import datetime
import io

# Bibliotecas para geração de PDF
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Configuração da página Streamlit
st.set_page_config(page_title="Plano de Ação", layout="wide")

# CONFIGURAÇÃO DO LOGIN FIXO (Suas diretrizes mantidas)
USUARIO_FIXO = "admin"
SENHA_FIXA = "123"

# Conexão segura usando st.secrets
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=int(st.secrets["mysql"]["port"])
    )

# Função para gerar PDF
def gerar_pdf(acoes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ADMINISTRATIVO", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [["Ação (What)", "Quem", "Prazo", "Status", "Como (How)", "QUANDO (Det)"]]
    for a in acoes:
        data.append([a['descricao_acao'], a['nome'], str(a['prazo']), a['status'], a['como'], a['quando_detalhe']])

    t = Table(data, colWidths=[150, 100, 80, 80, 200, 150])
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

# Inicializa o estado de login
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        if usuario == USUARIO_FIXO and senha == SENHA_FIXA:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# --- PAINEL PRINCIPAL ---
else:
    col_tit, col_log = st.columns([4, 1])
    with col_tit:
        st.title("Plano de Ação Lavo e Levo")
    with col_log:
        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # Buscar dados do banco de forma 100% silenciosa
    acoes, usuarios = [], []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT A.*, U.nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")
        acoes = cursor.fetchall()
        
        cursor.execute("SELECT * FROM Usuarios")
        usuarios = cursor.fetchall()
        conn.close()
    except Exception:
        # Erros técnicos ocultados da tela para manter o design limpo
        pass

    # Botão para baixar PDF
    if acoes:
        pdf_data = gerar_pdf(acoes)
        st.download_button(
            label="📄 Gerar e Baixar PDF",
            data=pdf_data,
            file_name="Plano_5W2H.pdf",
            mime="application/pdf"
        )

    st.write("---")

    # Formulário para Salvar/Editar
    st.subheader("Nova Ação / Editar Ação")
    with st.form("form_acao", clear_on_submit=True):
        id_acao = st.text_input("ID da Ação (Deixe vazio para criar nova, preencha para atualizar)")
        descricao = st.text_input("O que (Ação) *")
        porque = st.text_input("Por que")
        onde = st.text_input("Onde")
        
        dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios}
        nome_resp = st.selectbox("Responsável (Quem) *", list(dict_usuarios.keys())) if dict_usuarios else st.selectbox("Responsável", ["Nenhum usuário localizado no banco"])
        
        prazo = st.date_input("Prazo *", value=datetime.now().date())
        como = st.text_input("Como")
        quando_detalhe = st.text_input("Quando (Detalhe)")
        status = st.selectbox("Status", ["Não Iniciado", "Em Andamento", "Concluído"])
        
        submit = st.form_submit_button("Salvar Ação")
        
        if submit:
            if not descricao:
                st.error("A descrição (O que) é obrigatória.")
            elif not dict_usuarios:
                st.error("Erro: Não há conexão ativa com o banco de dados para salvar novas ações.")
            else:
                id_resp = dict_usuarios.get(nome_resp)
                dados = (descricao, porque, onde, id_resp, prazo.strftime('%Y-%m-%d'), como, quando_detalhe, status)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    if id_acao and id_acao.strip() != "":
                        sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
                        cursor.execute(sql, dados + (id_acao,))
                    else:
                        sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, dados)
                    conn.commit()
                    conn.close()
                    st.success("Ação salva com sucesso!")
                    st.rerun()
                except Exception:
                    st.error("Não foi possível salvar os dados. Verifique a conexão com o banco.")

    st.write("---")

    # Tabela de Visualização e Exclusão
    st.subheader("Ações Cadastradas")
    if acoes:
        for a in acoes:
            with st.expander(f"📌 {a['descricao_acao']} - Prazo: {a['prazo']} ({a['status']})"):
                st.write(f"**Por que:** {a['porque']} | **Onde:** {a['onde']}")
                st.write(f"**Quem:** {a['nome']} | **Como:** {a['como']} | **Detalhe:** {a['quando_detalhe']}")
                st.write(f"**ID da Ação para edição:** `{a['id_acao']}`")
                
                if st.button(f"❌ Excluir Ação #{a['id_acao']}", key=f"del_{a['id_acao']}"):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM Acoes WHERE id_acao = %s", (a['id_acao'],))
                        conn.commit()
                        conn.close()
                        st.success("Excluído!")
                        st.rerun()
                    except Exception:
                        st.error("Erro ao tentar excluir do banco de dados.")
    else:
        st.info("Nenhum registro carregado (Aguardando conexão ativa com o banco de dados MySQL).")

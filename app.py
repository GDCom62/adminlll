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

# CONFIGURAÇÃO DO LOGIN FIXO
USUARIO_FIXO = "admin"
SENHA_FIXA = "123"

# CONEXÃO DIRETA COM A CLEVER CLOUD (Preencha aqui com os dados reais)
def get_db_connection():
    return mysql.connector.connect(
        host="b7dxmekynipigcv1sftu-mysql.services.clever-cloud.com",
        user="uaoxaabon9ifpx5x",
        password="vDf6RJjOb2Bt16XX3YOg",
        database="b7dxmekynipigcv1sftu",
        port=3306
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

    # Buscar dados do banco de forma resiliente (Testa letras maiúsculas e minúsculas)
    acoes, usuarios = [], []
    erro_banco = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Tenta buscar os usuários (testando minúsculo se falhar)
        try:
            cursor.execute("SELECT * FROM Usuarios")
            usuarios = cursor.fetchall()
        except Exception:
            cursor.execute("SELECT * FROM usuarios")
            usuarios = cursor.fetchall()
            
        # Tenta buscar as ações
        try:
            cursor.execute("SELECT A.*, U.nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")
            acoes = cursor.fetchall()
        except Exception:
            cursor.execute("SELECT a.*, u.nome FROM acoes a JOIN usuarios u ON a.id_responsavel = u.id_usuario ORDER BY a.prazo ASC")
            acoes = cursor.fetchall()
            
        conn.close()
    except Exception as e:
        erro_banco = str(e)

    # Exibe o erro real de conexão se houver, ajudando a descobrir o problema
    if erro_banco:
        st.error(f"Erro de conexão com a Clever Cloud: {erro_banco}")

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
        
        dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios or u.get('nome') and [{'nome': u['nome'], 'id_usuario': u['id_usuario']} for u in usuarios]}
        # Garante compatibilidade de chaves
        if usuarios and 'nome' in usuarios[0]:
            dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios}
        elif usuarios and 'NOME' in usuarios[0]:
            dict_usuarios = {u['NOME']: u['ID_USUARIO'] for u in usuarios}
            
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
                    
                    # Detecta o nome correto da tabela para salvar
                    tabela_acoes = "Acoes"
                    try:
                        cursor.execute("SELECT 1 FROM Acoes LIMIT 1")
                    except Exception:
                        tabela_acoes = "acoes"

                    if id_acao and id_acao.strip() != "":
                        if tabela_acoes == "Acoes":
                            sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
                        else:
                            sql = "UPDATE acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
                        cursor.execute(sql, dados + (id_acao,))
                    else:
                        if tabela_acoes == "Acoes":
                            sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        else:
                            sql = "INSERT INTO acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, dados)
                        
                    conn.commit()
                    conn.close()
                    st.success("Ação salva com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível salvar os dados. Erro: {e}")

    st.write("---")

    # Tabela de Visualização e Exclusão
    st.subheader("Ações Cadastradas")
    if acoes:
        for a in acoes:
            # Garante leitura independente de maiúsculas/minúsculas vindas do banco
            d_acao = a.get('descricao_acao') or a.get('DESCRICAO_ACAO')
            p_praz = a.get('prazo') or a.get('PRAZO')
            s_stat = a.get('status') or a.get('STATUS')
            p_porq = a.get('porque') or a.get('PORQUE')
            o_onde = a.get('onde') or a.get('ONDE')
            n_nome = a.get('nome') or a.get('NOME')
            c_como = a.get('como') or a.get('COMO')
            q_deta = a.get('quando_detalhe') or a.get('QUANDO_DETALHE')
            i_id   = a.get('id_acao') or a.get('ID_ACAO')
            
            with st.expander(f"📌 {d_acao} - Prazo: {p_praz} ({s_stat})"):
                st.write(f"**Por que:** {p_porq} | **Onde:** {o_onde}")
                st.write(f"**Quem:** {n_nome} | **Como:** {c_como} | **Detalhe:** {q_deta}")
                st.write(f"**ID da Ação para edição:** `{i_id}`")
                
                if st.button(f"❌ Excluir Ação #{i_id}", key=f"del_{i_id}"):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("DELETE FROM Acoes WHERE id_acao = %s", (i_id,))
                        except Exception:
                            cursor.execute("DELETE FROM acoes WHERE id_acao = %s", (i_id,))
                        conn.commit()
                        conn.close()
                        st.success("Excluído!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao tentar excluir: {e}")
    else:
        st.info("Nenhum registro carregado (Banco conectado, mas sem ações criadas).

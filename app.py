import streamlit as st
import mysql.connector
from datetime import datetime
import io
import pandas as pd

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

# CONEXÃO DIRETA COM A CLEVER CLOUD
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
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.caption("📷 *[Insira o arquivo logo.png no seu GitHub para exibi-lo aqui]*")
    
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b2:
        st.markdown("<h2 style='text-align: center;'>Acesso ao Sistema</h2>", unsafe_allow_html=True)
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar", use_container_width=True):
            if usuario == USUARIO_FIXO and senha == SENHA_FIXA:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# --- PAINEL PRINCIPAL ---
else:
    col_tit, col_log = st.columns(2)
    with col_tit:
        st.title("Plano de Ação Lavo e Levo")
    with col_log:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state['logado'] = False
            st.rerun()

    # Buscar dados do banco
    acoes, usuarios = [], []
    erro_banco = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id_usuario, nome FROM Usuarios")
        usuarios = cursor.fetchall()
            
        cursor.execute("SELECT A.id_acao, A.descricao_acao, A.porque, A.onde, A.prazo, A.como, A.quando_detalhe, A.status, U.nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")
        acoes = cursor.fetchall()
            
        conn.close()
    except Exception as e:
        erro_banco = str(e)

    if erro_banco:
        st.error(f"Erro de conexão com a Clever Cloud: {erro_banco}")

    # --- INDICADORES GRÁFICOS ---
    st.write("---")
    st.subheader("📊 Gráfico de Monitoramento de Status")
    
    status_contagem = {"Não Iniciado": 0, "Em Andamento": 0, "Concluído": 0}
    if acoes:
        for a in acoes:
            if a['status'] in status_contagem:
                status_contagem[a['status']] += 1
    
    df_grafico = pd.DataFrame(list(status_contagem.items()), columns=["Status", "Quantidade"])
    st.bar_chart(df_grafico, x="Status", y="Quantidade", color="#1f77b4")

    if acoes:
        pdf_data = gerar_pdf(acoes)
        st.download_button(
            label="📄 Gerar e Baixar PDF",
            data=pdf_data,
            file_name="Plano_Lavo_Levo.pdf",
            mime="application/pdf"
        )

    st.write("---")

    # Formulário para Salvar/Editar
    st.subheader("Nova Ação / Editar Ação")
    with st.form("form_acao", clear_on_submit=True):
        st.info("💡 Para criar um novo item, deixe o ID vazio. Para editar, preencha com o número do ID desejado.")
        id_acao = st.text_input("ID da Ação (Somente números para editar)")
        descricao = st.text_input("O que (Ação) *")
        porque = st.text_input("Por que")
        onde = st.text_input("Onde")
        
        dict_usuarios = {}
        if usuarios:
            for u in usuarios:
                dict_usuarios[u['nome']] = u['id_usuario']
            
        nome_resp = st.selectbox("Responsável (Quem) *", list(dict_usuarios.keys())) if dict_usuarios else st.selectbox("Responsável", ["Nenhum usuário localizado no banco"])
        
        prazo = st.date_input("Prazo *", value=datetime.now().date())
        como = st.text_input("Como")
        quando_detalhe = st.text_input("Quando (Detalhe)")
        status = st.selectbox("Status", ["Não Iniciado", "Em Andamento", "Concluído"])
        
        submit = st.form_submit_button("Salvar Ação")
        
        if submit:
            id_limpo = id_acao.strip()
            if id_limpo != "" and not id_limpo.isdigit():
                st.error("Erro: O ID da Ação precisa ser um número inteiro válido (ex: 1, 5, 12).")
            elif not HallucinatoryTextPlaceholder:
                st.error("A descrição (O que) é obrigatória.")
            elif not dict_usuarios:
                st.error("Erro: Não há conexão ativa com o banco de dados para salvar novas ações.")
            else:
                id_resp = dict_usuarios.get(nome_resp)
                dados = (descricao, porque, onde, id_resp, prazo.strftime('%Y-%m-%d'), como, quando_detalhe, status)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    if id_limpo != "":
                        sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
                        cursor.execute(sql, dados + (int(id_limpo),))
                    else:
                        sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, dados)
                        
                    conn.commit()
                    conn.close()
                    st.success("Ação salva com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível salvar os dados. Erro: {e}")

    st.write("---")

    # --- TABELA DE VISUALIZAÇÃO COM ALERTA DE PRAZO VERMELHO ---
    st.subheader("Ações Cadastradas")
    if acoes:
        df = pd.DataFrame(acoes)
        df.columns = ["ID", "O que (Ação)", "Por que", "Onde", "Prazo", "Como", "Quando Det.", "Status", "Quem"]
        df = df[["ID", "O que (Ação)", "Quem", "Prazo", "Status", "Por que", "Onde", "Como", "Quando Det."]]
        
        hoje_atual = datetime.now().date()
        def aplicar_alerta_vencido(row):
            try:
                data_prazo = row["Prazo"]
                if isinstance(data_prazo, str):
                    data_prazo = datetime.strptime(data_prazo, "%Y-%m-%d").date()
                
                if data_prazo < hoje_atual and row["Status"] != "Concluído":
                    return ['background-color: #ffcccc; color: #990000; font-weight: bold'] * len(row)
            except Exception:
                pass
            return [''] * len(row)

        df_estilizado = df.style.apply(aplicar_alerta_vencido, axis=1)
        st.dataframe(df_estilizado, use_container_width=True, hide_index=True)
        
        # Gerenciamento de Exclusão
        st.write("<br>", unsafe_allow_html=True)
        st.caption("⚙️ **Área de Exclusão de Itens**")
        col_del_id, col_del_btn = st.columns(2)
        with col_del_id:
            id_para_deletar = st.text_input("ID para remover", key="id_del_input", placeholder="Ex: 1")
        with col_del_btn:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("❌ Confirmar e Apagar Ação", type="secondary", use_container_width=True):
                if id_para_deletar.strip().isdigit():
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM Acoes WHERE id_acao = %s", (int(id_para_deletar),))
                        conn.commit()
                        conn.close()
                        st.success(f"Ação #{id_para_deletar} excluída com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao tentar excluir: {e}")
                else:
                    st.warning("Digite um número de ID válido para poder excluir.")
    else:
        st.info("Nenhum registro carregado (Banco conectado, mas sem ações criadas).")

    # --- LOGO CORRIGIDO PARA LOGO1.PNG NO CANTO INFERIOR DIREITO (SEM ASPAS TRIPLAS SEPARADAS) ---

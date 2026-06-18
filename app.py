import streamlit as st
import mysql.connector
from datetime import datetime
import io
import pandas as pd
import base64
import os

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

# Função para gerar PDF com larguras corrigidas na linha 44
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

    # LARGURAS PREENCHIDAS CORRETAMENTE PARA EVITAR TRAVAMENTOS
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

# Inicializa o estado de login e edição
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
            st.session_state['edit_item'] = None
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

    # --- CONFIGURAÇÃO DE VALORES PADRÃO SE ESTIVER EDITANDO ---
    valores_padrao = {
        "id": "", "descricao": "", "porque": "", "onde": "", 
        "como": "", "quando_detalhe": "", "status": "Não Iniciado", "responsavel_nome": ""
    }
    
    if st.session_state['edit_item']:
        item = st.session_state['edit_item']
        valores_padrao = {
            "id": str(item['id_acao']),
            "descricao": item['descricao_acao'],
            "porque": item['porque'] if item['porque'] else "",
            "onde": item['onde'] if item['onde'] else "",
            "como": item['como'] if item['como'] else "",
            "quando_detalhe": item['quando_detalhe'] if item['quando_detalhe'] else "",
            "status": item['status'],
            "responsavel_nome": item['nome']
        }
        st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")

    # Formulário para Salvar/Editar
    st.subheader("Nova Ação / Editar Ação")
    with st.form("form_acao", clear_on_submit=False):
        id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True)
        descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"])
        porque = st.text_input("Por que", value=valores_padrao["porque"])
        onde = st.text_input("Onde", value=valores_padrao["onde"])
        
        dict_usuarios = {}
        lista_nomes_usuarios = []
        if usuarios:
            for u in usuarios:
                dict_usuarios[u['nome']] = u['id_usuario']
                lista_nomes_usuarios.append(u['nome'])
        
        index_resp = 0
        if valores_padrao["responsavel_nome"] in lista_nomes_usuarios:
            index_resp = lista_nomes_usuarios.index(valores_padrao["responsavel_nome"])
            
        nome_resp = st.selectbox("Responsável (Quem) *", lista_nomes_usuarios, index=index_resp) if lista_nomes_usuarios else st.selectbox("Responsável", ["Nenhum usuário no banco"])
        
        prazo_val = datetime.now().date()
        if st.session_state['edit_item'] and isinstance(item['prazo'], (str, datetime, datetime.date)):
            try:
                prazo_val = pd.to_datetime(item['prazo']).date()
            except Exception:
                pass
                
        prazo = st.date_input("Prazo *", value=prazo_val)
        como = st.text_input("Como", value=valores_padrao["como"])
        quando_detalhe = st.text_input("Quando (Detalhe)", value=valores_padrao["quando_detalhe"])
        
        lista_status = ["Não Iniciado", "Em Andamento", "Concluído"]
        index_status = lista_status.index(valores_padrao["status"]) if valores_padrao["status"] in lista_status else 0
        status = st.selectbox("Status", lista_status, index=index_status)
        
        col_btn_sub, col_btn_can = st.columns(2)
        with col_btn_sub:
            submit = st.form_submit_button("💾 Salvar")
        with col_btn_can:
            if st.session_state['edit_item']:
                if st.form_submit_button("❌ Cancelar Edição"):
                    st.session_state['edit_item'] = None
                    st.rerun()
        
        if submit:
            id_limpo = id_acao.strip()
            if not descricao.strip():
                st.error("A descrição é obrigatória.")
            elif not dict_usuarios:
                st.error("Erro: Sem conexão ativa com o banco.")
            else:
                id_resp = dict_usuarios.get(nome_resp)
                
                v_porque = porque.strip() if porque.strip() != "" else None
                v_onde = onde.strip() if onde.strip() != "" else None
                v_como = como.strip() if como.strip() != "" else None
                v_quando = quando_detalhe.strip() if quando_detalhe.strip() != "" else None
                
                dados = (descricao.strip(), v_porque, v_onde, id_resp, prazo.strftime('%Y-%m-%d'), v_como, v_quando, status)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    if id_limpo != "":
                        sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
                        cursor.execute(sql, dados + (int(id_limpo),))
                        st.session_state['edit_item'] = None
                    else:
                        sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
                        cursor.execute(sql, dados)
                        
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.success("Item processado e gravado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro interno do banco de dados ao salvar: {e}")

    st.write("---")

    # --- TABELA DE VISUALIZAÇÃO COM ALERTA ---
    st.subheader("Ações Cadastradas")
    if acoes:
        df = pd.DataFrame(acoes)

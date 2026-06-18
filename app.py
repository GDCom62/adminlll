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

# Função para gerar PDF corrigida definitivamente na linha 45
def gerar_pdf(acoes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ADMINISTRATIVO", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [["Ação (What)", "Responsável", "Prazo", "Status", "Como (How)", "QUANDO (Det)"]]
    for a in acoes:
        data.append([str(a[1]), str(a[4]), str(a[5]), str(a[8]), str(a[6]), str(a[7])])

    # CORREÇÃO DO ERRO: Adicionado os valores numéricos exatos de largura das colunas do PDF
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
    acoes = []
    erro_banco = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id_acao, descricao_acao, porque, onde, id_responsavel, DATE_FORMAT(prazo, '%Y-%m-%d'), como, quando_detalhe, status FROM Acoes ORDER BY prazo ASC")
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
            status_atual = str(a[8])
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
            mime="application/pdf"
        )

    st.write("---")

    # --- CONFIGURAÇÃO DE VALORES PADRÃO SE ESTIVER EDITANDO ---
    valores_padrao = {
        "id": "", "descricao": "", "porque": "", "onde": "", 
        "como": "", "quando_detalhe": "", "status": "Não Iniciado", "id_responsavel": "1"
    }
    
    if st.session_state['edit_item']:
        item = st.session_state['edit_item']
        valores_padrao = {
            "id": str(item[0]),
            "descricao": str(item[1]),
            "porque": str(item[2]) if item[2] else "",
            "onde": str(item[3]) if item[3] else "",
            "id_responsavel": str(item[4]),
            "como": str(item[6]) if item[6] else "",
            "quando_detalhe": str(item[7]) if item[7] else "",
            "status": str(item[8])
        }
        st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")

    # Formulário para Salvar/Editar
    st.subheader("Nova Ação / Editar Ação")
    with st.form("form_acao", clear_on_submit=False):
        id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True)
        descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"])
        porque = st.text_input("Por que", value=valores_padrao["porque"])
        onde = st.text_input("Onde", value=valores_padrao["onde"])
        
        responsavel_id_input = st.text_input("Código do Responsável (ID)", value=valores_padrao["id_responsavel"])
        
        prazo_val = datetime.now().date()
        if st.session_state['edit_item'] and item:
            try:
                prazo_val = datetime.strptime(str(item[5]), "%Y-%m-%d").date()
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
            else:
                v_porque = porque.strip() if porque.strip() != "" else None
                v_onde = onde.strip() if onde.strip() != "" else None
                v_como = como.strip() if como.strip() != "" else None
                v_quando = quando_detalhe.strip() if quando_detalhe.strip() != "" else None
                
                id_resp_final = int(responsavel_id_input.strip()) if responsavel_id_input.strip().isdigit() else 1
                dados = (descricao.strip(), v_porque, v_onde, id_resp_final, prazo.strftime('%Y-%m-%d'), v_como, v_quando, status)
                
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
                    st.success("Item gravado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro interno ao salvar: {e}")

    st.write("---")

    # --- LISTAGEM PURA PARSEADA VIA STRING CORRIGIDA ---
    st.subheader("Ações Cadastradas")
    if acoes:
        hoje_atual = datetime.now().date()
        for a in acoes:
            try:
                dt_pz = datetime.strptime(str(a[5]), "%Y-%m-%d").date()
            except Exception:
                dt_pz = hoje_atual
                
            esta_atrasado = dt_pz < hoje_atual and str(a[8]) != "Concluído"
            
            cor_fundo = "#fff2f2" if esta_atrasado else "#f9f9f9"
            cor_borda = "#ff4d4d" if esta_atrasado else "#ddd"
            texto_status = f"🚨 {str(a[8])} (ATRASADO)" if esta_atrasado else f"📌 {str(a[8])}"
            
            with st.container():
                html_card = "<div style='border:1px solid " + cor_borda + "; background-color:" + cor_fundo + "; padding:15px; border-radius:8px; margin-bottom:12px;'>"
                html_card += "<h4>ID #" + str(a[0]) + " - " + str(a[1]) + "</h4>"

import streamlit as st
import pandas as pd
import base64
import os
import io
import plotly.express as px  
import datetime  # <--- Certifique-se de que está exatamente assim, sem o "from"
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
        "id": str(item.get('id_acao', '')),
        "descricao": str(item.get('descricao_acao', '')),
        "porque": str(item.get('porque', '')) if item.get('porque') else "",
        "onde": str(item.get('onde', '')) if item.get('onde') else "",
        "id_responsavel": str(item.get('id_responsavel', '1')) if item.get('id_responsavel') else "1",
        "como": str(item.get('como', '')) if item.get('como') else "",
        "quando_detalhe": str(item.get('quando_detalhe', '')) if item.get('quando_detalhe') else "",
        "status": str(item.get('status', 'Não Iniciado')),
        "prazo": item.get('prazo'),
        "url_arquivo": item.get('url_arquivo')
    }

# --- INDICADORES GRÁFICOS E METRICAS ---
# --- LISTAGEM DOS ITENS SALVOS COM FILTROS E EXCEL ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes:
    # Criamos o DataFrame base com todas as ações do banco
    df_base = pd.DataFrame(acoes)
    
    # Garantimos que as colunas existam para evitar erros de leitura
    colunas_necessarias = ["id_acao", "descricao_acao", "porque", "onde", "id_responsavel", "prazo", "como", "quando_detalhe", "status", "url_arquivo"]
    for col in colunas_necessarias:
        if col not in df_base.columns:
            df_base[col] = ""

    # --- BARRA DE FILTROS DINÂMICOS ---
    st.markdown("🔍 **Filtros de Busca**")
    f_col1, f_col2 = st.columns(2)
    
    with f_col1:
        # Filtro por Status
        opcoes_status = ["Todos"] + sorted(list(df_base["status"].unique()))
        status_filtrado = st.selectbox("Filtrar por Status:", opcoes_status, key="filtro_status_dinamico")
        
    with f_col2:
        # Filtro por Responsável
        opcoes_resp = ["Todos"] + sorted(list(df_base["id_responsavel"].astype(str).unique()))
        resp_filtrado = st.selectbox("Filtrar por ID do Responsável:", opcoes_resp, key="filtro_resp_dinamico")

    # Aplicando os filtros no DataFrame de exibição
    df_filtrado = df_base.copy()
    if status_filtrado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == status_filtrado]
    if resp_filtrado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["id_responsavel"].astype(str) == resp_filtrado]

    # --- BOTÃO DE EXPORTAR PARA EXCEL ---
    # Geramos o arquivo em memória para download instantâneo
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        df_filtrado[colunas_necessarias].to_excel(writer, index=False, sheet_name='Planos de Ação')
    
    st.download_button(
        label="🟢 Baixar Lista Filtrada em Excel (.xlsx)",
        data=buffer_excel.getvalue(),
        file_name=f"plano_de_acao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="btn_download_excel_unico"
    )
    st.write("<br>", unsafe_allow_html=True)

    # Exibindo a tabela filtrada na tela
    df_exibicao = df_filtrado[colunas_necessarias].copy()
    df_exibicao.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    
    # --- BOTÕES DE GERENCIAMENTO (EDITAR / EXCLUIR) ---
    st.write("**Ações de Gerenciamento:**")
    col_sel, col_btn_ed, col_btn_ex = st.columns(3)
    
    with col_sel:
        # O seletor de ID agora mostra apenas os IDs que estão visíveis após o filtro aplicado
        ids_disponiveis = [a for a in df_filtrado['id_acao']]
        if ids_disponiveis:
            id_selecionado = st.selectbox("Selecione o ID de uma ação para modificar:", ids_disponiveis, key="select_id_gerenciamento_definitivo")
        else:
            st.caption("Nenhum ID disponível com os filtros atuais.")
            id_selecionado = None
    
    if id_selecionado:
        with col_btn_ed:
            if st.button("✏️ Editar Selecionado", use_container_width=True, key="btn_editar_item_definitivo"):
                item_procurado = next((item for item in acoes if item["id_acao"] == id_selecionado), None)
                if item_procurado:
                    st.session_state['edit_item'] = item_procurado
                    st.rerun()
                    
        with col_btn_ex:
            if st.button("🗑️ Excluir Selecionado", use_container_width=True, key="btn_excluir_item_definitivo"):
                try:
                    supabase = get_supabase_client()
                    supabase.table("Acoes").delete().eq("id_acao", id_selecionado).execute()
                    st.success(f"Ação ID #{id_selecionado} excluída!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
else:
    st.info("Nenhuma ação cadastrada no sistema até o momento.")

# --- PAINEL OPERACIONAL (ATUALIZADO COM FLUXO DE EDIÇÃO CORRETO) ---
st.write("---")
st.subheader("📝 Painel: Registrar Informações")

id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True)
descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"])
porque = st.text_input("Por que", value=valores_padrao["porque"])
onde = st.text_input("Onde", value=valores_padrao["onde"])
responsavel_id_input = st.text_input("Código do Responsável (ID)", value=valores_padrao["id_responsavel"])

prazo_val = pd.to_datetime(valores_padrao["prazo"]).date() if valores_padrao["prazo"] else pd.Timestamp.now().date()
prazo = st.date_input("Prazo *", value=prazo_val)

como = st.text_input("Como", value=valores_padrao["como"])
quando_detalhe = str(st.text_input("Quando (Detalhe)", value=valores_padrao["quando_detalhe"]))

lista_status = ["Não Iniciado", "Em Andamento", "Concluído"]
status_selecionado = st.selectbox("Status", lista_status, index=lista_status.index(valores_padrao["status"]) if valores_padrao["status"] in lista_status else 0)

arquivo_enviado = st.file_uploader("Anexar evidência ou documento (Opcional)", type=["png", "jpg", "pdf", "docx"])

# --- LÓGICA INTELIGENTE DE BOTÕES (SALVAR VS ATUALIZAR) ---
if st.session_state['edit_item']:
    # Se você clicou em editar, aparecem os botões de controle de alteração
    col_salvar, col_cancelar = st.columns(2)
    
    with col_salvar:
        btn_atualizar = st.button("🔄 Confirmar e Salvar Alterações", use_container_width=True, type="primary")
    with col_cancelar:
        btn_cancelar = st.button("❌ Cancelar Edição (Voltar ao Novo)", use_container_width=True)
        
    if btn_cancelar:
        st.session_state['edit_item'] = None
        st.rerun()
        
    if btn_atualizar:
        if not descricao:
            st.error("O campo 'Descrição (O que)' é obrigatório.")
        else:
            url_doc = valores_padrao["url_arquivo"]
            if arquivo_enviado:
                url_doc = fazer_upload_storage(arquivo_enviado)
                
            # Envia o ID para a função fazer o UPDATE no Supabase
            sucesso, msg = salvar_acao_no_banco(
                id_acao, descricao, porque, onde, responsavel_id_input, 
                str(prazo), como, quando_detalhe, status_selecionado, url_doc
            )
            if sucesso:
                st.success("Alterações salvas com sucesso!")
                st.session_state['edit_item'] = None  # Sai do modo edição
                st.rerun()
                
else:
    # Se você NÃO está editando, exibe o botão padrão de novo cadastro
    if st.button("💾 Salvar Novo Cadastro", use_container_width=True, type="primary"):
        if not descricao:
            st.error("O campo 'Descrição (O que)' é obrigatório.")
        else:
            url_doc = None
            if arquivo_enviado:
                url_doc = fazer_upload_storage(arquivo_enviado)
                
            # Como ID vai vazio, a função faz um INSERT automático no Supabase
            sucesso, msg = salvar_acao_no_banco(
                "", descricao, porque, onde, responsavel_id_input, 
                str(prazo), como, quando_detalhe, status_selecionado, url_doc
            )
            if sucesso:
                st.success("Nova ação cadastrada com sucesso!")
                st.rerun()
if st.session_state['edit_item']:
    st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")

# Chaves totalmente únicas usando o prefixo "reg_" para evitar colisões
id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True, key="reg_id")

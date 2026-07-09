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
else:
    # Buscar dados brutos do banco Supabase de forma protegida para alimentar filtros e tabelas
    acoes = []
    try:
        supabase = get_supabase_client()
        resposta = supabase.table("Acoes").select("*").order("prazo", desc=False).execute()
        acoes = resposta.data
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")

    # --- BARRA LATERAL (SIDEBAR) COM FILTROS AVANÇADOS ---
    st.sidebar.header("🔍 Filtros Avançados")

    filtro_status = st.sidebar.multiselect(
        "Filtrar por Status:", 
        ["Não Iniciado", "Em Andamento", "Concluído"], 
        default=["Não Iniciado", "Em Andamento", "Concluído"],
        key="main_filtro_status_sidebar"
    )

    responsáveis_disponiveis = sorted(list(set([str(a.get('id_responsavel', '1')) for a in acoes]))) if acoes else ["Todos"]
    filtro_resp = st.sidebar.selectbox(
        "Filtrar por ID do Responsável:", 
        ["Todos"] + responsáveis_disponiveis,
        key="main_filtro_resp_sidebar"
    )

    # Botão de Logout na lateral
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Sair do Sistema (Logout)", use_container_width=True, key="main_btn_logout_sidebar"):
        st.session_state['logado'] = False
        st.session_state['edit_item'] = None
        st.rerun()

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

    # --- TÍTULO DO PAINEL PRINCIPAL ---
    st.title("Plano de Ação Lavo e Levo")

    # --- PAINEL OPERACIONAL NO TOPO DO CODIGO ---
    st.write("---")
    st.subheader("📝 Painel: Registrar ou Modificar Informações")

    id_acao = st.text_input("ID da Ação", value=valores_padrao["id"], disabled=True, key="form_id_acao")
    descricao = st.text_input("O que (Ação) *", value=valores_padrao["descricao"], key="form_desc_acao")
    porque = st.text_input("Por que", value=valores_padrao["porque"], key="form_porque_acao")
    onde = st.text_input("Onde", value=valores_padrao["onde"], key="form_onde_acao")
    responsavel_id_input = st.text_input("Código do Responsável (ID)", value=valores_padrao["id_responsavel"], key="form_resp_acao")

    prazo_val = pd.to_datetime(valores_padrao["prazo"]).date() if valores_padrao["prazo"] else pd.Timestamp.now().date()
    prazo = st.date_input("Prazo *", value=prazo_val, key="form_prazo_acao")

    como = st.text_input("Como", value=valores_padrao["como"], key="form_como_acao")
    quando_detalhe = str(st.text_input("Quando (Detalhe)", value=valores_padrao["quando_detalhe"], key="form_quando_acao"))

    lista_status = ["Não Iniciado", "Em Andamento", "Concluído"]
    status_selecionado = st.selectbox("Status", lista_status, index=lista_status.index(valores_padrao["status"]) if valores_padrao["status"] in lista_status else 0, key="form_status_acao")

    arquivo_enviado = st.file_uploader("Anexar evidência ou documento (Opcional)", type=["png", "jpg", "pdf", "docx"], key="form_file_acao")

    # PROCESSAMENTO DOS BOTÕES DE SALVAMENTO / EDIÇÃO
    if st.session_state['edit_item']:
        st.warning(f"📝 Você está no modo de edição da Ação ID #{valores_padrao['id']}.")
        col_salvar, col_cancelar = st.columns(2)
        with col_salvar:
            btn_atualizar = st.button("🔄 Confirmar e Salvar Alterações", use_container_width=True, type="primary", key="btn_confirmar_edit")
        with col_cancelar:
            btn_cancelar = st.button("❌ Cancelar Edição (Voltar ao Novo)", use_container_width=True, key="btn_cancelar_edit")
            
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
                sucesso, msg = salvar_acao_no_banco(
                    id_acao, descricao, porque, onde, responsavel_id_input, 
                    str(prazo), como, quando_detalhe, status_selecionado, url_doc
                )
                if sucesso:
                    st.success("Alterações salvas com sucesso!")
                    st.session_state['edit_item'] = None
                    st.rerun()
    else:
        if st.button("💾 Salvar Novo Cadastro", use_container_width=True, type="primary", key="btn_salvar_novo"):
            if not descricao:
                st.error("O campo 'Descrição (O que)' é obrigatório.")
            else:
                url_doc = None
                if arquivo_enviado:
                    url_doc = fazer_upload_storage(arquivo_enviado)
                sucesso, msg = salvar_acao_no_banco(
                    "", descricao, porque, onde, responsavel_id_input, 
                    str(prazo), como, quando_detalhe, status_selecionado, url_doc
                )
                if sucesso:
                    st.success("Nova ação cadastrada com sucesso!")
                    st.rerun()

    # --- FILTRAGEM DE DADOS SEGURA ---
    acoes_filtradas = []
    if acoes:
        for a in acoes:
            status_limpo = str(a.get('status', 'Não Iniciado')).strip().title()
            status_permitidos = [s.title() for s in filtro_status] if filtro_status else []

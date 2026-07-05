import streamlit as st
import pandas as pd
import base64
import os
import io
import plotly.express as px  # Biblioteca estável para o gráfico
from supabase import create_client, Client

# Configuração da página Streamlit
st.set_page_config(page_title="Plano de Ação Lavo e Levo", layout="wide")

# CONEXÃO DIRETA COM O SUPABASE
# Cole aqui os dados exatos retirados de Settings > API do seu painel do Supabase
SUPABASE_URL = "https://otlzkpjlzorxdhagqksf.supabase.co" # Substitua pela sua URL real
SUPABASE_KEY = "sb_publishable_UtC2lBc6OwE0ZrWFpL7U9g_VuTjjjSw"    

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

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
        
        # Corrigido: Removidas as aspas extras do nome da tabela "Acoes"
        if id_limpo and id_limpo.isdigit():
            supabase.table("Acoes").update(dados_acao).eq("id_acao", int(id_limpo)).execute()
        else:
            supabase.table("Acoes").insert(dados_acao).execute()
            
        return True, "Operação realizada com sucesso!"
    except Exception as e:
        return False, f"Erro ao salvar no Supabase: {str(e)}"

# Inicializa os estados da sessão
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'edit_item' not in st.session_state:
    st.session_state['edit_item'] = None

# --- TELA DE LOGIN FIXO REATIVADA ---
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
            # Login rápido e seguro localmente
            if usuario == "admin" and senha == "123":
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

# Buscar dados do banco Supabase
acoes = []
try:
    supabase = get_supabase_client()
    # Corrigido: tabela sem aspas extras e uso de desc=False para as novas versões do Supabase
    resposta = supabase.table("Acoes").select("*").order("prazo", desc=False).execute()
    acoes = resposta.data
except Exception as e:
    st.error(f"Erro de conexão com o Supabase: {e}")

# --- INDICADORES GRÁFICOS (PIZZA DINÂMICA) ---
st.write("---")
st.subheader("📊 Distribuição de Status (Monitoramento)")

if acoes:
    lista_status_banco = []
    for a in acoes:
        status_texto = a.get('status')
        if status_texto:
            lista_status_banco.append(str(status_texto).strip().title())
        else:
            lista_status_banco.append("Não Iniciado")

    df_pizza = pd.DataFrame(lista_status_banco, columns=["Status"]).value_counts().reset_index()
    df_pizza.columns = ["Status", "Quantidade"]

    if df_pizza["Quantidade"].sum() > 0:
        fig_pizza = px.pie(
            df_pizza, 
            values='Quantidade', 
            names='Status', 
            hole=0.4,
            color='Status',
            color_discrete_map={
                'Não Iniciado': '#ff9999',
                'Em Andamento': '#66b3ff',
                'Concluído': '#99ff99',
                'Concluido': '#99ff99'
            }
        )
        fig_pizza.update_layout(
            width=450, 
            height=350, 
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_pizza, use_container_width=False)
    else:
        st.info("💡 Nenhuma quantidade válida encontrada para gerar as fatias do gráfico.")
else:
    st.info("💡 Insira ou altere o status de uma ação para visualizar as fatias do gráfico de pizza.")

# --- LISTAGEM DOS ITENS SALVOS ---
st.write("---")
st.subheader("📋 Ações Registradas")

if acoes:
    df_tabela = pd.DataFrame(acoes)
    colunas_necessarias = ["id_acao", "descricao_acao", "porque", "onde", "id_responsavel", "prazo", "como", "quando_detalhe", "status", "url_arquivo"]
    for col in colunas_necessarias:
        if col not in df_tabela.columns:
            df_tabela[col] = ""
            
    df_tabela = df_tabela[colunas_necessarias]
    df_tabela.columns = ["ID", "Descrição (O que)", "Por que", "Onde", "ID Resp.", "Prazo", "Como", "Quando Det.", "Status", "Link Arquivo"]
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
                supabase = get_supabase_client()
                supabase.table("Acoes").delete().eq("id_acao", id_selecionado).execute()
                st.success(f"Ação ID #{id_selecionado} excluída!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")
else:
    st.info("Nenhuma ação cadastrada no sistema até o momento.")

st.write("---")

# --- CONFIGURAÇÃO DE VALORES PADRÃO ---
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
    st.warning(f"📝 Editando Ação ID #{valores_padrao['id']}.")

# --- PAINEL OPERACIONAL ---
st.subheader("Painel: Registrar Informações")

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

# Botão Salvar Dados com Indentação Corrigida de Fábrica
if st.button("💾 Salvar Dados", use_container_width=True):
    if not descricao:
        st.error("O campo 'Descrição (O que)' é obrigatório.")
    else:
        url_doc = valores_padrao["url_arquivo"]
        if arquivo_enviado:
            url_doc = fazer_upload_storage(arquivo_enviado)
            

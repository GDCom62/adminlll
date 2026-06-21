import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime, date
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Lavo e Levo - Plano Estratégico", layout="wide")

# Estilização em CSS para fixar o logo1.png no rodapé direito inferior da tela
st.markdown("""
    <style>
    .footer-logo {
        position: fixed;
        bottom: 15px;
        right: 15px;
        width: 120px;
        z-index: 9999;
        opacity: 0.85;
        transition: opacity 0.3s;
    }
    .footer-logo:hover {
        opacity: 1;
    }
    </style>
    <img src="app/static/logo1.png" class="footer-logo" onerror="this.style.display='none'">
""", unsafe_allow_html=True)

# 2. SISTEMA DE ARQUIVO TEXTO SEGURO (Substitui o SQLite instável da nuvem)
ARQUIVO_BANCO = "plano_de_acao_seguro.json"

def carregar_dados_json():
    # Se o arquivo não existir, cria um lote padrão inicial estável
    if not os.path.exists(ARQUIVO_BANCO):
        dados_iniciais = [{
            "id_acao": 1,
            "descricao_acao": "Exemplo de Plano Estratégico Inicial",
            "porque": "Organizar as metas da lavanderia",
            "como": "Preenchendo o formulário 5W2H",
            "quem": "Equipe Lavo e Levo",
            "prazo": str(date.today()),
            "quanto_custa": 0.0,
            "status": "Em andamento",
            "prioridade": "Média",
            "observacoes": "Sistema operando em modo de persistência contínua por texto seguro."
        }]
        salvar_dados_json(dados_iniciais)
        return dados_iniciais
    try:
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def salvar_dados_json(dados):
    try:
        with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        st.error(f"Erro físico de gravação: {e}")
        return False

# Inicializa o banco de dados em texto estável
banco_dados_texto = carregar_dados_json()

# 3. CONTROLE DE SESSÃO
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h2 style='text-align: center;'>🧺 Lavanderia Lavo e Levo</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #1E3A8A;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                if u == "admin" and s == "123":
                    st.session_state['logado'] = True
                    st.rerun()
                else:
                    st.error("Dados de acesso incorretos. Use admin e 123.")
    st.stop()

# --- PREPARAÇÃO DAS TABELAS VISUAIS ---
df = pd.DataFrame(banco_dados_texto)
hoje = date.today()

# --- TITULO PERSONALIZADO ---
st.markdown("""
    <h1 style='text-align: center; color: #1E3A8A; padding-bottom: 5px;'>
        🧺 PLANO DE AÇAO - Administrativo
    </h1>
    <p style='text-align: center; color: #6B7280; font-size: 1.1em;'>Gestão 5W2H e Controle de Performance</p>
    <hr style='border: 1px solid #3B82F6; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

tab_lista, tab_graficos = st.tabs(["📝 Lançamentos e Controle", "📊 Análise de Performance"])

# ==============================================================================
# 📝 CONTEÚDO DA ABA 1: LANÇAMENTOS E CONTROLE
# ==============================================================================
if tab_lista.button("➕ Nova Ação (Limpar Formulário)", use_container_width=True):
    st.session_state.edit_id = None
    st.rerun()

dados_edit = None
if st.session_state.edit_id:
    for acao in banco_dados_texto:
        if acao['id_acao'] == st.session_state.edit_id:
            dados_edit = acao

titulo_formulario = f"📝 Editando Ação #{st.session_state.edit_id}" if st.session_state.edit_id else "📝 Formulário 5W2H"
form_expander = tab_lista.expander(titulo_formulario, expanded=(st.session_state.edit_id is not None))

with form_expander.form("form_5w2h", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        what = st.text_input("What (O que?) *", value=dados_edit['descricao_acao'] if dados_edit else "")
        why = st.text_area("Why (Por que?)", value=dados_edit['porque'] if dados_edit else "")
        how = st.text_area("How (Como?)", value=dados_edit['como'] if dados_edit else "")
        prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value=dados_edit['prioridade'] if dados_edit else "Média")
    with c2:
        lista_usuarios = ["Equipe Lavo e Levo", "Gerência", "Administrativo"]
        index_u = lista_usuarios.index(dados_edit['quem']) if dados_edit and dados_edit['quem'] in lista_usuarios else 0
        who = st.selectbox("Who (Quem?)", lista_usuarios, index=index_u)
        
        prazo_inicial = date.today()
        if dados_edit and dados_edit['prazo']:
            try:
                prazo_inicial = datetime.strptime(dados_edit['prazo'], '%Y-%m-%d').date()
            except:
                prazo_inicial = date.today()
                
        when = st.date_input("When (Prazo)", prazo_inicial, format="DD/MM/YYYY")
        cost = st.number_input("How Much (Custo R$)", value=float(dados_edit['quanto_custa'] or 0) if dados_edit else 0.0)
        
        status_opcoes = ["Em análise", "Em andamento", "Concluído"]
        status_index = status_opcoes.index(dados_edit['status']) if dados_edit and dados_edit['status'] in status_opcoes else 0
        status = st.selectbox("Status", status_opcoes, index=status_index)
        
        obs = st.text_input("Observações", value=dados_edit['observacoes'] if dados_edit else "")

    texto_botao_salvar = "💾 Gravar Alterações" if st.session_state.edit_id else "💾 Salvar Plano de Ação"
    if st.form_submit_button(texto_botao_salvar, use_container_width=True):
        if not what.strip():
            st.error("O campo 'What (O que?)' é obrigatório.")
        else:
            if st.session_state.edit_id:
                # Altera o item no banco de texto seguro
                for acao in banco_dados_texto:
                    if acao['id_acao'] == st.session_state.edit_id:
                        acao.update({
                            "descricao_acao": what, "porque": why, "como": how,
                            "quem": who, "prazo": str(when), "quanto_custa": cost,
                            "status": status, "prioridade": prio, "observacoes": obs
                        })
                salvar_dados_json(banco_dados_texto)
                st.session_state.edit_id = None
            else:
                # Determina o próximo ID de forma incremental
                novo_id = max([a['id_acao'] for a in banco_dados_texto]) + 1 if banco_dados_texto else 1
                banco_dados_texto.append({
                    "id_acao": novo_id,
                    "descricao_acao": what, "porque": why, "como": how,
                    "quem": who, "prazo": str(when), "quanto_custa": cost,
                    "status": status, "prioridade": prio, "observacoes": obs
                })
                salvar_dados_json(banco_dados_texto)
            st.rerun()

# --- PAINEL DE CONTROLE FIXO SUPERIOR ---
tab_lista.subheader("📋 Ações e Prazos")

if df.empty:
    tab_lista.info("Nenhuma ação cadastrada no sistema.")
else:
    st.markdown("### ⚙️ Painel de Manutenção de Ações")
    c_id, c_ed, c_ex = tab_lista.columns([0.4, 0.3, 0.3])
    
    lista_ids = df['id_acao'].tolist()
    id_selecionado = c_id.selectbox("Escolha o número do ID que deseja alterar ou apagar:", lista_ids)
    
    if c_ed.button("✏️ Editar ID Selecionado", use_container_width=True):
        st.session_state.edit_id = id_selecionado
        st.rerun()
        
    if c_ex.button("🗑️ Excluir ID Selecionado", use_container_width=True):
        banco_dados_texto = [a for a in banco_dados_texto if a['id_acao'] != id_selecionado]
        salvar_dados_json(banco_dados_texto)
        st.success(f"Item #{id_selecionado} removido com sucesso!")
        st.rerun()
        
    tab_lista.markdown("---")
    
    tab_lista.write("📊 **Lista de Controle Cadastrada:**")
    st_df = df[["id_acao", "descricao_acao", "prioridade", "quem", "prazo", "quanto_custa", "status"]]
    tab_lista.dataframe(st_df, use_container_width=True, hide_index=True)
    
    tab_lista.write("---")

    for _, row in df.iterrows():
        try:
            dt_br = datetime.strptime(row['prazo'], '%Y-%m-%d').strftime('%d/%m/%Y')
            data_prazo = datetime.strptime(row['prazo'], '%Y-%m-%d').date()
        except:
            dt_br = str(row['prazo'])
            data_prazo = hoje
            
        atraso = data_prazo < hoje and row['status'] != 'Concluído'
        cor = "#dc3545" if atraso else "#28a745" if row['status'] == "Concluído" else "#ffc107"
        
        card_container = tab_lista.container()
        card_container.markdown(f"<div style='background-color:{cor}; height:6px; width:100%; border-radius:5px; margin-bottom:8px;'></div>", unsafe_allow_html=True)
        
        card_container.write(f"📌 **[ID #{row['id_acao']}] - {row['descricao_acao']}** | Responsável: *{row['quem']}* | Prazo: **{dt_br}**")
        if row['porque']: card_container.caption(f"❓ **Motivo (Why):** {row['porque']}")
        if row['como']: card_container.caption(f"🔧 **Como fazer (How):** {row['como']}")

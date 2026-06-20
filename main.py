import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
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

# 2. FUNÇÃO DE CONEXÃO PERSISTENTE COM SQLITE
def executar_db(sql, params=None, retorno=True):
    try:
        conn = sqlite3.connect("banco_lavo_levo_estavel.db")
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()
        
        sql_convertido = sql.replace("%s", "?")
        cursor.execute(sql_convertido, params or ())
        
        if retorno:
            resultado = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return resultado
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return None

# --- INICIALIZAÇÃO DA ESTRUTURA FIXA DO BANCO ---
def inicializar_banco_local():
    executar_db("""
        CREATE TABLE IF NOT EXISTS Credenciais (
            id_credencial INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            senha TEXT NOT NULL,
            nivel TEXT DEFAULT 'Comum'
        )
    """, retorno=False)
    
    executar_db("""
        CREATE TABLE IF NOT EXISTS Usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        )
    """, retorno=False)
    
    executar_db("""
        CREATE TABLE IF NOT EXISTS Acoes (
            id_acao INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao_acao TEXT NOT NULL,
            porque TEXT,
            como TEXT,
            id_responsavel INTEGER,
            prazo TEXT,
            quanto_custa REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Em análise',
            prioridade TEXT DEFAULT 'Média',
            observacoes TEXT
        )
    """, retorno=False)

    usuarios_existentes = executar_db("SELECT * FROM Usuarios")
    if not usuarios_existentes:
        executar_db("INSERT INTO Credenciais (usuario, senha, nivel) VALUES (?, ?, ?)", ("admin", "123", "Administrador"), retorno=False)
        executar_db("INSERT INTO Usuarios (nome) VALUES (?)", ("Equipe Lavo e Levo",), retorno=False)
        executar_db("INSERT INTO Usuarios (nome) VALUES (?)", ("Gerência",), retorno=False)

    check_adm = executar_db("SELECT * FROM Usuarios WHERE nome = ?", ("Administrativo",))
    if not check_adm:
        executar_db("INSERT INTO Usuarios (nome) VALUES (?)", ("Administrativo",), retorno=False)

inicializar_banco_local()

# 3. CONTROLE DE SESSÃO
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'confirmar_excluir' not in st.session_state: st.session_state.confirmar_excluir = None

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.markdown("<h2 style='text-align: center;'>🧺 Lavanderia Lavo e Levo</h2>", unsafe_allow_html=True)
            st.caption("📷 *[Insira o arquivo logo.png no seu GitHub para exibir a imagem aqui]*")
        
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #1E3A8A;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                res = executar_db("SELECT * FROM Credenciais WHERE usuario=? AND senha=?", (u, s))
                if res and len(res) > 0:
                    # CORREÇÃO CRUCIAL DO LOGIN PARA EVITAR TRAVAMENTOS NO PYTHON 3.14
                    nivel_usuario = res[0]['nivel'] if 'nivel' in res[0] else 'Comum'
                    st.session_state['logado'], st.session_state['nivel'] = True, nivel_usuario
                    st.rerun()
                else:
                    st.error("Dados de acesso incorretos.")
    st.stop()

# --- CARREGAR DADOS ---
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")

dados_db = buscar_dados()
df = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()
hoje = date.today()

# --- TITULO PERSONALIZADO ---
st.markdown("""
    <h1 style='text-align: center; color: #1E3A8A; padding-bottom: 5px;'>
        🧺 PLANO ESTRATÉGICO DA LAVANDERIA LAVO E LEVO
    </h1>
    <p style='text-align: center; color: #6B7280; font-size: 1.1em;'>Gestão 5W2H e Controle de Performance</p>
    <hr style='border: 1px solid #3B82F6; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

tab_lista, tab_graficos = st.tabs(["📝 Lançamentos e Controle", "📊 Análise de Performance"])

# ==============================================================================
# 📝 CONTEÚDO DA ABA 1: LANÇAMENTOS E CONTROLE
# ==============================================================================
if tab_lista.button("➕ Nova Ação (Limpar)", use_container_width=True):
    st.session_state.edit_id = None
    st.rerun()

dados_edit = None
if st.session_state.edit_id:
    res_e = executar_db("SELECT * FROM Acoes WHERE id_acao=?", (st.session_state.edit_id,))
    if res_e and len(res_e) > 0: 
        # CORREÇÃO CRUCIAL DA EDIÇÃO PARA EVITAR TRAVAMENTOS NO PYTHON 3.14
        dados_edit = res_e[0]

res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {u['nome']: u['id_usuario'] for u in res_u} if res_u else {}

titulo_formulario = f"📝 Editando Ação #{st.session_state.edit_id}" if st.session_state.edit_id else "📝 Formulário 5W2H"
form_expander = tab_lista.expander(titulo_formulario, expanded=(st.session_state.edit_id is not None))

with form_expander.form("form_5w2h", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        what = st.text_input("What (O que?) *", value=dados_edit['descricao_acao'] if dados_edit else "")
        why = st.text_area("Why (Por que?)", value=dados_edit['porque'] if dados_edit else "")
        how = st.text_area("How (Como?)", value=dados_edit['como'] if dados_edit and 'como' in dados_edit else "")
        prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value=dados_edit['prioridade'] if dados_edit else "Média")
    with c2:
        nome_padrao = "Selecione"
        if dados_edit:
            for nome_u, id_u in dict_u.items():
                if id_u == dados_edit['id_responsavel']:
                    nome_padrao = nome_u
        
        lista_usuarios = list(dict_u.keys())
        index_u = lista_usuarios.index(nome_padrao) if nome_padrao in lista_usuarios else 0
        
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
                sql = "UPDATE Acoes SET descricao_acao=?, porque=?, como=?, id_responsavel=?, prazo=?, quanto_custa=?, status=?, prioridade=?, observacoes=? WHERE id_acao=?"
                executar_db(sql, (what, why, how, dict_u[who], str(when), cost, status, prio, obs, st.session_state.edit_id), False)
                st.session_state.edit_id = None
            else:
                sql = "INSERT INTO Acoes (descricao_acao, porque, como, id_responsavel, prazo, quanto_custa, status, prioridade, observacoes) VALUES (?,?,?,?,?,?,?,?,?)"
                executar_db(sql, (what, why, how, dict_u[who], str(when), cost, status, prio, obs), False)
            st.rerun()

if st.session_state.edit_id: 
    if form_expander.button("❌ Cancelar Modo Edição", use_container_width=True):
        st.session_state.edit_id = None
        st.rerun()

# FILTROS DE LISTAGEM ISOLADOS
tab_lista.subheader("📋 Ações e Prazos")
df_filtrado = df.copy()

if not df.empty:
    f1, f2 = tab_lista.columns(2)
    filtro_quem = f1.multiselect("Filtrar por Responsável", options=list(df['quem'].unique()), default=[])
    filtro_status = f2.multiselect("Filtrar por Status", options=list(df['status'].unique()), default=[])
    
    df_filtrado = df_filtrado[df_filtrado['quem'].isin(filtro_quem)] if filtro_quem else df_filtrado

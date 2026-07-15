# Formulário para Salvar/Editar
    st.subheader("Nova Ação / Editar Ação")
    with st.form("form_acao", clear_on_submit=True):
        st.info("💡 Para criar um novo item, deixe o ID da Ação vazio. Para editar, digite o número do ID correspondente.")
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
            elif not descricao:
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

    # Tabela de Visualização e Gerenciamento Estruturada
    st.subheader("Ações Cadastradas")
    if acoes:
        # Transforma os dados em uma tabela visual interativa
        df = pd.DataFrame(acoes)
        df.columns = ["ID", "O que (Ação)", "Por que", "Onde", "Prazo", "Como", "Quando Det.", "Status", "Quem"]
        # Reorganiza a ordem das colunas para ficar mais intuitivo
        df = df[["ID", "O que (Ação)", "Quem", "Prazo", "Status", "Por que", "Onde", "Como", "Quando Det."]]
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.write("<br>", unsafe_allow_html=True)
        st.caption("⚙️ **Área de Exclusão de Itens**")
        col_del_id, col_del_btn = st.columns([1, 4])
        with col_del_id:
            id_para_deletar = st.text_input("ID para remover", key="id_del_input", placeholder="Ex: 1")
        with col_del_btn:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("❌ Confirmar e Apagar Ação", type="secondary"):
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

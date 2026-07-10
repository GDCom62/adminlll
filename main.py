    # Gerador de Relatório PDF Integrado
    pdf_data = gerar_pdf_atualizado(acoes)
    st.download_button(
        label="📄 Gerar e Baixar Relatório (PDF)",
        data=pdf_data,
        file_name="Plano_Lavo_Levo.pdf",
        mime="application/pdf",
        key="btn_download_pdf_final",
        use_container_width=True
    )
    
    st.write("**Ações de Gerenciamento:**")
    col_sel, col_btn_ed, col_btn_ex = st.columns(3)
    
    with col_sel:
        id_selecionado = st.selectbox("Selecione o ID de uma ação para modificar:", [a['id_acao'] for a in acoes], key="select_id_manutencao")
        
    with col_btn_ed:
        if st.button("✏️ Editar Selecionado", use_container_width=True, key="btn_trigger_editar"):
            item_procurado = next((item for item in acoes if item["id_acao"] == id_selecionado), None)
            if item_procurado:
                st.session_state['edit_item'] = item_procurado
                st.rerun() 
                
    with col_btn_ex:
        if st.button("🗑️ Excluir Selecionado", use_container_width=True, key="btn_trigger_excluir"):
            try:
                supabase = get_supabase_client()
                supabase.table("Acoes").delete().eq("id_acao", id_selecionado).execute()
                st.success(f"Ação ID #{id_selecionado} excluída!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")

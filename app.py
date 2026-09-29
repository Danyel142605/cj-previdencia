import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import io
from supabase import create_client, Client

# 1. CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO ADVBOX
st.set_page_config(page_title="CJ Previdência", layout="wide")

st.markdown("""
    <style>
        @import url('https://googleapis.com');
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Inter', sans-serif;
            background-color: #f8f9fa;
        }
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e0e0e0;
        }
        [data-testid="stSidebar"] * {
            color: #333333 !important;
        }
        .sidebar-title {
            font-size: 20px;
            font-weight: 700;
            color: #1a1a1a !important;
            margin-bottom: 25px;
            padding-left: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXÃO COM O SUPABASE
SUPABASE_URL = 'https://foouqvaisepqvbamzcuh' + '.supabase.co'
SUPABASE_KEY = 'sb_publishable_P7sSXSgHemOw_JKiF1qBNw_hT1eAna6'

@st.cache_resource
def iniciar_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = iniciar_supabase()
except Exception:
    st.error("Erro ao conectar ao banco de dados em nuvem.")

# FUNÇÃO COMPACTA E CORRETA DE CONVERSÃO E ENVIO PARA O STORAGE SEGURO
def enviar_documento_storage(cpf, nome_doc, arquivo_upload):
    if arquivo_upload is not None:
        try:
            nome_arquivo = arquivo_upload.name.lower()
            if nome_arquivo.endswith('.pdf'):
                pdf_bytes = arquivo_upload.read()
            else:
                image = Image.open(arquivo_upload)
                if image.mode in ("RGBA", "P"): 
                    image = image.convert("RGB")
                pdf_buffer = io.BytesIO()
                image.save(pdf_buffer, format="PDF")
                pdf_bytes = pdf_buffer.getvalue()
            
            nome_final_arquivo = f"{cpf}/{nome_doc}.pdf"
            try:
                supabase.storage.from_("documentos_cj").remove([nome_final_arquivo])
            except Exception:
                pass
            
            supabase.storage.from_("documentos_cj").upload(nome_final_arquivo, pdf_bytes, {"content-type": "application/pdf"})
            return nome_final_arquivo
        except Exception:
            return None
    return None

# FUNÇÃO PARA GERAR LINKS DIRETOS DO STORAGE DE ARQUIVOS
def obtener_link_documento(caminho_storage):
    if caminho_storage:
        try:
            res = supabase.storage.from_("documentos_cj").create_signed_url(caminho_storage, 60)
            return res.get("signedURL")
        except Exception:
            return None
    return None

# 3. CONTROLE DE LOGIN / SESSÃO
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state: st.session_state['usuario_atual'] = ""
if 'perfil_atual' not in st.session_state: st.session_state['perfil_atual'] = "Colaborador"

if not st.session_state['logado']:
    st.markdown("<h2 style='text-align: center; margin-top: 40px;'>⚖️ CJ PREVIDÊNCIA</h2>", unsafe_allow_html=True)
    opcao_tela = st.radio("Selecione:", ["Fazer Login", "Criar Nova Conta de Funcionário"], horizontal=True, label_visibility="collapsed")
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        if opcao_tela == "Fazer Login":
            with st.form("login_form"):
                st.markdown("<p style='text-align: center; font-weight:600;'>Acesso ao Painel</p>", unsafe_allow_html=True)
                login_input = st.text_input("E-mail ou CPF")
                senha_input = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    if login_input == "admin@cjprevidencia.com.br" and senha_input == "admin123":
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = "Administrador Geral"
                        st.session_state['perfil_atual'] = "Admin"
                        st.rerun()
                    
                    try:
                        resposta = supabase.table("usuarios_sistema").select("*").eq("identificador", login_input).eq("senha", senha_input).execute()
                        dados = resposta.data
                        if dados and len(dados) > 0:
                            user = dados[0] if isinstance(dados, list) else dados
                            if user.get('status_liberacao') == "Liberado":
                                st.session_state['logado'] = True
                                st.session_state['usuario_atual'] = user.get('nome', 'Usuário')
                                st.session_state['perfil_atual'] = user.get('perfil', 'Colaborador')
                                st.rerun()
                            else:
                                st.warning("⚠️ Conta aguardando liberação do Administrador.")
                        else:
                            st.error("Credenciais incorretas.")
                    except Exception:
                        st.error("Erro ao validar login.")
        else:
            with st.form("cadastro_form_user"):
                st.markdown("<p style='text-align: center; font-weight:600;'>Solicitar Novo Acesso</p>", unsafe_allow_html=True)
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("E-mail corporativo ou CPF")
                senha_nova = st.text_input("Senha")
                tipo_perfil = st.selectbox("Perfil desejado:", ["Colaborador", "Admin"])
                if st.form_submit_button("Finalizar Meu Cadastro", use_container_width=True):
                    if nome_novo and login_novo and senha_nova:
                        try:
                            supabase.table("usuarios_sistema").insert({"nome": nome_novo, "identificador": login_novo, "senha": senha_nova, "perfil": tipo_perfil, "status_liberacao": "Aguardando Liberação"}).execute()
                            st.success("Cadastrado! Aguarde a liberação do Administrador.")
                        except Exception:
                            st.error("Este identificador já existe ou erro na nuvem.")
                    else: st.error("Preencha todos os campos.")
    st.stop()

# 4. INTERFACE APÓS LOGIN
st.sidebar.markdown("<div class='sidebar-title'>☤ CJ PREVIDÊNCIA</div>", unsafe_allow_html=True)
st.sidebar.write(f"👤 Usuário: **{st.session_state['usuario_atual']}**")
st.sidebar.write(f"🔰 Nível: **{st.session_state['perfil_atual']}**")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state['logado'] = False
    st.rerun()

st.sidebar.markdown("---")
opcoes_menu = ["🆕 Novo Processo", "🗂️ Processos", "📊 Status", "📋 Relatórios"]
if st.session_state['perfil_atual'] == "Admin":
    opcoes_menu.append("👥 Gerenciar Equipe (ADM)")

menu_selecionado = st.sidebar.radio("Navegação:", opcoes_menu)

# --- TELA: NOVO PROCESSO ---
if menu_selecionado == "🆕 Novo Processo":
    st.subheader("🆕 Cadastrar Novo Processo")
    with st.form("cadastro_inicial_form", clear_on_submit=True):
        nome_c = st.text_input("Nome da Cliente")
        cpf_c = st.text_input("CPF (Apenas números)")
        senha_c = st.text_input("Senha da Cliente", type="password")
        grupo_c = st.selectbox("Grupo de Ações:", ["PREVIDENCIÁRIO", "Administrativa", "Civil", "Trabalhista"])
        etapa_c = st.selectbox("Etapa Inicial:", ["Fazer Caepf", "Pagar Gps", "Protocolar", "Concedido", "Indeferido", "Cumprir exigência"])
        
        if st.form_submit_button("💼 INICIAR CASO E SALVAR FICHA", use_container_width=True):
            if nome_c and cpf_c and senha_c:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                dados_proc = {
                    "nome_cliente": nome_c, "cpf": cpf_c, "senha_cliente": senha_c, "grupo_acao": grupo_c, "etapa_atual": etapa_c,
                    "ultima_atualizacao": agora, "usuario_responsavel": st.session_state['usuario_atual']
                }
                try:
                    supabase.table("processos_v3").insert(dados_proc).execute()
                    st.success(f"Ficha de {nome_c} criada na nuvem! Agora vá na aba 'Processos' para gerenciar.")
                except Exception:
                    st.error("Erro ao salvar. Verifique se o CPF já existe ou se as tabelas estão alinhadas.")
            else:
                st.error("Preencha Nome, CPF e Senha da cliente.")

# --- TELA: PROCESSOS (EXIBIÇÃO E ALTERAÇÃO DE STATUS SOLICITADOS) ---
elif menu_selecionado == "🗂️ Processos":
    st.subheader("🗂️ Gerenciamento de Casos e Status")
    try:
        res_proc = supabase.table("processos_v3").select("*").execute()
        df_processos = pd.DataFrame(res_proc.data) if res_proc.data else pd.DataFrame()
        
        if not df_processos.empty:
            cli_sel = st.selectbox("Selecione a cliente para verificar e alterar informações:", df_processos['nome_cliente'].tolist())
            row_p = df_processos[df_processos['nome_cliente'] == cli_sel].iloc[0]
            id_p = int(row_p['id'])
            cpf_p = str(row_p['cpf'])
            
            # EXIBIÇÃO DE TODOS OS DADOS DE CADASTRO SOLICITADOS
            st.write("---")
            st.write("### 📋 Informações Atuais da Cliente")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.write(f"👤 **Nome:** {row_p['nome_cliente']}")
                st.write(f"💳 **CPF:** {row_p['cpf']}")
            with col_d2:
                st.write(f"🔑 **Senha Visível:** `{row_p['senha_cliente']}`")
                st.write(f"📅 **Última Atualização:** {row_p['ultima_atualizacao']}")
            
            st.write("---")
            st.write("### ⚙️ Alterar e Tramitar Status")
            
            # OPÇÃO DE EDITAR OS STATUS PEDIDOS EXATAMENTE COMO SOLICITADO
            lista_status = ["Fazer Caepf", "Pagar Gps", "Protocolar", "Concedido", "Indeferido", "Cumprir exigência"]
            
            status_atual = row_p['etapa_atual']
            idx_status = lista_status.index(status_atual) if status_atual in lista_status else 0
            
            novo_status = st.selectbox("Selecione o Novo Status do Processo:", lista_status, index=idx_status)
            grupo_at = st.selectbox("Grupo de Ação:", ["PREVIDENCIÁRIO", "Administrativa", "Civil", "Trabalhista"], index=["PREVIDENCIÁRIO", "Administrativa", "Civil", "Trabalhista"].index(row_p['grupo_acao']) if row_p['grupo_acao'] in ["PREVIDENCIÁRIO", "Administrativa", "Civil", "Trabalhista"] else 0)
            
            st.write("---")
            st.write("##### 📁 Anexar Novos Documentos para esta Cliente")
            up_rg = st.file_uploader("Atualizar RG (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"], key="rg_p")
            up_cert = st.file_uploader("Atualizar Certidão (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"], key="cert_p")
            up_res = st.file_uploader("Atualizar Comprovante Residência (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"], key="res_p")
            
            if st.button("💾 CONFIRMAR ALTERAÇÕES E ATUALIZAR STATUS", use_container_width=True, type="primary"):
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                up_dados = {
                    "etapa_atual": novo_status,
                    "grupo_acao": grupo_at,
                    "ultima_atualizacao": agora,
                    "usuario_responsavel": st.session_state['usuario_atual']
                }
                
                if up_rg: up_dados["pdf_rg"] = enviar_documento_storage(cpf_p, "rg", up_rg)
                if up_cert: up_dados["pdf_certidao"] = enviar_documento_storage(cpf_p, "certidao", up_cert)
                if up_res: up_dados["pdf_residencia"] = enviar_documento_storage(cpf_p, "residencia", up_res)
                
                supabase.table("processos_v3").update(up_dados).eq("id", id_p).execute()
                st.success("Status e informações atualizados com absoluto sucesso!")
                st.rerun()
                
            # LINKS DE DOWNLOAD AUTOMÁTICOS
            st.write("---")
            st.write("##### 📥 Documentos Disponíveis em PDF")
            for nome_label, campo_banco in [("RG", "pdf_rg"), ("Certidão", "pdf_certidao"), ("Comprovante Residência", "pdf_residencia")]:
                caminho_arq = row_p.get(campo_banco) if pd.notna(row_p.get(campo_banco)) else None
                if caminho_arq and str(caminho_arq) != "None":
                    link_pdf = obtener_link_documento(caminho_arq)
                    if link_pdf:
                        st.markdown(f"🔗 **[Abrir / Baixar PDF do {nome_label}]({link_pdf})**")
                        
        else: st.info("Nenhum processo localizado no banco de dados.")
    except Exception:
        st.error("Erro ao processar as informações.")

# --- TELA: STATUS ---
elif menu_selecionado == "📊 Status":
    st.subheader("📊 Filtros Rápidos de Status")
    try:
        res_st = supabase.table("processos_v3").select("*").execute()
        if res_st.data:
            df_f = pd.DataFrame(res_st.data)
            st.dataframe(df_f[["nome_cliente", "cpf", "grupo_acao", "etapa_atual", "ultima_atualizacao"]], use_container_width=True, hide_index=True)
        else: st.info("Nenhum caso ativo localizado.")
    except Exception: st.error("Erro ao carregar tela de status.")

# --- TELA: RELATÓRIOS ---
elif menu_selecionado == "📋 Relatórios":
    st.subheader("📋 Relatório Diário de Casos")
    try:
        res_rel = supabase.table("processos_v3").select("*").execute()
        if res_rel.data:
            df_r = pd.DataFrame(res_rel.data)
            st.dataframe(df_r[["nome_cliente", "cpf", "grupo_acao", "etapa_atual", "ultima_atualizacao", "usuario_responsavel"]], use_container_width=True, hide_index=True)
            csv = df_r.to_csv(index=False).encode('utf-8-sig')
            st.download_button(label="📥 Baixar Planilha Geral (.CSV)", data=csv, file_name="Relatorio_CJ_Previdencia.csv", mime="text/csv")
        else: st.info("Nenhum registro para exportação.")
    except Exception: st.error("Erro ao gerar relatório de dados.")

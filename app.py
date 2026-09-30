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

# 3. CONTROLE DE LOGIN / SESSÃO (MUDADO PARA CADASTRO E ENTRADA DIRETA AUTOMÁTICA)
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
                            st.session_state['logado'] = True
                            st.session_state['usuario_atual'] = user.get('nome', 'Usuário')
                            st.session_state['perfil_atual'] = user.get('perfil', 'Colaborador')
                            st.rerun()
                        else:
                            st.error("Credenciais incorretas.")
                    except Exception:
                        st.error("Erro ao validar login.")
        else:
            with st.form("cadastro_form_user"):
                st.markdown("<p style='text-align: center; font-weight:600;'>Solicitar Novo Acesso</p>", unsafe_allow_html=True)
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("E-mail corporativo ou CPF")
                senha_novo = st.text_input("Senha")
                tipo_perfil = st.selectbox("Perfil desejado:", ["Colaborador", "Admin"])
                if st.form_submit_button("Finalizar Meu Cadastro e Entrar", use_container_width=True):
                    if nome_novo and login_novo and senha_novo:
                        try:
                            # Cadastra o usuário com status Liberado para entrada direta
                            supabase.table("usuarios_sistema").insert({
                                "nome": nome_novo, 
                                "identificador": login_novo, 
                                "senha": senha_novo, 
                                "perfil": tipo_perfil, 
                                "status_liberacao": "Liberado"
                            }).execute()
                            
                            # Efetua o login instantâneo após o clique
                            st.session_state['logado'] = True
                            st.session_state['usuario_atual'] = nome_novo
                            st.session_state['perfil_atual'] = tipo_perfil
                            st.success("Cadastro realizado com sucesso! Entrando no painel...")
                            st.rerun()
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

# --- TELA: GERENCIAR EQUIPE (NOMEADO CONFORME O SEU NOVO FORMATO EXCLUSIVO) ---
if menu_selecionado == "👥 Gerenciar Equipe (ADM)":
    st.subheader("👥 Controle e Monitoramento de Equipe (ADM)")
    try:
        res_users = supabase.table("usuarios_sistema").select("*").execute()
        df_usuarios = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
        
        if not df_usuarios.empty:
            st.write("##### 📋 Colaboradores Cadastrados no Banco de Dados")
            st.dataframe(df_usuarios[["id", "nome", "identificador", "perfil"]], use_container_width=True, hide_index=True)
            st.write("---")
            
            user_sel = st.selectbox("Selecione um Funcionário para Remover do Sistema:", df_usuarios['nome'].tolist())
            row_user = df_usuarios[df_usuarios['nome'] == user_sel].iloc[0]
            
            if st.button("🗑️ DELETAR ACESSO DO FUNCIONÁRIO", type="primary", use_container_width=True):
                supabase.table("usuarios_sistema").delete().eq("id", int(row_user['id'])).execute()
                st.success(f"O acesso do colaborador {user_sel} foi removido com sucesso!")
                st.rerun()
        else:
            st.info("Nenhum funcionário cadastrado na base de dados até o momento.")
    except Exception:
        st.error("Erro ao carregar listagem de equipe.")

# --- TELA: NOVO PROCESSO ---
elif menu_selecionado == "🆕 Novo Processo":
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

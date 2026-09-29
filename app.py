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

# 2. CONEXÃO COM O SUPABASE (BANCO DE DADOS EM NUVEM PERMANENTE)
SUPABASE_URL = 'https://supabase.co'
SUPABASE_KEY = 'sb_publishable_P7sSXSgHemOw_JKiF1qBNw_hT1eAna6'

@st.cache_resource
def iniciar_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = iniciar_supabase()
except Exception:
    st.error("Erro ao conectar ao banco de dados em nuvem. Verifique as chaves URL e KEY.")

import base64  # Certifique-se de que essa linha está no topo do seu arquivo

def processar_e_converter_arquivo(arquivo_upload):
    if arquivo_upload is not None:
        nome_arquivo = arquivo_upload.name.lower()
        if nome_arquivo.endswith('.pdf'):
            # Lê o arquivo e converte para um texto Base64 seguro
            return base64.b64encode(arquivo_upload.read()).decode('utf-8')
        elif nome_arquivo.endswith(('.jpg', '.jpeg', '.png')):
            image = Image.open(arquivo_upload)
            if image.mode in ("RGBA", "P"): 
                image = image.convert("RGB")
            pdf_buffer = io.BytesIO()
            image.save(pdf_buffer, format="PDF")
            # Converte a imagem transformada em PDF para texto Base64 seguro
            return base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
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
                    
                    resposta = supabase.table("usuarios_sistema").select("*").eq("identificador", login_input).eq("senha", senha_input).execute()
                    if resposta.data:
                        user = resposta.data[0] if isinstance(resposta.data, list) else resposta.data
                        if user['status_liberacao'] == "Liberado":
                            st.session_state['logado'] = True
                            st.session_state['usuario_atual'] = user['nome']
                            st.session_state['perfil_atual'] = user['perfil']
                            st.rerun()
                        else:
                            st.warning("⚠️ Conta aguardando liberação do Administrador.")
                    else:
                        st.error("Credenciais incorretas.")
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

# --- TELA: GERENCIAR EQUIPE (ADM) ---
if menu_selecionado == "👥 Gerenciar Equipe (ADM)":
    st.subheader("👥 Controle de Usuários e Suporte (Painel ADM)")
    res_users = supabase.table("usuarios_sistema").select("id, nome, identificador, perfil, status_liberacao").execute()
    df_usuarios = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame()
    
    if not df_usuarios.empty:
        st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
        st.write("---")
        user_sel = st.selectbox("Selecione o Funcionário para modificar:", df_usuarios['nome'].tolist())
        row_user = df_usuarios[df_usuarios['nome'] == user_sel].iloc[0]
        
        nova_lib = st.selectbox("Alterar Status de Acesso:", ["Liberado", "Aguardando Liberação"], index=["Liberado", "Aguardando Liberação"].index(row_user['status_liberacao']))
        novo_perf = st.selectbox("Mudar Perfil/Cargo:", ["Colaborador", "Admin"], index=["Colaborador", "Admin"].index(row_user['perfil']))
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Salvar Alterações do Funcionário", use_container_width=True):
                supabase.table("usuarios_sistema").update({"status_liberacao": nova_lib, "perfil": novo_perf}).eq("id", int(row_user['id'])).execute()
                st.success("Cadastro atualizado na nuvem!")
                st.rerun()
        with col_b2:
            if st.button("🗑️ DELETAR FUNCIONÁRIO", type="primary", use_container_width=True):
                supabase.table("usuarios_sistema").delete().eq("id", int(row_user['id'])).execute()
                st.success("Funcionário removido.")
                st.rerun()
    else: st.info("Nenhum funcionário cadastrado no banco de dados.")

# --- TELA: NOVO PROCESSO ---
elif menu_selecionado == "🆕 Novo Processo":
    st.subheader("🆕 Cadastrar Novo Processo")
    with st.form("cadastro_processo_form", clear_on_submit=True):
        nome_c = st.text_input("Nome da Cliente")
        cpf_c = st.text_input("CPF (Apenas números)")
        senha_c = st.text_input("Senha da Cliente", type="password")
        grupo_c = st.selectbox("Grupo de Ações:", ["PREVIDENCIÁRIO", "Administrativa", "Civil", "Trabalhista"])
        etapa_c = st.selectbox("Etapa Inicial:", ["Aguardando Assinatura do contrato", "Caepf", "Pagamento GPS", "Protocolar"])
        
        up_rg = st.file_uploader("RG (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"])
        up_cert = st.file_uploader("Certidão de Nascimento (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"])
        up_res = st.file_uploader("Comprovante de Residência (JPG ou PDF)", type=["jpg", "jpeg", "png", "pdf"])
        
        if st.form_submit_button("Salvar Novo Caso"):
            if nome_c and cpf_c and senha_c:
                agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                dados_proc = {
                    "nome_cliente": nome_c, "cpf": cpf_c, "senha_cliente": senha_c, "grupo_acao": grupo_c, "etapa_atual": etapa_c,
                    "pdf_rg": processar_e_converter_arquivo(up_rg), "pdf_certidao": processar_e_converter_arquivo(up_cert),
                    "pdf_residencia": processar_e_converter_arquivo(up_res), "ultima_atualizacao": agora, "usuario_responsavel": st.session_state['usuario_atual']
                }
                supabase.table("processos_v3").insert(dados_proc).execute()
                st.success("Ficha criada e salva permanentemente na nuvem!")
            else: st.error("Preencha Nome, CPF e Senha.")

# --- TELA: PROCESSOS ---
elif menu_selecionado == "🗂️ Processos":
    st.subheader("🗂️ Gerenciamento de Casos")
    res_proc = supabase.table("processos_v3").select("id, nome_cliente, cpf, grupo_acao, etapa_atual, status_caepf, status_protocolo, status_geral, numero_inss").execute()
    df_processos = pd.DataFrame(res_proc.data) if res_proc.data else pd.DataFrame()
    

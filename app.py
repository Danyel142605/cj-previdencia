import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from PIL import Image
import io

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

# 2. BANCO DE DADOS
conn = sqlite3.connect('escritorio_advocacia.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS processos_v3 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_cliente TEXT, cpf TEXT UNIQUE, senha_cliente TEXT, grupo_acao TEXT, etapa_atual TEXT, status_caepf TEXT DEFAULT 'Pendente doc no drive', status_protocolo TEXT DEFAULT 'Pendente doc no drive', status_geral TEXT DEFAULT 'Analise', pdf_rg BLOB, pdf_residencia BLOB, pdf_certidao BLOB, pdf_contrato BLOB, pdf_caepf BLOB, pdf_gps BLOB, numero_inss TEXT, ultima_atualizacao TEXT, usuario_responsavel TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS usuarios_sistema (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, identificador TEXT UNIQUE, senha TEXT, perfil TEXT DEFAULT 'Colaborador', status_liberacao TEXT DEFAULT 'Aguardando Liberação')")

# Garante conta master do ADM
cursor.execute("SELECT COUNT(*) FROM usuarios_sistema WHERE perfil = 'Admin'")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO usuarios_sistema (nome, identificador, senha, perfil, status_liberacao) VALUES ('Administrador Geral', 'admin@cjprevidencia.com.br', 'admin123', 'Admin', 'Liberado')")
conn.commit()

def processar_e_converter_arquivo(arquivo_upload):
    if arquivo_upload is not None:
        nome_arquivo = arquivo_upload.name.lower()
        if nome_arquivo.endswith('.pdf'):
            return arquivo_upload.read()
        elif nome_arquivo.endswith(('.jpg', '.jpeg', '.png')):
            image = Image.open(arquivo_upload)
            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
            pdf_buffer = io.BytesIO()
            image.save(pdf_buffer, format="PDF")
            return pdf_buffer.getvalue()
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
                    cursor.execute("SELECT nome, perfil, status_liberacao FROM usuarios_sistema WHERE identificador = ? AND senha = ?", (login_input, senha_input))
                    user_data = cursor.fetchone()
                    if user_data:
                        nome_user, perfil, status_lib = user_data
                        if status_lib == "Liberado":
                            st.session_state['logado'] = True
                            st.session_state['usuario_atual'] = nome_user
                            st.session_state['perfil_atual'] = perfil
                            st.success("Logado com sucesso!")
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
                        cursor.execute("INSERT INTO usuarios_sistema (nome, identificador, senha, perfil, status_liberacao) VALUES (?, ?, ?, ?, 'Aguardando Liberação')", (nome_novo, login_novo, senha_nova, tipo_perfil))
                        conn.commit()
                        st.success("Cadastrado! Aguarde a liberação do Administrador.")
                    else:
                        st.error("Preencha todos os campos.")
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
    df_usuarios = pd.read_sql_query("SELECT id, nome, identificador, perfil, status_liberacao FROM usuarios_sistema", conn)
    st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
    
    st.write("---")
    if not df_usuarios.empty:
        user_sel = st.selectbox("Selecione o Funcionário para modificar:", df_usuarios['nome'].tolist())
        row_user = df_usuarios[df_usuarios['nome'] == user_sel].iloc[0]
        
        nova_lib = st.selectbox("Alterar Status de Acesso:", ["Liberado", "Aguardando Liberação"], index=["Liberado", "Aguardando Liberação"].index(row_user['status_liberacao']))
        novo_perf = st.selectbox("Mudar Perfil/Cargo:", ["Colaborador", "Admin"], index=["Colaborador", "Admin"].index(row_user['perfil']))
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Salvar Alterações do Funcionário", use_container_width=True):
                cursor.execute("UPDATE usuarios_sistema SET status_liberacao = ?, perfil = ? WHERE id = ?", (nova_lib, novo_perf, int(row_user['id'])))
                conn.commit()
                st.success("Cadastro atualizado!")
                st.rerun()
        with col_b2:
            if st.button("🗑️ DELETAR FUNCIONÁRIO", type="primary", use_container_width=True):
                if row_user['identificador'] == "admin@cjprevidencia.com.br":
                    st.error("Não é possível apagar o Administrador mestre.")
                else:
                    cursor.execute("DELETE FROM usuarios_sistema WHERE id = ?", (int(row_user['id']),))
                    conn.commit()
                    st.success("Funcionário removido.")
                    st.rerun()

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
                cursor.execute("INSERT INTO processos_v3 (nome_cliente, cpf, senha_cliente, grupo_acao, etapa_atual, pdf_rg, pdf_certidao, pdf_residencia, ultima_atualizacao, usuario_responsavel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (nome_c, cpf_c, senha_c, grupo_c, etapa_c, processar_e_converter_arquivo(up_rg), processar_e_converter_arquivo(up_cert), processar_e_converter_arquivo(up_res), agora, st.session_state['usuario_atual']))
                conn.commit()
                st.success("Ficha criada com sucesso!")
            else: st.error("Preencha Nome, CPF e Senha.")

# --- TELA: PROCESSOS ---

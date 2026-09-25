import os
import shutil
import sqlite3
import tempfile
import webbrowser
import base64
import json
import hashlib
import secrets
from datetime import datetime
from PIL import Image
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Configurações Globais de Tema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ==============================================================================
# PALETA VISUAL FIEL AO NOVO DESIGN (macOS / SaaS Enterprise Dark)
# ==============================================================================
THEME = {
    "bg_app": "#121824",           # Fundo geral azul-ardósia escuro
    "sidebar": "#161e2e",          # Sidebar esquerda
    "topbar": "#182132",           # Barra de navegação superior
    "card_main": "#1b2438",        # Card central do formulário
    "card_border": "#28344e",      # Borda refinada dos cards
    "card_right": "#182133",       # Painel lateral direito (Últimos Cadastros)
    "input_bg": "#151c2c",         # Fundo dos campos de digitação
    "input_border": "#2a3752",     # Borda padrão dos campos
    "input_focus": "#3b82f6",      # Foco ativo
    "nav_active": "#ff6363",       # Coral / Salmão vibrante da aba ativa
    "nav_active_text": "#ffffff",  
    "nav_idle": "transparent",     
    "nav_idle_text": "#8e9bb2",    
    "accent_blue": "#3b82f6",      # Azul do botão 'Salvar Cadastro'
    "accent_indigo": "#4f46e5",    # Índigo do botão 'Incluir no Cadastro +'
    "accent_emerald": "#10b981",   # Verde de validação e status Ativo
    "accent_emerald_bg": "#064e3b",
    "text_primary": "#f8fafc",     # Texto principal claro
    "text_muted": "#8a97ae",       # Textos secundários
    "traffic_red": "#ff5f56",      # Controles de janela macOS
    "traffic_yellow": "#ffbd2e",
    "traffic_green": "#27c93f",
    
    # BOTÕES CIRCULARES ESTILIZADOS
    "btn_circle_add": "#3a445d",        # Tom azul-acinzentado (+)
    "btn_circle_add_hover": "#4a5676",
    "btn_circle_add_icon": "#d8e1f5",
    
    "btn_circle_edit": "#544a53",       # Tom marrom/ameixa (✎)
    "btn_circle_edit_hover": "#695c68",
    "btn_circle_edit_icon": "#eedee8",
    
    "btn_circle_del": "#6e454f",        # Tom vinho/rosa queimado (🗑)
    "btn_circle_del_hover": "#865460",
    "btn_circle_del_icon": "#ffd6dc",
    
    "btn_circle_search": "#3e475d",     # Tom azul-ardósia (🔍)
    "btn_circle_search_hover": "#4e5975",
    "btn_circle_search_icon": "#d8e1f5"
}

# ==============================================================================
# SEGURANÇA E CRIPTOGRAFIA DE SENHAS
# ==============================================================================
class SecurityHelper:
    @staticmethod
    def gerar_hash(senha: str) -> tuple:
        salt = secrets.token_hex(16)
        senha_hash = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        return senha_hash, salt

    @staticmethod
    def verificar_senha(senha: str, hash_salvo: str, salt: str) -> bool:
        teste_hash = hashlib.pbkdf2_hmac(
            "sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        return secrets.compare_digest(hash_salvo, teste_hash)

# ==============================================================================
# CAMADA DE BANCO DE DADOS (SQLite WAL Mode)
# ==============================================================================
class DatabaseManager:
    def __init__(self, db_name="recibo_software.db"):
        self.db_path = db_name
        self._init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("PRAGMA journal_mode=WAL;")
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario TEXT UNIQUE NOT NULL,
                    senha_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    nome_completo TEXT NOT NULL,
                    perfil TEXT NOT NULL,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS recibos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    numero TEXT NOT NULL,
                    cliente_nome TEXT NOT NULL,
                    cliente_doc TEXT,
                    referente TEXT NOT NULL,
                    data_recibo TEXT NOT NULL,
                    valor REAL NOT NULL,
                    emitente_nome TEXT,
                    emitente_doc TEXT,
                    emitente_cidade TEXT,
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    tipo_pessoa TEXT,
                    cpf TEXT,
                    cnpj TEXT,
                    email TEXT,
                    data_nasc TEXT,
                    tel1 TEXT,
                    tel2 TEXT,
                    endereco TEXT,
                    bairro TEXT,
                    cidade TEXT,
                    estado TEXT,
                    cep TEXT,
                    obs TEXT,
                    status TEXT DEFAULT 'ATIVO',
                    criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            c.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    chave TEXT PRIMARY KEY,
                    valor TEXT
                )
            """)
            
            # Criação do Administrador Inicial Padrão se não houver usuários
            total_users = c.execute("SELECT COUNT(id) FROM usuarios").fetchone()[0]
            if total_users == 0:
                h, s = SecurityHelper.gerar_hash("admin123")
                c.execute("""
                    INSERT INTO usuarios (usuario, senha_hash, salt, nome_completo, perfil)
                    VALUES (?, ?, ?, ?, ?)
                """, ("admin", h, s, "Administrador Geral", "ADMIN"))
                
            conn.commit()

    def autenticar(self, usuario, senha):
        with self.get_connection() as conn:
            user = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario.strip(),)).fetchone()
            if user and SecurityHelper.verificar_senha(senha, user["senha_hash"], user["salt"]):
                return dict(user)
        return None

    def cadastrar_usuario(self, usuario, senha, nome, perfil="OPERADOR"):
        h, s = SecurityHelper.gerar_hash(senha)
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO usuarios (usuario, senha_hash, salt, nome_completo, perfil)
                VALUES (?, ?, ?, ?, ?)
            """, (usuario.strip(), h, s, nome.strip(), perfil))
            conn.commit()

    def listar_usuarios(self):
        with self.get_connection() as conn:
            return conn.execute("SELECT id, usuario, nome_completo, perfil, criado_em FROM usuarios ORDER BY id ASC").fetchall()

    def excluir_usuario(self, user_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
            conn.commit()

    def set_config(self, chave, valor):
        with self.get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))
            conn.commit()

    def get_config(self, chave, default=""):
        with self.get_connection() as conn:
            row = conn.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
            return row["valor"] if row else default

    def get_proximo_numero_recibo(self):
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(id) AS total FROM recibos").fetchone()
            return str((row["total"] if row else 0) + 1)

    def total_clientes(self):
        with self.get_connection() as conn:
            row = conn.execute("SELECT COUNT(id) as total FROM clientes").fetchone()
            return row["total"] if row else 0

    def ultimos_recibos(self, limite=3):
        with self.get_connection() as conn:
            return conn.execute("SELECT * FROM recibos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()

    def buscar_recibos(self, nome_termo="", ordem="alfabetica_az"):
        query = "SELECT * FROM recibos WHERE cliente_nome LIKE ? OR numero LIKE ?"
        ordens = {
            "alfabetica_az": " ORDER BY cliente_nome ASC",
            "alfabetica_za": " ORDER BY cliente_nome DESC",
            "data_recente": " ORDER BY id DESC",
            "data_antiga": " ORDER BY id ASC"
        }
        query += ordens.get(ordem, " ORDER BY cliente_nome ASC")
        with self.get_connection() as conn:
            param = f"%{nome_termo}%"
            return conn.execute(query, (param, param)).fetchall()

    def exportar_backup_nuvem_json(self):
        with self.get_connection() as conn:
            recibos = [dict(r) for r in conn.execute("SELECT * FROM recibos").fetchall()]
            clientes = [dict(c) for c in conn.execute("SELECT * FROM clientes").fetchall()]
            configs = [dict(cfg) for cfg in conn.execute("SELECT * FROM configuracoes").fetchall()]

        return {
            "app": "Recibo Software Pro",
            "versao": "2.8",
            "sincronizado_em": datetime.now().isoformat(),
            "recibos": recibos,
            "clientes": clientes,
            "configuracoes": configs
        }

    def importar_backup_nuvem_json(self, payload):
        with self.get_connection() as conn:
            c = conn.cursor()
            for rec in payload.get("recibos", []):
                c.execute("""
                    INSERT OR IGNORE INTO recibos (id, tipo, numero, cliente_nome, cliente_doc, referente, data_recibo, valor, emitente_nome, emitente_doc, emitente_cidade)
                    VALUES (:id, :tipo, :numero, :cliente_nome, :cliente_doc, :referente, :data_recibo, :valor, :emitente_nome, :emitente_doc, :emitente_cidade)
                """, rec)

            for cli in payload.get("clientes", []):
                c.execute("""
                    INSERT OR IGNORE INTO clientes (id, nome, tipo_pessoa, cpf, cnpj, email, data_nasc, tel1, tel2, endereco, bairro, cidade, estado, cep, obs, status)
                    VALUES (:id, :nome, :tipo_pessoa, :cpf, :cnpj, :email, :data_nasc, :tel1, :tel2, :endereco, :bairro, :cidade, :estado, :cep, :obs, :status)
                """, cli)

            for cfg in payload.get("configuracoes", []):
                c.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (cfg["chave"], cfg["valor"]))

            conn.commit()

# ==============================================================================
# CONVERSÃO DE VALOR POR EXTENSO
# ==============================================================================
def valor_por_extenso(valor: float) -> str:
    inteiro = int(valor)
    centavos = int(round((valor - inteiro) * 100))

    unidades = ["", "Um", "Dois", "Três", "Quatro", "Cinco", "Seis", "Sete", "Oito", "Nove"]
    dezenas = ["", "Dez", "Vinte", "Trinta", "Quarenta", "Cinquenta", "Sessenta", "Setenta", "Oitenta", "Noventa"]
    teens = ["Dez", "Onze", "Doze", "Treze", "Quatorze", "Quinze", "Dezesseis", "Dezessete", "Dezoito", "Dezenove"]
    centenas = ["", "Cento", "Duzentos", "Trezentos", "Quatrocentos", "Quinhentos", "Seiscentos", "Setecentos", "Oitocentos", "Novecentos"]

    def conv_3(n):
        if n == 100: return "Cem"
        c, r = divmod(n, 100)
        d, u = divmod(r, 10)
        partes = []
        if c: partes.append(centenas[c])
        if d == 1:
            partes.append(teens[u])
        else:
            if d: partes.append(dezenas[d])
            if u: partes.append(unidades[u])
        return " e ".join(partes)

    extenso = conv_3(inteiro) + (" Real" if inteiro == 1 else " Reais") if inteiro > 0 else ""
    if centavos > 0:
        c_ext = conv_3(centavos) + (" Centavo" if centavos == 1 else " Centavos")
        extenso = f"{extenso} e {c_ext}" if extenso else c_ext
    return (extenso.strip() + ".") if extenso else "Zero Reais."

# ==============================================================================
# JANELA DE LOGIN MODERNA
# ==============================================================================
class LoginWindow(ctk.CTkToplevel):
    def __init__(self, parent, db: DatabaseManager, on_success):
        super().__init__(parent)
        self.db = db
        self.on_success = on_success

        self.title("Acesso Restrito - Recibo Software")
        self.geometry("420x460")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_app"])

        # Centraliza na tela
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 460) // 2
        self.geometry(f"+{x}+{y}")
        self.grab_set()

        card = ctk.CTkFrame(self, fg_color=THEME["card_main"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="both", expand=True, padx=24, pady=24)

        # Header macOS
        traffic = ctk.CTkFrame(card, fg_color="transparent")
        traffic.pack(anchor="w", padx=16, pady=(16, 6))
        for cor in [THEME["traffic_red"], THEME["traffic_yellow"], THEME["traffic_green"]]:
            ctk.CTkLabel(traffic, text="●", font=ctk.CTkFont(size=12), text_color=cor).pack(side="left", padx=2)

        ctk.CTkLabel(card, text="RECIBO", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=THEME["text_primary"]).pack(pady=(4, 0))
        ctk.CTkLabel(card, text="Acesso ao Sistema", font=ctk.CTkFont(size=12), text_color=THEME["accent_blue"]).pack(pady=(0, 20))

        # Campos
        ctk.CTkLabel(card, text="USUÁRIO", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", padx=24, pady=(0, 2))
        self.txt_user = ctk.CTkEntry(card, height=40, placeholder_text="Ex: admin", fg_color=THEME["input_bg"], border_color=THEME["input_border"])
        self.txt_user.insert(0, "admin")
        self.txt_user.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="SENHA", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", padx=24, pady=(0, 2))
        self.txt_pass = ctk.CTkEntry(card, height=40, show="•", placeholder_text="Digite sua senha...", fg_color=THEME["input_bg"], border_color=THEME["input_border"])
        self.txt_pass.insert(0, "admin123")
        self.txt_pass.pack(fill="x", padx=24, pady=(0, 20))
        self.txt_pass.bind("<Return>", lambda e: self._fazer_login())

        btn_entrar = ctk.CTkButton(
            card, text="Entrar no Sistema", height=42, corner_radius=10,
            fg_color=THEME["accent_blue"], hover_color="#2563eb",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._fazer_login
        )
        btn_entrar.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(card, text="Padrão inicial: admin | admin123", font=ctk.CTkFont(size=10), text_color=THEME["text_muted"]).pack()

    def _fazer_login(self):
        u = self.txt_user.get().strip()
        p = self.txt_pass.get().strip()

        usuario_autenticado = self.db.autenticar(u, p)
        if usuario_autenticado:
            self.destroy()
            self.on_success(usuario_autenticado)
        else:
            messagebox.showerror("Acesso Negado", "Usuário ou senha inválidos. Tente novamente.")

# ==============================================================================
# APLICAÇÃO PRINCIPAL
# ==============================================================================
class ReciboSoftwareApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.usuario_logado = None

        self.title("RECIBO - SOFTWARE v2.8 (Enterprise)")
        self.geometry("1340x820")
        self.minsize(1180, 720)
        self.configure(fg_color=THEME["bg_app"])

        self.cliente_id_atual = None
        self.recibo_id_atual = None
        self.logo_preview_img = None
        self.nav_btns = {}

        # Oculta a janela principal até autenticar
        self.withdraw()
        LoginWindow(self, self.db, on_success=self._iniciar_sessao)

    def _iniciar_sessao(self, usuario):
        self.usuario_logado = usuario
        self.deiconify()
        self._construir_base()
        self._construir_views()
        self.navegar("cadastros")

    def _construir_base(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ----------------------------------------------------------------------
        # 1. SIDEBAR LATERAL ESQUERDA
        # ----------------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=THEME["sidebar"], border_width=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Controles macOS
        traffic_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        traffic_box.pack(anchor="w", padx=20, pady=(18, 14))

        for cor in [THEME["traffic_red"], THEME["traffic_yellow"], THEME["traffic_green"]]:
            ctk.CTkLabel(traffic_box, text="●", font=ctk.CTkFont(size=14), text_color=cor).pack(side="left", padx=3)

        # Cabeçalho da Marca
        brand_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_box.pack(anchor="w", padx=20, pady=(0, 24))

        ctk.CTkLabel(brand_box, text="RECIBO", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w")
        
        sub_box = ctk.CTkFrame(brand_box, fg_color="transparent")
        sub_box.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(sub_box, text="— SOFTWARE", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=THEME["text_muted"]).pack(side="left")
        
        badge_ver = ctk.CTkLabel(sub_box, text=" v2.8 ", font=ctk.CTkFont(size=9, weight="bold"), fg_color="#20304c", text_color="#60a5fa", corner_radius=4)
        badge_ver.pack(side="left", padx=(6, 0))

        # Botões de Navegação
        self.nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=12, pady=0)

        self._criar_item_nav("📄  RECIBOS", "recibos")
        self.btn_nav_cadastros = self._criar_item_nav("👥  CADASTROS", "cadastros")
        self._criar_item_nav("⚙️  RECURSOS", "recursos")
        self._criar_item_nav("📊  RELATÓRIOS", "relatorios")

        # Histórico Recente
        hist_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        hist_box.pack(fill="x", padx=18, pady=(30, 10))

        ctk.CTkLabel(hist_box, text="HISTÓRICO RECENTE  ⌵", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", pady=(0, 8))
        
        self.box_itens_historico = ctk.CTkFrame(hist_box, fg_color="transparent")
        self.box_itens_historico.pack(fill="x")
        self._atualizar_historico_sidebar()

        # Rodapé: Sincronização em Nuvem
        footer_side = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_side.pack(side="bottom", fill="x", padx=14, pady=16)

        self.btn_cloud_sync = ctk.CTkButton(
            footer_side, text="☁  Sincronizar Nuvem", height=32, corner_radius=8,
            fg_color="#18273d", hover_color="#203452", border_width=1, border_color="#23426e",
            text_color=THEME["accent_emerald"], font=ctk.CTkFont(size=11, weight="bold"),
            command=self._sincronizar_nuvem_acao
        )
        self.btn_cloud_sync.pack(fill="x")

        # ----------------------------------------------------------------------
        # 2. TOP BAR SUPERIOR
        # ----------------------------------------------------------------------
        self.topbar = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color=THEME["topbar"], border_width=0)
        self.topbar.grid(row=0, column=1, sticky="ew", padx=0, pady=0)
        self.topbar.grid_propagate(False)

        top_title = ctk.CTkFrame(self.topbar, fg_color="transparent")
        top_title.pack(side="left", padx=24)
        ctk.CTkLabel(top_title, text="👥", font=ctk.CTkFont(size=16), text_color=THEME["accent_blue"]).pack(side="left", padx=(0, 8))
        self.lbl_view_title = ctk.CTkLabel(top_title, text="Cadastro de Clientes e Fornecedores", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color=THEME["text_primary"])
        self.lbl_view_title.pack(side="left")

        # Seletor de Empresa
        ws_btn = ctk.CTkButton(
            self.topbar, text="Áreas de Trabalho\nTechNova S.A.  ⌵", height=38, corner_radius=8,
            fg_color="transparent", hover_color=THEME["card_main"], text_color=THEME["text_muted"],
            font=ctk.CTkFont(size=11), command=self._abrir_modal_emitente_logo
        )
        ws_btn.pack(side="left", padx=(20, 10))

        # Campo de Busca Global
        self.search_pill = ctk.CTkEntry(
            self.topbar, width=200, height=36, corner_radius=18,
            placeholder_text="🔍  Buscar... (⌘K)", fg_color=THEME["input_bg"],
            border_color=THEME["card_border"], text_color=THEME["text_primary"]
        )
        self.search_pill.pack(side="left", padx=10)
        self.search_pill.bind("<Return>", lambda e: self._busca_global(self.search_pill.get()))

        # Botão Logomarca
        btn_top_logo = ctk.CTkButton(
            self.topbar, text="🖼️ Logomarca", width=105, height=32, corner_radius=16,
            fg_color=THEME["card_main"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"], font=ctk.CTkFont(size=11, weight="bold"),
            command=self._abrir_modal_emitente_logo
        )
        btn_top_logo.pack(side="left", padx=6)

        # Botão Gestão de Usuários (Visível/Acessível apenas ao Administrador)
        if self.usuario_logado and self.usuario_logado["perfil"] == "ADMIN":
            btn_top_users = ctk.CTkButton(
                self.topbar, text="👤 Usuários", width=95, height=32, corner_radius=16,
                fg_color=THEME["card_main"], hover_color=THEME["btn_circle_add_hover"],
                border_width=1, border_color=THEME["accent_blue"], text_color=THEME["accent_blue"],
                font=ctk.CTkFont(size=11, weight="bold"), command=self._abrir_modal_gestao_usuarios
            )
            btn_top_users.pack(side="left", padx=6)

        # Perfil Operador
        user_pill = ctk.CTkFrame(self.topbar, fg_color="transparent")
        user_pill.pack(side="right", padx=24)

        nome_user = self.usuario_logado["nome_completo"] if self.usuario_logado else "Operador"
        perfil_tag = self.usuario_logado["perfil"] if self.usuario_logado else "USER"
        iniciais_user = "".join([p[0] for p in nome_user.split()[:2]]).upper()

        avatar = ctk.CTkLabel(user_pill, text=iniciais_user, font=ctk.CTkFont(size=11, weight="bold"), width=34, height=34, corner_radius=17, fg_color="#2b3b5c", text_color="#93c5fd")
        avatar.pack(side="left", padx=(0, 8))

        u_info = ctk.CTkFrame(user_pill, fg_color="transparent")
        u_info.pack(side="left")
        ctk.CTkLabel(u_info, text=f"{nome_user} ({perfil_tag})", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(u_info, text="● Online", font=ctk.CTkFont(size=10), text_color=THEME["accent_emerald"]).pack(anchor="w")

        # ----------------------------------------------------------------------
        # 3. CONTAINER PRINCIPAL
        # ----------------------------------------------------------------------
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=THEME["bg_app"])
        self.main_container.grid(row=1, column=1, sticky="nsew", padx=16, pady=16)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

    def _criar_item_nav(self, rotulo, chave):
        btn = ctk.CTkButton(
            self.nav_container, text=rotulo, height=44, corner_radius=10, anchor="w",
            fg_color=THEME["nav_idle"], text_color=THEME["nav_idle_text"],
            hover_color="#1c2538", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=lambda k=chave: self.navegar(k)
        )
        btn.pack(fill="x", pady=3)
        self.nav_btns[chave] = btn
        return btn

    def _atualizar_historico_sidebar(self):
        for w in self.box_itens_historico.winfo_children():
            w.destroy()
        recibos = self.db.ultimos_recibos(3)
        if not recibos:
            for it in ["🕒  Histórico recente", "✎  Histórico recente (...)", "☵  Histórico recente"]:
                ctk.CTkLabel(self.box_itens_historico, text=it, font=ctk.CTkFont(size=11), text_color="#5b6b85").pack(anchor="w", pady=2)
        else:
            for r in recibos:
                lbl = f"📄 Nº {r['numero']} - {r['cliente_nome'][:14]}"
                btn = ctk.CTkButton(
                    self.box_itens_historico, text=lbl, anchor="w", height=24, fg_color="transparent",
                    hover_color="#1c2538", text_color="#7b8ba5", font=ctk.CTkFont(size=10),
                    command=lambda rec=r: self._carregar_recibo_historico(rec)
                )
                btn.pack(fill="x", pady=1)

    def navegar(self, destino):
        titulos = {
            "cadastros": "Cadastro de Clientes e Fornecedores",
            "recibos": "Emissão de Recibos de Pagamento",
            "recursos": "Recursos, Backups e Suporte",
            "relatorios": "Relatórios e Consultas Consolidadas"
        }
        self.lbl_view_title.configure(text=titulos.get(destino, "Recibo Software"))

        tot = self.db.total_clientes()
        self.btn_nav_cadastros.configure(text=f"👥  CADASTROS  [{tot}]")

        for chave, frame in self.frames.items():
            frame.grid_forget()
            self.nav_btns[chave].configure(fg_color=THEME["nav_idle"], text_color=THEME["nav_idle_text"])

        self.frames[destino].grid(row=0, column=0, sticky="nsew")
        self.nav_btns[destino].configure(fg_color=THEME["nav_active"], text_color=THEME["nav_active_text"])

        if destino == "cadastros":
            self._recarregar_ultimos_cadastros()
        elif destino == "recibos":
            self.txt_rec_num.delete(0, "end")
            self.txt_rec_num.insert(0, self.db.get_proximo_numero_recibo())
            self._atualizar_preview_logo_recibos()

    def _construir_views(self):
        self.frames = {
            "cadastros": self._view_cadastros(),
            "recibos": self._view_recibos(),
            "recursos": self._view_recursos(),
            "relatorios": self._view_relatorios()
        }

    # ==============================================================================
    # CRIAÇÃO DA BARRA DE 4 BOTÕES CIRCULARES ESTILIZADOS
    # ==============================================================================
    def _criar_botoes_circulares_acao(self, parent_frame, cmd_novo, cmd_editar, cmd_excluir, cmd_buscar):
        actions_bar = ctk.CTkFrame(parent_frame, fg_color="transparent")
        
        btn_add = ctk.CTkButton(
            actions_bar, text="+", width=42, height=42, corner_radius=21,
            fg_color=THEME["btn_circle_add"], hover_color=THEME["btn_circle_add_hover"],
            text_color=THEME["btn_circle_add_icon"], font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            command=cmd_novo
        )
        btn_add.pack(side="left", padx=5)

        btn_edit = ctk.CTkButton(
            actions_bar, text="✎", width=42, height=42, corner_radius=21,
            fg_color=THEME["btn_circle_edit"], hover_color=THEME["btn_circle_edit_hover"],
            text_color=THEME["btn_circle_edit_icon"], font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            command=cmd_editar
        )
        btn_edit.pack(side="left", padx=5)

        btn_del = ctk.CTkButton(
            actions_bar, text="🗑", width=42, height=42, corner_radius=21,
            fg_color=THEME["btn_circle_del"], hover_color=THEME["btn_circle_del_hover"],
            text_color=THEME["btn_circle_del_icon"], font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            command=cmd_excluir
        )
        btn_del.pack(side="left", padx=5)

        btn_search = ctk.CTkButton(
            actions_bar, text="🔍", width=42, height=42, corner_radius=21,
            fg_color=THEME["btn_circle_search"], hover_color=THEME["btn_circle_search_hover"],
            text_color=THEME["btn_circle_search_icon"], font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            command=cmd_buscar
        )
        btn_search.pack(side="left", padx=5)

        return actions_bar

    # ==============================================================================
    # MODAL DE GESTÃO DE USUÁRIOS (EXCLUSIVO PARA ADMIN)
    # ==============================================================================
    def _abrir_modal_gestao_usuarios(self):
        if not self.usuario_logado or self.usuario_logado["perfil"] != "ADMIN":
            messagebox.showerror("Acesso Negado", "Apenas o Administrador pode gerenciar usuários!")
            return

        modal = ctk.CTkToplevel(self)
        modal.title("Gestão de Usuários e Operadores")
        modal.geometry("640x560")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text="CONTROLE DE USUÁRIOS E PERMISSÕES", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["accent_blue"]).pack(pady=(18, 4))
        ctk.CTkLabel(modal, text="Somente o Administrador tem permissão para cadastrar e excluir contas.", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).pack(pady=(0, 14))

        # Bloco de Cadastro de Novo Usuário
        form_box = ctk.CTkFrame(modal, fg_color=THEME["input_bg"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        form_box.pack(fill="x", padx=24, pady=8, ipady=8)

        ctk.CTkLabel(form_box, text="CADASTRAR NOVO USUÁRIO", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", padx=16, pady=(6, 8))

        r1 = ctk.CTkFrame(form_box, fg_color="transparent")
        r1.pack(fill="x", padx=16, pady=2)
        r1.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(r1, text="Nome Completo", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).grid(row=0, column=0, sticky="w")
        txt_nome = ctk.CTkEntry(r1, height=36, corner_radius=8, fg_color=THEME["card_main"], border_color=THEME["card_border"])
        txt_nome.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(r1, text="Nome de Usuário (Login)", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).grid(row=0, column=1, sticky="w")
        txt_user = ctk.CTkEntry(r1, height=36, corner_radius=8, fg_color=THEME["card_main"], border_color=THEME["card_border"])
        txt_user.grid(row=1, column=1, sticky="ew")

        r2 = ctk.CTkFrame(form_box, fg_color="transparent")
        r2.pack(fill="x", padx=16, pady=(8, 12))
        r2.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(r2, text="Senha de Acesso", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).grid(row=0, column=0, sticky="w")
        txt_pass = ctk.CTkEntry(r2, height=36, corner_radius=8, show="•", fg_color=THEME["card_main"], border_color=THEME["card_border"])
        txt_pass.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkLabel(r2, text="Perfil / Nível", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).grid(row=0, column=1, sticky="w")
        cb_perfil = ctk.CTkComboBox(r2, values=["OPERADOR", "ADMIN"], height=36, corner_radius=8, fg_color=THEME["card_main"], border_color=THEME["card_border"])
        cb_perfil.set("OPERADOR")
        cb_perfil.grid(row=1, column=1, sticky="ew")

        def add_user():
            u = txt_user.get().strip()
            p = txt_pass.get().strip()
            n = txt_nome.get().strip()
            perf = cb_perfil.get()

            if not u or not p or not n:
                messagebox.showwarning("Atenção", "Preencha todos os campos do usuário!")
                return
            try:
                self.db.cadastrar_usuario(u, p, n, perf)
                txt_nome.delete(0, "end"); txt_user.delete(0, "end"); txt_pass.delete(0, "end")
                carregar_lista_usuarios()
                messagebox.showinfo("Sucesso", f"Usuário '{u}' cadastrado com sucesso!")
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro", "Nome de usuário já existe no sistema.")

        ctk.CTkButton(form_box, text="+ Adicionar Usuário", height=36, corner_radius=8, fg_color=THEME["accent_emerald"], hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=add_user).pack(padx=16, pady=(0, 4))

        # Lista de Usuários Ativos
        ctk.CTkLabel(modal, text="USUÁRIOS CADASTRADOS", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", padx=24, pady=(10, 4))
        scroll_users = ctk.CTkScrollableFrame(modal, fg_color=THEME["input_bg"], corner_radius=12)
        scroll_users.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        def carregar_lista_usuarios():
            for w in scroll_users.winfo_children(): w.destroy()
            users = self.db.listar_usuarios()
            for u in users:
                row = ctk.CTkFrame(scroll_users, fg_color=THEME["card_main"], corner_radius=8)
                row.pack(fill="x", pady=3, padx=4)

                txt_lbl = f"{u['nome_completo']} ({u['usuario']}) - [{u['perfil']}]"
                ctk.CTkLabel(row, text=txt_lbl, font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_primary"]).pack(side="left", padx=12, pady=8)

                if u["usuario"] != "admin" and u["id"] != self.usuario_logado["id"]:
                    btn_del = ctk.CTkButton(
                        row, text="Remover", width=80, height=28, corner_radius=6,
                        fg_color=THEME["btn_circle_del"], hover_color=THEME["btn_circle_del_hover"],
                        text_color=THEME["btn_circle_del_icon"], font=ctk.CTkFont(size=10, weight="bold"),
                        command=lambda uid=u["id"]: [self.db.excluir_usuario(uid), carregar_lista_usuarios()]
                    )
                    btn_del.pack(side="right", padx=10)

        carregar_lista_usuarios()

    # ==============================================================================
    # 1. VIEW CADASTROS
    # ==============================================================================
    def _view_cadastros(self):
        root = ctk.CTkFrame(self.main_container, fg_color="transparent")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=4)
        root.grid_columnconfigure(1, weight=1)

        center_col = ctk.CTkFrame(root, fg_color="transparent")
        center_col.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        center_col.grid_rowconfigure(1, weight=1)
        center_col.grid_columnconfigure(0, weight=1)

        top_switch = ctk.CTkFrame(center_col, fg_color="transparent")
        top_switch.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            top_switch, text="<  1. Identificação (ativo)  ➔  2. Contatos & Docs  ➔  3. Endereço",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]
        ).pack(side="left")

        btn_logo_tab = ctk.CTkButton(
            top_switch, text="🖼️  Logomarca da Empresa", height=32, corner_radius=16,
            fg_color=THEME["card_main"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["accent_blue"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11, weight="bold"), command=self._abrir_modal_emitente_logo
        )
        btn_logo_tab.pack(side="right")

        card_form = ctk.CTkFrame(center_col, fg_color=THEME["card_main"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_form.grid(row=1, column=0, sticky="nsew")

        scroll = ctk.CTkScrollableFrame(card_form, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=22, pady=16)

        ctk.CTkLabel(
            scroll, text="01 | IDENTIFICAÇÃO E DADOS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=THEME["text_muted"]
        ).pack(anchor="w", pady=(4, 10))

        r0 = ctk.CTkFrame(scroll, fg_color="transparent")
        r0.pack(fill="x", pady=3)
        r0.grid_columnconfigure(0, weight=1)
        r0.grid_columnconfigure(1, weight=3)

        self.txt_cad_id = ctk.CTkEntry(
            r0, width=130, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_id.insert(0, f"{self.db.total_clientes()+1:03d}")
        self.txt_cad_id.grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.cb_cad_tipo = ctk.CTkComboBox(
            r0, values=["Jurídica", "Física"], height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"],
            text_color=THEME["text_primary"], button_color=THEME["input_border"]
        )
        self.cb_cad_tipo.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(scroll, text="Nome/Razão Social", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w", pady=(8, 2))
        self.txt_cad_nome = ctk.CTkEntry(
            scroll, height=40, corner_radius=8, placeholder_text="Razão Social ou Nome Completo...",
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_nome.insert(0, "Carlos Eduardo de Souza S.A.")
        self.txt_cad_nome.pack(fill="x", pady=(0, 8))

        r1 = ctk.CTkFrame(scroll, fg_color="transparent")
        r1.pack(fill="x", pady=2)
        r1.grid_columnconfigure(0, weight=3)
        r1.grid_columnconfigure(1, weight=2)
        r1.grid_columnconfigure(2, weight=3)

        ctk.CTkLabel(r1, text="CPF/CNPJ", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=0, sticky="w")
        f_cnpj = ctk.CTkFrame(r1, fg_color="transparent")
        f_cnpj.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))
        
        self.txt_cad_cnpj = ctk.CTkEntry(
            f_cnpj, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_cnpj.insert(0, "12.345.678/0001-90")
        self.txt_cad_cnpj.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_cnpj, text=" ✓ ", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["accent_emerald"]).pack(side="left", padx=4)

        ctk.CTkLabel(r1, text="CPF", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=1, sticky="w")
        self.txt_cad_cpf = ctk.CTkEntry(
            r1, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_cpf.insert(0, "-")
        self.txt_cad_cpf.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(2, 0))

        btn_inc = ctk.CTkButton(
            r1, text="Incluir no Cadastro  +", height=38, corner_radius=8,
            fg_color=THEME["accent_indigo"], hover_color="#4338ca",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._salvar_cliente_form
        )
        btn_inc.grid(row=1, column=2, sticky="ew", pady=(2, 0))

        r2 = ctk.CTkFrame(scroll, fg_color="transparent")
        r2.pack(fill="x", pady=(10, 4))
        r2.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(r2, text="Documento & Contatos", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=0, sticky="w")
        self.txt_cad_email = ctk.CTkEntry(
            r2, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_email.insert(0, "contato@carlos-desouza.co")
        self.txt_cad_email.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r2, text="Data Nasc./Abertura", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=1, sticky="w")
        f_dt = ctk.CTkFrame(r2, fg_color="transparent")
        f_dt.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 0))
        self.txt_cad_data = ctk.CTkEntry(
            f_dt, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_data.insert(0, "10/05/2015")
        self.txt_cad_data.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_dt, text=" 🗓 ", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).pack(side="left")

        ctk.CTkLabel(r2, text="Telefone 1", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=2, sticky="w")
        self.txt_cad_tel1 = ctk.CTkEntry(
            r2, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_tel1.insert(0, "(11) 98765-4321")
        self.txt_cad_tel1.grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r2, text="Telefone 2", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=3, sticky="w")
        self.txt_cad_tel2 = ctk.CTkEntry(
            r2, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_tel2.grid(row=1, column=3, sticky="ew", pady=(2, 0))

        ctk.CTkLabel(scroll, text="E-mail", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).pack(anchor="w", pady=(1, 10))

        ctk.CTkLabel(
            scroll, text="02 | ENDEREÇO & OBSERVAÇÕES",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=THEME["text_muted"]
        ).pack(anchor="w", pady=(10, 8))

        r3 = ctk.CTkFrame(scroll, fg_color="transparent")
        r3.pack(fill="x", pady=2)
        r3.grid_columnconfigure(0, weight=4)
        r3.grid_columnconfigure(1, weight=2)
        r3.grid_columnconfigure(2, weight=3)
        r3.grid_columnconfigure(3, weight=1)
        r3.grid_columnconfigure(4, weight=2)

        ctk.CTkLabel(r3, text="Endereço", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=0, sticky="w")
        self.txt_cad_end = ctk.CTkEntry(
            r3, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_end.insert(0, "Av. Paulista, 1000 - Cj 42")
        self.txt_cad_end.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r3, text="Bairro", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=1, sticky="w")
        self.txt_cad_bairro = ctk.CTkEntry(
            r3, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_bairro.insert(0, "Bela Vista")
        self.txt_cad_bairro.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r3, text="Cidade", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=2, sticky="w")
        self.txt_cad_cid = ctk.CTkEntry(
            r3, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_cid.insert(0, "São Paulo")
        self.txt_cad_cid.grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r3, text="Estado", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=3, sticky="w")
        self.cb_cad_uf = ctk.CTkComboBox(
            r3, values=["SP", "RJ", "MG", "ES", "PR", "SC", "RS", "BA", "DF"], width=75, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"], button_color=THEME["input_border"]
        )
        self.cb_cad_uf.set("SP")
        self.cb_cad_uf.grid(row=1, column=3, sticky="ew", padx=(0, 8), pady=(2, 0))

        ctk.CTkLabel(r3, text="CEP", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=4, sticky="w")
        f_cep = ctk.CTkFrame(r3, fg_color="transparent")
        f_cep.grid(row=1, column=4, sticky="ew", pady=(2, 0))
        self.txt_cad_cep = ctk.CTkEntry(
            f_cep, height=38, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_cep.insert(0, "01310-100")
        self.txt_cad_cep.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_cep, text=" ✓ ", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["accent_emerald"]).pack(side="left", padx=3)

        ctk.CTkLabel(scroll, text="Observações", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w", pady=(10, 2))
        self.txt_cad_obs = ctk.CTkEntry(
            scroll, height=44, corner_radius=8,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        self.txt_cad_obs.insert(0, "Cliente preferencial, faturamento mensal via PIX.")
        self.txt_cad_obs.pack(fill="x", pady=(0, 10))

        # BARRA DE AÇÕES INFERIOR
        bot_bar = ctk.CTkFrame(center_col, height=54, fg_color="transparent")
        bot_bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        ctk.CTkButton(
            bot_bar, text="Salvar Cadastro", width=140, height=38, corner_radius=19,
            fg_color=THEME["accent_blue"], hover_color="#2563eb",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._salvar_cliente_form
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            bot_bar, text="Cancelar", width=110, height=38, corner_radius=19,
            fg_color=THEME["card_main"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"],
            text_color=THEME["text_muted"], font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self._limpar_cliente_form
        ).pack(side="left")

        # 4 BOTÕES CIRCULARES DE AÇÃO
        botoes_circulares = self._criar_botoes_circulares_acao(
            bot_bar,
            cmd_novo=self._limpar_cliente_form,
            cmd_editar=self._salvar_cliente_form,
            cmd_excluir=self._excluir_cliente_db,
            cmd_buscar=self._modal_buscar_cliente
        )
        botoes_circulares.pack(side="right")

        # PAINEL DIREITO: ÚLTIMOS CADASTROS
        right_panel = ctk.CTkFrame(root, fg_color=THEME["card_right"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        right_panel.grid(row=0, column=1, sticky="nsew")

        h_right = ctk.CTkFrame(right_panel, fg_color="transparent")
        h_right.pack(fill="x", padx=16, pady=(16, 12))
        ctk.CTkLabel(h_right, text="👤  ÚLTIMOS CADASTROS", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w")

        self.scroll_ultimos = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        self.scroll_ultimos.pack(fill="both", expand=True, padx=12, pady=6)

        return root

    # ==============================================================================
    # MODAL DE PESQUISA POR NOME & ORDEM ALFABÉTICA DOS RECIBOS
    # ==============================================================================
    def _abrir_modal_pesquisa_alfabetica_recibos(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Pesquisa de Recibos - Ordem Alfabética")
        modal.geometry("640x520")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text="CONSULTA E ORDENAÇÃO DE RECIBOS", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["accent_blue"]).pack(pady=(16, 4))
        
        filter_bar = ctk.CTkFrame(modal, fg_color="transparent")
        filter_bar.pack(fill="x", padx=18, pady=8)

        txt_busca_nome = ctk.CTkEntry(
            filter_bar, height=38, corner_radius=8,
            placeholder_text="Buscar por nome do cliente ou número...",
            fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"]
        )
        txt_busca_nome.pack(side="left", fill="x", expand=True, padx=(0, 10))

        cb_ordem = ctk.CTkComboBox(
            filter_bar, values=["Ordem A-Z", "Ordem Z-A", "Mais Recentes", "Mais Antigos"],
            height=38, corner_radius=8, width=140,
            fg_color=THEME["input_bg"], border_color=THEME["input_border"],
            text_color=THEME["text_primary"], button_color=THEME["input_border"]
        )
        cb_ordem.set("Ordem A-Z")
        cb_ordem.pack(side="left")

        scroll_resultados = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll_resultados.pack(fill="both", expand=True, padx=18, pady=10)

        def atualizar_lista():
            for w in scroll_resultados.winfo_children(): w.destroy()

            mapa_ordens = {
                "Ordem A-Z": "alfabetica_az",
                "Ordem Z-A": "alfabetica_za",
                "Mais Recentes": "data_recente",
                "Mais Antigos": "data_antiga"
            }
            chave_ordem = mapa_ordens.get(cb_ordem.get(), "alfabetica_az")
            termo = txt_busca_nome.get().strip()

            recibos = self.db.buscar_recibos(nome_termo=termo, ordem=chave_ordem)
            if not recibos:
                ctk.CTkLabel(scroll_resultados, text="Nenhum recibo localizado.", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).pack(pady=20)
                return

            for r in recibos:
                item_card = ctk.CTkFrame(scroll_resultados, fg_color=THEME["input_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
                item_card.pack(fill="x", pady=4, padx=2)

                c_info = ctk.CTkFrame(item_card, fg_color="transparent")
                c_info.pack(side="left", fill="both", expand=True, padx=12, pady=8)

                ctk.CTkLabel(c_info, text=f"Nº {r['numero']}  •  {r['cliente_nome']}", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_primary"], anchor="w").pack(fill="x")
                ctk.CTkLabel(c_info, text=f"Data: {r['data_recibo']}  |  Valor: R$ {r['valor']:,.2f}  |  Ref: {r['referente'][:30]}", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"], anchor="w").pack(fill="x", pady=(2, 0))

                btn_carregar = ctk.CTkButton(
                    item_card, text="Abrir no Recibo", width=120, height=32, corner_radius=6,
                    fg_color=THEME["accent_blue"], hover_color="#2563eb", font=ctk.CTkFont(size=11, weight="bold"),
                    command=lambda rec=r: [self._carregar_recibo_historico(rec), modal.destroy()]
                )
                btn_carregar.pack(side="right", padx=10)

        txt_busca_nome.bind("<KeyRelease>", lambda e: atualizar_lista())
        cb_ordem.configure(command=lambda e: atualizar_lista())
        atualizar_lista()

    # ==============================================================================
    # SINCRONIZAÇÃO EM NUVEM
    # ==============================================================================
    def _sincronizar_nuvem_acao(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Sincronização em Nuvem")
        modal.geometry("460x320")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text="☁  SALVAMENTO EM NUVEM", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["accent_emerald"]).pack(pady=(20, 6))
        ctk.CTkLabel(modal, text="Exporte ou importe a base sincronizada com sua pasta de nuvem\n(Google Drive, OneDrive, Dropbox ou Servidor Local).", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"], justify="center").pack(pady=(0, 16))

        box = ctk.CTkFrame(modal, fg_color=THEME["input_bg"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        box.pack(fill="x", padx=24, pady=8, ipady=8)

        def exportar_nuvem():
            caminho = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("Backup Nuvem JSON", "*.json")],
                initialfile=f"recibo_cloud_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            if caminho:
                try:
                    payload = self.db.exportar_backup_nuvem_json()
                    with open(caminho, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    self.btn_cloud_sync.configure(text="☁  Sincronizado Agora")
                    messagebox.showinfo("Sucesso", "Base completa exportada e sincronizada com sucesso!")
                    modal.destroy()
                except Exception as err:
                    messagebox.showerror("Erro", f"Falha na exportação: {err}")

        def importar_nuvem():
            caminho = filedialog.askopenfilename(filetypes=[("Backup Nuvem JSON", "*.json")])
            if caminho:
                try:
                    with open(caminho, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    self.db.importar_backup_nuvem_json(payload)
                    self.navegar("cadastros")
                    self._atualizar_historico_sidebar()
                    self.btn_cloud_sync.configure(text="☁  Sincronizado Agora")
                    messagebox.showinfo("Sucesso", "Dados importados e mesclados com sucesso!")
                    modal.destroy()
                except Exception as err:
                    messagebox.showerror("Erro", f"Falha ao carregar arquivo de nuvem: {err}")

        ctk.CTkButton(box, text="⬆  Salvar / Exportar para Nuvem", height=40, corner_radius=8, fg_color=THEME["accent_emerald"], hover_color="#059669", font=ctk.CTkFont(weight="bold"), command=exportar_nuvem).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(box, text="⬇  Carregar / Importar da Nuvem", height=40, corner_radius=8, fg_color=THEME["accent_blue"], hover_color="#2563eb", font=ctk.CTkFont(weight="bold"), command=importar_nuvem).pack(fill="x", padx=16, pady=6)
        ctk.CTkButton(modal, text="Fechar", width=100, height=32, corner_radius=6, fg_color=THEME["circle_btn"], hover_color=THEME["btn_circle_add_hover"], command=modal.destroy).pack(pady=10)

    # ==============================================================================
    # MODAL DE LOGOMARCA E EMITENTE
    # ==============================================================================
    def _abrir_modal_emitente_logo(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Configurações da Empresa & Logomarca")
        modal.geometry("560x580")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text="EMITENTE & LOGOMARCA", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["accent_blue"]).pack(pady=(18, 4))
        ctk.CTkLabel(modal, text="Defina os dados da empresa e a imagem que aparecerá nos recibos impressos.", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).pack(pady=(0, 14))

        box_logo = ctk.CTkFrame(modal, fg_color=THEME["input_bg"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        box_logo.pack(fill="x", padx=24, pady=8, ipady=10)

        lbl_preview = ctk.CTkLabel(
            box_logo, text="Sem Logomarca\nCarregada", width=220, height=100,
            fg_color=THEME["card_main"], text_color=THEME["text_muted"], corner_radius=10,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        lbl_preview.pack(pady=(8, 10))

        def refresh_preview():
            p = self.db.get_config("logo_path", "")
            if not p or not os.path.exists(p):
                if os.path.exists("Logo.jpg"): p = os.path.abspath("Logo.jpg")
            if p and os.path.exists(p):
                try:
                    pil = Image.open(p)
                    w, h = pil.size
                    prop = min(220 / w, 100 / h)
                    nw, nh = max(1, int(w * prop)), max(1, int(h * prop))
                    img_ctk = ctk.CTkImage(light_image=pil, dark_image=pil, size=(nw, nh))
                    lbl_preview.configure(image=img_ctk, text="")
                    return
                except Exception: pass
            lbl_preview.configure(image="", text="Sem Logomarca\nCarregada")

        refresh_preview()

        b_row = ctk.CTkFrame(box_logo, fg_color="transparent")
        b_row.pack(pady=4)

        def pick_logo():
            caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg *.jpeg *.png *.bmp")])
            if caminho:
                try:
                    dest = os.path.abspath("Logo.jpg")
                    Image.open(caminho).convert("RGB").save(dest, "JPEG")
                    self.db.set_config("logo_path", dest)
                    refresh_preview()
                    self._atualizar_preview_logo_recibos()
                    messagebox.showinfo("Sucesso", "Logomarca salva e atualizada com sucesso!")
                except Exception as err:
                    messagebox.showerror("Erro", f"Falha ao carregar imagem: {err}")

        def delete_logo():
            self.db.set_config("logo_path", "")
            if os.path.exists("Logo.jpg"):
                try: os.remove("Logo.jpg")
                except Exception: pass
            refresh_preview()
            self._atualizar_preview_logo_recibos()
            messagebox.showinfo("Sucesso", "Logomarca removida com sucesso!")

        ctk.CTkButton(b_row, text="📁 Localizar Logomarca", width=170, height=36, corner_radius=8, fg_color=THEME["accent_blue"], font=ctk.CTkFont(weight="bold"), command=pick_logo).pack(side="left", padx=6)
        ctk.CTkButton(b_row, text="🗑 Excluir Logo", width=130, height=36, corner_radius=8, fg_color=THEME["btn_circle_del"], hover_color=THEME["btn_circle_del_hover"], text_color=THEME["btn_circle_del_icon"], command=delete_logo).pack(side="left", padx=6)

        f_empresa = ctk.CTkFrame(modal, fg_color="transparent")
        f_empresa.pack(fill="x", padx=24, pady=12)

        ctk.CTkLabel(f_empresa, text="Nome da Empresa / Profissional", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w")
        txt_em_nome = ctk.CTkEntry(f_empresa, height=38, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        txt_em_nome.insert(0, self.db.get_config("emitente_nome", "TechNova S.A."))
        txt_em_nome.pack(fill="x", pady=(2, 8))

        r_em = ctk.CTkFrame(f_empresa, fg_color="transparent")
        r_em.pack(fill="x")
        r_em.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(r_em, text="CPF / CNPJ do Emitente", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=0, sticky="w")
        txt_em_doc = ctk.CTkEntry(r_em, height=38, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        txt_em_doc.insert(0, self.db.get_config("emitente_doc", "00.000.000/0001-00"))
        txt_em_doc.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(2, 0))

        ctk.CTkLabel(r_em, text="Cidade do Emitente", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).grid(row=0, column=1, sticky="w")
        txt_em_cid = ctk.CTkEntry(r_em, height=38, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        txt_em_cid.insert(0, self.db.get_config("emitente_cidade", "São Paulo"))
        txt_em_cid.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(2, 0))

        def salvar_empresa():
            self.db.set_config("emitente_nome", txt_em_nome.get().strip())
            self.db.set_config("emitente_doc", txt_em_doc.get().strip())
            self.db.set_config("emitente_cidade", txt_em_cid.get().strip())
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
            modal.destroy()

        ctk.CTkButton(modal, text="Salvar Todas as Configurações", height=42, corner_radius=10, fg_color=THEME["accent_emerald"], hover_color="#059669", font=ctk.CTkFont(size=13, weight="bold"), command=salvar_empresa).pack(pady=16)

    # ==============================================================================
    # 2. VIEW RECIBOS
    # ==============================================================================
    def _view_recibos(self):
        root = ctk.CTkFrame(self.main_container, fg_color="transparent")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=3)
        root.grid_columnconfigure(1, weight=1)

        card_form = ctk.CTkFrame(root, fg_color=THEME["card_main"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card_form.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        scroll = ctk.CTkScrollableFrame(card_form, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=20)

        ctk.CTkLabel(scroll, text="EMISSÃO DE RECIBOS DE PAGAMENTO", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"]).pack(anchor="w", pady=(0, 12))

        logo_quick = ctk.CTkFrame(scroll, fg_color=THEME["input_bg"], corner_radius=10, border_width=1, border_color=THEME["card_border"])
        logo_quick.pack(fill="x", pady=(0, 14), ipady=4)

        self.lbl_logo_recibo_thumb = ctk.CTkLabel(logo_quick, text="[Logomarca Ativa no Recibo]", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"])
        self.lbl_logo_recibo_thumb.pack(side="left", padx=16)

        ctk.CTkButton(logo_quick, text="Alterar Logo", width=110, height=28, corner_radius=6, fg_color=THEME["btn_circle_add"], hover_color=THEME["btn_circle_add_hover"], text_color=THEME["text_primary"], command=self._abrir_modal_emitente_logo).pack(side="right", padx=14)

        r1 = ctk.CTkFrame(scroll, fg_color="transparent")
        r1.pack(fill="x", pady=4)
        r1.grid_columnconfigure(0, weight=3)
        r1.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(r1, text="Tipo de Operação", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=0, column=0, sticky="w")
        self.cb_rec_tipo = ctk.CTkComboBox(r1, values=["Pagamento", "Recebimento"], height=40, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], button_color=THEME["input_border"])
        self.cb_rec_tipo.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))

        ctk.CTkLabel(r1, text="Nº Documento", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=0, column=1, sticky="w")
        self.txt_rec_num = ctk.CTkEntry(r1, height=40, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"], font=ctk.CTkFont(weight="bold"))
        self.txt_rec_num.insert(0, self.db.get_proximo_numero_recibo())
        self.txt_rec_num.grid(row=1, column=1, sticky="ew", pady=(2, 0))

        ctk.CTkLabel(scroll, text="Recebi(emos) de / Beneficiário", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w", pady=(10, 2))
        self.txt_rec_cli = ctk.CTkEntry(scroll, height=40, corner_radius=8, placeholder_text="Nome completo ou Razão Social...", fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        self.txt_rec_cli.pack(fill="x")

        ctk.CTkLabel(scroll, text="CPF / CNPJ", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w", pady=(8, 2))
        self.txt_rec_doc = ctk.CTkEntry(scroll, height=40, corner_radius=8, placeholder_text="000.000.000-00", fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        self.txt_rec_doc.pack(fill="x")

        ctk.CTkLabel(scroll, text="Referente à", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(anchor="w", pady=(8, 2))
        self.txt_rec_ref = ctk.CTkEntry(scroll, height=48, corner_radius=8, placeholder_text="Descrição dos serviços ou produtos...", fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        self.txt_rec_ref.pack(fill="x")

        r2 = ctk.CTkFrame(scroll, fg_color="transparent")
        r2.pack(fill="x", pady=10)
        r2.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(r2, text="Data de Emissão", font=ctk.CTkFont(size=12), text_color=THEME["text_muted"]).grid(row=0, column=0, sticky="w")
        self.txt_rec_data = ctk.CTkEntry(r2, height=40, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["text_primary"])
        self.txt_rec_data.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.txt_rec_data.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(2, 0))

        ctk.CTkLabel(r2, text="Valor Total (R$)", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["accent_emerald"]).grid(row=0, column=1, sticky="w")
        self.txt_rec_val = ctk.CTkEntry(r2, height=40, corner_radius=8, fg_color=THEME["input_bg"], border_color=THEME["input_border"], text_color=THEME["accent_emerald"], font=ctk.CTkFont(size=14, weight="bold"))
        self.txt_rec_val.insert(0, "1,00")
        self.txt_rec_val.grid(row=1, column=1, sticky="ew", pady=(2, 0))

        side_print = ctk.CTkFrame(root, fg_color=THEME["card_right"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        side_print.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(side_print, text="IMPRESSÃO", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_primary"]).pack(pady=(24, 16))

        ctk.CTkButton(
            side_print, text="🖨️\n\nIMPRIMIR\n1 Recibo / Folha", height=140, corner_radius=12,
            fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"],
            font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.imprimir_recibo(1)
        ).pack(fill="x", padx=16, pady=10)

        ctk.CTkButton(
            side_print, text="🖨️ 🖨️\n\nIMPRIMIR\n2 Recibos / Folha", height=140, corner_radius=12,
            fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1.5, border_color=THEME["accent_blue"], text_color=THEME["accent_blue"],
            font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.imprimir_recibo(2)
        ).pack(fill="x", padx=16, pady=10)

        return root

    def _atualizar_preview_logo_recibos(self):
        p = self.db.get_config("logo_path", "")
        if not p or not os.path.exists(p):
            if os.path.exists("Logo.jpg"): p = os.path.abspath("Logo.jpg")
        if p and os.path.exists(p):
            try:
                pil = Image.open(p)
                w, h = pil.size
                prop = min(120 / w, 40 / h)
                img_ctk = ctk.CTkImage(light_image=pil, dark_image=pil, size=(int(w*prop), int(h*prop)))
                self.lbl_logo_recibo_thumb.configure(image=img_ctk, text="")
                return
            except Exception: pass
        self.lbl_logo_recibo_thumb.configure(image="", text="[Logomarca Ativa no Recibo]")

    # ==============================================================================
    # 3. VIEW RECURSOS
    # ==============================================================================
    def _view_recursos(self):
        root = ctk.CTkFrame(self.main_container, fg_color="transparent")
        card = ctk.CTkFrame(root, fg_color=THEME["card_main"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="both", expand=True)

        center = ctk.CTkFrame(card, fg_color="transparent")
        center.pack(expand=True)

        ctk.CTkButton(
            center, text="💾\n\nBACKUP LOCAL SQLITE\nExportar Base Completa", width=240, height=170, corner_radius=14,
            fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self._executar_backup
        ).pack(side="left", padx=15)

        ctk.CTkButton(
            center, text="☁\n\nSINCRONIZAÇÃO NUVEM\nBackup em Nuvem JSON", width=240, height=170, corner_radius=14,
            fg_color=THEME["input_bg"], text_color=THEME["accent_emerald"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self._sincronizar_nuvem_acao
        ).pack(side="left", padx=15)

        ctk.CTkButton(
            center, text="📖\n\nSUPORTE & CONTATO\nRobson Cadete", width=240, height=170, corner_radius=14,
            fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"], font=ctk.CTkFont(size=14, weight="bold"),
            command=self._modal_sobre
        ).pack(side="left", padx=15)

        return root

    def _modal_sobre(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Suporte & Desenvolvedor")
        modal.geometry("450x330")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text="RECIBO SOFTWARE PRO v2.8", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["accent_blue"]).pack(pady=(22, 6))
        
        info = ctk.CTkFrame(modal, fg_color=THEME["input_bg"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        info.pack(fill="x", padx=24, pady=16, ipady=8)

        ctk.CTkLabel(info, text="Desenvolvido por:", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).pack(pady=(4, 1))
        ctk.CTkLabel(info, text="Robson Cadete", font=ctk.CTkFont(size=16, weight="bold"), text_color=THEME["text_primary"]).pack()
        ctk.CTkLabel(info, text="📞 WhatsApp / Tel: (21) 97462-3033", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack(pady=(8, 2))
        ctk.CTkLabel(info, text="✉️ E-mail: robson.cadete@gmail.com", font=ctk.CTkFont(size=12), text_color=THEME["text_primary"]).pack()

        ctk.CTkButton(modal, text="Fechar", width=120, height=36, corner_radius=8, fg_color=THEME["accent_blue"], command=modal.destroy).pack(pady=8)

    # ==============================================================================
    # 4. VIEW RELATÓRIOS
    # ==============================================================================
    def _view_relatorios(self):
        root = ctk.CTkFrame(self.main_container, fg_color="transparent")
        card = ctk.CTkFrame(root, fg_color=THEME["card_main"], corner_radius=16, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="both", expand=True)

        center = ctk.CTkFrame(card, fg_color="transparent")
        center.pack(expand=True)

        reports = [
            ("🔄", "TODOS OS RECIBOS", None),
            ("📤", "RECIBOS PAGAMENTO", "Pagamento"),
            ("📥", "RECIBOS RECEBIMENTO", "Recebimento")
        ]

        for icon, title, filtro in reports:
            ctk.CTkButton(
                center, text=f"{icon}\n\n{title}", width=210, height=150, corner_radius=14,
                fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
                border_width=1, border_color=THEME["card_border"], font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda t=title, fil=filtro: self._modal_relatorio(t, fil)
            ).pack(side="left", padx=14)

        return root

    def _modal_relatorio(self, rotulo, tipo_filtro):
        modal = ctk.CTkToplevel(self)
        modal.title(f"Relatório - {rotulo}")
        modal.geometry("400x230")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"Filtro: {rotulo}", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_primary"]).pack(pady=(16, 12))

        grid = ctk.CTkFrame(modal, fg_color="transparent")
        grid.pack(pady=6)

        ctk.CTkLabel(grid, text="Data Inicial", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).grid(row=0, column=0, padx=8)
        txt_i = ctk.CTkEntry(grid, width=120, height=36, fg_color=THEME["input_bg"])
        txt_i.insert(0, "01/01/" + str(datetime.now().year))
        txt_i.grid(row=1, column=0, padx=8, pady=(2, 0))

        ctk.CTkLabel(grid, text="Data Final", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).grid(row=0, column=1, padx=8)
        txt_f = ctk.CTkEntry(grid, width=120, height=36, fg_color=THEME["input_bg"])
        txt_f.insert(0, datetime.now().strftime("%d/%m/%Y"))
        txt_f.grid(row=1, column=1, padx=8, pady=(2, 0))

        def process():
            di, df = txt_i.get().strip(), txt_f.get().strip()
            try:
                datetime.strptime(di, "%d/%m/%Y")
                datetime.strptime(df, "%d/%m/%Y")
            except ValueError:
                messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/AAAA.")
                return

            q = "SELECT *, substr(data_recibo,7,4)||'-'||substr(data_recibo,4,2)||'-'||substr(data_recibo,1,2) as dt_iso FROM recibos WHERE dt_iso BETWEEN ? AND ?"
            params = [datetime.strptime(di, "%d/%m/%Y").strftime("%Y-%m-%d"), datetime.strptime(df, "%d/%m/%Y").strftime("%Y-%m-%d")]
            if tipo_filtro:
                q += " AND tipo = ?"
                params.append(tipo_filtro)
            q += " ORDER BY id DESC"

            with self.db.get_connection() as conn:
                registros = conn.execute(q, params).fetchall()

            if not registros:
                messagebox.showinfo("Aviso", "Nenhum recibo localizado para o período.")
                return

            modal.destroy()
            total = sum(r["valor"] for r in registros)
            linhas = "".join([f"<tr><td>{r['numero']}</td><td>{r['data_recibo']}</td><td>{r['tipo']}</td><td>{r['cliente_nome']}</td><td>{r['referente']}</td><td style='text-align:right;'>R$ {r['valor']:,.2f}</td></tr>" for r in registros])

            html = f"""
            <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Relatório - {rotulo}</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; padding: 25px; background: #fff; color: #0b0f19; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; font-size: 12px; }}
                th {{ background: #f1f5f9; text-align: left; }}
                .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
                .total {{ text-align: right; margin-top: 16px; font-size: 15px; font-weight: bold; color: #3b82f6; }}
                @media print {{ .btn-print {{ display: none; }} }}
            </style></head>
            <body>
                <button class="btn-print" onclick="window.print()" style="padding: 9px 18px; margin-bottom: 12px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">Imprimir Relatório</button>
                <div class="header">
                    <div><h2>Relatório - {rotulo}</h2><p>Período: {di} até {df}</p></div>
                    <div>Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
                </div>
                <table>
                    <thead><tr><th>Nº</th><th>Data</th><th>Tipo</th><th>Cliente</th><th>Referente</th><th style="text-align:right;">Valor</th></tr></thead>
                    <tbody>{linhas}</tbody>
                </table>
                <div class="total">Total Geral: R$ {total:,.2f}</div>
            </body></html>
            """
            temp = os.path.join(tempfile.gettempdir(), f"relatorio_{datetime.now().strftime('%H%M%S')}.html")
            with open(temp, "w", encoding="utf-8") as file: file.write(html)
            webbrowser.open(f"file://{temp}")

        ctk.CTkButton(modal, text="Visualizar Relatório", height=40, fg_color=THEME["accent_blue"], command=process).pack(pady=18)

    # ==============================================================================
    # FUNÇÕES DE CLIENTES
    # ==============================================================================
    def _recarregar_ultimos_cadastros(self):
        for w in self.scroll_ultimos.winfo_children(): w.destroy()
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 10").fetchall()

        if not rows:
            with self.db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO clientes (nome, tipo_pessoa, cnpj, email, tel1, endereco, bairro, cidade, estado, cep, obs, status)
                    VALUES ('Carlos Eduardo de Souza S.A.', 'Jurídica', '12.345.678/0001-90', 'contato@carlos-desouza.co', '(11) 98765-4321', 'Av. Paulista, 1000 - Cj 42', 'Bela Vista', 'São Paulo', 'SP', '01310-100', 'Cliente preferencial, faturamento mensal via PIX.', 'ATIVO')
                """)
                conn.execute("""
                    INSERT INTO clientes (nome, tipo_pessoa, cpf, email, tel1, endereco, bairro, cidade, estado, cep, obs, status)
                    VALUES ('Maria Clara Oliveira', 'Física', '12.345.600-90', 'maria.clara@gmail.com', '(21) 99887-6655', 'Rua das Laranjeiras, 45', 'Laranjeiras', 'Rio de Janeiro', 'RJ', '22240-000', 'Pagamento à vista.', 'ATIVO')
                """)
                conn.commit()
            with self.db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM clientes ORDER BY id DESC LIMIT 10").fetchall()

        for c in rows:
            self._criar_card_cliente_recente(c)

    def _criar_card_cliente_recente(self, cliente):
        card = ctk.CTkFrame(self.scroll_ultimos, fg_color=THEME["card_main"], corner_radius=12, border_width=1, border_color=THEME["card_border"])
        card.pack(fill="x", pady=6, padx=2)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(10, 4))

        iniciais = "".join([part[0] for part in cliente["nome"].split()[:2]]).upper() if cliente["nome"] else "CL"
        avatar = ctk.CTkLabel(
            top_row, text=iniciais, width=36, height=36, corner_radius=18,
            fg_color="#334155", text_color="#f8fafc", font=ctk.CTkFont(size=12, weight="bold")
        )
        avatar.pack(side="left", padx=(0, 8))

        info_box = ctk.CTkFrame(top_row, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(info_box, text=cliente["nome"][:24], font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_primary"], anchor="w").pack(fill="x")

        badge_row = ctk.CTkFrame(info_box, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(badge_row, text="ATIVO", font=ctk.CTkFont(size=9, weight="bold"), fg_color=THEME["accent_emerald_bg"], text_color=THEME["accent_emerald"], corner_radius=4).pack(side="left")

        doc = cliente["cnpj"] or cliente["cpf"] or "Sem documento"
        tipo_doc = "CNPJ" if cliente["tipo_pessoa"] == "Jurídica" else "CPF"
        ctk.CTkLabel(card, text=f"{tipo_doc} · {doc}", font=ctk.CTkFont(size=10), text_color=THEME["text_muted"]).pack(anchor="w", padx=12, pady=(4, 8))

        ctk.CTkButton(
            card, text="Visualizar", height=30, corner_radius=15,
            fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
            border_width=1, border_color=THEME["card_border"],
            text_color=THEME["text_primary"], font=ctk.CTkFont(size=11),
            command=lambda c_data=cliente: self._carregar_cliente_nos_campos(c_data)
        ).pack(fill="x", padx=12, pady=(0, 10))

    def _carregar_cliente_nos_campos(self, c):
        self.cliente_id_atual = c["id"]
        self.txt_cad_id.delete(0, "end"); self.txt_cad_id.insert(0, f"{c['id']:03d}")
        self.cb_cad_tipo.set(c["tipo_pessoa"] or "Jurídica")
        self.txt_cad_nome.delete(0, "end"); self.txt_cad_nome.insert(0, c["nome"] or "")
        self.txt_cad_cnpj.delete(0, "end"); self.txt_cad_cnpj.insert(0, c["cnpj"] or "")
        self.txt_cad_cpf.delete(0, "end"); self.txt_cad_cpf.insert(0, c["cpf"] or "")
        self.txt_cad_email.delete(0, "end"); self.txt_cad_email.insert(0, c["email"] or "")
        self.txt_cad_data.delete(0, "end"); self.txt_cad_data.insert(0, c["data_nasc"] or "")
        self.txt_cad_tel1.delete(0, "end"); self.txt_cad_tel1.insert(0, c["tel1"] or "")
        self.txt_cad_tel2.delete(0, "end"); self.txt_cad_tel2.insert(0, c["tel2"] or "")
        self.txt_cad_end.delete(0, "end"); self.txt_cad_end.insert(0, c["endereco"] or "")
        self.txt_cad_bairro.delete(0, "end"); self.txt_cad_bairro.insert(0, c["bairro"] or "")
        self.txt_cad_cid.delete(0, "end"); self.txt_cad_cid.insert(0, c["cidade"] or "")
        self.cb_cad_uf.set(c["estado"] or "SP")
        self.txt_cad_cep.delete(0, "end"); self.txt_cad_cep.insert(0, c["cep"] or "")
        self.txt_cad_obs.delete(0, "end"); self.txt_cad_obs.insert(0, c["obs"] or "")

    def _salvar_cliente_form(self):
        nome = self.txt_cad_nome.get().strip()
        if not nome:
            messagebox.showwarning("Atenção", "O Nome/Razão Social é obrigatório.")
            return

        dados = (
            nome, self.cb_cad_tipo.get(), self.txt_cad_cpf.get().strip(),
            self.txt_cad_cnpj.get().strip(), self.txt_cad_email.get().strip(),
            self.txt_cad_data.get().strip(), self.txt_cad_tel1.get().strip(),
            self.txt_cad_tel2.get().strip(), self.txt_cad_end.get().strip(),
            self.txt_cad_bairro.get().strip(), self.txt_cad_cid.get().strip(),
            self.cb_cad_uf.get(), self.txt_cad_cep.get().strip(),
            self.txt_cad_obs.get().strip()
        )

        with self.db.get_connection() as conn:
            if self.cliente_id_atual:
                conn.execute("""
                    UPDATE clientes SET nome=?, tipo_pessoa=?, cpf=?, cnpj=?, email=?, data_nasc=?, tel1=?, tel2=?, endereco=?, bairro=?, cidade=?, estado=?, cep=?, obs=?
                    WHERE id=?
                """, dados + (self.cliente_id_atual,))
            else:
                conn.execute("""
                    INSERT INTO clientes (nome, tipo_pessoa, cpf, cnpj, email, data_nasc, tel1, tel2, endereco, bairro, cidade, estado, cep, obs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, dados)
            conn.commit()

        messagebox.showinfo("Sucesso", "Cadastro salvo com sucesso!")
        self.navegar("cadastros")

    def _limpar_cliente_form(self):
        self.cliente_id_atual = None
        self.txt_cad_id.delete(0, "end"); self.txt_cad_id.insert(0, f"{self.db.total_clientes()+1:03d}")
        self.txt_cad_nome.delete(0, "end")
        self.txt_cad_cnpj.delete(0, "end")
        self.txt_cad_cpf.delete(0, "end"); self.txt_cad_cpf.insert(0, "-")
        self.txt_cad_email.delete(0, "end")
        self.txt_cad_data.delete(0, "end")
        self.txt_cad_tel1.delete(0, "end")
        self.txt_cad_tel2.delete(0, "end")
        self.txt_cad_end.delete(0, "end")
        self.txt_cad_bairro.delete(0, "end")
        self.txt_cad_cid.delete(0, "end")
        self.cb_cad_uf.set("SP")
        self.txt_cad_cep.delete(0, "end")
        self.txt_cad_obs.delete(0, "end")

    def _excluir_cliente_db(self):
        if not self.cliente_id_atual:
            messagebox.showwarning("Atenção", "Selecione um cliente para excluir.")
            return
        if messagebox.askyesno("Excluir", "Deseja remover o registro selecionado?"):
            with self.db.get_connection() as conn:
                conn.execute("DELETE FROM clientes WHERE id = ?", (self.cliente_id_atual,))
                conn.commit()
            self._limpar_cliente_form()
            self.navegar("cadastros")

    def _modal_buscar_cliente(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Localizar Cliente")
        modal.geometry("540x440")
        modal.configure(fg_color=THEME["card_main"])
        modal.grab_set()

        txt = ctk.CTkEntry(modal, height=40, placeholder_text="Filtrar por nome ou documento...", fg_color=THEME["input_bg"])
        txt.pack(fill="x", padx=16, pady=12)

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        def load(filtro=""):
            for w in scroll.winfo_children(): w.destroy()
            with self.db.get_connection() as conn:
                rows = conn.execute("SELECT * FROM clientes WHERE nome LIKE ? OR cnpj LIKE ? OR cpf LIKE ? ORDER BY nome ASC LIMIT 50", (f"%{filtro}%", f"%{filtro}%", f"%{filtro}%")).fetchall()
            for r in rows:
                ctk.CTkButton(
                    scroll, text=f"{r['nome']}   ({r['cnpj'] or r['cpf'] or 'Sem doc'})", height=36, anchor="w",
                    fg_color=THEME["input_bg"], hover_color=THEME["btn_circle_add_hover"],
                    command=lambda cli=r: [self._carregar_cliente_nos_campos(cli), modal.destroy()]
                ).pack(fill="x", pady=2)

        txt.bind("<KeyRelease>", lambda e: load(txt.get().strip()))
        load()

    def _busca_global(self, termo):
        if not termo.strip(): return
        self.navegar("cadastros")
        self._modal_buscar_cliente()

    def _carregar_recibo_historico(self, r):
        self.navegar("recibos")
        self.recibo_id_atual = r["id"]
        self.cb_rec_tipo.set(r["tipo"])
        self.txt_rec_num.delete(0, "end"); self.txt_rec_num.insert(0, r["numero"])
        self.txt_rec_cli.delete(0, "end"); self.txt_rec_cli.insert(0, r["cliente_nome"])
        self.txt_rec_doc.delete(0, "end"); self.txt_rec_doc.insert(0, r["cliente_doc"] or "")
        self.txt_rec_ref.delete(0, "end"); self.txt_rec_ref.insert(0, r["referente"] or "")
        self.txt_rec_data.delete(0, "end"); self.txt_rec_data.insert(0, r["data_recibo"])
        self.txt_rec_val.delete(0, "end"); self.txt_rec_val.insert(0, f"{r['valor']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _executar_backup(self):
        dest = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("Banco SQLite", "*.db")], initialfile=f"backup_recibo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        if dest:
            try:
                shutil.copy(self.db.db_path, dest)
                messagebox.showinfo("Backup", "Backup exportado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha no backup: {e}")

    # ==============================================================================
    # MOTOR DE IMPRESSÃO (RECIBO COM LOGOMARCA EMBUTIDA EM BASE64)
    # ==============================================================================
    def imprimir_recibo(self, vias=1):
        num = self.txt_rec_num.get().strip()
        cli = self.txt_rec_cli.get().strip()
        doc = self.txt_rec_doc.get().strip()
        ref = self.txt_rec_ref.get().strip()
        val = self.txt_rec_val.get().strip().replace(".", "").replace(",", ".")
        dt = self.txt_rec_data.get().strip()

        if not num or not cli or not val:
            messagebox.showwarning("Atenção", "Preencha número, cliente e valor para emitir.")
            return

        try:
            val_f = float(val)
        except ValueError:
            messagebox.showerror("Erro", "Valor numérico inválido.")
            return

        em_nome = self.db.get_config("emitente_nome", "TechNova S.A.")
        em_doc = self.db.get_config("emitente_doc", "00.000.000/0001-00")
        em_cid = self.db.get_config("emitente_cidade", "São Paulo")

        with self.db.get_connection() as conn:
            conn.execute("""
                INSERT INTO recibos (tipo, numero, cliente_nome, cliente_doc, referente, data_recibo, valor, emitente_nome, emitente_doc, emitente_cidade)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.cb_rec_tipo.get(), num, cli, doc, ref, dt, val_f, em_nome, em_doc, em_cid))
            conn.commit()

        self._atualizar_historico_sidebar()
        extenso = valor_por_extenso(val_f)

        logo_path = self.db.get_config("logo_path", "")
        if not logo_path or not os.path.exists(logo_path):
            if os.path.exists("Logo.jpg"): logo_path = os.path.abspath("Logo.jpg")

        logo_html = 'Logomarca da<br>sua Empresa'
        if logo_path and os.path.exists(logo_path):
            try:
                with open(logo_path, "rb") as f_img:
                    encoded = base64.b64encode(f_img.read()).decode("utf-8")
                    logo_html = f'<img src="data:image/jpeg;base64,{encoded}" style="max-width:175px; max-height:65px; object-fit:contain;">'
            except Exception: pass

        bloco_recibo = f"""
        <div class="recibo-box">
            <div class="header-recibo">
                <div class="logo-area">{logo_html}</div>
                <div class="titulo-area">Recibo</div>
                <div class="valor-area">
                    <div class="num-doc">nº &nbsp; {num}</div>
                    <div class="box-valor">R$ <span>{val_f:,.2f}</span></div>
                </div>
            </div>
            <div class="linha-campo"><span class="label">Recebi(emos) de</span><span class="dado">{cli}</span></div>
            <div class="linha-campo"><span class="label">CPF/CNPJ</span><span class="dado">{doc}</span></div>
            <div class="linha-campo campo-extenso"><span class="label">a quantia de</span><span class="extenso-box">{extenso}</span></div>
            <div class="linha-campo"><span class="label">referente</span><span class="dado">{ref}</span></div>
            <div class="footer-data"><div class="data-linha">{em_cid} , {dt}</div></div>
            <div class="assinatura-area"><div class="traco-assinatura"></div><div class="nome-empresa">{em_nome}</div></div>
        </div>
        """

        segunda_via = f'<div class="corte-pontilhado"><span>✂ 2ª VIA DO RECIBO</span></div>{bloco_recibo}' if vias == 2 else ""

        html = f"""
        <!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><title>Recibo Nº {num}</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; }}
            body {{ background: #f3f4f6; padding: 20px; display: flex; justify-content: center; }}
            .container-folha {{ width: 100%; max-width: 820px; background: #fff; padding: 30px; box-shadow: 0 4px 14px rgba(0,0,0,0.08); }}
            .recibo-box {{ border: 1px solid #111; padding: 20px 24px; position: relative; background: #fff; }}
            .header-recibo {{ display: grid; grid-template-columns: 190px 1fr 180px; align-items: center; margin-bottom: 20px; }}
            .logo-area {{ border: 1px solid #333; width: 175px; height: 65px; display: flex; align-items: center; justify-content: center; text-align: center; font-size: 12px; font-weight: bold; background: #fafafa; overflow: hidden; }}
            .titulo-area {{ text-align: center; font-size: 30px; font-weight: bold; color: #000; }}
            .valor-area {{ text-align: right; display: flex; flex-direction: column; align-items: flex-end; }}
            .num-doc {{ font-size: 22px; font-weight: bold; margin-bottom: 3px; }}
            .box-valor {{ font-size: 20px; font-weight: bold; display: flex; align-items: center; gap: 6px; }}
            .box-valor span {{ background: #d1d5db; padding: 2px 14px; display: inline-block; min-width: 110px; text-align: right; }}
            .linha-campo {{ display: flex; align-items: baseline; margin-bottom: 12px; font-size: 14px; }}
            .linha-campo .label {{ padding-right: 8px; white-space: nowrap; color: #111; }}
            .linha-campo .dado {{ flex-grow: 1; border-bottom: 1px solid #000; font-weight: bold; text-transform: uppercase; padding-left: 6px; min-height: 18px; }}
            .campo-extenso .extenso-box {{ background: #d1d5db; flex-grow: 1; padding: 3px 8px; font-weight: bold; font-size: 13px; }}
            .footer-data {{ margin-top: 25px; display: flex; justify-content: flex-end; }}
            .data-linha {{ border-bottom: 1px solid #000; padding: 0 15px 2px 25px; font-size: 13px; text-transform: uppercase; margin-bottom: 35px; }}
            .assinatura-area {{ width: 320px; margin: 0 auto; text-align: center; }}
            .traco-assinatura {{ border-top: 1px solid #000; margin-bottom: 4px; }}
            .nome-empresa {{ font-size: 12px; font-weight: bold; text-transform: uppercase; }}
            .corte-pontilhado {{ border-top: 1px dashed #4b5563; margin: 25px 0; position: relative; text-align: center; }}
            .corte-pontilhado span {{ position: absolute; top: -10px; background: #fff; padding: 0 10px; font-size: 11px; color: #6b7280; font-weight: bold; }}
            @media print {{
                body {{ background: #fff; padding: 0; }}
                .container-folha {{ box-shadow: none; padding: 0; max-width: 100%; }}
                .btn-print {{ display: none; }}
                .box-valor span, .campo-extenso .extenso-box {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            }}
        </style></head>
        <body>
            <div class="container-folha">
                <button class="btn-print" onclick="window.print()" style="padding: 10px 20px; margin-bottom: 15px; background: #3b82f6; color: #fff; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 14px;">Imprimir / Salvar PDF</button>
                {bloco_recibo}
                {segunda_via}
            </div>
        </body></html>
        """
        temp = os.path.join(tempfile.gettempdir(), f"recibo_{num}.html")
        with open(temp, "w", encoding="utf-8") as file: file.write(html)
        webbrowser.open(f"file://{temp}")

if __name__ == "__main__":
    app = ReciboSoftwareApp()
    app.mainloop()

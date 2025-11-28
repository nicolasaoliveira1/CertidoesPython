# 📋 Sistema de Controle de Certidões Fiscais - Python (⚠️ Em Desenvolvimento..)

Sistema web desenvolvido em Flask para gerenciamento e automação de emissão de certidões fiscais (Federal, FGTS, Estadual, Municipal e Trabalhista) de empresas.

![Dashboard](docs/screenshot-dashboard.png)
*Adicionar aqui uma screenshot do dashboard*

---

## 🎯 Sobre o Projeto

Este sistema foi desenvolvido para facilitar o controle e a emissão automatizada de certidões fiscais de múltiplas empresas. Atualmente, utilizado no escritório contábil onde trabalho, o que me ajuda a ter mais tempo para outras tarefas importantes.
Com uma interface web moderna e intuitiva, permite:

- **Gerenciar empresas** e suas certidões em um único lugar
- **Automatizar a emissão** de certidões via Selenium WebDriver
- **Monitorar validades** com sistema de alertas por cores
- **Filtrar e pesquisar** empresas de forma ágil
- **Tema claro/escuro** com persistência de preferência

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python** (3.10+)
- **Flask** - Framework web
- **SQLAlchemy** - ORM
- **Flask-Migrate** - Gerenciamento de migrations
- **Selenium** - Automação de navegador
- **webdriver-manager** - Gerenciamento automático do ChromeDriver

### Frontend
- **Bootstrap 5.3** - Framework CSS
- **JavaScript** - Interatividade e tema
- **HTML/CSS** - Estrutura e estilização

### Automação
- **Selenium WebDriver** (Chrome)
- **ChromeDriver** (gerenciado automaticamente)

---

## ✨ Funcionalidades

### 📊 Dashboard Interativo
- Visualização de todas as empresas e suas certidões
- Sistema de cores para status de validade:
  - 🟢 **Verde**: Válida (mais de 7 dias)
  - 🟡 **Amarelo**: A vencer (até 7 dias)
  - 🔴 **Vermelho**: Vencida ou pendente
  - ⚪ **Cinza**: Sem data cadastrada

### 🔍 Filtros e Busca
- Filtro por status: Todas, Válidas, A Vencer, Vencidas, Pendentes
- Busca em tempo real por nome de empresa
- Interface responsiva e adaptável

### 🤖 Automação de Certidões
- Emissão automática via Selenium (Chrome WebDriver)
- Sites suportados:
  - **Federal**: Receita Federal
  - **FGTS**: Caixa Econômica Federal
  - **Estadual**: SEFAZ/RS
  - **Municipal**: Configurável por município
  - **Trabalhista**: TST (CNDT)
- Download automático dos PDFs
- Organização por empresa e tipo de certidão

### 📁 Gestão de Arquivos
- Salvamento organizado em pastas por empresa
- Nomenclatura padronizada dos arquivos
- Alerta visual com caminho do arquivo salvo

### 🎨 Interface Moderna
- Tema claro/escuro (bootstrap)
- Menu offcanvas responsivo
- Logo adaptável ao tema e zoom
- Design mobile-friendly

### 🗄️ Banco de Dados
- SQLite (padrão) ou configurável via `.env`
- Migrations com Flask-Migrate (Alembic)
- Modelos:
  - **Empresa**: Nome, CNPJ, Cidade, Inscrição Mobiliária
  - **Certidão**: Tipo, Validade, Status Especial
  - **Município**: Configurações de automação personalizadas

---

## 📦 Instalação

### Pré-requisitos
- Python 3.10 ou superior
- Google Chrome instalado
- Git

### Passo a Passo

1. **Clone o repositório**
```powershell
git clone https://github.com/nicolasaoliveira1/CertidoesPython.git
cd CertidoesPython
```

2. **Crie um ambiente virtual**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

3. **Instale as dependências**
```powershell
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente** (opcional)

Crie um arquivo `.env` na raiz do projeto:
```env
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=sqlite:///instance/database.db
```

5. **Inicialize o banco de dados**
```powershell
flask db upgrade
```

6. **Execute a aplicação**
```powershell
python run.py
```

7. **Acesse no navegador**
```
http://localhost:5000
```

---

## ⚙️ Configuração

### 📂 Caminho de Salvamento das Certidões

⚠️ **IMPORTANTE**: Você deve configurar o caminho onde as certidões serão salvas.

Edite o arquivo `app/file_manager.py` ou `app/routes.py` e defina o caminho base:

```python
# Exemplo: caminho para servidor local ou rede
CERTIDOES_BASE_PATH = r"C:\CaminhoDoServidor\CERTIDOES"
# ou
CERTIDOES_BASE_PATH = r"\\ServidorRede\Compartilhado\CERTIDOES"
```

**Estrutura de pastas criada automaticamente:**
```
CERTIDOES/
├── Empresa 1/
│   ├── Federal_CNPJ_20250101.pdf
│   ├── FGTS_CNPJ_20250101.pdf
│   └── ...
├── Empresa 2/
│   └── ...
```

### 🏛️ Configuração de Municípios

Para adicionar automação de certidões municipais:

1. Acesse o banco de dados (`instance/database.db`)
2. Insira um registro na tabela `municipio`:
   - `nome`: Nome do município
   - `url_certidao`: URL do site da prefeitura
   - `cnpj_field_id`: Seletor do campo CNPJ
   - `by`: Tipo de seletor (`id`, `name`, `css_selector`, etc.)
   - Campos opcionais para inscrição mobiliária e shadow DOM

---

## 🗂️ Estrutura do Projeto

```
CertidoesPython/
├── app/
│   ├── __init__.py              # Inicialização do Flask
│   ├── models.py                # Modelos do banco de dados
│   ├── routes.py                # Rotas e lógica de negócio
│   ├── automation.py            # Configurações de automação
│   ├── file_manager.py          # Gerenciamento de arquivos
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css        # Estilos customizados
│   │   └── images/              # Logos e ícones
│   └── templates/
│       ├── base.html            # Template base
│       └── dashboard.html       # Dashboard principal
├── migrations/                   # Migrations do Alembic
├── instance/
│   └── database.db              # Banco de dados SQLite
├── config.py                    # Configurações da aplicação
├── run.py                       # Ponto de entrada
├── requirements.txt             # Dependências Python
└── README.md                    # Este arquivo
```

---

## 🚀 Uso

### Adicionar Empresa
1. No dashboard, clique em "Adicionar Empresa"
2. Preencha: Nome, CNPJ, Cidade, Inscrição Mobiliária (opcional)
3. As 5 certidões são criadas automaticamente

### Abrir Site Certidão (IMPORTANTE: utilize esse botão para emitir certidões federais)
1. Clique no botão "Abrir Site" na certidão desejada
2. O sistema abre uma aba ao lado no site de emissão e copia o CNPJ da empresa para colar
3. Baixe o PDF em Downloads e ele será movido para a pasta configurada
4. Feche o site e volte ao sistema para confirmar validade da certidão

### Emitir Certidão Automaticamente
1. Clique no botão "Baixar" na certidão desejada
2. O sistema abre uma janela anônima no site desejado e preenche os dados automaticamente
3. Baixe o PDF em Download e ele será movido para a pasta configurada
4. Feche a janela do Chrome que foi aberta e volte ao sistema para confirmar a validade da certidão

### Atualizar Validade
1. Clique no botão "Editar" na certidão desejada
2. Informe a nova data de validade
3. Salve

### Marcar como Pendente
1. Após clicar em "Editar", clique em "Marcar como Pendente" no modal
2. A certidão ficará destacada em vermelho e será escrito: "Pendente"

---

## 🔧 Migrations (Alembic)

### Criar nova migration
```powershell
flask db migrate -m "Descrição da alteração"
```

### Aplicar migrations
```powershell
flask db upgrade
```

### Reverter última migration
```powershell
flask db downgrade
```

---

## 🎨 Personalização

### Alterar Tema
- O sistema detecta automaticamente a preferência do sistema
- Use o botão sol/lua no navbar para alternar manualmente
- A preferência é salva no `localStorage`

### Ajustar Logo
Atualmente utiliza a logo do escritório onde trabalho
- Logos em `app/static/images/`
- Logo claro: `asseconlogo.png` (versão completa) e `assecon_preto.png` (compacta)
- Logo escuro: `assecon_branco_logo.png` (completa) e `assecon_branco.png` (compacta)

### Modificar Cores de Status
Edite em `app/templates/base.html`:
```css
.status-verde .date-cell { background-color: #c4ffcf !important; }
.status-amarelo .date-cell { background-color: #fffcaa !important; }
.status-vermelho .date-cell { background-color: #ffb6b8 !important; }
```

---

## 📝 Migrations Aplicadas

1. **eca48a272f38** - Cria tabelas Empresa e Certidão
2. **233660c7e937** - Cria tabela Município para automação
3. **9d46bcffc7cb** - Adiciona status_especial (Pendente)
4. **a4a53448d4b5** - Adiciona segundo campo de preenchimento automático

---

## ⚠️ Limitações Conhecidas

- A automação depende da estabilidade dos sites governamentais
- Mudanças nos sites podem quebrar os seletores (requer atualização manual)
- O download automático do PDF depende das configurações do navegador
- Sites com CAPTCHA não são automatizáveis (pelo menos não agora)
- Requer configuração manual do caminho de salvamento
- Para emissão de certidões municipais não implementadas requer adição de automação do site específico

---

## 🛣️ Roadmap

- [ ] Configuração de caminho via interface web (sem editar código)
- [ ] Download automático completo (salvar PDF sem intervenção)
- [ ] Notificações por e-mail para certidões vencendo
- [ ] Relatórios em Excel/PDF
- [ ] API REST para integração
- [ ] Autenticação de usuários
- [ ] Logs de auditoria
- [ ] Suporte a mais estados (certidão estadual)

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para:

1. Fazer um fork do projeto
2. Criar uma branch para sua feature (`git checkout -b feature/NovaFuncionalidade`)
3. Commitar suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abrir um Pull Request

---

## 📄 Licença

Este projeto é de código aberto. Consulte o proprietário para mais informações sobre licenciamento.

---

## 👤 Autor

Nome: Nicolas Oliveira
Email: eu@nicolasoliveira.dev.br

---

## Status

Iniciado em: 20/10/2025
Em desenvolvimento...

Tradutor Pro

Aplicação web para tradução automática de livros e documentos, desenvolvida em Python com o framework FastAPI.

O sistema recebe arquivos em diferentes formatos, traduz o conteúdo preservando a estrutura do texto (capítulos, partes, formatação) e gera uma versão traduzida pronta para leitura, incluindo exportação em PDF formatado.

Funcionalidades


Upload de livros e documentos em PDF, EPUB, DOCX e TXT
Tradução automática do conteúdo para múltiplos idiomas (pt-BR, en, es, fr, de)
Detecção automática de capítulos e partes do livro
Revisão gramatical do texto traduzido
Geração de PDF formatado com capa, sumário (TOC), cabeçalhos e numeração de página
Sistema de checkpoint/retomada, permitindo continuar traduções grandes de onde pararam
Processamento em paralelo para acelerar a tradução de arquivos extensos


Tecnologias utilizadas


Python 3 + FastAPI — backend e API
SQLAlchemy + PostgreSQL — persistência de dados
deep-translator — motor de tradução (Google Translate)
language-tool-python — revisão gramatical
ReportLab / fpdf2 — geração de PDF
pypdf / pdfplumber — leitura e extração de conteúdo de PDF
python-docx — leitura de arquivos do Word
ebooklib + BeautifulSoup4 — leitura de arquivos EPUB
python-dotenv — gerenciamento de variáveis de ambiente


Como rodar o projeto localmente


Clone o repositório e entre na pasta do projeto
Crie e ative um ambiente virtual:


bash   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Linux/Mac


Instale as dependências:


bash   pip install -r requirements.txt


Copie o arquivo de exemplo de variáveis de ambiente e preencha com seus dados:


bash   cp .env.example .env


Configure um banco PostgreSQL local e ajuste a DATABASE_URL no .env
Crie as tabelas do banco:


bash   python create_tables.py


Rode a aplicação:


bash   uvicorn main:app --reload


Acesse no navegador: http://127.0.0.1:8000


Estrutura do projeto

Tradutor_pro/
├── app/
│   ├── database/     # Conexão com o banco de dados
│   ├── models/       # Modelos (usuário, tradução, glossário)
│   ├── routes/       # Rotas da API (upload, tradução, download, auth)
│   ├── services/      # Lógica de negócio (tradutor, chunker, PDF builder, etc.)
│   ├── static/        # CSS e JS do frontend
│   └── templates/     # HTML do frontend
├── uploads/          # Arquivos enviados pelo usuário (ignorado no git)
├── translated/        # Arquivos traduzidos gerados (ignorado no git)
├── progress/          # Checkpoints de progresso (ignorado no git)
├── main.py            # Ponto de entrada da aplicação
├── config.py           # Configurações gerais
├── requirements.txt     # Dependências do projeto
└── .env.example         # Modelo de variáveis de ambiente

Observação

Este é um projeto pessoal em desenvolvimento contínuo. Dados de exemplo, uploads e arquivos traduzidos reais não são versionados por conterem informações privadas — apenas a estrutura do projeto é mantida no repositório.

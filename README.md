# EduCore – Learning Management System

Plataforma de cursos online construída com Django, unindo catálogo de cursos, aulas, materiais, inscrições, anúncios e fórum da comunidade. Agora inclui a Suite IA (Mentor + Atlas, Radar e Studio) para elevar a experiência de aprendizagem e a autoria de conteúdo.

---

**Sumário**
- Visão geral
- Recursos principais
- Suite IA
- Stack e dependências
- Como rodar localmente
- Variáveis de ambiente
- Testes
- Checklist visual
- Estrutura do projeto
- CI
- Licença

---

**Visão geral**
O EduCore (projeto `core`) organiza cursos, aulas e materiais, permite que usuários se inscrevam e interajam via anúncios e comentários, e oferece um fórum com tópicos e respostas. A autenticação usa um modelo de usuário customizado.

Rotas principais:
- `/`: página inicial
- `/cursos/`: catálogo de cursos
- `/conta/`: autenticação e painel do usuário
- `/forum/`: fórum da comunidade
- `/ai/`: Mentor IA
- `/ai/radar/`: Radar (staff)
- `/ai/studio/`: Studio (staff)
- `/ai/atlas/`: Atlas (staff)
- `/admin/`: painel administrativo do Django

---

**Recursos principais**
- Catálogo de cursos com listagem por título e descrição
- Aulas com disponibilidade por data e controle de acesso por inscrição
- Materiais por aula (vídeo embutido e/ou arquivo para download)
- Inscrições com status (pendente, aprovado, cancelado, recusado)
- Anúncios de curso com comentários
- Disparo de email para alunos inscritos quando um anúncio é criado
- Contato do curso por formulário (envio por email)
- Fórum com tópicos, respostas, tags, paginação e marcação de resposta correta
- Autenticação completa com usuário customizado e fluxo de reset de senha
- Painel administrativo do Django

---

**Suite IA**
- **Mentor + Atlas**: tutor IA com recuperação contextual (RAG). Respostas usam o índice Atlas para conectar cursos, aulas, materiais e discussões do fórum.
- **Radar**: sinais de risco com base em eventos reais (queda de engajamento) e revisão humana.
- **Studio**: autoria inteligente para quizzes, rubricas e comunicados, com rascunhos revisáveis.

Comandos úteis:
```bash
python manage.py rebuild_atlas
```

---

**Dados de demonstração (investidores)**
Para preencher a plataforma com **12 cursos de TI**, imagens HD e interações realistas (fórum, anúncios, Mentor IA, Radar e Atlas), use:
```bash
python manage.py seed_investor_demo --purge --purge-media --students 22 --stock-images
```
O comando faz backup do `db.sqlite3` em `backup/` e limpa a base preservando os usuários existentes quando `--purge` é usado.

---

**Stack e dependências**
- Python 3.8+ (compatível com Django 4.1.2)
- Django 4.1.2
- SQLite (padrão de desenvolvimento)
- django-taggit (tags no fórum)
- Pillow (upload de imagens)
- Front-end: Font Awesome e jQuery (assets em `static/`)
- Integração IA: OpenAI API via requests HTTP (sem SDK)

Todas as dependências estão em `requirements.txt`.

---

**Como rodar localmente**
1. Clonar o repositório
```bash
git clone <URL_DO_REPOSITORIO>
cd "EduCore – Learning Management"
```

2. Criar e ativar o ambiente virtual
```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux/Mac:
```bash
source .venv/bin/activate
```

3. Instalar dependências
```bash
pip install -r requirements.txt
```

4. Aplicar migrações
```bash
python manage.py migrate
```

5. (Opcional) Criar superusuário
```bash
python manage.py createsuperuser
```

6. Iniciar servidor
```bash
python manage.py runserver
```

A aplicação fica disponível em `http://127.0.0.1:8000`.

---

**Variáveis de ambiente**
Arquivo: `core/settings.py`
- `DEBUG`: deixe `True` apenas em desenvolvimento
- `ALLOWED_HOSTS`: configure para produção
- `SECRET_KEY`: substitua em produção
- `EMAIL_BACKEND`: por padrão usa backend de console
- `DEFAULT_FROM_EMAIL` e `CONTACT_EMAIL`: remetente e destino do contato
- `MEDIA_ROOT` e `STATIC_ROOT`: diretórios de arquivos enviados e estáticos

Configurações OpenAI:
- `OPENAI_API_KEY`: chave da API
- `OPENAI_DEFAULT_MODEL`: modelo de resposta (default: `gpt-4.1`)
- `OPENAI_EMBEDDING_MODEL`: modelo de embedding (default: `text-embedding-3-small`)
- `OPENAI_TIMEOUT`: timeout em segundos (default: `30`)

Para envio real de emails, configure SMTP e troque o `EMAIL_BACKEND`.

---

**Testes**
Execução simples:
```bash
python manage.py test
```

Cobertura de testes:
```bash
pip install -r requirements-dev.txt
coverage run manage.py test
coverage report -m
coverage html
```


---

**Checklist visual**
Para validar rapidamente a interface (modo claro/escuro, carrossel de curso e i18n), use o arquivo `CHECKLIST_VISUAL.md`.


**Estrutura do projeto**
```
ai/
accounts/
cursos/
forum/
templates/
static/
media/
manage.py
requirements.txt
requirements-dev.txt
azure-pipelines.yml
.coveragerc
```

---

**CI**
O repositório inclui pipeline em `azure-pipelines.yml` com execução de testes Django e análise via SonarCloud.

---

**Licença**
Este projeto ainda não possui licença definida.

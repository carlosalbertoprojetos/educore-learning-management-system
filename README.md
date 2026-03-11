# EduCore - Learning Management System

Plataforma de cursos online construída com Django, com catálogo de cursos, aulas, materiais, inscrições, anúncios e fórum da comunidade. O projeto foi pensado para estudos e como base extensível para aplicações educacionais.

---

**Sumário**
- Visão geral
- Funcionalidades
- Stack e dependências
- Como rodar localmente
- Configurações importantes
- Testes
- Estrutura do projeto
- CI
- Licença

---

**Visão geral**
O EduCore (projeto `cursos_online`) organiza cursos, aulas e materiais, permite que usuários se inscrevam e interajam via anúncios e comentários, e oferece um fórum com tópicos e respostas. A autenticação usa um modelo de usuário customizado.

Rotas principais:
- `/`: página inicial
- `/cursos/`: catálogo de cursos
- `/conta/`: autenticação e painel do usuário
- `/forum/`: fórum da comunidade
- `/admin/`: painel administrativo do Django

---

**Funcionalidades**
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

**Stack e dependências**
- Python 3.8+ (compatível com Django 4.1.2)
- Django 4.1.2
- SQLite (padrão de desenvolvimento)
- django-taggit (tags no fórum)
- Pillow (upload de imagens)
- Front-end: Bootstrap, Font Awesome e jQuery (assets em `static/`)

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

**Configurações importantes**
Arquivo: `cursos_online/settings.py`
- `DEBUG`: deixe `True` apenas em desenvolvimento
- `ALLOWED_HOSTS`: configure para produção
- `SECRET_KEY`: substitua em produção
- `EMAIL_BACKEND`: por padrão usa backend de console
- `DEFAULT_FROM_EMAIL` e `CONTACT_EMAIL`: remetente e destino do contato
- `MEDIA_ROOT` e `STATIC_ROOT`: diretórios de arquivos enviados e estáticos

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

**Estrutura do projeto**
```
cursos_online/
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

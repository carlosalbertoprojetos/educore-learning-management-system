# EduCore – Learning Management System

Plataforma de cursos online construída com Django, cobrindo catálogo de cursos, aulas, materiais, inscrições, anúncios e fórum da comunidade. O projeto foi pensado para estudos e como base extensível para aplicações educacionais.

---

**Sumário**
1. Visão geral
2. Funcionalidades
3. Stack e dependências
4. Como rodar localmente
5. Configurações importantes
6. Testes
7. Estrutura do projeto
8. CI
9. Licença

---

**Visão geral**
O CursosOnline organiza cursos, aulas e materiais, permite que usuários se inscrevam e interajam via anúncios e comentários, e oferece um fórum com tópicos e respostas. A autenticação usa um modelo de usuário customizado.

---

**Funcionalidades**
- Catálogo de cursos com busca por nome e descrição
- Aulas com disponibilidade por data
- Materiais por aula (vídeo embutido e/ou arquivo)
- Inscrições com status (pendente, aprovado, cancelado, recusado)
- Anúncios de curso com comentários
- Disparo de email para alunos inscritos ao criar anúncio
- Fórum com tópicos, respostas, tags e marcação de resposta correta
- Autenticação completa com usuário customizado e reset de senha
- Painel administrativo do Django

---

**Stack e dependências**
- Python 3.8+ (compatível com Django 4.1)
- Django 4.1.2
- SQLite (padrão de desenvolvimento)
- django-taggit (tags no fórum)
- Pillow (upload de imagens)

Todas as dependências estão em `requirements.txt`.

---

**Como rodar localmente**
1. Clonar o repositório
```bash
git clone <URL_DO_REPOSITORIO>
cd Cursos_Online
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
- `MEDIA_ROOT` e `STATIC_ROOT`: diretórios de arquivos enviados e estáticos

Para envio real de emails, configure SMTP e troque o `EMAIL_BACKEND`.

---

**Testes**
```bash
python manage.py test
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
```

---

**CI**
O repositório inclui pipeline em `azure-pipelines.yml` com execução de testes Django e análise via SonarCloud.

---

**Licença**
Este projeto ainda não possui licença definida.


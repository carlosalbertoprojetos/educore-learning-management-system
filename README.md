# FlaskFullStack

O objetivo deste projeto é demonstrar, de forma prática, a construção de uma aplicação web completa utilizando o **framework Flask** no backend e tecnologias modernas no frontend.

O sistema inclui:

* Autenticação de usuários
* Operações CRUD completas
* Integração com banco de dados
* Templates dinâmicos
* Formulários com validação
* API RESTful
* Estrutura preparada para deployment

---

# Funcionalidades

## Autenticação de Usuários

* Registro de novos usuários
* Login seguro
* Logout de sessão
* Gerenciamento de sessão utilizando **Flask-Login**

## Operações CRUD

* Criar registros
* Listar dados
* Atualizar informações
* Excluir registros

## Banco de Dados

* Integração com **SQLite**
* Controle de migrações utilizando **Flask-Migrate**

## Templates Dinâmicos

* Renderização de páginas com **Jinja2**
* Estrutura modular de templates

## Formulários

* Criação e validação de formulários utilizando **WTForms**

## API RESTful

* Implementação de endpoints REST com **Flask-RESTful**
* Estrutura preparada para integração com aplicações externas

## Deployment

* Aplicação preparada para implantação em ambientes de produção.

---

# Tecnologias Utilizadas

## Backend

* Python
* Flask
* Flask-Login
* Flask-WTF
* Flask-Migrate
* Flask-RESTful

## Frontend

* HTML
* CSS
* JavaScript
* Bootstrap

## Banco de Dados

* SQLite

---

# Estrutura do Projeto

```
projeto_flask/
│
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   │
│   ├── templates/
│   │
│   └── static/
│
├── migrations/
│
├── tests/
│
├── .gitignore
├── config.py
├── manage.py
├── README.md
└── requirements.txt
```

Descrição dos principais diretórios:

* **app/** → núcleo da aplicação Flask
* **models.py** → definição dos modelos do banco de dados
* **routes.py** → definição das rotas da aplicação
* **templates/** → arquivos HTML renderizados pelo Jinja2
* **static/** → arquivos estáticos (CSS, JS, imagens)
* **migrations/** → histórico de migrações do banco
* **tests/** → testes automatizados da aplicação

---

# Instalação

Siga os passos abaixo para configurar o ambiente de desenvolvimento.

## 1. Clonar o repositório

```bash
git clone https://github.com/seu_usuario/projeto_flask.git
cd projeto_flask
```

---

## 2. Criar ambiente virtual

```bash
python3 -m venv venv
```

---

## 3. Ativar ambiente virtual

Linux / Mac:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

---

## 4. Instalar dependências

```bash
pip install -r requirements.txt
```

---

# Configuração do Banco de Dados

Inicializar migrações:

```bash
flask db init
```

Criar migração inicial:

```bash
flask db migrate -m "Initial migration"
```

Aplicar migrações:

```bash
flask db upgrade
```

---

# Executar a Aplicação

```bash
flask run
```

A aplicação estará disponível em:

```
http://127.0.0.1:5000
```

---

# Testes

Caso existam testes implementados no diretório **tests**, eles podem ser executados com:

```bash
pytest
```

---

# Contribuições

Contribuições são bem-vindas.

Se desejar colaborar:

1. Faça um **fork do projeto**
2. Crie uma **branch para sua feature**

```
git checkout -b feature/minha-feature
```

3. Faça o commit das alterações

```
git commit -m "Adiciona nova funcionalidade"
```

4. Envie para seu fork

```
git push origin feature/minha-feature
```

5. Abra um **Pull Request**

---

# Licença

Este projeto está licenciado sob a **Licença MIT**.
Consulte o arquivo **LICENSE** para mais informações.


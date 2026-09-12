🇺🇸 [Read in English](README.md)

# Integration Hub

Um serviço de backend que centraliza integrações com APIs REST externas: cadastre uma integração (base URL, tipo de autenticação, headers padrão, timeout), armazene a credencial dela criptografada e — conforme os próximos incrementos entram — execute requisições através dela, mantenha um histórico de execuções e rode health checks contra ela.

Ele modela o dia a dia de um Integration / API Support Engineer: credenciais que não podem vazar, requisições que dão timeout ou voltam `401`, e a necessidade de saber *qual* integração falhou, *quando* e *por quê*.

É um projeto de portfólio, construído de forma incremental. Este README descreve o que existe hoje; o [Roadmap](#roadmap) lista o que vem a seguir e em que ordem.

## Visão geral

O conceito central é uma **Integration**: uma API externa com a qual o hub sabe conversar. Cada integração tem no máximo uma **Credential**, que guarda o segredo necessário para autenticar naquela API.

```
Integration        (name, slug, base_url, auth_type, default_headers, timeout_seconds, status)
  └── Credential   (API_KEY | BEARER_TOKEN; config em JSONB puro, segredo criptografado com Fernet)
```

O `auth_type` da integração declara *como* ela autentica (`NONE`, `API_KEY`, `BEARER_TOKEN`, `OAUTH2_CLIENT_CREDENTIALS`). A credencial fornece o *valor*. Os dois são mantidos consistentes: uma credencial do tipo errado é rejeitada, e o `auth_type` não pode mudar enquanto existir uma credencial.

## Arquitetura

```
integration-hub/
├── docker-compose.yml         # postgres + api; migrations rodam no start
├── Dockerfile
├── pyproject.toml             # dependências, config do ruff e do pytest
├── alembic/                   # migrations (autogeradas, revisadas à mão)
├── app/
│   ├── main.py                # app FastAPI, routers, exception handlers, /health
│   ├── api/                   # só HTTP: parseia, chama um service, mapeia o status code
│   │   ├── deps.py            # DbSession, require_api_key
│   │   ├── integrations.py
│   │   └── credentials.py
│   ├── core/                  # config, logging, security (criptografia), exceptions
│   ├── db/
│   │   ├── session.py         # engine, SessionLocal, Base, get_db
│   │   └── models.py          # modelos SQLAlchemy
│   ├── schemas/               # modelos Pydantic de request/response
│   └── services/              # regras de negócio; sem imports do FastAPI
├── scripts/create-test-db.sql
└── tests/
```

**Rotas finas; regras nos services.** Uma rota parseia a entrada, chama uma função de service e mapeia o resultado para um status code. Tudo que é regra — unicidade de nome, "essa credencial não bate com o tipo de autenticação da integração", "não troque o `auth_type` enquanto houver um segredo guardado" — mora em `services/` e levanta exceções Python puras (`NotFoundError`, `ConflictError`). O `main.py` traduz isso para `404`/`409`. Os services nunca importam FastAPI, então podem ser exercitados por testes ou por um worker futuro sem uma requisição HTTP no meio.

**SQLAlchemy síncrono e HTTP síncrono, de propósito.** Os handlers são `def`, não `async def`; o FastAPI os roda numa thread de trabalho, então uma chamada bloqueante ao banco não trava o event loop. Quando a execução de requisições entrar, ela vai usar `httpx.Client` pelo mesmo motivo — um único modelo de concorrência por requisição, em vez de misturar uma sessão síncrona com um cliente HTTP assíncrono.

**Uma credencial por integração.** Uma integração autentica de um jeito só, então a credencial é um filho 1:1 (`PUT` cria ou substitui) em vez de uma lista onde o código precisa adivinhar qual entrada usar.

**Config e segredo ficam separados.** A credencial tem uma coluna `config` em texto puro (configurações não sensíveis, como o nome do header da API key) e uma coluna `encrypted_secret`. Leituras nunca tocam o segredo; só a execução de requisições vai descriptografá-lo, em memória, para montar a chamada de saída. O que conta como segredo é decidido no schema Pydantic — todo campo tipado como `SecretStr` é criptografado, o resto é config — então adicionar um tipo novo de credencial não exige mexer no service.

**Status do operador vs. saúde observada.** O `Integration.status` (`ACTIVE`/`PAUSED`) é definido por um operador e nunca é alterado pelo sistema. Resultados de health check vão viver em campos próprios quando essa funcionalidade entrar, para que "alguém pausou isso" e "a última checagem falhou" continuem distinguíveis.

**Integrações são endereçáveis por slug, não só por UUID.** Toda rota `/integrations/{ref}` aceita o id ou o slug (`GET /integrations/payments-api`). O slug é derivado do nome na criação quando não é informado (`"Integração ERP (v2)"` → `integracao-erp-v2`), precisa casar com `^[a-z0-9]+(-[a-z0-9]+)*$` e é único. O UUID continua sendo a chave canônica para foreign keys e logs; o slug existe para uma pessoa conseguir digitar.

**Enums são armazenados como `VARCHAR`, não como tipos `ENUM` nativos do Postgres.** Adicionar um valor (um `auth_type` novo, por exemplo) não precisa de migration com `ALTER TYPE`, e os valores permitidos já são garantidos pelo Pydantic na borda da API.

**A própria API do hub exige uma chave.** Toda rota exceto `/health` exige um header `X-API-Key` igual ao `HUB_API_KEY`, comparado em tempo constante. Um serviço que guarda credenciais e vai executar requisições com elas não deveria ficar aberto, nem em um MVP.

## Funcionalidades (atuais)

- Criar, listar (paginado, com busca por nome e filtro por status), consultar, atualizar e remover integrações
- Endereçar uma integração por um `slug` legível, além do UUID
- Validar e normalizar a `base_url` (só http/https, sem query string ou fragment, host em minúsculas, sem barra final)
- Rejeitar `Authorization` em `default_headers` — esse header pertence à credencial
- Guardar uma credencial por integração (`API_KEY` ou `BEARER_TOKEN`), criptografada em repouso, nunca retornada nem logada
- Garantir consistência entre `auth_type` e a credencial armazenada
- Endpoint de health que checa conectividade real com o banco
- Logs estruturados em JSON
- Subida reproduzível com Docker Compose (migrations aplicadas automaticamente)

## Stack

Python 3.14 · FastAPI · Pydantic v2 · SQLAlchemy 2.x · PostgreSQL 17 · Alembic · Pytest · HTTPX · Docker / Docker Compose · Ruff

Sem Redis, message broker, Celery, Kubernetes ou provedor de nuvem. O foco do projeto são os fundamentos de integração; isso adicionaria peças móveis sem demonstrar nada que o escopo atual peça.

## Como rodar

### Pré-requisitos

- Docker e Docker Compose

### Setup

```bash
git clone https://github.com/thelukashdbr/integration-hub.git
cd integration-hub
cp .env.example .env
```

Preencha os dois segredos no `.env`:

```bash
# CREDENTIAL_ENCRYPTION_KEY — chave Fernet usada para criptografar as credenciais em repouso
docker run --rm python:3.14-slim python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# HUB_API_KEY — a chave que os clientes enviam em X-API-Key
docker run --rm python:3.14-slim python -c "import secrets; print(secrets.token_urlsafe(32))"
```

A aplicação se recusa a iniciar com uma chave Fernet inválida, então um erro de configuração aparece na hora, não na primeira gravação de credencial.

### Subindo com Docker

```bash
docker compose up --build
```

| Serviço    | Porta | Função                                        |
|------------|-------|-----------------------------------------------|
| `api`      | 8000  | Integration Hub                               |
| `postgres` | 5432  | Banco de dados (também cria o banco de teste) |

O container `api` roda `alembic upgrade head` antes de subir o uvicorn, então uma clonagem limpa fica utilizável com esse único comando. Documentação interativa: **http://localhost:8000/docs** — clique em *Authorize* e cole o seu `HUB_API_KEY`.

### Rodando localmente sem Docker (só a API)

O Postgres continua vindo do Compose; a API roda num virtualenv com auto-reload:

```bash
docker compose up -d postgres
python -m venv .venv && source .venv/bin/activate   # .venv\Scripts\activate no Windows
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

### Variáveis de ambiente

| Variável                    | Obrigatória | Padrão                                    | Descrição                                                    |
|-----------------------------|-------------|-------------------------------------------|--------------------------------------------------------------|
| `DATABASE_URL`              | não         | `postgresql+psycopg://…@localhost:5432/…` | URL do SQLAlchemy. O Compose aponta para o serviço `postgres` |
| `CREDENTIAL_ENCRYPTION_KEY` | **sim**     | —                                         | Chave Fernet; validada no startup                            |
| `HUB_API_KEY`               | **sim**     | —                                         | Chave estática esperada no header `X-API-Key`                |
| `HTTP_TIMEOUT_SECONDS`      | não         | `10`                                      | Timeout padrão das requisições de saída (usado pela execução) |
| `LOG_LEVEL`                 | não         | `INFO`                                    |                                                              |
| `TEST_DATABASE_URL`         | não         | `…/integration_hub_test`                  | Usada só pela suíte de testes                                |

## Documentação da API

OpenAPI/Swagger completo em `/docs`. Resumo:

| Método | Rota                                    | Descrição                                                   |
|--------|-----------------------------------------|-------------------------------------------------------------|
| POST   | `/integrations`                         | Cria uma integração                                         |
| GET    | `/integrations`                         | Lista integrações, **paginada**, `?name=` (parcial, case-insensitive) e `?status=` opcionais |
| GET    | `/integrations/{ref}`                   | Consulta uma integração                                     |
| PATCH  | `/integrations/{ref}`                   | Atualização parcial (qualquer campo, inclusive `status` e `slug`) |
| DELETE | `/integrations/{ref}`                   | Remove a integração e a credencial dela                     |
| PUT    | `/integrations/{ref}/credential`        | Cria (`201`) ou substitui (`200`) a credencial              |
| GET    | `/integrations/{ref}/credential`        | Lê os metadados da credencial (nunca o segredo)             |
| DELETE | `/integrations/{ref}/credential`        | Remove a credencial                                         |

`{ref}` é o id da integração (UUID) ou o slug dela.
| GET    | `/health`                               | Liveness + conectividade com o banco (não exige API key)    |

### Paginação

`GET /integrations` aceita `?limit=` (padrão `20`, máximo `100`) e `?offset=` (padrão `0`):

```json
{ "items": [ ... ], "limit": 20, "offset": 0, "total": 87 }
```

`total` conta todas as linhas que casam com o filtro, não só a página. Valores fora do intervalo são `422`, não ajustados silenciosamente. Os resultados são ordenados por `created_at` decrescente com `id` como desempate, então duas linhas com o mesmo timestamp não trocam de lugar entre páginas.

## Exemplo de fluxo

Todas as requisições abaixo levam `X-API-Key: <HUB_API_KEY>`.

**1. Criar uma integração**

```http
POST /integrations
{
  "name": "Payments API",
  "description": "Internal payments service",
  "base_url": "https://Payments.Example.com/v1/",
  "auth_type": "API_KEY",
  "default_headers": { "Accept": "application/json" },
  "timeout_seconds": 5
}
```
```json
{
  "id": "47f476e9-…",
  "name": "Payments API",
  "slug": "payments-api",
  "base_url": "https://payments.example.com/v1",
  "auth_type": "API_KEY",
  "default_headers": { "Accept": "application/json" },
  "timeout_seconds": 5.0,
  "status": "ACTIVE",
  "created_at": "…", "updated_at": "…"
}
```

A `base_url` voltou normalizada e o `slug` foi derivado do nome (passe `"slug": "…"` para escolher um). Mandar de novo com o mesmo `name` ou `slug` → `409 Conflict`, e a mensagem diz qual dos dois colidiu. Daqui em diante a integração pode ser referenciada como `payments-api` em vez do UUID.

**2. Guardar a credencial**

```http
PUT /integrations/payments-api/credential
{ "auth_type": "API_KEY", "header_name": "X-Api-Key", "api_key": "sk_live_example" }
```
```json
{
  "id": "c92e8048-…",
  "integration_id": "47f476e9-…",
  "auth_type": "API_KEY",
  "config": { "header_name": "X-Api-Key" },
  "created_at": "…", "updated_at": "…"
}
```

Status `201`. O `api_key` não está na resposta, e nunca vai estar. Mandar o `PUT` de novo substitui o segredo no lugar e retorna `200`.

Para uma integração com bearer token o payload é `{ "auth_type": "BEARER_TOKEN", "token": "…" }`. O corpo é uma união discriminada por `auth_type`, então o Swagger mostra um schema por tipo.

**3. Incompatibilidades são recusadas, não adivinhadas**

```http
PUT /integrations/payments-api/credential
{ "auth_type": "BEARER_TOKEN", "token": "…" }
```
```json
{ "detail": "Credential type BEARER_TOKEN does not match integration auth_type API_KEY" }
```

Status `409`. O mesmo status volta ao tentar um `PATCH` no `auth_type` enquanto existe uma credencial — remova a credencial primeiro, depois troque o tipo.

**4. Pausar**

```http
PATCH /integrations/payments-api
{ "status": "PAUSED" }
```

`PAUSED` é decisão do operador; quando a execução de requisições entrar, uma integração pausada se recusa a executar (`409`).

## Tratamento de erros e segurança

| Status | Significado                                                                                  |
|--------|----------------------------------------------------------------------------------------------|
| 401    | `X-API-Key` ausente ou inválida                                                              |
| 404    | Integração ou credencial não encontrada                                                     |
| 409    | Nome ou slug de integração duplicado · tipo da credencial ≠ `auth_type` · troca de `auth_type` com credencial presente |
| 422    | Corpo da requisição falha na validação (`base_url` ou `slug` inválidos, `Authorization` nos headers, payload errado) |
| 503    | `/health`: banco inacessível                                                                 |

**Segredos.** Os segredos das credenciais são criptografados com Fernet (AES-128-CBC + HMAC, da biblioteca `cryptography`) usando `CREDENTIAL_ENCRYPTION_KEY`. Os campos de segredo são tipados como `SecretStr` nos schemas, então até um `repr` acidental imprime `**********`. A suíte de testes afirma que o texto puro está ausente dos bytes no banco, de toda resposta da API e de todo registro de log. **Limitação documentada:** a chave vive numa variável de ambiente no container da API. Para um MVP de portfólio está bom; um deploy em produção buscaria a chave num gerenciador de segredos (AWS KMS, Vault, Azure Key Vault) com rotação e auditoria de acesso. O `.env` está no `.gitignore`.

**Nada de `Authorization` na configuração.** `default_headers` rejeita esse header: a credencial é o único lugar onde um segredo pode viver, então ele não vai parar numa coluna JSONB em texto puro por acidente.

## Banco de dados e migrations

O Alembic lê a string de conexão do mesmo objeto `Settings` que a app usa — não existe uma segunda cópia da URL no `alembic.ini`. As migrations são autogeradas contra um Postgres real e revisadas à mão antes de serem commitadas:

```bash
alembic revision --autogenerate -m "descreva a mudança"
alembic upgrade head
alembic check          # falha se models e migrations divergiram
```

O `alembic check` vai rodar no CI, para que uma mudança de model sem migration derrube o build, não o deploy.

## Logging

Um objeto JSON por linha (`python-json-logger`), para que os campos sejam consultáveis em vez de extraídos de texto com grep:

```json
{"timestamp": "2026-09-12 17:22:59,845", "level": "INFO", "name": "app.services.credential_service", "message": "credential created", "integration_id": "3be27f89-…", "auth_type": "BEARER_TOKEN"}
```

Tokens, API keys e outros segredos nunca entram num registro de log. O logger do próprio `httpx` fica em `WARNING` porque ele loga a URL completa de toda chamada de saída em `INFO`.

## Rodando os testes

Os testes rodam contra um Postgres real — `JSONB` e `UUID` são específicos do Postgres, então um banco mais leve exercitaria caminhos diferentes. O banco `integration_hub_test` é criado automaticamente pelo serviço Postgres do Compose (`scripts/create-test-db.sql`).

```bash
# dentro do container da api
docker compose run --rm api pytest

# ou localmente, com o postgres do Compose no ar
pytest
```

As tabelas são criadas a partir dos models no início da sessão e todas são limpas após cada teste. Lint e formatação:

```bash
ruff check . && ruff format --check .
```

Cobertura atual (50 testes): exigência da API key, health check do banco (incluindo o caso inacessível, afirmando que nada vaza), CRUD de integrações com validação, derivação e busca por slug, busca por nome, normalização, paginação, filtro e casos `409`, e credenciais — criptografia em repouso, segredo ausente de respostas e logs, regras de incompatibilidade de tipo, cascade no delete.

## Roadmap

Sendo construído incrementalmente, nesta ordem:

1. ~~Fundação do projeto~~ · ~~CRUD de integrações~~ · ~~Credenciais criptografadas~~ · ~~Busca por slug e por nome~~
2. **Execução de requisições** — `POST /integrations/{ref}/execute` com método, path, headers, query e corpo JSON; a credencial é aplicada no servidor; timeouts, erros de conexão, respostas não-2xx e payloads inválidos são classificados, não só relançados
3. **Histórico de execuções** — cada execução registrada com método, path, status code, duração, resultado e mensagem de erro; consultável por integração
4. **Health check** — `POST /integrations/{ref}/health-check` distinguindo *inacessível*, *timeout*, *erro de autenticação*, *erro HTTP* e *resposta inesperada*
5. **OAuth 2.0 client credentials** — endpoint de token, cache de token criptografado com renovação por expiração
6. **Request-id nos logs**, **CI com GitHub Actions** (Postgres como service container, ruff, `alembic check`, pytest)

Deliberadamente fora do escopo do MVP: retries automáticos com backoff, workers em background, métricas/tracing, rate limiting, integração com gerenciador de segredos e UI.

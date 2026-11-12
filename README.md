# Ohmnia — Plataforma Operacional de Medição (projeto acadêmico)

Aplicação web acadêmica e independente para operação de medição de energia: medição de clientes
livres, medição centralizada, equipes de campo, laboratório de medidores, comunicação de campo,
diagnóstico de falhas em média tensão, console de telemetria e uma visão 360 da instalação com
motor de regras.

> **Aviso:** todos os dados são **sintéticos** e todas as integrações externas são **simuladas**.
> O projeto foi construído com base nas funcionalidades de um sistema de referência, sem copiar
> código, dados, credenciais, marcas ou infraestrutura. Veja [docs/DIAGNOSTICO.md](docs/DIAGNOSTICO.md).

## Tecnologias

| Camada | Tecnologia |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 3, Recharts, lucide-react |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, PyJWT, bcrypt |
| Banco | SQLite (padrão) — compatível com PostgreSQL via `OHMNIA_DATABASE_URL` |
| Testes | pytest + TestClient (backend), `node --test` (frontend) |

## Como executar

Pré-requisitos: **Python 3.11 ou 3.12** e **Node.js 20+**.

**Windows:** dê dois cliques em `rodar.bat`. **Linux/macOS:** `sh rodar.sh`.

Manualmente:

```bash
# backend
cd backend
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt      # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m app.seed --reset           # opcional: o primeiro start já gera a base
.venv/Scripts/python -m uvicorn app.main:app --port 8000

# frontend (outro terminal)
cd frontend
npm install
npm run dev
```

Abra http://localhost:3000. Documentação da API: http://localhost:8000/api/docs.

## Usuários de demonstração (fictícios)

Senha de todos: `Ohmnia@2026`

| Matrícula | Perfil | O que demonstra |
|---|---|---|
| OH0001 | Administrador | Tudo, inclusive integrações simuladas e usuários |
| OH0002 | Gestor operacional | Aprovação de laudos, rotinas, edição dos módulos operacionais |
| OH0003 | Analista de laboratório | Fluxo do laboratório (não aprova: segregação de função) |
| OH0004 | Operador de campo | Comunicação de campo, SMC, equipes, console |
| OH0005 | Consulta Visão 360 | Perfil restrito: só a Visão 360 |

## Testes

```bash
cd backend && .venv/Scripts/python -m pytest -q        # 39 testes: regras, API, fluxos, simulações, erros
cd frontend && npm test && npm run typecheck && npm run build
```

## Estrutura

```
backend/app/
  core/          configuração, banco, segurança (bcrypt, JWT, RBAC), auditoria
  recursos.py    ~35 telas operacionais declaradas (campos, validações, fluxos de status, efeitos)
  rules/         visao360.py (14 regras) · diagnostico_mt.py (risco, enlace, ação recomendada)
  services/      diagnostico.py (simulação diária) · jobs.py (rotinas e agendador)
  integrations/  simulador.py (ERP, MDM, head-end, data lake, câmara, bot, diretório, issues)
  routers/       auth, recursos, painel (painel/360/MT), analise, operacao, admin
  seed.py        geração determinística da base sintética
frontend/src/
  app/(app)/     telas autenticadas; app/login
  components/    RecursoPage (tela genérica), shell (menu, cabeçalho, Ctrl+K), ui
  lib/           api, auth (permissões), nav (menu), utils
docs/            DIAGNOSTICO.md (inventário, matriz, riscos, checklist, limitações)
```

## Dados sintéticos

`python -m app.seed --reset [--instalacoes N]` recria a base (semente fixa `OHMNIA_SEED`, padrão 2026):
1 200 instalações em 8 municípios fictícios, ~1 300 medidores de 5 modelos fictícios
(um deles com taxa de falha acima do parque, de propósito), 52 torres de 3 operadoras fictícias,
24 meses de consumo com anomalias plantadas (quedas, picos, leituras estimadas, MMGD com
subgeração e injeção impossível), 30 dias de telemetria, 120 análises de laboratório e cerca de
2 000 registros operacionais ligados a esses medidores e instalações.

## Limitações conhecidas

Ver seção 8 de [docs/DIAGNOSTICO.md](docs/DIAGNOSTICO.md): anexos e fotos, bot real, mapas com
relevo, painel personalizável e alguns fluxos muito específicos não foram reproduzidos.

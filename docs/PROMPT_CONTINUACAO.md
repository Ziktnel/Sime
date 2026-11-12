# Prompt para continuar o projeto Ohmnia com outra IA

Copie o bloco abaixo e envie junto com a pasta `ohmnia/` (sem `node_modules`, `.next`, `.venv` e `backend/data`).

---

Você vai continuar o desenvolvimento da **Ohmnia**, uma aplicação web acadêmica de operação de
medição de energia. O projeto já existe e funciona; seu trabalho é evoluí-lo sem quebrar o que
está pronto.

## Contexto obrigatório
1. Leia primeiro `README.md` e `docs/DIAGNOSTICO.md`. O diagnóstico contém o inventário de módulos,
   a matriz de equivalência (✅ pronto, 🟡 simplificado, ⛔ não reproduzido), as integrações
   simuladas, a checklist e as limitações.
2. Todos os dados são sintéticos (gerados por `backend/app/seed.py`). **Nunca** introduza dados
   reais, nomes de empresas, marcas, URLs internas, credenciais ou identificadores reais. Se
   precisar de exemplos, gere-os com o mesmo padrão do seed (municípios, operadoras e fabricantes fictícios).
3. Stack: FastAPI + SQLAlchemy 2 + SQLite (backend) e Next.js 15 + React 19 + Tailwind + Recharts
   (frontend). Textos da interface em português do Brasil.

## Como o código está organizado
- **Telas de cadastro/consulta** são declaradas em `backend/app/recursos.py` (campos, validações,
  fluxo de status em `transicoes`, `validador` e `efeito` entre módulos). A API genérica
  (`routers/recursos.py`) e a tela genérica (`frontend/src/components/RecursoPage.tsx`, rota
  `/r/<chave>`) funcionam automaticamente para qualquer recurso novo. Para criar uma tela simples,
  adicione um `Recurso`, gere registros de exemplo em `criar_registros` (seed) e um item no menu
  (`frontend/src/lib/nav.ts`).
- **Regras de negócio** ficam em `backend/app/rules/` como funções puras com testes em
  `backend/tests/test_regras.py`.
- **Rotinas** (jobs com progresso, log, cancelamento e agendamento diário) ficam em
  `backend/app/services/jobs.py` (dicionário `JOBS`).
- **Integrações externas** passam sempre por `integrations/simulador.chamar(db, "<nome>")`, que
  aplica os modos normal/vazio/falha/lento configuráveis na tela de integrações.
- **Permissões**: padrão `<modulo>:<recurso>:<ação>` com curingas, definido em
  `core/security.py` (`PERFIS`) e espelhado em `frontend/src/lib/auth.ts`. Toda rota nova precisa de
  `Depends(require_permission(...))` e todo item de menu precisa de `permission`.
- Toda alteração de dados deve gravar auditoria com `core/auditoria.registrar`.

## Regras de trabalho
- Uma funcionalidade só está pronta quando tem backend, frontend, dados de exemplo coerentes e
  teste automatizado. Rode antes de concluir:
  `cd backend && python -m pytest -q` e `cd frontend && npm test && npm run typecheck && npm run build`.
- Não remova validações nem testes existentes para fazer algo passar.
- Mantenha a identidade visual própria (paleta `marca`/`ambar` do `tailwind.config.ts`, logo em
  `components/shell/Logo.tsx`).
- Atualize a matriz em `docs/DIAGNOSTICO.md` sempre que mudar o status de um item.
- Se propor algo que não existia no sistema de referência, marque como "proposta adicional".

## Backlog sugerido (itens ⛔/🟡 da matriz), em ordem de valor para a apresentação
1. Upload de anexos e fotos (laboratório, cliente livre, sugestões) com armazenamento local em
   `backend/data/anexos/`, limite de tamanho, tipos permitidos e listagem/download autenticado.
2. Painel personalizável por usuário (grade de cartões salva no banco) e favoritos no menu.
3. Carta ao cliente e reagendamento de análise no laboratório; laudo em PDF gerado no servidor.
4. Mapa com camadas (cobertura estimada por torre usando o modelo de `diagnostico_mt.sinal_estimado`).
5. Lotes de ações da Gestão MT e arquivo de-para de exportação.
6. Pesquisa progressiva na Visão 360 (cadastro primeiro, depois série, depois regras).
7. Testes de interface ponta a ponta (Playwright) para login, recurso genérico, laboratório e Visão 360.
8. Dockerfile e docker-compose (backend + frontend) para facilitar a avaliação.

Comece listando o que entendeu da arquitetura e o plano para o item 1, e só então implemente.

---

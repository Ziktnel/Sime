# Ohmnia — Diagnóstico, planejamento e matriz de equivalência

> Documento da Etapa 1 (diagnóstico) e Etapa 2 (planejamento) do projeto acadêmico.
> O sistema de referência é tratado apenas como **referência funcional**. Nenhum código,
> dado, credencial, marca, endereço de serviço ou identificador real foi copiado.
> Nomes internos de produtos e de sistemas corporativos foram substituídos por termos genéricos.

## 1. Visão geral do sistema de referência

Plataforma web interna de operação de medição de energia de uma distribuidora. Reúne, num
único portal com controle de acesso por perfil, rotinas que antes viviam em planilhas e scripts:
cadastro e manutenção de medição de clientes livres, gestão de medidores com comunicação remota,
laboratório de aferição, atendimento de equipes de campo, diagnóstico de falhas de comunicação em
média tensão e uma "visão 360" que cruza histórico de consumo e cadastro para apontar indícios de
irregularidade.

| Camada | Sistema de referência | Observação |
|---|---|---|
| Frontend | Next.js (App Router) + React + TypeScript + Tailwind + Radix + Recharts + Leaflet + zustand | ~50 telas, menu por permissão, paleta de comandos, notificações |
| Backend | FastAPI (Python) organizado por módulos (`router` + `service` + `repositories`) | ~300 endpoints; RBAC por permissão `<modulo>:<recurso>:<ação>` |
| Banco | PostgreSQL com ~180 migrations, views materializadas para painéis | |
| Integrações | ERP, MDM, head-end de telemetria, data lake, câmara de comercialização, bot de mensagens, diretório corporativo, issue tracker, serviço de laudos | todas privadas |
| Rotinas | Agendador interno de jobs (diagnóstico diário, ingestão, sincronizações) com log e cancelamento | |
| Entrega | Containers + esteira de CI/CD própria | fora do escopo acadêmico |

## 2. Inventário de módulos e funcionalidades

Legenda de status (coluna "Ohmnia"): **✅ implementado e testado** · **🟡 implementado de forma simplificada** · **⛔ não reproduzido (justificativa na seção 8)**.

### 2.1 Autenticação, perfis e shell
| Funcionalidade de referência | Regras / comportamento | Ohmnia |
|---|---|---|
| Login por matrícula e senha; token Bearer em toda `/api/*` | Limite de tentativas; sessão expira | ✅ bcrypt + JWT HS256, bloqueio após 5 erros por 15 min, expiração configurável |
| RBAC por permissão com curingas | Menu e rotas filtrados por permissão; perfil restrito só acessa a Visão 360 | ✅ mesmo modelo de curingas no backend e no frontend; perfil `consulta_360` |
| Menu lateral por seções, favoritos, paleta de comandos (Ctrl+K) | | ✅ menu + paleta (favoritos ⛔) |
| Sino de notificações por permissão | Notifica quem tem a permissão do evento | ✅ |
| Troca de senha, "minha conta" | Força mínima de senha | ✅ |
| Tema claro/escuro | | ✅ |

### 2.2 Painel (Dashboard)
| Referência | Ohmnia |
|---|---|
| Resumo com KPIs e gráficos do parque, filtros | ✅ KPIs (instalações, medidores, % comunicando, risco alto, pendências por módulo), série diária de comunicação, consumo mensal, status, análises; filtros por regional, tecnologia e período |
| Grade de painel personalizável por usuário | ⛔ (layout fixo) |

### 2.3 Visão 360 da Instalação
| Referência | Regras | Ohmnia |
|---|---|---|
| Busca por instalação, medidor ou cliente | Pesquisa progressiva | ✅ busca por prefixo de instalação, série/SSN ou nome (🟡 sem carregamento progressivo) |
| Dossiê: cadastro, medidores, trocas, 24 meses de consumo, geração distribuída | Dados mascarados (privacidade) | ✅ documento sempre mascarado; consulta registrada na auditoria |
| Motor de 14 regras de diagnóstico (consumo, comercial, medição, MMGD, vizinhança) | Picos com proeminência relativa 0,2 e distância 2; salto ≥ 50 %; faixas 10 %/20 %; tendência de 3 meses | ✅ reimplementação própria (`backend/app/rules/visao360.py`) com testes |
| Gráfico com marcação das regras | | ✅ |
| Relatório congelado (snapshot com hash) e PDF | Imutável, identificado por SHA-256 | ✅ snapshot SHA-256 + CSV (🟡 PDF substituído por exportação CSV/impressão) |

### 2.4 Medição
| Tela | Funcionalidades | Ohmnia |
|---|---|---|
| Clientes Livres | CRUD de medição principal/retaguarda, protocolo, código SCDE, remota, porta; histórico | ✅ recurso `medicao_clientes_livres` |
| Base Telemedidos | Espelho do MDM, atualização sob demanda, exportação CSV | ✅ somente leitura + rotina `atualizar_base_mdm` |
| KEs | Constantes de multiplicação | ✅ regra KE = RTC × RTP |
| Simplificadas | Migrações e solicitação de retorno ao cativo com histórico | ✅ fluxo de situação com transições |
| CCEE | Consulta de curva SCDE por código, P/R, período, integralização 5/60 min, inverter sinal; exportação | ✅ curva determinística + CSV; validações de período |
| Subestação | Cadastro e mapa de subestações | ✅ cadastro (🟡 sem mapa dedicado) |

### 2.5 Medição Centralizada (SMC)
| Tela | Funcionalidades | Ohmnia |
|---|---|---|
| Agrupamento | CRUD de concentradores e agrupamentos | ✅ unicidade do agrupamento |
| Base MDM | Espelho dos pontos, CSV | ✅ |
| Controle Cadastral | Divergências MDM × ERP | ✅ correção da operadora reflete no medidor |
| Comissionamento | Job que gera arquivo a partir de pares CP × medidor | ✅ rotina com progresso + CSV |
| Programações de Nota | Status ABERTA → PROGRAMADO → FINALIZADA/INTERROMPIDA/ENCERRADO, prioridade 0–3, lote, edição e status em massa, importação | ✅ transições, exigência de nota DD, massa, importação CSV; **finalizar restaura a comunicação do medidor** |
| Recapacitação | Programação, atendimento ANTES/DEPOIS, validação, conclusão com resultado e justificativa | ✅ regras de fluxo; substituição concluída marca troca de remota no medidor |

### 2.6 Equipes de Campo (programa BT)
| Referência | Ohmnia |
|---|---|
| Carteira de notas por serviço, prioridades, importação de notas | ✅ `equipes_notas` (importação CSV genérica) |
| Equipes em campo, status | ✅ `equipes_campo` |
| Layout de painel personalizável e modelos de arquivo por serviço | ⛔ |

### 2.7 Laboratório de Medidores
| Tela | Regras | Ohmnia |
|---|---|---|
| Cadastro manual (entrada) | Medidor deve existir; não pode haver análise aberta | ✅ medidor sai da instalação e vai para LABORATÓRIO |
| Análise e pós-análise | Controle de versão; campos obrigatórios para envio | ✅ erro > ±2 % ou lacre violado não pode ser REGULAR |
| Aprovações em lote | Numeração sequencial de laudo | ✅ `LAU-AAAA-NNNN`, **segregação de função** (examinador não aprova) |
| Laudo | Documento do laudo | ✅ HTML imprimível (Salvar como PDF) |
| Quarentena | Irregular aguarda vínculo com nota | ✅ PENDENTE → VINCULADO, medidor vai para descarte |
| Importação de bancada | Sincroniza resultados do software de ensaio | ✅ CSV `serie;erro;lacre` |
| Calendário, indicadores, notas de aferição, configurações | | ✅ |
| Anexos, assinaturas digitalizadas, carta ao cliente, reagendamentos, envio do laudo a serviço externo | | ⛔ |

### 2.8 Comunicação de Campo
| Tela | Ohmnia |
|---|---|
| Cliente cativo: Projeto, Manutenção, Programa BT, Outros (atendimentos com protocolo, equipe, coordenadas, histórico) | ✅ 4 recursos com validação de coordenadas e regra "concluir exige equipe e data" |
| Cliente livre — manutenção (com fotos) | ✅ (🟡 fotos representadas por contador) |
| Substituição de CS | ✅ |
| Cadastro de equipes do bot, logs do bot | ✅ |
| CPU e memória do bot | ✅ série simulada com alerta |
| Bot de mensagens em si (conversa com equipes) | ⛔ — substituído pelos logs sintéticos |

### 2.9 Laboratório de Telecom
| Tela | Ohmnia |
|---|---|
| Triagem de remotas | ✅ |
| Simcards suspensos (com histórico e exportação) | ✅ suspensão derruba a comunicação do medidor; reativação restaura |

### 2.10 Gestão MT (prévia e faturamento de média tensão)
| Referência | Regras | Ohmnia |
|---|---|---|
| Rotina diária: coleta de telemetria → status → risco de falha → ação recomendada final | Risco alto ≥ 70; sinal bom > −95 dBm; fraco ≤ −101 dBm; faixa plausível −130…−30; simula até 2 torres por operadora em 15 km | ✅ `diagnostico_diario` + `rules/diagnostico_mt.py` (modelo de propagação próprio) |
| Painel MT, diagnóstico por medidor, perfil de enlace | | ✅ |
| Mapa de medidores e torres (camadas, coberturas) | | ✅ mapa SVG próprio (🟡 sem camadas de relevo/cobertura) |
| Plano de campo, controle de notas | | ✅ geração do plano a partir das ações, sem duplicar |
| Faturamento MT: triagem, agenda, campo D 10:00, não enviados ao MDM, correção cadastral | | ✅ 5 recursos |
| Lotes de ações e exportação de-para | | ⛔ |

### 2.11 Console de telemetria
| Referência | Ohmnia |
|---|---|
| Pesquisa de SSN, execução em massa de comandos, log, encerrar | ✅ resultado depende do estado do medidor (sem comunicação → TIMEOUT; inexistente → ERROR; sincronizar relógio corrige RELOGIO_CRITICO) |

### 2.12 Gerenciamento
| Referência | Ohmnia |
|---|---|
| Gerenciador de tarefas (jobs): listar, executar, cancelar, agendar, histórico, log | ✅ |
| Usuários (CRUD), acessos por módulo, auditoria de vínculos com diretório | ✅ rotina revoga acesso de vínculo encerrado |
| Calendário/agenda do laboratório | ✅ |
| Credenciais de integrações por usuário | 🟡 substituído por **Integrações simuladas** (modos normal/vazio/falha/lento) |
| Telas demonstrativas | ⛔ (todas as telas da Ohmnia são funcionais) |

### 2.13 Sugestões
| Referência | Ohmnia |
|---|---|
| Registro de melhoria/bug com triagem, prioridade, comentários | ✅ |
| Encaminhar para issue tracker | ✅ endpoint `POST /api/sugestoes/{id}/encaminhar` (issue tracker simulado) |
| Anexos e webhook de retorno | ⛔ |

## 3. Integrações substituídas

| Sistema externo (categoria) | Uso no sistema de referência | Substituto na Ohmnia | Cenários demonstráveis |
|---|---|---|---|
| ERP | Notas de serviço, ordens, cadastro comercial | Tabelas locais + serviço `erp` | normal, falha |
| MDM (gestão de medição) | Base de telemedidos, pontos SMC | Rotina `atualizar_base_mdm` sobre os medidores sintéticos | normal, vazio (bases esvaziadas), falha (rotina em erro) |
| Head-end de telemetria | Leituras diárias, comandos remotos | `simular_dia` + console | normal, falha, lento |
| Data lake | Histórico, comissionamento | Consumo sintético de 24 meses; rotina de comissionamento | normal, falha |
| Câmara de comercialização | Curvas SCDE | Curva determinística por hash do código | normal, vazio, falha |
| Bot de mensagens | Atendimentos de campo, métricas | Logs sintéticos e série de CPU/memória | normal, vazio |
| Diretório corporativo | Vínculo ativo de usuários | Campo `vinculo_ativo` + rotina de auditoria | normal, falha |
| Issue tracker | Encaminhar sugestões | Numeração local `#NNN` | normal, falha |
| Autenticação corporativa | Login | bcrypt + JWT local | — |

Implementação: `backend/app/integrations/simulador.py`. Cada chamada incrementa contadores e
respeita o modo configurado em **Gerenciamento → Integrações simuladas**; em falha a API devolve
HTTP 502 com `{"detail", "integracao"}` e a tela mostra o erro.

## 4. Riscos de exposição identificados (sem valores)

| Categoria encontrada na referência | Função | Tratamento na Ohmnia |
|---|---|---|
| Arquivo de variáveis de ambiente com segredos | Conexão a banco e serviços | Não lido nem copiado; a Ohmnia não precisa de segredo (gera o próprio segredo JWT localmente em `backend/data/`, fora do git) |
| Tokens pessoais de acesso a data lake e a serviço de laudos | Integrações | Não reproduzidos; substituídos por simuladores |
| Credenciais de banco de dados de produção/QA | Persistência | SQLite local |
| URLs e IPs de serviços internos, nomes de hosts | Infraestrutura | Nenhum; único destino é `localhost` |
| Planilhas exportadas de produção e bases locais de dados | Carga inicial | Não copiadas; base 100 % gerada por `app/seed.py` |
| Nomes, matrículas, documentos de clientes e empregados | Operação | Nomes gerados a partir de listas genéricas; documentos sempre mascarados; e-mails `@ohmnia.example` |
| Logos, nome da empresa, nomes internos de programas e produtos | Identidade | Nome e marca próprios ("Ohmnia"), paleta própria, programas renomeados |
| Esteira de deploy e configurações de servidores | Entrega | Fora do escopo |

## 5. Arquitetura proposta (implementada)

```
frontend (Next.js 15, React 19, Tailwind, Recharts)   :3000
   │  /api/*  (rewrite do Next, sem CORS)
backend (FastAPI)                                     :8000
   ├── core/          config por ambiente, banco, segurança (bcrypt/JWT/RBAC), auditoria
   ├── recursos.py    registro declarativo de ~35 telas operacionais (campos, validações, fluxos, efeitos)
   ├── rules/         visao360.py (14 regras) · diagnostico_mt.py (risco, enlace, ação final)
   ├── services/      diagnostico.py (simulação diária) · jobs.py (rotinas + agendador)
   ├── integrations/  simulador.py (8 integrações configuráveis)
   ├── routers/       auth · recursos (API genérica) · painel (painel, 360, MT) · analise · operacao · admin
   └── seed.py        base sintética determinística
SQLite (backend/data/ohmnia.db) — compatível com PostgreSQL via OHMNIA_DATABASE_URL
```

Decisão principal: as telas de cadastro/consulta do sistema de referência são muito parecidas
entre si (tabela + filtros + formulário + histórico + exportação). Em vez de 35 implementações,
a Ohmnia usa **um motor declarativo** (`recursos.py` + `RecursoPage.tsx`). Isso reduz código e
garante que todas as telas tenham filtros, ordenação, paginação, validação, controle de versão,
histórico, comentários, CSV e importação. As telas com lógica própria (Visão 360, diagnóstico,
laboratório, console, CCEE, rotinas) têm backend e frontend dedicados.

### Modelagem de dados
`usuarios` · `instalacoes` (1 200) · `medidores` (≈1 300, com ERB, operadora, sinal, risco) ·
`erbs` · `trocas_medidor` · `consumo_mensal` (24 meses por instalação, geração/injeção/crédito
para MMGD) · `telemetria_diaria` (30 dias por medidor) · `analises` · `acoes_recomendadas` ·
`registros` (recursos genéricos, JSON) · `historico` (auditoria) · `job_runs` · `agendamentos` ·
`notificacoes` · `integracoes` · `relatorios_360`.

Consistência entre módulos: todo registro operacional referencia instalações e medidores que
existem (a validação `ref` recusa códigos inexistentes); efeitos colaterais propagam mudanças
(programação finalizada, recapacitação concluída, simcard suspenso/reativado, correção cadastral,
entrada e aprovação no laboratório, comando de sincronismo de relógio) e o painel recalcula.

## 6. Plano por etapas

| Etapa | Entregas | Situação |
|---|---|---|
| 1 Diagnóstico | Este documento, seções 1–4 | concluída |
| 2 Planejamento | Arquitetura, modelagem, matriz | concluída |
| 3 Preparação | Estrutura, configuração por ambiente, scripts `rodar.bat`/`rodar.sh` | concluída |
| 4 Desenvolvimento | Backend completo, motor de recursos, 12 módulos, frontend | concluída (lacunas na seção 8) |
| 5 Integração | Efeitos entre módulos, notificações, auditoria | concluída |
| 6 Testes | 39 testes de backend (regras, endpoints, fluxos, simulações, erros) + teste de navegação do frontend | concluída |
| 7 Documentação | README, este diagnóstico, checklist | concluída |

## 7. Checklist de validação por módulo

Execute `pytest` (backend) e `npm test` (frontend) e confira manualmente:

- [ ] **Login**: entrar com `OH0001`/`Ohmnia@2026`; errar a senha 5× em `OH0010` → bloqueio (HTTP 423).
- [ ] **Perfis**: `OH0005` só vê a Visão 360; `OH0003` não vê Aprovações; `OH0004` não edita KEs.
- [ ] **Painel**: trocar regional/tecnologia altera KPIs e gráficos.
- [ ] **Visão 360**: buscar uma instalação; ver achados, gráfico, medidor e vínculos; congelar relatório; exportar CSV.
- [ ] **Programações de Nota**: tentar FINALIZADA → ABERTA (recusado); finalizar um PROGRAMADO e ver o medidor COMUNICANDO na Visão 360.
- [ ] **Status em massa**: selecionar várias ABERTA → NÃO PROGRAMAR.
- [ ] **Recapacitação**: tentar concluir sem atendimento DEPOIS (recusado).
- [ ] **KEs**: KE diferente de RTC × RTP é recusado.
- [ ] **Importar CSV**: linha com instalação inexistente é rejeitada com número da linha.
- [ ] **Laboratório**: cadastro manual de medidor em estoque → salvar REGULAR com erro 5 % (recusado no envio) → IRREGULAR → enviar → aprovar como `OH0002` → laudo → quarentena → vincular nota.
- [ ] **Diagnóstico MT**: rodar diagnóstico do próximo dia, acompanhar o log, ver data de referência avançar e notificação no sino; abrir medidor e ver simulação de torres; gerar plano de campo (rodar de novo não duplica).
- [ ] **Mapa**: filtrar município/status e abrir um medidor.
- [ ] **Console**: pesquisar SSN, executar SINCRONIZAR_RELOGIO em lote com um SSN inexistente (ERROR).
- [ ] **CCEE**: consultar; repetir (mesmo resultado); período > 31 dias (recusado); integração `ccee` em falha (erro 502) e vazio (estado vazio).
- [ ] **Rotinas**: alterar horário/ativar agendamento; cancelar uma execução.
- [ ] **Usuários**: criar com senha fraca (recusado); rodar auditoria de vínculos e ver acessos revogados.
- [ ] **Auditoria**: conferir que as ações acima aparecem na trilha.

## 8. Limitações e itens não reproduzidos

| Item | Motivo | Alternativa |
|---|---|---|
| Upload de anexos/fotos/assinaturas | Escopo e armazenamento de arquivos | Contadores e comentários no histórico |
| Envio do laudo a serviço externo, carta ao cliente | Serviço proprietário | Laudo HTML imprimível |
| Bot de mensagens real | Depende de plataforma externa e credenciais | Logs e métricas sintéticos |
| Painel personalizável (grade arrastável) e favoritos | Baixo valor para a demonstração | Layout fixo |
| Mapas com camadas de relevo, cobertura e propagação 3D | Exige dados geográficos reais | Mapa SVG + simulação de enlace log-distância |
| Lotes de ações MT, de-para de exportação | Fluxos muito específicos do processo interno | Recursos de triagem/exportação |
| Pesquisa progressiva (carregamento por etapas) da Visão 360 | Volume sintético é pequeno | Dossiê completo em uma chamada |
| Esteira de CI/CD, containers, migrations versionadas | Fora do escopo acadêmico | `create_all` + seed |
| Modelo de propagação de RF | Simplificação didática | Fórmula documentada em `rules/diagnostico_mt.py` |

Proposta adicional (não existia na referência e está sinalizada): a tela de modos de falha
configuráveis das integrações simuladas, criada para demonstrar os cenários de erro e ausência de dados.

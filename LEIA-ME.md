# SIME — Guia rápido para testar

Sistema acadêmico de gestão operacional de medição de energia. **Todos os dados são fictícios**, nada aqui é real.

## 1. O que precisa ter instalado

- **Python 3.11 ou 3.12**: https://www.python.org/downloads/ (na instalação, marque **"Add Python to PATH"**)
- **Node.js LTS**: https://nodejs.org

Depois de instalar, feche e abra o terminal (ou reinicie o PC).

## 2. Como rodar

**Windows:** dê dois cliques em **`rodar.bat`**.

- Na primeira vez ele instala tudo sozinho. Isso leva de 3 a 5 minutos.
- Vão abrir duas janelas, **SIME API** e **SIME Web**. Deixe as duas abertas.
- Quando a janela **SIME Web** mostrar `Ready`, abra no navegador: **http://localhost:3010**

**Linux/macOS:** rode `sh rodar.sh` e abra http://localhost:3000

Para desligar, feche as duas janelas.

## 3. Logins de teste

A senha é a mesma para todos: **`Ohmnia@2026`**

| Matrícula | Perfil | O que dá para testar |
|---|---|---|
| **OH0001** | Administrador | Tudo, inclusive usuários, auditoria e integrações |
| **OH0002** | Gestora operacional | Aprovar laudos do laboratório, rotinas e edição dos módulos |
| **OH0003** | Analista de laboratório | Fazer análises de medidores (mas não pode aprovar) |
| **OH0004** | Operador de campo | Comunicação de campo, equipes e console de telemetria |
| **OH0005** | Consulta | Só a tela Visão 360 (perfil restrito) |

> Dica: na tela de login, clique em "Usuários de demonstração" para preencher a matrícula.

## 4. Dados de exemplo para testar

A base é gerada igual em todo computador. Por isso os exemplos abaixo funcionam em qualquer máquina.

**Visão 360 da Instalação**: digite o código da instalação, o SSN do medidor ou o nome do cliente:

| Buscar por | Quem é | O que mostra |
|---|---|---|
| `4036974998` | Queila Esteves Queiroz (residencial) | Caso normal, medidor comunicando |
| `4024807223` | Hotel Ferraz Ltda | Medidor que **não responde**, risco de falha alto (91) |
| `4024113414` | Sofia Salgado Teixeira | Cliente com **geração solar** (MMGD, 12 kWp) |
| `4054351640` | Têxtil Valente Ltda | Cliente do **mercado livre** |

**Console de Telemetria**: pesquise por SSN ou número de série:

| SSN | Série | Situação |
|---|---|---|
| `SSN0000001` | `KW57113061` | Comunicando |
| `SSN0000045` | `KW80579025` | Medidor não responde |
| `SSN0000024` | `KW97356734` | Intermitente, instalação com geração solar |

**Laboratório de Medidores**: protocolos em cada etapa do fluxo:

| Protocolo | Status inicial |
|---|---|
| `AM-2026-00013` | Aguardando |
| `AM-2026-00001` | Em análise |
| `AM-2026-00024` | Aguardando aprovação (entre como **OH0002** para aprovar) |
| `AM-2026-00002` | Aprovada (já tem laudo) |
| `AM-2026-00006` | Reaberta |

## 5. Roteiro sugerido (10 minutos)

1. Entre como **OH0001** e veja o **Painel**. Mude os filtros (regional, tecnologia, período) e veja os números mudarem.
2. Abra a **Visão 360** e busque `4024807223`. Veja os alertas das regras.
3. Vá em **Equipes de Campo → Notas BT**. Pesquise, filtre, crie uma nota em **+ Novo** e exporte o CSV.
4. No **Console de Telemetria**, pesquise `SSN0000045` e mande um comando.
5. Saia e entre como **OH0003**. Abra uma análise e tente aprovar (não deixa, porque é segregação de função).
6. Entre como **OH0002** e aprove a análise `AM-2026-00024`.
7. Entre como **OH0005**. Veja que só aparece a Visão 360.
8. Use **Ctrl + K** em qualquer tela para buscar telas rapidamente.

## 6. Deu problema?

| Problema | Solução |
|---|---|
| `'npm' não é reconhecido` | Instale o Node.js e abra o terminal de novo |
| `'python' não é reconhecido` | Reinstale o Python marcando "Add Python to PATH" |
| `Errno 10048` na janela SIME API | A porta 8010 está em uso. Feche outros sistemas abertos |
| "Matrícula ou senha inválidas" | Confira se abriu **http://localhost:3010** (e não a 3000) |
| Quer zerar os dados | Feche tudo, apague a pasta `backend\data` e rode `rodar.bat` de novo |

Documentação da API (para quem quiser testar os endpoints): http://localhost:8010/api/docs

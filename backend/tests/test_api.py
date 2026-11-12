"""Testes de endpoints, fluxos entre módulos e integrações simuladas."""
import time

from app.models import Medidor, Registro, Usuario
from app.recursos import RECURSOS


def _aguardar(client, h, run_id, limite=30):
    for _ in range(limite * 10):
        r = client.get(f"/api/jobs/runs/{run_id}", headers=h).json()
        if r["status"] != "running":
            return r
        time.sleep(0.1)
    raise AssertionError("rotina não terminou")


# ------------------------------------------------------------------ auth
def test_login_invalido_e_bloqueio(client, db):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"matricula": "OH0010", "senha": "errada"}).status_code == 401
    assert client.post("/api/auth/login", json={"matricula": "OH0010", "senha": "errada"}).status_code == 423
    u = db.query(Usuario).filter_by(matricula="OH0010").first()
    assert u.bloqueado_ate is not None and u.senha_hash.startswith("$2")  # bcrypt, nunca texto puro


def test_rota_exige_token(client):
    assert client.get("/api/dashboard/resumo").status_code == 401
    assert client.get("/api/dashboard/resumo", headers={"Authorization": "Bearer xyz"}).status_code == 401


def test_perfil_consulta_so_ve_visao_360(client, consulta):
    assert client.get("/api/dashboard/resumo", headers=consulta).status_code == 403
    assert client.get("/api/recursos", headers=consulta).json() == []
    assert client.get("/api/visao-360/busca?q=400", headers=consulta).status_code == 200


# ---------------------------------------------------------------- painel
def test_dashboard_kpis_e_filtros(client, gestor):
    r = client.get("/api/dashboard/resumo", headers=gestor).json()
    assert r["kpis"]["medidores"] > 0 and 0 <= r["kpis"]["comunicando_pct"] <= 100
    assert len(r["serie_comunicacao"]) >= 7 and len(r["consumo_mensal"]) == 12
    reg = r["regionais"][0]
    f = client.get(f"/api/dashboard/resumo?regional={reg}", headers=gestor).json()
    assert f["kpis"]["instalacoes"] < r["kpis"]["instalacoes"]


# ------------------------------------------------------ recursos genéricos
def test_metadados_respeitam_permissoes(client, campo, analista):
    chaves = {r["chave"] for r in client.get("/api/recursos", headers=campo).json()}
    assert "com_cativo_projeto" in chaves and "am_catalogos" not in chaves
    chaves_lab = {r["chave"] for r in client.get("/api/recursos", headers=analista).json()}
    assert "am_catalogos" in chaves_lab and "smc_agrupamentos" not in chaves_lab


def test_listagem_filtro_ordenacao_paginacao(client, gestor):
    r = client.get("/api/recursos/smc_programacoes_nota?f_status=ABERTA&ordenar=lote&direcao=desc&tamanho=5", headers=gestor).json()
    assert r["total"] > 0 and len(r["itens"]) <= 5
    assert all(i["status"] == "ABERTA" for i in r["itens"])
    lotes = [i["lote"] for i in r["itens"]]
    assert lotes == sorted(lotes, reverse=True)
    assert "status" in r["contagem"]


def test_crud_validacao_historico_e_concorrencia(client, admin, db):
    inst = db.query(Registro).filter_by(recurso="smc_programacoes_nota").first().dados["instalacao"]
    ruim = client.post("/api/recursos/com_cativo_projeto", headers=admin, json={"instalacao": "123", "tipo_servico": "VISTORIA", "status": "ABERTO"})
    assert ruim.status_code == 422 and any("10 dígitos" in e for e in ruim.json()["detail"])
    ok = client.post("/api/recursos/com_cativo_projeto", headers=admin,
                     json={"instalacao": inst, "tipo_servico": "VISTORIA", "status": "ABERTO", "atendimento": "AT12345678"})
    assert ok.status_code == 201, ok.text
    rid, versao = ok.json()["id"], ok.json()["versao"]
    # concluir sem equipe/data viola regra de negócio
    assert client.put(f"/api/recursos/com_cativo_projeto/{rid}", headers=admin, json={"status": "CONCLUIDO", "versao": versao}).status_code == 422
    e = client.put(f"/api/recursos/com_cativo_projeto/{rid}", headers=admin,
                   json={"status": "CONCLUIDO", "equipe": "EQP-01", "data_atendimento": "2026-01-10", "versao": versao})
    assert e.status_code == 200 and e.json()["versao"] == versao + 1
    assert client.put(f"/api/recursos/com_cativo_projeto/{rid}", headers=admin, json={"status": "ABERTO", "versao": versao}).status_code == 409
    hist = client.get(f"/api/recursos/com_cativo_projeto/{rid}/historico", headers=admin).json()
    assert [h["acao"] for h in hist] == ["edicao", "criacao"]
    assert client.delete(f"/api/recursos/com_cativo_projeto/{rid}", headers=admin).status_code == 200


def test_transicao_invalida_e_status_em_massa(client, gestor, db):
    regs = db.query(Registro).filter_by(recurso="smc_programacoes_nota").all()
    finalizada = next(r for r in regs if r.dados["status"] == "FINALIZADA")
    abertas = [r.id for r in regs if r.dados["status"] == "ABERTA"][:3]
    r = client.put(f"/api/recursos/smc_programacoes_nota/{finalizada.id}", headers=gestor, json={"status": "ABERTA"})
    assert r.status_code == 422 and "Transição" in r.json()["detail"][0]
    m = client.patch("/api/recursos/smc_programacoes_nota/status-em-massa", headers=gestor, json={"ids": abertas, "status": "NÃO PROGRAMAR"}).json()
    assert m["atualizados"] == len(abertas)


def test_efeito_entre_modulos_programacao_finalizada_restaura_medidor(client, gestor, db):
    reg = next(r for r in db.query(Registro).filter_by(recurso="smc_programacoes_nota").all()
               if r.dados["status"] == "PROGRAMADO" and r.dados.get("medidor"))
    serie = reg.dados["medidor"]
    db.query(Medidor).filter_by(serie=serie).update({"status_comunicacao": "SEM COMUNICACAO"})
    db.commit()
    r = client.put(f"/api/recursos/smc_programacoes_nota/{reg.id}", headers=gestor, json={"status": "FINALIZADA"})
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(Medidor).filter_by(serie=serie).first().status_comunicacao == "COMUNICANDO"


def test_regra_ke_e_unicidade(client, admin, db):
    k = db.query(Registro).filter_by(recurso="medicao_kes").first().dados
    r = client.post("/api/recursos/medicao_kes", headers=admin, json={**k, "ke": k["ke"] + 1})
    assert r.status_code == 422 and "RTC × RTP" in r.json()["detail"][0]
    a = db.query(Registro).filter_by(recurso="smc_agrupamentos").first().dados
    assert client.post("/api/recursos/smc_agrupamentos", headers=admin, json=a).status_code == 409


def test_somente_leitura_e_exportacao_csv(client, gestor):
    assert client.post("/api/recursos/com_logs_bot", headers=gestor, json={}).status_code in (403, 405)
    r = client.get("/api/recursos/lab_simcards_suspensos/export?f_status=SUSPENSO", headers=gestor)
    assert r.status_code == 200 and r.text.lstrip("﻿").startswith("id;ICCID")


def test_importacao_csv_valida_linha_a_linha(client, admin, db):
    inst = db.query(Registro).filter_by(recurso="smc_programacoes_nota").first().dados["instalacao"]
    csv = f"Equipe;Encarregado;Base;Situação\nEQP-99;Fulano;Vale Verde;DISPONIVEL\n"
    r = client.post("/api/recursos/equipes_campo/importar", headers=admin, json={"csv": csv}).json()
    assert r["criados"] == 0 and r["erros"][0]["linha"] == 2
    csv2 = f"instalacao;nota;servico;status\n{inst};12345678;IP;PENDENTE\n"
    assert client.post("/api/recursos/equipes_notas/importar", headers=admin, json={"csv": csv2}).json()["criados"] == 1


def test_todos_recursos_listam(client, admin):
    for chave in RECURSOS:
        assert client.get(f"/api/recursos/{chave}?tamanho=1", headers=admin).status_code == 200, chave


# ------------------------------------------------------------- Visão 360
def test_visao_360_dossie_relatorio_e_csv(client, consulta, db):
    cod = db.query(Registro).filter_by(recurso="smc_programacoes_nota").first().dados["instalacao"]
    d = client.get(f"/api/visao-360/dossie/{cod}", headers=consulta).json()
    assert d["instalacao"]["codigo"] == cod and len(d["serie"]) == 24
    assert d["diagnostico"]["regras_avaliadas"] == 14
    assert any(v["recurso"] == "smc_programacoes_nota" for v in d["vinculos"]["registros"])
    sha = client.post(f"/api/visao-360/relatorios?codigo={cod}", headers=consulta).json()["sha256"]
    assert len(sha) == 64 and client.get(f"/api/visao-360/relatorios/{sha}", headers=consulta).status_code == 200
    assert client.get(f"/api/visao-360/exportar/{cod}", headers=consulta).text.count("\n") > 24
    assert client.get("/api/visao-360/dossie/0000000000", headers=consulta).status_code == 404


# -------------------------------------------------------------- Gestão MT
def test_diagnostico_e_plano_de_campo(client, gestor):
    d = client.get("/api/gestao-mt/diagnostico", headers=gestor).json()
    assert d["dataref"] and d["itens"]
    det = client.get(f"/api/gestao-mt/medidor/{d['itens'][0]['medidor']['serie']}", headers=gestor).json()
    assert det["acao"] and len(det["telemetria"]) > 0
    p1 = client.post("/api/gestao-mt/plano-campo/gerar", headers=gestor).json()
    p2 = client.post("/api/gestao-mt/plano-campo/gerar", headers=gestor).json()
    assert p2["criados"] == 0  # não duplica itens já planejados
    assert p1["criados"] >= 0


def test_rotina_diagnostico_avanca_um_dia(client, admin):
    antes = client.get("/api/gestao-mt/diagnostico", headers=admin).json()["dataref"]
    run = client.post("/api/jobs/diagnostico_diario/executar", headers=admin).json()
    fim = _aguardar(client, admin, run["id"])
    assert fim["status"] == "success", fim["log"]
    assert client.get("/api/gestao-mt/diagnostico", headers=admin).json()["dataref"] > antes
    assert client.get("/api/notificacoes", headers=admin).json()["nao_lidas"] >= 1


# --------------------------------------------------------- Laboratório
def test_fluxo_completo_de_analise(client, analista, gestor, db):
    m = db.query(Medidor).filter_by(situacao="ESTOQUE").first()
    a = client.post("/api/analise-medidores", headers=analista, json={"serie": m.serie, "solicitante": "CLIENTE"})
    assert a.status_code == 201, a.text
    aid = a.json()["id"]
    assert client.post("/api/analise-medidores", headers=analista, json={"serie": m.serie, "solicitante": "CLIENTE"}).status_code == 409
    assert client.post(f"/api/analise-medidores/{aid}/enviar-aprovacao", headers=analista).status_code == 422
    s = client.put(f"/api/analise-medidores/{aid}", headers=analista, json={"versao": 1, "resultado": "REGULAR", "erro_percentual": 5.0,
                                                                           "lacre_numero": "LC1", "lacre_integro": True})
    assert s.status_code == 200
    r = client.post(f"/api/analise-medidores/{aid}/enviar-aprovacao", headers=analista)
    assert r.status_code == 422 and "REGULAR" in r.json()["detail"]  # erro 5% não pode ser regular
    client.put(f"/api/analise-medidores/{aid}", headers=analista, json={"versao": 2, "resultado": "IRREGULAR",
                                                                      "irregularidade": "Erro de exatidão acima do limite"})
    assert client.post(f"/api/analise-medidores/{aid}/enviar-aprovacao", headers=analista).status_code == 200
    assert client.post("/api/analise-medidores/aprovacoes/aprovar-lote", headers=analista, json={"ids": [aid]}).status_code == 403
    ap = client.post("/api/analise-medidores/aprovacoes/aprovar-lote", headers=gestor, json={"ids": [aid]}).json()
    assert ap["aprovadas"] == 1 and ap["laudos"][0].startswith("LAU-")
    db.expire_all()
    assert db.get(Medidor, m.id).situacao == "QUARENTENA"
    assert "Laudo técnico" in client.get(f"/api/analise-medidores/{aid}/laudo", headers=gestor).text
    v = client.post(f"/api/analise-medidores/{aid}/quarentena/vincular", headers=analista, json={"nota_irregularidade": "12345678"})
    assert v.status_code == 200 and v.json()["quarentena"] == "VINCULADO"


def test_indicadores_laboratorio(client, analista):
    r = client.get("/api/analise-medidores/indicadores", headers=analista).json()
    assert r["total"] > 0 and r["por_fabricante"]


# ------------------------------------------- integrações simuladas e console
def test_integracao_em_falha_e_vazia(client, admin):
    body = {"codigo": "ESVV123456", "tipo": "P", "inicio": "2026-01-01", "fim": "2026-01-02", "integralizacao": "60min"}
    ok = client.post("/api/medicao/ccee/consultas", headers=admin, json=body).json()
    assert len(ok["pontos"]) == 48 and ok == client.post("/api/medicao/ccee/consultas", headers=admin, json=body).json()
    client.put("/api/integracoes/ccee", headers=admin, json={"modo": "falha"})
    r = client.post("/api/medicao/ccee/consultas", headers=admin, json=body)
    assert r.status_code == 502 and r.json()["integracao"] == "ccee"
    client.put("/api/integracoes/ccee", headers=admin, json={"modo": "vazio"})
    assert client.post("/api/medicao/ccee/consultas", headers=admin, json=body).json()["pontos"] == []
    client.put("/api/integracoes/ccee", headers=admin, json={"modo": "normal"})
    ruim = client.post("/api/medicao/ccee/consultas", headers=admin, json={**body, "fim": "2026-03-01"})
    assert ruim.status_code == 422


def test_console_telemetria_execucao(client, campo, db):
    ssns = [m.ssn for m in db.query(Medidor).filter_by(situacao="INSTALADO").limit(3)] + ["SSN_INEXISTENTE"]
    assert client.get(f"/api/telemetria/pesquisar?ssn={ssns[0]}", headers=campo).status_code == 200
    run = client.post("/api/telemetria/execucoes", headers=campo, json={"comando": "STATUS_SINAL", "ssns": ssns}).json()
    fim = _aguardar(client, campo, run["id"])
    assert fim["status"] == "success"
    res = {r["ssn"]: r["status"] for r in fim["resultado"]["resultados"]}
    assert res["SSN_INEXISTENTE"] == "ERROR"


def test_comissionamento_gera_csv(client, gestor, db):
    m = db.query(Medidor).filter_by(situacao="INSTALADO").first()
    run = client.post("/api/smc/comissionamento", headers=gestor, json={"pares": f"CP-001;{m.serie}\nCP-002;NAOEXISTE"}).json()
    fim = _aguardar(client, gestor, run["id"])
    assert fim["resultado"]["erros"] == 1 and fim["resultado"]["csv"].startswith("cp;medidor")


# ---------------------------------------------------------- gerenciamento
def test_usuarios_e_auditoria_de_vinculos(client, admin, gestor):
    assert client.post("/api/admin/usuarios", headers=admin, json={"matricula": "OH9001", "nome": "Novo Usuário", "email": "n@x.example",
                                                                 "perfil": "gestor", "senha": "fraca"}).status_code == 422
    assert client.post("/api/admin/usuarios", headers=admin, json={"matricula": "OH9001", "nome": "Novo Usuário", "email": "n@x.example",
                                                                 "perfil": "gestor", "senha": "Segura123"}).status_code == 201
    assert client.put("/api/admin/usuarios/OH0001", headers=admin, json={"ativo": False}).status_code == 409
    assert client.post("/api/admin/usuarios", headers=gestor, json={}).status_code in (403, 422)
    antes = client.get("/api/admin/auditoria-vinculos", headers=admin).json()
    run = client.post("/api/jobs/auditoria_vinculos/executar", headers=admin).json()
    assert _aguardar(client, admin, run["id"])["resultado"]["revogados"] == len(antes["desligados_com_acesso"])
    assert client.get("/api/admin/auditoria-vinculos", headers=admin).json()["desligados_com_acesso"] == []


def test_sugestao_encaminhada_para_issue(client, gestor, db):
    rid = db.query(Registro).filter_by(recurso="sugestoes").first().id
    r = client.post(f"/api/sugestoes/{rid}/encaminhar", headers=gestor)
    assert r.status_code == 200 and r.json()["issue"].startswith("#")
    assert client.post(f"/api/sugestoes/{rid}/encaminhar", headers=gestor).status_code == 409

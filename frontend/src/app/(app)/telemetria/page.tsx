"use client";

import { useState } from "react";
import { Search, Send } from "lucide-react";
import { JobAcompanhar } from "@/components/JobAcompanhar";
import { Botao, Campo, Cartao, Erro, Selo, Titulo, inputCls, useCarregar, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtData, fmtDataHora, rotulo } from "@/lib/utils";

export default function Telemetria() {
  const toast = useToast();
  const [ssn, setSsn] = useState("");
  const [info, setInfo] = useState<any>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [comando, setComando] = useState("LEITURA_INSTANTANEA");
  const [lista, setLista] = useState("");
  const [run, setRun] = useState<number | null>(null);
  const [resultado, setResultado] = useState<any>(null);
  const { dados: comandos } = useCarregar<string[]>(() => api("/api/telemetria/comandos"));
  const { dados: execs, recarregar } = useCarregar<any[]>(() => api("/api/telemetria/execucoes"));

  async function pesquisar(e: React.FormEvent) {
    e.preventDefault(); setErro(null); setInfo(null);
    try { setInfo(await api(`/api/telemetria/pesquisar?ssn=${encodeURIComponent(ssn)}`)); } catch (err) { setErro((err as Error).message); }
  }
  async function executar() {
    const ssns = lista.split(/[\s,;]+/).filter(Boolean);
    if (!ssns.length) { toast("erro", "Informe ao menos um SSN."); return; }
    try { const r = await api("/api/telemetria/execucoes", { method: "POST", body: { comando, ssns } }); setResultado(null); setRun(r.id); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  return (
    <div>
      <Titulo titulo="Console de telemetria" descricao="Consulta e comandos remotos sobre o head-end simulado. Os resultados dependem do estado real de cada medidor na base." />
      <div className="grid gap-4 lg:grid-cols-2">
        <Cartao titulo="Pesquisar medidor">
          <form onSubmit={pesquisar} className="flex gap-2">
            <input className={inputCls} placeholder="SSN ou série" value={ssn} onChange={(e) => setSsn(e.target.value.toUpperCase())} aria-label="SSN" />
            <Botao type="submit"><Search className="h-4 w-4" />Pesquisar</Botao>
          </form>
          {erro && <div className="mt-3"><Erro texto={erro} /></div>}
          {info && (
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex flex-wrap gap-x-4 gap-y-1"><b>{info.ssn}</b><span>Série {info.serie}</span><span>{info.modelo} fw {info.firmware}</span><span>{rotulo(info.tecnologia)} {info.operadora ?? ""}</span><Selo valor={info.status} /></div>
              <p>Sinal {info.sinal_dbm ?? "—"} dBm · disponibilidade 14 dias: <b>{info.online_pct_14d ?? "—"}%</b> · instalação {info.instalacao ?? "—"}</p>
              <div className="flex gap-1">{info.ultimas.slice().reverse().map((t: any) => <span key={t.data} title={`${fmtData(t.data)}: ${t.leituras} leituras`} className={cn("h-6 flex-1 rounded", t.comunicou ? "bg-marca-500" : "bg-rose-400")} />)}</div>
              <Botao variante="secundario" onClick={() => setLista((l) => (l ? `${l}\n${info.ssn}` : info.ssn))}>Adicionar à execução</Botao>
            </div>
          )}
        </Cartao>
        <Cartao titulo="Execução em massa">
          <div className="space-y-3">
            <Campo rotulo="Comando"><select className={inputCls} value={comando} onChange={(e) => setComando(e.target.value)}>{comandos?.map((c) => <option key={c} value={c}>{rotulo(c)}</option>)}</select></Campo>
            <Campo rotulo="SSNs" ajuda="Um por linha, ou separados por vírgula. Máximo 200."><textarea rows={5} className={cn(inputCls, "font-mono text-xs")} value={lista} onChange={(e) => setLista(e.target.value.toUpperCase())} /></Campo>
            <Botao onClick={executar} disabled={!pode("telemetria:executar")}><Send className="h-4 w-4" />Executar</Botao>
          </div>
        </Cartao>
      </div>
      <div className="mt-4">
        {run && <JobAcompanhar runId={run} onFim={(r) => { setRun(null); setResultado(r.resultado); recarregar(); }} />}
        {resultado && (
          <Cartao titulo={`Resultado — ${rotulo(resultado.comando)}`}>
            <div className="mb-2 flex flex-wrap gap-2">{Object.entries(resultado.resumo || {}).map(([k, v]) => <Selo key={k} valor={`${k}: ${v}`} />)}</div>
            <table className="tabela"><thead><tr><th>SSN</th><th>Status</th><th>Detalhe</th></tr></thead>
              <tbody>{resultado.resultados.map((r: any) => <tr key={r.ssn}><td>{r.ssn}</td><td><Selo valor={r.status} /></td><td>{r.detalhe}</td></tr>)}</tbody></table>
          </Cartao>
        )}
      </div>
      <Cartao titulo="Execuções recentes" className="mt-4">
        <table className="tabela"><thead><tr><th>#</th><th>Comando</th><th>SSNs</th><th>Por</th><th>Início</th><th>Status</th></tr></thead>
          <tbody>{execs?.map((r) => (
            <tr key={r.id} className="cursor-pointer" onClick={() => setResultado(r.resultado)}><td>{r.id}</td><td>{rotulo(r.parametros?.comando)}</td><td>{r.parametros?.ssns?.length}</td><td>{r.disparado_por}</td><td>{fmtDataHora(r.iniciado_em)}</td><td><Selo valor={r.status} /></td></tr>))}</tbody></table>
      </Cartao>
    </div>
  );
}

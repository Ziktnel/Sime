"use client";

import { useState } from "react";
import { ClipboardCheck, Play } from "lucide-react";
import { DetalheMedidor } from "@/components/DetalheMedidor";
import { Botao, Carregando, Erro, Selo, Titulo, Vazio, inputCls, useCarregar, useToast } from "@/components/ui";
import { JobAcompanhar } from "@/components/JobAcompanhar";
import { api, qs } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtData, fmtNum, rotulo } from "@/lib/utils";

const ACOES = ["SUBSTITUIR_MEDIDOR", "TROCAR_OPERADORA", "ANTENA_EXTERNA", "VERIFICAR_ANTENA", "REINICIAR_REMOTA", "SINCRONIZAR_RELOGIO", "INSPECIONAR_CABO", "VISITA_TECNICA", "MONITORAR"];

export default function Diagnostico() {
  const toast = useToast();
  const [codigo, setCodigo] = useState("");
  const [confianca, setConfianca] = useState("");
  const [tensao, setTensao] = useState("");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const [run, setRun] = useState<number | null>(null);
  const { dados: d, erro, carregando, recarregar } = useCarregar<any>(() => api(`/api/gestao-mt/diagnostico${qs({ codigo, confianca, tensao, q })}`), [codigo, confianca, tensao, q]);

  async function rodar() {
    try { const r = await api("/api/jobs/diagnostico_diario/executar", { method: "POST" }); setRun(r.id); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  async function gerarPlano() {
    try { const r = await api("/api/gestao-mt/plano-campo/gerar", { method: "POST" }); toast("ok", `${r.criados} visita(s) incluída(s) no Plano de Campo.`); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  return (
    <div>
      <Titulo titulo="Diagnóstico de medidores" descricao={`Ação recomendada final por medidor com falha ou risco alto${d?.dataref ? ` — referência ${fmtData(d.dataref)}` : ""}.`} acoes={<>
        {pode("gestao-mt:plano-campo:criar") && <Botao variante="secundario" onClick={gerarPlano}><ClipboardCheck className="h-4 w-4" />Gerar plano de campo</Botao>}
        {pode("gerenciamento:tarefas:executar") && <Botao onClick={rodar}><Play className="h-4 w-4" />Rodar diagnóstico do próximo dia</Botao>}
      </>} />
      {run && <JobAcompanhar runId={run} onFim={() => { setRun(null); recarregar(); }} />}
      <div className="mb-3 flex flex-wrap gap-2">
        <input className={cn(inputCls, "max-w-xs")} placeholder="Série, SSN ou instalação" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Pesquisar" />
        <select className={cn(inputCls, "w-auto")} value={codigo} onChange={(e) => setCodigo(e.target.value)} aria-label="Ação"><option value="">Todas as ações</option>{ACOES.map((a) => <option key={a} value={a}>{rotulo(a)}</option>)}</select>
        <select className={cn(inputCls, "w-auto")} value={confianca} onChange={(e) => setConfianca(e.target.value)} aria-label="Confiança"><option value="">Qualquer confiança</option>{["ALTA", "MEDIA", "BAIXA"].map((c) => <option key={c}>{c}</option>)}</select>
        <select className={cn(inputCls, "w-auto")} value={tensao} onChange={(e) => setTensao(e.target.value)} aria-label="Tensão"><option value="">BT e MT</option><option>MT</option><option>BT</option></select>
      </div>
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {carregando && !d ? <Carregando /> : d && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <table className="tabela">
            <thead><tr><th>Medidor</th><th>Instalação</th><th>Tensão</th><th>Status</th><th>Risco</th><th>Sinal</th><th>Ação recomendada</th><th>Confiança</th></tr></thead>
            <tbody>{d.itens.map((i: any) => (
              <tr key={i.id} className="cursor-pointer" onClick={() => setSel(i.medidor.serie)}>
                <td className="font-medium text-marca-700 dark:text-marca-400">{i.medidor.serie}</td><td>{i.medidor.instalacao}</td><td>{i.medidor.tensao}</td>
                <td><Selo valor={i.medidor.status_comunicacao} /></td><td>{fmtNum(i.medidor.risco_falha)}</td><td>{i.medidor.ultimo_sinal_dbm ?? "—"}</td>
                <td title={i.texto}>{i.titulo}</td><td><Selo valor={i.confianca} /></td>
              </tr>))}</tbody>
          </table>
          {d.itens.length === 0 && <Vazio />}
          <p className="px-3 py-2 text-xs text-slate-500">{d.itens.length} medidor(es). Clique numa linha para ver telemetria e simulação de torres.</p>
        </div>
      )}
      {sel && <DetalheMedidor serie={sel} fechar={() => setSel(null)} />}
    </div>
  );
}

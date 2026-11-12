"use client";

import { useState } from "react";
import { Play } from "lucide-react";
import { JobAcompanhar } from "@/components/JobAcompanhar";
import { Botao, Cartao, Carregando, Erro, Selo, Titulo, inputCls, useCarregar, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtDataHora, rotulo } from "@/lib/utils";

export default function Tarefas() {
  const toast = useToast();
  const [run, setRun] = useState<number | null>(null);
  const { dados: jobs, erro, recarregar } = useCarregar<any[]>(() => api("/api/jobs"));
  const { dados: runs, recarregar: recRuns } = useCarregar<any[]>(() => api("/api/jobs/runs"));
  const exec = pode("gerenciamento:tarefas:executar");

  async function disparar(k: string) {
    try { const r = await api(`/api/jobs/${k}/executar`, { method: "POST" }); setRun(r.id); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  async function agendar(k: string, horario: string, ativo: boolean) {
    try { await api(`/api/jobs/${k}/agendamento`, { method: "PUT", body: { horario, ativo } }); toast("ok", "Agendamento atualizado."); recarregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  return (
    <div>
      <Titulo titulo="Rotinas e agendamentos" descricao="Processamentos locais que substituem as rotinas automáticas do sistema de referência. O agendador verifica os horários a cada 30 segundos." />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {run && <JobAcompanhar runId={run} onFim={() => { setRun(null); recarregar(); recRuns(); }} />}
      {!jobs ? <Carregando /> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {jobs.filter((j) => j.job_key !== "console_telemetria").map((j) => (
            <Cartao key={j.job_key} titulo={j.titulo} acoes={exec && j.job_key !== "comissionamento" && <Botao onClick={() => disparar(j.job_key)}><Play className="h-4 w-4" />Executar agora</Botao>}>
              <p className="text-xs text-slate-500">{j.area} · chave <code>{j.job_key}</code></p>
              {j.agendamento ? (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
                  Diário às
                  <input type="time" className={cn(inputCls, "w-auto")} defaultValue={j.agendamento.horario} disabled={!exec} aria-label="Horário"
                    onBlur={(e) => e.target.value !== j.agendamento.horario && agendar(j.job_key, e.target.value, j.agendamento.ativo)} />
                  <label className="flex items-center gap-1"><input type="checkbox" checked={j.agendamento.ativo} disabled={!exec} onChange={(e) => agendar(j.job_key, j.agendamento.horario, e.target.checked)} />ativo</label>
                </div>
              ) : <p className="mt-2 text-sm text-slate-500">Executada sob demanda pela tela do módulo.</p>}
              {j.ultima && <p className="mt-2 text-xs">Última: #{j.ultima.id} <Selo valor={j.ultima.status} /> {fmtDataHora(j.ultima.iniciado_em)} por {j.ultima.disparado_por}</p>}
            </Cartao>
          ))}
        </div>
      )}
      <Cartao titulo="Histórico de execuções" className="mt-4">
        <div className="overflow-x-auto"><table className="tabela"><thead><tr><th>#</th><th>Rotina</th><th>Status</th><th>Progresso</th><th>Por</th><th>Início</th><th>Fim</th></tr></thead>
          <tbody>{runs?.map((r) => (
            <tr key={r.id} className="cursor-pointer" onClick={() => setRun(r.id)}><td>{r.id}</td><td>{rotulo(r.job_key)}</td><td><Selo valor={r.status} /></td><td>{r.progresso}%</td><td>{r.disparado_por}</td><td>{fmtDataHora(r.iniciado_em)}</td><td>{fmtDataHora(r.finalizado_em)}</td></tr>))}</tbody></table></div>
      </Cartao>
    </div>
  );
}

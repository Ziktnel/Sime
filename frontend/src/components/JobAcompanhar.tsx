"use client";

import { useEffect, useRef, useState } from "react";
import { Botao, Selo } from "@/components/ui";
import { api } from "@/lib/api";

/** Acompanha uma rotina em execução (polling), mostrando progresso e log. */
export function JobAcompanhar({ runId, onFim }: { runId: number; onFim?: (run: any) => void }) {
  const [run, setRun] = useState<any>(null);
  const fim = useRef(onFim);
  fim.current = onFim;
  useEffect(() => {
    let vivo = true;
    const tick = async () => {
      try {
        const r = await api(`/api/jobs/runs/${runId}`);
        if (!vivo) return;
        setRun(r);
        if (r.status === "running") setTimeout(tick, 700);
        else fim.current?.(r);
      } catch { if (vivo) setTimeout(tick, 1500); }
    };
    tick();
    return () => { vivo = false; };
  }, [runId]);
  if (!run) return null;
  return (
    <div className="mb-4 rounded-xl border border-slate-200 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-2 flex items-center gap-3">
        <b>Execução #{run.id}</b><Selo valor={run.status} /><span className="text-slate-500">{run.progresso}%</span>
        {run.status === "running" && <Botao variante="fantasma" className="ml-auto" onClick={() => api(`/api/jobs/runs/${run.id}/cancelar`, { method: "POST" })}>Cancelar</Botao>}
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-full bg-marca-500 transition-all" style={{ width: `${run.progresso}%` }} /></div>
      <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs dark:bg-slate-950">{run.log}</pre>
    </div>
  );
}

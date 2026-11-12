"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { JobAcompanhar } from "@/components/JobAcompanhar";
import { Botao, Campo, Cartao, Titulo, inputCls, useToast } from "@/components/ui";
import { api, baixarBlob } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function Comissionamento() {
  const toast = useToast();
  const [pares, setPares] = useState("");
  const [run, setRun] = useState<number | null>(null);
  const [res, setRes] = useState<any>(null);
  async function gerar() {
    try { const r = await api("/api/smc/comissionamento", { method: "POST", body: { pares } }); setRes(null); setRun(r.id); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  return (
    <div>
      <Titulo titulo="Comissionamento SMC" descricao="Gera o arquivo de comissionamento de pares concentrador × medidor, consultando o data lake simulado. Medidores sem comunicação saem como PENDENTE." />
      <Cartao>
        <Campo rotulo="Pares (CP;medidor), um por linha"><textarea rows={8} className={cn(inputCls, "font-mono text-xs")} value={pares} onChange={(e) => setPares(e.target.value)} placeholder={"CP-001;VO12345671\nCP-002;KW76543212"} /></Campo>
        <div className="mt-3 flex justify-end"><Botao onClick={gerar} disabled={!pares.trim()}>Gerar arquivo</Botao></div>
      </Cartao>
      <div className="mt-4">
        {run && <JobAcompanhar runId={run} onFim={(r) => { setRun(null); setRes(r.resultado); }} />}
        {res && (
          <Cartao titulo={`${res.pares} par(es) processado(s), ${res.erros} com erro`} acoes={<Botao variante="secundario" onClick={() => baixarBlob(new Blob([res.csv], { type: "text/csv" }), "comissionamento.csv")}><Download className="h-4 w-4" />Baixar CSV</Botao>}>
            <pre className="max-h-72 overflow-auto rounded bg-slate-50 p-2 text-xs dark:bg-slate-950">{res.csv}</pre>
          </Cartao>
        )}
      </div>
    </div>
  );
}

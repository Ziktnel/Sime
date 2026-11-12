"use client";

import { useState } from "react";
import { Botao, Cartao, Titulo, inputCls, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function Bancada() {
  const toast = useToast();
  const [csv, setCsv] = useState("serie;erro_percentual;lacre\n");
  const [res, setRes] = useState<any>(null);
  const [enviando, setEnviando] = useState(false);
  async function enviar() {
    setEnviando(true);
    try { const r = await api("/api/analise-medidores/sincronizacao-bancada", { method: "POST", body: { csv } }); setRes(r); toast("ok", `${r.atualizadas} análise(s) atualizada(s).`); }
    catch (e) { toast("erro", (e as Error).message); }
    finally { setEnviando(false); }
  }
  return (
    <div>
      <Titulo titulo="Importar resultados de bancada" descricao="Simula a sincronização com o software da bancada de ensaios: cada linha atualiza a análise aberta do medidor (erro de exatidão e lacre)." />
      <Cartao>
        <input type="file" accept=".csv,text/csv" className="mb-2 text-sm" onChange={async (e) => { const f = e.target.files?.[0]; if (f) setCsv(await f.text()); }} />
        <textarea className={cn(inputCls, "font-mono text-xs")} rows={10} value={csv} onChange={(e) => setCsv(e.target.value)} aria-label="CSV da bancada" />
        <div className="mt-3 flex justify-end"><Botao onClick={enviar} carregando={enviando}>Importar</Botao></div>
        {res && (
          <div className="mt-3 text-sm">
            <p><b>{res.atualizadas}</b> atualizada(s), <b>{res.erros.length}</b> linha(s) com erro.</p>
            <ul className="list-disc pl-5 text-rose-700 dark:text-rose-300">{res.erros.map((e: any) => <li key={e.linha}>Linha {e.linha}: {e.erro}</li>)}</ul>
          </div>
        )}
      </Cartao>
    </div>
  );
}

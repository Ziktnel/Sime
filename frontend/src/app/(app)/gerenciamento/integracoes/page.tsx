"use client";

import { Cartao, Carregando, Erro, Selo, Titulo, inputCls, useCarregar, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtNum } from "@/lib/utils";

const MODOS: Record<string, string> = { normal: "Normal", vazio: "Vazio (sem registros)", falha: "Falha (HTTP 502)", lento: "Lento (latência)" };

export default function Integracoes() {
  const toast = useToast();
  const { dados, erro, recarregar } = useCarregar<any[]>(() => api("/api/integracoes"));
  const editar = pode("gerenciamento:integracoes:editar");
  async function mudar(nome: string, modo: string, latencia_ms: number) {
    try { await api(`/api/integracoes/${nome}`, { method: "PUT", body: { modo, latencia_ms } }); toast("ok", `Integração ${nome}: ${MODOS[modo]}.`); recarregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  return (
    <div>
      <Titulo titulo="Integrações simuladas" descricao="Cada sistema externo do sistema de referência foi substituído por um serviço local. Mude o modo para demonstrar sucesso, ausência de dados, falha e lentidão nas telas que dependem dele." />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {!dados ? <Carregando /> : (
        <div className="grid gap-3 md:grid-cols-2">
          {dados.map((i) => (
            <Cartao key={i.nome} titulo={<span className="flex items-center gap-2"><code>{i.nome}</code><Selo valor={i.modo === "normal" ? "OK" : i.modo === "falha" ? "Falha" : i.modo} /></span>}>
              <p className="text-sm text-slate-600 dark:text-slate-300">{i.descricao}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <select className={cn(inputCls, "w-auto")} value={i.modo} disabled={!editar} onChange={(e) => mudar(i.nome, e.target.value, i.latencia_ms)} aria-label={`Modo ${i.nome}`}>
                  {Object.entries(MODOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                {i.modo === "lento" && <input type="number" className={cn(inputCls, "w-28")} defaultValue={i.latencia_ms} min={0} max={5000} disabled={!editar} aria-label="Latência (ms)" onBlur={(e) => mudar(i.nome, i.modo, Number(e.target.value))} />}
                <span className="ml-auto text-xs text-slate-500">{fmtNum(i.chamadas)} chamadas · {fmtNum(i.falhas)} falhas</span>
              </div>
            </Cartao>
          ))}
        </div>
      )}
    </div>
  );
}

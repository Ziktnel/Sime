"use client";

import { useState } from "react";
import { FileText, Plus } from "lucide-react";
import { Botao, Campo, Carregando, Erro, Modal, Selo, Titulo, Vazio, inputCls, useCarregar, useToast } from "@/components/ui";
import { abrirHtml, api, qs } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtData, rotulo } from "@/lib/utils";

const STATUS = ["AGUARDANDO", "EM_ANALISE", "REABERTA", "AGUARDANDO_APROVACAO", "APROVADA"];
const IRREG = ["Lacre violado", "Bobina de potencial interrompida", "Registrador adulterado", "Ponte entre bornes", "Erro de exatidão acima do limite"];

export default function Analises() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [nova, setNova] = useState(false);
  const [aberta, setAberta] = useState<any>(null);
  const { dados: d, erro, carregando, recarregar } = useCarregar<any>(() => api(`/api/analise-medidores${qs({ status, q })}`), [status, q]);

  return (
    <div>
      <Titulo titulo="Análises de medidores" descricao="Fila do laboratório: entrada → análise → envio para aprovação → laudo. Medidores irregulares aprovados vão para a quarentena."
        acoes={pode("analise-medidores:entrada-manual:criar") && <Botao onClick={() => setNova(true)}><Plus className="h-4 w-4" />Cadastro manual</Botao>} />
      <div className="mb-3 flex flex-wrap gap-2">
        {["", ...STATUS].map((s) => (
          <button key={s} onClick={() => setStatus(s)} className={cn("rounded-full border px-3 py-1 text-xs", status === s ? "border-marca-600 bg-marca-600 text-white" : "border-slate-300 dark:border-slate-600")}>
            {s ? rotulo(s) : "Todas"} {d?.status && (s ? d.status[s] ?? 0 : Object.values(d.status as Record<string, number>).reduce((a, b) => a + b, 0))}
          </button>))}
        <input className={cn(inputCls, "ml-auto max-w-xs")} placeholder="Protocolo, medidor, instalação, nota" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Pesquisar" />
      </div>
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {carregando && !d ? <Carregando /> : d && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <table className="tabela">
            <thead><tr><th>Protocolo</th><th>Medidor</th><th>Fabricante</th><th>Solicitante</th><th>Entrada</th><th>Status</th><th>Resultado</th><th>Laudo</th><th /></tr></thead>
            <tbody>{d.itens.map((a: any) => (
              <tr key={a.id}>
                <td className="font-medium">{a.protocolo}</td><td>{a.medidor}</td><td>{a.fabricante} {a.modelo}</td><td>{rotulo(a.solicitante)}</td>
                <td>{fmtData(a.dt_entrada)}</td><td><Selo valor={a.status} /></td><td>{a.resultado ? <Selo valor={a.resultado} /> : "—"}</td>
                <td>{a.numero_laudo ? <button className="inline-flex items-center gap-1 text-marca-700 hover:underline dark:text-marca-400" onClick={() => abrirHtml(`/api/analise-medidores/${a.id}/laudo`).catch((e) => toast("erro", e.message))}><FileText className="h-3 w-3" />{a.numero_laudo}</button> : "—"}</td>
                <td><Botao variante="fantasma" onClick={() => setAberta(a)}>Abrir</Botao></td>
              </tr>))}</tbody>
          </table>
          {d.itens.length === 0 && <Vazio />}
        </div>
      )}
      {nova && <NovaEntrada fechar={() => setNova(false)} feito={() => { setNova(false); recarregar(); }} />}
      {aberta && <Editor analise={aberta} fechar={() => setAberta(null)} feito={() => { setAberta(null); recarregar(); }} />}
    </div>
  );
}

function NovaEntrada({ fechar, feito }: { fechar: () => void; feito: () => void }) {
  const toast = useToast();
  const [v, setV] = useState({ serie: "", solicitante: "DISTRIBUIDORA", nota_servico: "", instalacao: "", dt_agendada: "" });
  const [erro, setErro] = useState<string | null>(null);
  async function salvar(e: React.FormEvent) {
    e.preventDefault(); setErro(null);
    try {
      const r = await api("/api/analise-medidores", { method: "POST", body: { ...v, nota_servico: v.nota_servico || null, instalacao: v.instalacao || null, dt_agendada: v.dt_agendada || null } });
      toast("ok", `Entrada registrada: ${r.protocolo}`); feito();
    } catch (err) { setErro((err as Error).message); }
  }
  return (
    <Modal aberto titulo="Entrada de medidor no laboratório" onFechar={fechar}>
      <form onSubmit={salvar} className="grid gap-3 sm:grid-cols-2">
        <Campo rotulo="Série do medidor *" ajuda="Use um medidor em ESTOQUE (ex.: consulte na Visão 360)."><input className={inputCls} value={v.serie} onChange={(e) => setV({ ...v, serie: e.target.value.toUpperCase() })} required /></Campo>
        <Campo rotulo="Aferição a pedido de *"><select className={inputCls} value={v.solicitante} onChange={(e) => setV({ ...v, solicitante: e.target.value })}>{["CLIENTE", "DISTRIBUIDORA", "ORGAO_REGULADOR"].map((s) => <option key={s} value={s}>{rotulo(s)}</option>)}</select></Campo>
        <Campo rotulo="Nota de serviço" ajuda="8 a 10 dígitos"><input className={inputCls} value={v.nota_servico} onChange={(e) => setV({ ...v, nota_servico: e.target.value })} /></Campo>
        <Campo rotulo="Instalação" ajuda="10 dígitos (opcional)"><input className={inputCls} value={v.instalacao} onChange={(e) => setV({ ...v, instalacao: e.target.value })} /></Campo>
        <Campo rotulo="Data agendada"><input type="date" className={inputCls} value={v.dt_agendada} onChange={(e) => setV({ ...v, dt_agendada: e.target.value })} /></Campo>
        {erro && <p role="alert" className="text-sm text-rose-600 sm:col-span-2">{erro}</p>}
        <div className="flex justify-end gap-2 sm:col-span-2"><Botao type="button" variante="secundario" onClick={fechar}>Cancelar</Botao><Botao type="submit">Registrar</Botao></div>
      </form>
    </Modal>
  );
}

function Editor({ analise, fechar, feito }: { analise: any; fechar: () => void; feito: () => void }) {
  const toast = useToast();
  const [a, setA] = useState(analise);
  const [erro, setErro] = useState<string | null>(null);
  const bloqueada = ["APROVADA", "AGUARDANDO_APROVACAO"].includes(a.status) || !pode("analise-medidores:entrada-manual:criar");
  const set = (k: string, val: unknown) => setA({ ...a, [k]: val });
  async function salvar(enviar: boolean) {
    setErro(null);
    try {
      const salvo = await api(`/api/analise-medidores/${a.id}`, { method: "PUT", body: {
        versao: a.versao, resultado: a.resultado || null, irregularidade: a.resultado === "IRREGULAR" ? a.irregularidade || null : null,
        erro_percentual: a.erro_percentual === "" || a.erro_percentual === null ? null : Number(a.erro_percentual),
        lacre_numero: a.lacre_numero || null, lacre_integro: a.lacre_integro, observacao: a.observacao || null } });
      setA(salvo);
      if (enviar) { await api(`/api/analise-medidores/${a.id}/enviar-aprovacao`, { method: "POST" }); toast("ok", "Enviada para aprovação."); feito(); }
      else toast("ok", "Análise salva.");
    } catch (e) { setErro((e as Error).message); }
  }
  return (
    <Modal aberto titulo={`Análise ${a.protocolo} — medidor ${a.medidor}`} onFechar={fechar}>
      <div className="mb-3 flex flex-wrap gap-3 text-sm"><Selo valor={a.status} /><span>{a.fabricante} {a.modelo}</span><span>Instalação {a.instalacao ?? "—"}</span><span>Examinador {a.examinador ?? "—"}</span></div>
      <fieldset disabled={bloqueada} className="grid gap-3 sm:grid-cols-2">
        <Campo rotulo="Resultado"><select className={inputCls} value={a.resultado || ""} onChange={(e) => set("resultado", e.target.value)}><option value="">—</option><option>REGULAR</option><option>IRREGULAR</option></select></Campo>
        <Campo rotulo="Irregularidade"><select className={inputCls} value={a.irregularidade || ""} disabled={a.resultado !== "IRREGULAR"} onChange={(e) => set("irregularidade", e.target.value)}><option value="">—</option>{IRREG.map((i) => <option key={i}>{i}</option>)}</select></Campo>
        <Campo rotulo="Erro de exatidão (%)" ajuda="Limite para REGULAR: ±2%"><input type="number" step="0.01" className={inputCls} value={a.erro_percentual ?? ""} onChange={(e) => set("erro_percentual", e.target.value)} /></Campo>
        <Campo rotulo="Número do lacre"><input className={inputCls} value={a.lacre_numero || ""} onChange={(e) => set("lacre_numero", e.target.value)} /></Campo>
        <Campo rotulo="Lacre íntegro?"><select className={inputCls} value={a.lacre_integro === null ? "" : String(a.lacre_integro)} onChange={(e) => set("lacre_integro", e.target.value === "" ? null : e.target.value === "true")}><option value="">—</option><option value="true">Sim</option><option value="false">Não</option></select></Campo>
        <div className="sm:col-span-2"><Campo rotulo="Observação"><textarea rows={3} className={inputCls} value={a.observacao || ""} onChange={(e) => set("observacao", e.target.value)} /></Campo></div>
      </fieldset>
      {erro && <p role="alert" className="mt-3 rounded bg-rose-50 p-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-200">{erro}</p>}
      <div className="mt-4 flex justify-end gap-2">
        <Botao variante="secundario" onClick={fechar}>Fechar</Botao>
        {!bloqueada && <><Botao variante="secundario" onClick={() => salvar(false)}>Salvar</Botao><Botao onClick={() => salvar(true)}>Salvar e enviar para aprovação</Botao></>}
      </div>
    </Modal>
  );
}

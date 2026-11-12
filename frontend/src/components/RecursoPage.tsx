"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownUp, Download, History, Pencil, Plus, RefreshCw, Send, Trash2, Upload } from "lucide-react";
import { Botao, Campo as CampoUI, Carregando, Erro, Modal, Selo, Titulo, Vazio, inputCls, useToast } from "@/components/ui";
import { ApiError, api, baixar, qs } from "@/lib/api";
import { cn, fmtData, fmtDataHora, rotulo } from "@/lib/utils";

export type CampoMeta = {
  nome: string; rotulo: string; tipo: string; obrigatorio: boolean; opcoes: string[] | null; lista: boolean; filtro: boolean;
  somente_leitura: boolean; padrao: string | null; msg_padrao: string | null; max_len: number | null;
};
export type RecursoMeta = {
  chave: string; titulo: string; grupo: string; descricao: string; campos: CampoMeta[]; campo_status: string | null;
  transicoes: Record<string, string[]> | null; somente_leitura: boolean; acao_atualizar: string | null;
  acoes: Record<"visualizar" | "criar" | "editar" | "excluir" | "exportar", boolean>;
};
type Linha = Record<string, any> & { id: number; versao: number };
type Lista = { total: number; itens: Linha[]; contagem: Record<string, Record<string, number>> };

let cacheMeta: Promise<RecursoMeta[]> | null = null;
export const carregarMeta = () => (cacheMeta ??= api<RecursoMeta[]>("/api/recursos").catch((e) => { cacheMeta = null; throw e; }));

function valorCelula(c: CampoMeta, v: unknown) {
  if (v === null || v === undefined || v === "") return <span className="text-slate-400">—</span>;
  if (c.tipo === "data") return fmtData(String(v));
  if (c.tipo === "booleano") return v ? "Sim" : "Não";
  if (c.opcoes && (c.nome === "status" || c.nome === "situacao" || c.nome.startsWith("status"))) return <Selo valor={v} />;
  return String(v);
}

export function RecursoPage({ chave }: { chave: string }) {
  const toast = useToast();
  const [meta, setMeta] = useState<RecursoMeta | null>(null);
  const [erroMeta, setErroMeta] = useState<string | null>(null);
  const [lista, setLista] = useState<Lista | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [filtros, setFiltros] = useState<Record<string, string>>({});
  const [ordem, setOrdem] = useState<{ campo: string; dir: "asc" | "desc" } | null>(null);
  const [pagina, setPagina] = useState(1);
  const [tamanho, setTamanho] = useState(25);
  const [selecionados, setSelecionados] = useState<number[]>([]);
  const [editando, setEditando] = useState<Linha | "novo" | null>(null);
  const [historico, setHistorico] = useState<Linha | null>(null);
  const [importar, setImportar] = useState(false);
  const [massa, setMassa] = useState("");

  useEffect(() => {
    setMeta(null);
    setFiltros({}); setQ(""); setPagina(1); setOrdem(null); setSelecionados([]);
    carregarMeta().then((ms) => {
      const m = ms.find((x) => x.chave === chave);
      if (m) setMeta(m);
      else setErroMeta("Você não tem acesso a esta tela ou ela não existe.");
    }).catch((e) => setErroMeta(e.message));
  }, [chave]);

  const params = useMemo(() => ({ q, ordenar: ordem?.campo, direcao: ordem?.dir, pagina, tamanho,
    ...Object.fromEntries(Object.entries(filtros).map(([k, v]) => [`f_${k}`, v])) }), [q, ordem, pagina, tamanho, filtros]);

  const carregar = useCallback(async () => {
    if (!meta) return;
    setCarregando(true); setErro(null);
    try { setLista(await api<Lista>(`/api/recursos/${chave}${qs(params)}`)); }
    catch (e) { setErro((e as Error).message); }
    finally { setCarregando(false); }
  }, [meta, chave, params]);

  useEffect(() => { const t = setTimeout(carregar, 250); return () => clearTimeout(t); }, [carregar]);

  if (erroMeta) return <Erro texto={erroMeta} />;
  if (!meta) return <Carregando />;

  const colunas = meta.campos.filter((c) => c.lista);
  const camposFiltro = meta.campos.filter((c) => c.filtro);
  const paginas = lista ? Math.max(1, Math.ceil(lista.total / tamanho)) : 1;
  const ordenar = (campo: string) => setOrdem((o) => (o?.campo === campo ? { campo, dir: o.dir === "asc" ? "desc" : "asc" } : { campo, dir: "asc" }));
  const statusPossiveis = meta.campo_status ? meta.campos.find((c) => c.nome === meta.campo_status)?.opcoes || [] : [];

  async function excluir(l: Linha) {
    if (!confirm(`Excluir o registro #${l.id}? Esta ação fica registrada na auditoria.`)) return;
    try { await api(`/api/recursos/${chave}/${l.id}`, { method: "DELETE" }); toast("ok", "Registro excluído."); carregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  async function aplicarMassa() {
    if (!massa || !selecionados.length) return;
    try {
      const r = await api<{ atualizados: number; falhas: { id: number; erro: string }[] }>(`/api/recursos/${chave}/status-em-massa`,
        { method: "PATCH", body: { ids: selecionados, status: massa } });
      toast(r.falhas.length ? "erro" : "ok", `${r.atualizados} atualizado(s).` + (r.falhas.length ? `\n${r.falhas.length} recusado(s): ${r.falhas[0].erro}` : ""));
      setSelecionados([]); setMassa(""); carregar();
    } catch (e) { toast("erro", (e as Error).message); }
  }

  async function atualizarBase() {
    try { const r = await api<{ run_id: number }>(`/api/recursos/${chave}/atualizar`, { method: "POST" }); toast("ok", `Rotina #${r.run_id} iniciada. Recarregue em alguns segundos.`); setTimeout(carregar, 3000); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  return (
    <div>
      <Titulo titulo={meta.titulo} descricao={meta.descricao} acoes={<>
        {meta.acao_atualizar && <Botao variante="secundario" onClick={atualizarBase}><RefreshCw className="h-4 w-4" />Atualizar do MDM</Botao>}
        {meta.acoes.exportar && <Botao variante="secundario" onClick={() => baixar(`/api/recursos/${chave}/export${qs({ q, ...Object.fromEntries(Object.entries(filtros).map(([k, v]) => [`f_${k}`, v])) })}`, `${chave}.csv`).catch((e) => toast("erro", e.message))}><Download className="h-4 w-4" />Exportar CSV</Botao>}
        {meta.acoes.criar && <Botao variante="secundario" onClick={() => setImportar(true)}><Upload className="h-4 w-4" />Importar</Botao>}
        {meta.acoes.criar && <Botao onClick={() => setEditando("novo")}><Plus className="h-4 w-4" />Novo</Botao>}
      </>} />

      <div className="mb-3 flex flex-wrap items-end gap-2">
        <input className={cn(inputCls, "max-w-xs")} placeholder="Pesquisar em todos os campos..." value={q} onChange={(e) => { setQ(e.target.value); setPagina(1); }} aria-label="Pesquisar" />
        {camposFiltro.map((c) => {
          const cont = lista?.contagem[c.nome] || {};
          const opcoes = c.opcoes || Object.keys(cont).filter((k) => k !== "None");
          return (
            <select key={c.nome} aria-label={c.rotulo} className={cn(inputCls, "w-auto")} value={filtros[c.nome] || ""}
              onChange={(e) => { setFiltros((f) => ({ ...f, [c.nome]: e.target.value })); setPagina(1); }}>
              <option value="">{c.rotulo}: todos</option>
              {opcoes.map((o) => <option key={o} value={o}>{rotulo(o)}{cont[o] !== undefined && !filtros[c.nome] ? ` (${cont[o]})` : ""}</option>)}
            </select>
          );
        })}
        {(q || Object.values(filtros).some(Boolean)) && <Botao variante="fantasma" onClick={() => { setQ(""); setFiltros({}); }}>Limpar filtros</Botao>}
      </div>

      {meta.campo_status && meta.acoes.editar && selecionados.length > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-marca-200 bg-marca-50 p-2 text-sm dark:border-marca-800 dark:bg-marca-900/30">
          <span>{selecionados.length} selecionado(s)</span>
          <select className={cn(inputCls, "w-auto")} value={massa} onChange={(e) => setMassa(e.target.value)} aria-label="Novo status">
            <option value="">Alterar status para...</option>
            {statusPossiveis.map((s) => <option key={s} value={s}>{rotulo(s)}</option>)}
          </select>
          <Botao onClick={aplicarMassa} disabled={!massa}>Aplicar</Botao>
          <Botao variante="fantasma" onClick={() => setSelecionados([])}>Cancelar</Botao>
        </div>
      )}

      {erro && <Erro texto={erro} tentar={carregar} />}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
        <table className="tabela">
          <thead>
            <tr>
              {meta.campo_status && meta.acoes.editar && (
                <th className="w-8"><input type="checkbox" aria-label="Selecionar página"
                  checked={!!lista?.itens.length && lista.itens.every((l) => selecionados.includes(l.id))}
                  onChange={(e) => setSelecionados(e.target.checked ? lista?.itens.map((l) => l.id) || [] : [])} /></th>
              )}
              <th><button onClick={() => ordenar("id")} className="inline-flex items-center gap-1">#<ArrowDownUp className="h-3 w-3" /></button></th>
              {colunas.map((c) => (
                <th key={c.nome}><button onClick={() => ordenar(c.nome)} className="inline-flex items-center gap-1">{c.rotulo}
                  <ArrowDownUp className={cn("h-3 w-3", ordem?.campo === c.nome ? "text-marca-600" : "opacity-40")} /></button></th>
              ))}
              <th className="text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {lista?.itens.map((l) => (
              <tr key={l.id}>
                {meta.campo_status && meta.acoes.editar && (
                  <td><input type="checkbox" aria-label={`Selecionar ${l.id}`} checked={selecionados.includes(l.id)}
                    onChange={(e) => setSelecionados((s) => e.target.checked ? [...s, l.id] : s.filter((x) => x !== l.id))} /></td>
                )}
                <td className="text-slate-400">{l.id}</td>
                {colunas.map((c) => <td key={c.nome}>{valorCelula(c, l[c.nome])}</td>)}
                <td className="text-right">
                  <div className="inline-flex gap-1">
                    <button className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" title="Histórico e comentários" onClick={() => setHistorico(l)}><History className="h-4 w-4" /></button>
                    {chave === "sugestoes" && meta.acoes.editar && !l.issue && (
                      <button className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" title="Encaminhar para o issue tracker simulado"
                        onClick={() => api(`/api/sugestoes/${l.id}/encaminhar`, { method: "POST" }).then((r) => { toast("ok", `Issue ${r.issue} aberta.`); carregar(); }).catch((e) => toast("erro", e.message))}>
                        <Send className="h-4 w-4" /></button>
                    )}
                    {meta.acoes.editar && <button className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800" title="Editar" onClick={() => setEditando(l)}><Pencil className="h-4 w-4" /></button>}
                    {meta.acoes.excluir && <button className="rounded p-1 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950" title="Excluir" onClick={() => excluir(l)}><Trash2 className="h-4 w-4" /></button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {carregando && !lista && <Carregando />}
        {lista && lista.itens.length === 0 && <Vazio />}
      </div>

      {lista && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-slate-600 dark:text-slate-300">
          <span>{lista.total} registro(s){carregando && " · atualizando..."}</span>
          <div className="flex items-center gap-2">
            <select className={cn(inputCls, "w-auto")} value={tamanho} onChange={(e) => { setTamanho(Number(e.target.value)); setPagina(1); }} aria-label="Itens por página">
              {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n} por página</option>)}
            </select>
            <Botao variante="secundario" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>Anterior</Botao>
            <span>{pagina} / {paginas}</span>
            <Botao variante="secundario" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>Próxima</Botao>
          </div>
        </div>
      )}

      {editando && <Formulario meta={meta} linha={editando === "novo" ? null : editando} fechar={() => setEditando(null)} salvo={() => { setEditando(null); carregar(); }} />}
      {historico && <Historico chave={chave} linha={historico} fechar={() => setHistorico(null)} />}
      {importar && <Importar meta={meta} fechar={() => setImportar(false)} feito={carregar} />}
    </div>
  );
}

function Formulario({ meta, linha, fechar, salvo }: { meta: RecursoMeta; linha: Linha | null; fechar: () => void; salvo: () => void }) {
  const toast = useToast();
  const [v, setV] = useState<Record<string, any>>(() => linha ? { ...linha } : {});
  const [erros, setErros] = useState<string[]>([]);
  const [salvando, setSalvando] = useState(false);
  const statusAtual = linha && meta.campo_status ? linha[meta.campo_status] : null;

  function opcoesDe(c: CampoMeta) {
    if (c.nome !== meta.campo_status || !meta.transicoes) return c.opcoes || [];
    const chave = linha ? String(statusAtual) : "null";
    const prox = meta.transicoes[chave] ?? c.opcoes ?? [];
    return linha ? [statusAtual, ...prox.filter((s) => s !== statusAtual)] : prox;
  }

  function erroLocal(c: CampoMeta): string | undefined {
    const x = v[c.nome];
    if (c.obrigatorio && (x === undefined || x === null || x === "")) return undefined; // backend devolve a mensagem
    if (c.padrao && x && !new RegExp(`^(?:${c.padrao})$`).test(String(x))) return c.msg_padrao || "Formato inválido";
    return undefined;
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setSalvando(true); setErros([]);
    const corpo: Record<string, any> = {};
    meta.campos.forEach((c) => { if (!c.somente_leitura || !linha) corpo[c.nome] = v[c.nome] ?? null; });
    try {
      if (linha) await api(`/api/recursos/${meta.chave}/${linha.id}`, { method: "PUT", body: { ...corpo, versao: linha.versao } });
      else await api(`/api/recursos/${meta.chave}`, { method: "POST", body: corpo });
      toast("ok", linha ? "Alterações salvas." : "Registro criado.");
      salvo();
    } catch (err) {
      const e2 = err as ApiError;
      setErros(e2.detalhes?.length ? e2.detalhes : [e2.message]);
    } finally { setSalvando(false); }
  }

  return (
    <Modal aberto titulo={linha ? `Editar #${linha.id}` : `Novo — ${meta.titulo}`} onFechar={fechar}>
      <form onSubmit={salvar} className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {meta.campos.map((c) => {
            const longo = c.tipo === "texto_longo";
            const disabled = c.somente_leitura;
            const val = v[c.nome] ?? "";
            const set = (x: any) => setV((s) => ({ ...s, [c.nome]: x }));
            return (
              <div key={c.nome} className={longo ? "sm:col-span-2" : ""}>
                <CampoUI rotulo={`${c.rotulo}${c.obrigatorio ? " *" : ""}`} erro={erroLocal(c)} ajuda={c.msg_padrao || undefined}>
                  {c.opcoes ? (
                    <select className={inputCls} value={val} onChange={(e) => set(e.target.value)} disabled={disabled}>
                      <option value="">—</option>
                      {opcoesDe(c).map((o) => <option key={String(o)} value={String(o)}>{rotulo(o)}</option>)}
                    </select>
                  ) : c.tipo === "booleano" ? (
                    <input type="checkbox" checked={!!v[c.nome]} onChange={(e) => set(e.target.checked)} disabled={disabled} />
                  ) : longo ? (
                    <textarea className={inputCls} rows={3} value={val} onChange={(e) => set(e.target.value)} disabled={disabled} maxLength={c.max_len || undefined} />
                  ) : (
                    <input className={inputCls} value={val} disabled={disabled}
                      type={c.tipo === "data" ? "date" : c.tipo === "numero" || c.tipo === "inteiro" ? "number" : "text"}
                      step={c.tipo === "numero" ? "any" : undefined} onChange={(e) => set(e.target.value)} />
                  )}
                </CampoUI>
              </div>
            );
          })}
        </div>
        {meta.transicoes && linha && <p className="text-xs text-slate-500">O status só pode avançar pelas transições permitidas no fluxo do módulo.</p>}
        {erros.length > 0 && <ul role="alert" className="list-disc space-y-1 rounded-lg bg-rose-50 p-3 pl-6 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-200">{erros.map((x) => <li key={x}>{x}</li>)}</ul>}
        <div className="flex justify-end gap-2">
          <Botao type="button" variante="secundario" onClick={fechar}>Cancelar</Botao>
          <Botao type="submit" carregando={salvando}>Salvar</Botao>
        </div>
      </form>
    </Modal>
  );
}

function Historico({ chave, linha, fechar }: { chave: string; linha: Linha; fechar: () => void }) {
  const [itens, setItens] = useState<any[] | null>(null);
  const [texto, setTexto] = useState("");
  const toast = useToast();
  const carregar = useCallback(() => api<any[]>(`/api/recursos/${chave}/${linha.id}/historico`).then(setItens).catch((e) => toast("erro", e.message)), [chave, linha.id, toast]);
  useEffect(() => { carregar(); }, [carregar]);
  async function comentar() {
    if (!texto.trim()) return;
    try { await api(`/api/recursos/${chave}/${linha.id}/comentarios`, { method: "POST", body: { texto } }); setTexto(""); carregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  return (
    <Modal aberto titulo={`Histórico do registro #${linha.id}`} onFechar={fechar}>
      <div className="mb-4 flex gap-2">
        <input className={inputCls} placeholder="Adicionar comentário..." value={texto} onChange={(e) => setTexto(e.target.value)} onKeyDown={(e) => e.key === "Enter" && comentar()} />
        <Botao onClick={comentar}>Comentar</Botao>
      </div>
      {!itens ? <Carregando /> : itens.length === 0 ? <Vazio texto="Sem histórico (registro gerado pela base sintética)." /> : (
        <ol className="space-y-3">
          {itens.map((h) => (
            <li key={h.id} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
              <div className="flex justify-between text-xs text-slate-500"><span className="font-semibold uppercase">{rotulo(h.acao)} · {h.usuario}</span><span>{fmtDataHora(h.em)}</span></div>
              {h.texto && <p className="mt-1">{h.texto}</p>}
              {h.acao === "edicao" && h.depois && (
                <ul className="mt-1 space-y-0.5">{Object.keys(h.depois).map((k) => <li key={k}><b>{k}</b>: {String(h.antes?.[k] ?? "—")} → {String(h.depois[k] ?? "—")}</li>)}</ul>
              )}
            </li>
          ))}
        </ol>
      )}
    </Modal>
  );
}

function Importar({ meta, fechar, feito }: { meta: RecursoMeta; fechar: () => void; feito: () => void }) {
  const cab = meta.campos.filter((c) => !c.somente_leitura).map((c) => c.nome).join(";");
  const [csv, setCsv] = useState(cab + "\n");
  const [res, setRes] = useState<{ criados: number; erros: { linha: number; erros: string[] }[] } | null>(null);
  const [enviando, setEnviando] = useState(false);
  async function enviar() {
    setEnviando(true);
    try { const r = await api(`/api/recursos/${meta.chave}/importar`, { method: "POST", body: { csv } }); setRes(r); if (r.criados) feito(); }
    catch (e) { setRes({ criados: 0, erros: [{ linha: 0, erros: [(e as Error).message] }] }); }
    finally { setEnviando(false); }
  }
  return (
    <Modal aberto titulo={`Importar — ${meta.titulo}`} onFechar={fechar}>
      <p className="mb-2 text-sm text-slate-500">Cole um CSV (separador ; ou ,). A primeira linha é o cabeçalho com os nomes ou rótulos dos campos. Cada linha é validada com as mesmas regras do cadastro.</p>
      <input type="file" accept=".csv,text/csv" className="mb-2 text-sm" onChange={async (e) => { const f = e.target.files?.[0]; if (f) setCsv(await f.text()); }} />
      <textarea className={cn(inputCls, "font-mono text-xs")} rows={8} value={csv} onChange={(e) => setCsv(e.target.value)} />
      {res && (
        <div className="mt-3 text-sm">
          <p className="font-medium">{res.criados} registro(s) criado(s), {res.erros.length} linha(s) recusada(s).</p>
          <ul className="mt-1 max-h-40 list-disc overflow-y-auto pl-5 text-rose-700 dark:text-rose-300">{res.erros.map((e) => <li key={e.linha}>Linha {e.linha}: {e.erros.join("; ")}</li>)}</ul>
        </div>
      )}
      <div className="mt-4 flex justify-end gap-2"><Botao variante="secundario" onClick={fechar}>Fechar</Botao><Botao onClick={enviar} carregando={enviando}>Importar</Botao></div>
    </Modal>
  );
}

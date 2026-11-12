"use client";

import { useEffect, useState } from "react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, FileLock2, Search } from "lucide-react";
import { Botao, Cartao, Carregando, Erro, Kpi, Selo, Titulo, Vazio, inputCls, useToast } from "@/components/ui";
import { api, baixar } from "@/lib/api";
import { cn, fmtData, fmtNum, rotulo } from "@/lib/utils";

const COR_SEV: Record<string, string> = { critico: "border-rose-400 bg-rose-50 dark:bg-rose-950/40", atencao: "border-ambar-400 bg-ambar-300/10", info: "border-sky-300 bg-sky-50 dark:bg-sky-950/30" };

export default function Visao360() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [sugestoes, setSugestoes] = useState<any[]>([]);
  const [codigo, setCodigo] = useState<string | null>(null);
  const [d, setD] = useState<any>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  useEffect(() => {
    if (q.trim().length < 3) { setSugestoes([]); return; }
    const t = setTimeout(() => api<any[]>(`/api/visao-360/busca?q=${encodeURIComponent(q.trim())}`).then(setSugestoes).catch(() => setSugestoes([])), 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (!codigo) return;
    setCarregando(true); setErro(null);
    api(`/api/visao-360/dossie/${codigo}`).then(setD).catch((e) => { setErro(e.message); setD(null); }).finally(() => setCarregando(false));
  }, [codigo]);

  async function congelar() {
    try {
      const r = await api<{ sha256: string }>(`/api/visao-360/relatorios?codigo=${codigo}`, { method: "POST" });
      toast("ok", `Relatório congelado.\nSHA-256: ${r.sha256.slice(0, 16)}…`);
    } catch (e) { toast("erro", (e as Error).message); }
  }

  const i = d?.instalacao;
  return (
    <div>
      <Titulo titulo="Visão 360 da Instalação" descricao="Pesquise por instalação (10 dígitos), série/SSN do medidor ou nome do cliente. O dossiê roda 14 regras de diagnóstico sobre 24 meses de histórico." />
      <div className="relative mb-5 max-w-xl">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input className={cn(inputCls, "pl-9")} placeholder="Ex.: 40… , SSN0000123 ou nome do cliente" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && sugestoes[0]) { setCodigo(sugestoes[0].codigo); setSugestoes([]); } }} aria-label="Pesquisar instalação" />
        {sugestoes.length > 0 && (
          <ul className="absolute z-20 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
            {sugestoes.map((s) => (
              <li key={s.codigo}><button className="block w-full px-3 py-2 text-left text-sm hover:bg-marca-50 dark:hover:bg-slate-800"
                onClick={() => { setCodigo(s.codigo); setSugestoes([]); setQ(s.codigo); }}>
                <b>{s.codigo}</b> · {s.cliente} <span className="text-xs text-slate-500">({rotulo(s.categoria)}, {s.municipio})</span></button></li>
            ))}
          </ul>
        )}
      </div>
      {erro && <Erro texto={erro} />}
      {carregando && <Carregando texto="Montando dossiê..." />}
      {!codigo && !carregando && <Vazio texto="Nenhuma instalação selecionada." />}
      {d && !carregando && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">{i.codigo} — {i.cliente}</h2>
              <p className="text-sm text-slate-500">{i.endereco} · {i.classe_tarifaria} · {i.tensao} · mercado {rotulo(i.mercado)} · documento {i.documento}</p>
            </div>
            <div className="flex gap-2">
              <Botao variante="secundario" onClick={() => baixar(`/api/visao-360/exportar/${i.codigo}`, `visao360_${i.codigo}.csv`).catch((e) => toast("erro", e.message))}><Download className="h-4 w-4" />CSV</Botao>
              <Botao onClick={congelar}><FileLock2 className="h-4 w-4" />Congelar relatório</Botao>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi titulo="Nível de suspeita" valor={<Selo valor={d.diagnostico.nivel_suspeita} className="text-base" />} sub={`${d.diagnostico.pontuacao} pontos`}
              tom={d.diagnostico.nivel_suspeita === "ALTO" ? "rose" : d.diagnostico.nivel_suspeita === "MEDIO" ? "ambar" : "marca"} />
            <Kpi titulo="Achados" valor={d.diagnostico.achados.length} sub={`${d.diagnostico.regras_avaliadas} regras avaliadas`} />
            <Kpi titulo="Mediana de consumo" valor={`${fmtNum(d.diagnostico.mediana_kwh)} kWh`} />
            <Kpi titulo="Mediana da vizinhança" valor={d.vizinhanca_mediana_kwh ? `${fmtNum(d.vizinhanca_mediana_kwh)} kWh` : "—"} sub="mesmo bairro e categoria" />
          </div>
          <Cartao titulo="Histórico de 24 meses">
            <div className="h-72"><ResponsiveContainer><ComposedChart data={d.serie}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="referencia" fontSize={11} /><YAxis fontSize={11} />
              <Tooltip formatter={(v: number, n: string) => [fmtNum(v, 1), n]} /><Legend />
              <Bar dataKey="kwh" name="Consumo (kWh)" fill="#3fb3a3" />
              {i.mmgd && <Line dataKey="gerado_kwh" name="Gerado (kWh)" stroke="#f2a541" dot={false} />}
              {i.mmgd && <Line dataKey="injetado_kwh" name="Injetado (kWh)" stroke="#e0607e" dot={false} />}
              {d.vizinhanca_mediana_kwh && <ReferenceLine y={d.vizinhanca_mediana_kwh} stroke="#5b7fd6" strokeDasharray="4 4" label={{ value: "vizinhança", fontSize: 10 }} />}
              {d.diagnostico.achados.filter((a: any) => a.referencia).map((a: any) => {
                const [m, y] = a.referencia.split("/");
                return <ReferenceLine key={a.codigo} x={`${y}-${m}`} stroke="#e08a1e" label={{ value: a.codigo, fontSize: 10, position: "top" }} />;
              })}
            </ComposedChart></ResponsiveContainer></div>
          </Cartao>
          <div className="grid gap-4 lg:grid-cols-3">
            <Cartao titulo="Achados do diagnóstico" className="lg:col-span-2">
              {d.diagnostico.achados.length === 0 ? <Vazio texto="Nenhuma regra disparou para esta instalação." /> : (
                <ul className="space-y-2">{d.diagnostico.achados.map((a: any) => (
                  <li key={a.codigo} className={cn("rounded-lg border-l-4 p-3 text-sm", COR_SEV[a.severidade])}>
                    <div className="flex flex-wrap items-center gap-2"><b>{a.codigo}</b> {a.titulo}<Selo valor={a.severidade} /><span className="text-xs text-slate-500">{a.grupo}</span></div>
                    <p className="mt-1">{a.descricao}</p>
                    {a.evidencias.length > 0 && <ul className="mt-1 list-disc pl-5 text-xs text-slate-600 dark:text-slate-300">{a.evidencias.map((e: string) => <li key={e}>{e}</li>)}</ul>}
                  </li>))}</ul>
              )}
            </Cartao>
            <div className="space-y-4">
              <Cartao titulo="Medidores">
                {d.medidores.length === 0 ? <Vazio texto="Sem medidor instalado." /> : d.medidores.map((m: any) => (
                  <div key={m.serie} className="space-y-1 text-sm">
                    <div className="flex justify-between"><b>{m.serie}</b><Selo valor={m.status_comunicacao} /></div>
                    <p className="text-xs text-slate-500">{m.fabricante} {m.modelo} · {rotulo(m.tecnologia)} {m.operadora ? `· ${m.operadora}` : ""} · {m.ssn}</p>
                    <p className="text-xs">Sinal {m.ultimo_sinal_dbm ?? "—"} dBm · risco {fmtNum(m.risco_falha)}</p>
                  </div>))}
              </Cartao>
              <Cartao titulo="Cadastro">
                <dl className="grid grid-cols-2 gap-1 text-xs">
                  <dt className="text-slate-500">Ligação</dt><dd>{fmtData(i.data_ligacao)}</dd>
                  <dt className="text-slate-500">Titular desde</dt><dd>{fmtData(i.titular_desde)}</dd>
                  <dt className="text-slate-500">Situação</dt><dd>{rotulo(i.situacao)}</dd>
                  <dt className="text-slate-500">MMGD</dt><dd>{i.mmgd ? `${i.mmgd_kwp} kWp desde ${fmtData(i.mmgd_desde)}` : "Não"}</dd>
                </dl>
                {d.trocas.length > 0 && <p className="mt-2 text-xs text-slate-500">{d.trocas.length} troca(s) de medidor registrada(s).</p>}
              </Cartao>
              <Cartao titulo="Registros em outros módulos">
                {d.vinculos.analises.length + d.vinculos.registros.length === 0 ? <p className="text-xs text-slate-500">Nenhum.</p> : (
                  <ul className="space-y-1 text-xs">
                    {d.vinculos.analises.map((a: any) => <li key={a.protocolo}>Laboratório {a.protocolo} · <Selo valor={a.status} /></li>)}
                    {d.vinculos.registros.map((r: any) => <li key={`${r.recurso}-${r.id}`}><a className="text-marca-700 hover:underline dark:text-marca-400" href={`/r/${r.recurso}`}>{rotulo(r.recurso)} #{r.id}</a> {r.status && <Selo valor={r.status} />}</li>)}
                  </ul>
                )}
              </Cartao>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

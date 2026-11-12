"use client";

import { useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Cartao, Carregando, Erro, Kpi, Titulo, inputCls, useCarregar } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { CORES_GRAFICO, cn, fmtData, fmtNum, rotulo } from "@/lib/utils";

export default function Painel() {
  const [regional, setRegional] = useState("");
  const [tecnologia, setTecnologia] = useState("");
  const [dias, setDias] = useState(30);
  const { dados: d, erro, carregando, recarregar } = useCarregar<any>(
    () => api(`/api/dashboard/resumo${qs({ regional, tecnologia, dias })}`), [regional, tecnologia, dias]);

  return (
    <div>
      <Titulo titulo="Painel operacional" descricao="Indicadores calculados sobre a base sintética. Os filtros recalculam KPIs e gráficos."
        acoes={<>
          <select className={cn(inputCls, "w-auto")} value={regional} onChange={(e) => setRegional(e.target.value)} aria-label="Regional">
            <option value="">Todas as regionais</option>{d?.regionais?.map((r: string) => <option key={r}>{r}</option>)}
          </select>
          <select className={cn(inputCls, "w-auto")} value={tecnologia} onChange={(e) => setTecnologia(e.target.value)} aria-label="Tecnologia">
            <option value="">Todas as tecnologias</option>{["CELULAR", "RF_MESH", "PLC"].map((t) => <option key={t} value={t}>{rotulo(t)}</option>)}
          </select>
          <select className={cn(inputCls, "w-auto")} value={dias} onChange={(e) => setDias(Number(e.target.value))} aria-label="Período">
            {[7, 15, 30].map((n) => <option key={n} value={n}>Últimos {n} dias</option>)}
          </select>
        </>} />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {carregando && !d ? <Carregando /> : d && (
        <div className={cn("space-y-4", carregando && "opacity-60")}>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi titulo="Instalações" valor={fmtNum(d.kpis.instalacoes)} />
            <Kpi titulo="Medidores instalados" valor={fmtNum(d.kpis.medidores)} />
            <Kpi titulo="Comunicando" valor={`${fmtNum(d.kpis.comunicando_pct, 1)}%`} tom={d.kpis.comunicando_pct < 85 ? "ambar" : "marca"} />
            <Kpi titulo="Risco de falha alto" valor={fmtNum(d.kpis.risco_alto)} tom="rose" sub="pontuação ≥ 70" />
            <Kpi titulo="Análises pendentes" valor={fmtNum(d.kpis.analises_pendentes)} tom="ambar" />
            <Kpi titulo="Programações abertas" valor={fmtNum(d.kpis.programacoes_abertas)} tom="ambar" />
            <Kpi titulo="Recapacitações em curso" valor={fmtNum(d.kpis.recapacitacoes_abertas)} />
            <Kpi titulo="Sugestões abertas" valor={fmtNum(d.kpis.sugestoes_abertas)} />
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <Cartao titulo="Medidores comunicando por dia (%)" className="lg:col-span-2">
              <div className="h-64"><ResponsiveContainer><AreaChart data={d.serie_comunicacao}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="data" tickFormatter={(v) => fmtData(v).slice(0, 5)} fontSize={11} />
                <YAxis domain={["dataMin - 2", 100]} fontSize={11} />
                <Tooltip labelFormatter={(v) => fmtData(String(v))} formatter={(v: number) => [`${v}%`, "Comunicando"]} />
                <Area dataKey="percentual" stroke="#5270da" fill="#c9d3f5" />
              </AreaChart></ResponsiveContainer></div>
            </Cartao>
            <Cartao titulo="Status de comunicação">
              <div className="h-52"><ResponsiveContainer><PieChart>
                <Pie data={d.status_comunicacao} dataKey="quantidade" nameKey="status" innerRadius={45} outerRadius={80}>
                  {d.status_comunicacao.map((_: unknown, i: number) => <Cell key={i} fill={CORES_GRAFICO[i % CORES_GRAFICO.length]} />)}
                </Pie>
                <Tooltip formatter={(v: number, n: string) => [v, rotulo(n)]} />
              </PieChart></ResponsiveContainer></div>
              <ul className="mt-2 space-y-1 text-xs">{d.status_comunicacao.map((s: any, i: number) => (
                <li key={s.status} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: CORES_GRAFICO[i % CORES_GRAFICO.length] }} />{rotulo(s.status)}
                  <span className="ml-auto font-medium">{s.quantidade}</span>
                </li>))}</ul>
            </Cartao>
            <Cartao titulo="Consumo faturado (MWh/mês)" className="lg:col-span-2">
              <div className="h-64"><ResponsiveContainer><BarChart data={d.consumo_mensal}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" /><XAxis dataKey="referencia" fontSize={11} /><YAxis fontSize={11} />
                <Tooltip formatter={(v: number) => [`${fmtNum(v, 1)} MWh`, "Consumo"]} />
                <Bar dataKey="mwh" fill="#5270da" radius={[4, 4, 0, 0]} />
              </BarChart></ResponsiveContainer></div>
            </Cartao>
            <Cartao titulo="Análises de laboratório por status">
              <div className="h-64"><ResponsiveContainer><BarChart data={d.analises_por_status} layout="vertical">
                <XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="status" tickFormatter={rotulo} fontSize={10} width={120} />
                <Tooltip labelFormatter={rotulo} /><Bar dataKey="quantidade" fill="#ca8a04" radius={[0, 4, 4, 0]} />
              </BarChart></ResponsiveContainer></div>
            </Cartao>
          </div>
        </div>
      )}
    </div>
  );
}

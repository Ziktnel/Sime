"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Cartao, Carregando, Erro, Kpi, Titulo, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtData, fmtNum, rotulo } from "@/lib/utils";

export default function PainelMT() {
  const { dados: d, erro, recarregar } = useCarregar<any>(() => api("/api/gestao-mt/dashboard"));
  if (erro) return <Erro texto={erro} tentar={recarregar} />;
  if (!d) return <Carregando />;
  const status = Object.fromEntries(d.status.map((s: any) => [s.status, s.quantidade]));
  return (
    <div>
      <Titulo titulo="Painel MT" descricao={`Saúde do parque de média tensão. Diagnóstico de referência: ${fmtData(d.dataref)}.`} />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi titulo="Medidores MT" valor={fmtNum(d.medidores_mt)} />
        <Kpi titulo="Comunicando" valor={fmtNum(status.COMUNICANDO || 0)} />
        <Kpi titulo="Com falha" valor={fmtNum(d.medidores_mt - (status.COMUNICANDO || 0))} tom="ambar" />
        <Kpi titulo="Risco alto" valor={fmtNum(d.faixas_risco.find((f: any) => f.faixa === "70-100")?.quantidade)} tom="rose" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Cartao titulo="Faixas de risco de falha">
          <div className="h-56"><ResponsiveContainer><BarChart data={d.faixas_risco}><XAxis dataKey="faixa" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Bar dataKey="quantidade" fill="#e0607e" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </Cartao>
        <Cartao titulo="Ações recomendadas (todo o parque)">
          <div className="h-56"><ResponsiveContainer><BarChart data={d.acoes} layout="vertical"><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="codigo" tickFormatter={rotulo} width={130} fontSize={10} /><Tooltip labelFormatter={rotulo} /><Bar dataKey="quantidade" fill="#14786d" /></BarChart></ResponsiveContainer></div>
        </Cartao>
        <Cartao titulo="Comunicação por operadora (MT)">
          <table className="tabela"><thead><tr><th>Operadora</th><th>Medidores</th><th>Comunicando</th></tr></thead>
            <tbody>{d.operadoras.map((o: any) => <tr key={o.operadora}><td>{o.operadora}</td><td>{o.medidores}</td><td>{fmtNum(o.comunicando_pct, 1)}%</td></tr>)}</tbody></table>
          <div className="mt-4 h-28"><ResponsiveContainer><BarChart data={d.operadoras}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="operadora" fontSize={10} /><YAxis domain={[0, 100]} fontSize={10} /><Bar dataKey="comunicando_pct" fill="#f2a541" /></BarChart></ResponsiveContainer></div>
        </Cartao>
      </div>
    </div>
  );
}

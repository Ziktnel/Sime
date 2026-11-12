"use client";

import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Cartao, Carregando, Erro, Kpi, Titulo, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtNum } from "@/lib/utils";

export default function Indicadores() {
  const { dados: d, erro } = useCarregar<any>(() => api("/api/analise-medidores/indicadores"));
  if (erro) return <Erro texto={erro} />;
  if (!d) return <Carregando />;
  return (
    <div>
      <Titulo titulo="Indicadores do laboratório" descricao="Produtividade e resultados das análises." />
      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Kpi titulo="Análises registradas" valor={fmtNum(d.total)} />
        <Kpi titulo="Tempo médio entrada → análise" valor={`${fmtNum(d.tempo_medio_dias, 1)} dias`} tom="ambar" />
        <Kpi titulo="Taxa de irregularidade" valor={`${fmtNum(d.irregularidade_pct, 1)}%`} tom="rose" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Cartao titulo="Entradas x analisadas por mês">
          <div className="h-64"><ResponsiveContainer><LineChart data={d.por_mes}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="mes" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend />
            <Line dataKey="entradas" stroke="#f2a541" /><Line dataKey="analisadas" stroke="#14786d" /></LineChart></ResponsiveContainer></div>
        </Cartao>
        <Cartao titulo="Resultado por fabricante">
          <div className="h-64"><ResponsiveContainer><BarChart data={d.por_fabricante}><XAxis dataKey="fabricante" fontSize={11} /><YAxis fontSize={11} /><Tooltip /><Legend />
            <Bar dataKey="regular" stackId="a" fill="#14786d" /><Bar dataKey="irregular" stackId="a" fill="#e0607e" /></BarChart></ResponsiveContainer></div>
        </Cartao>
        <Cartao titulo="Tipos de irregularidade" className="lg:col-span-2">
          <div className="h-56"><ResponsiveContainer><BarChart data={d.irregularidades} layout="vertical"><XAxis type="number" fontSize={11} /><YAxis type="category" dataKey="tipo" width={220} fontSize={11} /><Tooltip /><Bar dataKey="quantidade" fill="#f2a541" /></BarChart></ResponsiveContainer></div>
        </Cartao>
      </div>
    </div>
  );
}

"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Carregando, Erro, Modal, Selo, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtData, fmtNum } from "@/lib/utils";

export function DetalheMedidor({ serie, fechar }: { serie: string; fechar: () => void }) {
  const { dados: d, erro } = useCarregar<any>(() => api(`/api/gestao-mt/medidor/${serie}`), [serie]);
  return (
    <Modal aberto titulo={`Medidor ${serie}`} onFechar={fechar} largura="max-w-3xl">
      {erro && <Erro texto={erro} />}
      {!d && !erro && <Carregando />}
      {d && (
        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            <span>Instalação <b>{d.medidor.instalacao ?? "—"}</b></span><span>{d.medidor.modelo} · {d.medidor.tecnologia}</span>
            <span>Operadora {d.medidor.operadora ?? "—"}</span><span>Sinal {d.medidor.ultimo_sinal_dbm ?? "—"} dBm</span>
            <span>Risco <b>{fmtNum(d.medidor.risco_falha)}</b></span><Selo valor={d.medidor.status_comunicacao} />
          </div>
          {d.acao && (
            <div className="rounded-lg border-l-4 border-marca-500 bg-marca-50 p-3 dark:bg-marca-900/30">
              <p className="font-semibold">{d.acao.titulo} <Selo valor={d.acao.confianca} className="ml-1" /></p>
              <p>{d.acao.texto}</p><p className="text-xs text-slate-500">Justificativa: {d.acao.justificativa} · diagnóstico de {fmtData(d.acao.dataref)}</p>
            </div>
          )}
          <div>
            <p className="mb-1 font-medium">Leituras recebidas por dia (últimos 30 dias)</p>
            <div className="h-40"><ResponsiveContainer><BarChart data={d.telemetria}>
              <XAxis dataKey="data" tickFormatter={(v) => fmtData(v).slice(0, 5)} fontSize={10} /><YAxis domain={[0, 96]} fontSize={10} />
              <Tooltip labelFormatter={(v) => fmtData(String(v))} />
              <Bar dataKey="leituras">{d.telemetria.map((t: any) => <Cell key={t.data} fill={t.comunicou ? "#14786d" : "#e0607e"} />)}</Bar>
            </BarChart></ResponsiveContainer></div>
          </div>
          {d.enlaces.length > 0 && (
            <div>
              <p className="mb-1 font-medium">Simulação de enlace com torres próximas (raio de 15 km)</p>
              <table className="tabela"><thead><tr><th>Torre</th><th>Operadora</th><th>Distância</th><th>Sinal estimado</th><th>Viável</th></tr></thead>
                <tbody>{d.enlaces.map((e: any) => (
                  <tr key={e.erb}><td>{e.erb}</td><td>{e.operadora}{e.operadora === d.medidor.operadora && " (atual)"}</td><td>{fmtNum(e.distancia_m / 1000, 1)} km</td>
                    <td>{e.sinal_estimado_dbm} dBm</td><td><Selo valor={e.viavel ? "OK" : "Fraco"} /></td></tr>))}</tbody></table>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

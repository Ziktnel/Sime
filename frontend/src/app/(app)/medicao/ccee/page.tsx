"use client";

import { useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download } from "lucide-react";
import { Botao, Campo, Cartao, Erro, Kpi, Titulo, Vazio, inputCls, useToast } from "@/components/ui";
import { ApiError, api, baixar } from "@/lib/api";
import { fmtNum } from "@/lib/utils";

const hoje = new Date();
const iso = (d: Date) => d.toISOString().slice(0, 10);

export default function Ccee() {
  const toast = useToast();
  const [f, setF] = useState({ codigo: "ESVV123456", tipo: "P", inicio: iso(new Date(hoje.getTime() - 6 * 864e5)), fim: iso(new Date(hoje.getTime() - 864e5)), integralizacao: "60min", inverter: false });
  const [res, setRes] = useState<any>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function consultar(e: React.FormEvent) {
    e.preventDefault(); setErro(null); setCarregando(true);
    try { setRes(await api("/api/medicao/ccee/consultas", { method: "POST", body: f })); }
    catch (err) { const x = err as ApiError; setErro(x.detalhes.length ? x.detalhes.join(" ") : x.message); setRes(null); }
    finally { setCarregando(false); }
  }

  return (
    <div>
      <Titulo titulo="Consulta de medição na câmara (SCDE)" descricao="Curva de carga simulada e determinística por código: a mesma consulta sempre retorna os mesmos valores. Coloque a integração 'ccee' em falha ou vazio para ver os outros cenários." />
      <Cartao>
        <form onSubmit={consultar} className="grid gap-3 sm:grid-cols-3 lg:grid-cols-7">
          <Campo rotulo="Código SCDE" ajuda="4 letras + 6 dígitos"><input className={inputCls} value={f.codigo} onChange={(e) => setF({ ...f, codigo: e.target.value.toUpperCase() })} /></Campo>
          <Campo rotulo="Medidor"><select className={inputCls} value={f.tipo} onChange={(e) => setF({ ...f, tipo: e.target.value })}><option value="P">Principal</option><option value="R">Retaguarda</option></select></Campo>
          <Campo rotulo="Início"><input type="date" className={inputCls} value={f.inicio} onChange={(e) => setF({ ...f, inicio: e.target.value })} /></Campo>
          <Campo rotulo="Fim" ajuda="Máximo 31 dias"><input type="date" className={inputCls} value={f.fim} onChange={(e) => setF({ ...f, fim: e.target.value })} /></Campo>
          <Campo rotulo="Integralização"><select className={inputCls} value={f.integralizacao} onChange={(e) => setF({ ...f, integralizacao: e.target.value })}><option>5min</option><option>60min</option></select></Campo>
          <label className="flex items-center gap-2 self-center text-sm"><input type="checkbox" checked={f.inverter} onChange={(e) => setF({ ...f, inverter: e.target.checked })} />Inverter sinal</label>
          <div className="flex items-end gap-2"><Botao type="submit" carregando={carregando}>Consultar</Botao>
            <Botao type="button" variante="secundario" onClick={() => baixar("/api/medicao/ccee/consultas/csv", `ccee_${f.codigo}${f.tipo}.csv`, { method: "POST", body: f }).catch((e) => toast("erro", e.message))} aria-label="Baixar CSV"><Download className="h-4 w-4" /></Botao></div>
        </form>
      </Cartao>
      {erro && <div className="mt-4"><Erro texto={erro} /></div>}
      {res && (res.pontos.length === 0 ? <div className="mt-4"><Vazio texto="A câmara não retornou medições para este período." /></div> : (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">
            <Kpi titulo="Energia ativa no período" valor={`${fmtNum(res.total_kwh / 1000, 2)} MWh`} />
            <Kpi titulo="Demanda máxima" valor={`${fmtNum(res.demanda_max_kw, 1)} kW`} tom="ambar" />
            <Kpi titulo="Intervalos" valor={fmtNum(res.pontos.length)} />
          </div>
          <Cartao titulo="Curva de carga (kWh por intervalo)">
            <div className="h-72"><ResponsiveContainer><AreaChart data={res.pontos}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="instante" tickFormatter={(v) => v.slice(5, 13).replace("T", " ")} fontSize={10} minTickGap={40} /><YAxis fontSize={11} /><Tooltip />
              <Area dataKey="ativa_kwh" name="Ativa" stroke="#5270da" fill="#c9d3f5" /><Area dataKey="reativa_kvarh" name="Reativa" stroke="#ca8a04" fill="#f5d27a" fillOpacity={0.3} /></AreaChart></ResponsiveContainer></div>
          </Cartao>
        </div>
      ))}
    </div>
  );
}

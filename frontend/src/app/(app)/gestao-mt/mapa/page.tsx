"use client";

import { useMemo, useState } from "react";
import { DetalheMedidor } from "@/components/DetalheMedidor";
import { Cartao, Carregando, Erro, Titulo, inputCls, useCarregar } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { cn, rotulo } from "@/lib/utils";

const MUNICIPIOS = ["Vale Verde", "Porto Claro", "Serra Alta", "Rio Manso", "Campo Belo do Sul", "Nova Aurora", "Santa Luzia do Mar", "Pedra Azul do Norte"];
const COR: Record<string, string> = { COMUNICANDO: "#14786d", INTERMITENTE: "#f2a541", "SEM COMUNICACAO": "#e0607e", "MEDIDOR NAO RESPONDE": "#b4235a", RELOGIO_CRITICO: "#8e6cc9" };
const COR_OP: Record<string, string> = { "Aurora Tel": "#5b7fd6", "Brisa Móvel": "#e08a1e", "Celta Net": "#7a8a8a" };

/** Mapa em SVG com projeção equiretangular simples — dispensa provedores de mapa externos. */
export default function Mapa() {
  const [municipio, setMunicipio] = useState("");
  const [status, setStatus] = useState("");
  const [sel, setSel] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const { dados: d, erro } = useCarregar<any>(() => api(`/api/gestao-mt/mapa${qs({ municipio })}`), [municipio]);

  const proj = useMemo(() => {
    if (!d) return null;
    const pts = [...d.medidores, ...d.erbs].filter((p: any) => p.lat);
    const lat = pts.map((p: any) => p.lat), lon = pts.map((p: any) => p.lon);
    const [a, b, c, e] = [Math.min(...lat), Math.max(...lat), Math.min(...lon), Math.max(...lon)];
    return (la: number, lo: number) => ({ x: 20 + ((lo - c) / (e - c || 1)) * 760, y: 20 + ((b - la) / (b - a || 1)) * 560 });
  }, [d]);

  const meds = (d?.medidores || []).filter((m: any) => !status || m.status_comunicacao === status);
  return (
    <div>
      <Titulo titulo="Mapa de medidores celulares e torres" descricao="Círculos: medidores (cor = status). Triângulos: torres (cor = operadora). Clique num medidor para o diagnóstico." acoes={<>
        <select className={cn(inputCls, "w-auto")} value={municipio} onChange={(e) => setMunicipio(e.target.value)} aria-label="Município"><option value="">Todos os municípios</option>{MUNICIPIOS.map((m) => <option key={m}>{m}</option>)}</select>
        <select className={cn(inputCls, "w-auto")} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">Todos os status</option>{Object.keys(COR).map((s) => <option key={s} value={s}>{rotulo(s)}</option>)}</select>
      </>} />
      {erro && <Erro texto={erro} />}
      {!d || !proj ? <Carregando /> : (
        <Cartao>
          <svg viewBox="0 0 800 600" className="h-auto w-full rounded-lg bg-marca-50/50 dark:bg-slate-950" role="img" aria-label="Mapa">
            {d.erbs.map((e: any) => { const p = proj(e.lat, e.lon); return (
              <polygon key={e.codigo} points={`${p.x},${p.y - 8} ${p.x - 7},${p.y + 5} ${p.x + 7},${p.y + 5}`} fill={COR_OP[e.operadora]} opacity={0.85}><title>{e.codigo} · {e.operadora} {e.tecnologia}</title></polygon>); })}
            {meds.map((m: any) => { const p = proj(m.lat, m.lon); return (
              <circle key={m.serie} cx={p.x} cy={p.y} r={hover === m.serie ? 7 : 4} fill={COR[m.status_comunicacao] || "#999"} stroke="#fff" strokeWidth={1}
                className="cursor-pointer" onMouseEnter={() => setHover(m.serie)} onMouseLeave={() => setHover(null)} onClick={() => setSel(m.serie)}>
                <title>{m.serie} · {m.instalacao} · {rotulo(m.status_comunicacao)} · {m.ultimo_sinal_dbm} dBm</title></circle>); })}
          </svg>
          <div className="mt-3 flex flex-wrap gap-4 text-xs">
            {Object.entries(COR).map(([k, c]) => <span key={k} className="flex items-center gap-1"><span className="h-3 w-3 rounded-full" style={{ background: c }} />{rotulo(k)}</span>)}
            {Object.entries(COR_OP).map(([k, c]) => <span key={k} className="flex items-center gap-1"><span className="h-0 w-0 border-x-[6px] border-b-[10px] border-x-transparent" style={{ borderBottomColor: c }} />{k}</span>)}
            <span className="ml-auto text-slate-500">{meds.length} medidores · {d.erbs.length} torres</span>
          </div>
        </Cartao>
      )}
      {sel && <DetalheMedidor serie={sel} fechar={() => setSel(null)} />}
    </div>
  );
}

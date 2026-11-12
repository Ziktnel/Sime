"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Cartao, Carregando, Erro, Titulo, Vazio, inputCls, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function MonitoramentoBot() {
  const [horas, setHoras] = useState(6);
  const { dados: d, erro, recarregar } = useCarregar<any>(() => api(`/api/comunicacao-campo/bot/monitoramento?horas=${horas}`), [horas]);
  useEffect(() => { const t = setInterval(recarregar, 60000); return () => clearInterval(t); }, [recarregar]);
  return (
    <div>
      <Titulo titulo="CPU e memória do bot" descricao="Telemetria simulada do servidor do bot de atendimento, atualizada a cada minuto. Alerta quando a CPU passa de 80% na última meia hora."
        acoes={<select className={cn(inputCls, "w-auto")} value={horas} onChange={(e) => setHoras(Number(e.target.value))} aria-label="Janela">{[1, 6, 12, 24].map((h) => <option key={h} value={h}>Últimas {h} h</option>)}</select>} />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {!d ? <Carregando /> : d.pontos.length === 0 ? <Vazio texto="O bot não enviou métricas (integração em modo vazio)." /> : (
        <Cartao titulo={d.alerta ? "⚠ CPU acima de 80% nos últimos 30 minutos" : "Operação normal"}>
          <div className="h-80"><ResponsiveContainer><LineChart data={d.pontos}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="instante" tickFormatter={(v) => v.slice(11, 16)} fontSize={11} minTickGap={30} /><YAxis domain={[0, 100]} fontSize={11} /><Tooltip /><Legend />
            <ReferenceLine y={80} stroke="#e0607e" strokeDasharray="4 4" /><Line dataKey="cpu_pct" name="CPU %" stroke="#14786d" dot={false} /><Line dataKey="memoria_pct" name="Memória %" stroke="#f2a541" dot={false} /></LineChart></ResponsiveContainer></div>
        </Cartao>
      )}
    </div>
  );
}

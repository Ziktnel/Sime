"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Botao, Cartao, Carregando, Erro, Titulo, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";
import { cn, tomStatus } from "@/lib/utils";

const mesStr = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

export default function Calendario() {
  const [ref, setRef] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const { dados: d, erro } = useCarregar<any>(() => api(`/api/analise-medidores/calendario?mes=${mesStr(ref)}`), [ref]);
  const inicio = new Date(ref.getFullYear(), ref.getMonth(), 1 - ref.getDay());
  const dias = Array.from({ length: 42 }, (_, k) => new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + k));
  const iso = (x: Date) => `${mesStr(x)}-${String(x.getDate()).padStart(2, "0")}`;
  return (
    <div>
      <Titulo titulo="Calendário de análises" descricao="Medidores agendados para análise na bancada." acoes={<>
        <Botao variante="secundario" onClick={() => setRef(new Date(ref.getFullYear(), ref.getMonth() - 1, 1))} aria-label="Mês anterior"><ChevronLeft className="h-4 w-4" /></Botao>
        <span className="self-center text-sm font-medium capitalize">{ref.toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}</span>
        <Botao variante="secundario" onClick={() => setRef(new Date(ref.getFullYear(), ref.getMonth() + 1, 1))} aria-label="Próximo mês"><ChevronRight className="h-4 w-4" /></Botao>
      </>} />
      {erro && <Erro texto={erro} />}
      {!d ? <Carregando /> : (
        <Cartao>
          <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg bg-slate-200 text-xs dark:bg-slate-700">
            {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map((x) => <div key={x} className="bg-slate-50 p-2 text-center font-semibold dark:bg-slate-800">{x}</div>)}
            {dias.map((dia) => {
              const evs = d.eventos.filter((e: any) => e.data === iso(dia));
              return (
                <div key={iso(dia)} className={cn("min-h-24 bg-white p-1 dark:bg-slate-900", dia.getMonth() !== ref.getMonth() && "opacity-40")}>
                  <div className="mb-1 font-medium">{dia.getDate()}</div>
                  {evs.slice(0, 3).map((e: any) => <div key={e.id} title={e.titulo} className={cn("mb-0.5 truncate rounded px-1", tomStatus(e.status))}>{e.titulo}</div>)}
                  {evs.length > 3 && <div className="text-slate-500">+{evs.length - 3}</div>}
                </div>
              );
            })}
          </div>
        </Cartao>
      )}
    </div>
  );
}

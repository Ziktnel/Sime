"use client";

import { Activity, AlertTriangle, CheckCircle2, Inbox, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { cn, rotulo, tomStatus } from "@/lib/utils";

export function Botao({ variante = "primario", className, carregando, children, ...p }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primario" | "secundario" | "perigo" | "fantasma"; carregando?: boolean }) {
  const v = {
    primario: "border border-marca-600 bg-marca-600 text-white hover:bg-marca-700 disabled:opacity-55",
    secundario: "border border-sime-borda bg-white text-slate-600 hover:bg-[#edf0f5] dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700",
    perigo: "border border-[#dc2626] bg-[#dc2626] text-white hover:bg-rose-700 disabled:opacity-55",
    fantasma: "text-slate-500 hover:bg-[#edf0f5] dark:text-slate-300 dark:hover:bg-slate-800",
  }[variante];
  return (
    <button {...p} disabled={p.disabled || carregando}
      className={cn("inline-flex min-h-[39px] items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed", v, className)}>
      {carregando && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Cartao({ titulo, acoes, children, className }: { titulo?: ReactNode; acoes?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-xl border border-sime-borda bg-white p-6 shadow-sime dark:border-slate-700 dark:bg-slate-900", className)}>
      {(titulo || acoes) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {titulo && <h2 className="text-base font-bold tracking-[-.2px] text-slate-900 dark:text-slate-100">{titulo}</h2>}
          {acoes}
        </header>
      )}
      {children}
    </section>
  );
}

export function Kpi({ titulo, valor, sub, tom = "marca" }: { titulo: string; valor: ReactNode; sub?: string; tom?: "marca" | "ambar" | "rose" }) {
  const icone = { marca: "bg-[#eff2fd] text-marca-600", ambar: "bg-[#fff8e9] text-[#ca8a04]", rose: "bg-[#fef0ef] text-[#dc2626]" }[tom];
  return (
    <div className="relative overflow-hidden rounded-xl border border-sime-borda bg-white p-[22px] shadow-sime dark:border-slate-700 dark:bg-slate-900">
      <span className={cn("absolute right-[18px] top-[18px] grid h-8 w-8 place-items-center rounded-[10px]", icone)}><Activity className="h-[17px] w-[17px]" strokeWidth={1.7} /></span>
      <p className="mb-4 mr-9 text-xs text-slate-500">{titulo}</p>
      <p className="mb-2 text-[32px] font-bold leading-none tracking-[-.7px] text-slate-900 dark:text-white">{valor}</p>
      {sub && <p className="text-[10px] text-slate-500">{sub}</p>}
    </div>
  );
}

export function Selo({ valor, className }: { valor: unknown; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-[9px] py-[5px] text-xs font-medium", tomStatus(valor), className)}><span className="h-[5px] w-[5px] shrink-0 rounded-full bg-current" />{rotulo(valor)}</span>;
}

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return <div className="flex items-center justify-center gap-3 py-14 text-sm text-slate-500"><span className="h-5 w-5 animate-spin rounded-full border-2 border-[#e6eafb] border-t-marca-600" />{texto}</div>;
}

export function Vazio({ texto = "Nenhum registro encontrado." }: { texto?: string }) {
  return <div className="flex flex-col items-center gap-2 py-10 text-sm text-slate-500"><Inbox className="h-6 w-6" />{texto}</div>;
}

export function Erro({ texto, tentar }: { texto: string; tentar?: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-[#f5cccc] bg-[#fef0ef] p-4 text-sm text-[#b91c1c] dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200">
      <AlertTriangle className="h-4 w-4" />{texto}
      {tentar && <button onClick={tentar} className="font-semibold text-marca-600 hover:underline">Tentar novamente</button>}
    </div>
  );
}

export function Modal({ aberto, titulo, onFechar, children, largura = "max-w-2xl" }:
  { aberto: boolean; titulo: string; onFechar: () => void; children: ReactNode; largura?: string }) {
  useEffect(() => {
    if (!aberto) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onFechar();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto, onFechar]);
  if (!aberto) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/40 p-4" onMouseDown={onFechar}>
      <div role="dialog" aria-modal aria-label={titulo} onMouseDown={(e) => e.stopPropagation()}
        className={cn("mt-10 w-full rounded-[14px] border border-sime-borda bg-white shadow-[0_16px_64px_rgba(15,23,42,.22)] dark:bg-slate-900", largura)}>
        <header className="flex items-center justify-between border-b border-sime-borda px-6 py-5 dark:border-slate-700">
          <h3 className="text-xl font-bold tracking-[-.3px] text-slate-900 dark:text-white">{titulo}</h3>
          <button onClick={onFechar} aria-label="Fechar" className="grid h-8 w-8 place-items-center rounded-[7px] text-slate-500 hover:bg-[#edf0f5] dark:hover:bg-slate-800"><X className="h-4 w-4" /></button>
        </header>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

export const inputCls = "min-h-[39px] w-full rounded-lg border border-slate-900/[.12] bg-white px-3 py-2 text-xs text-slate-900 outline-none placeholder:text-[#96a0b1] focus:border-marca-600 focus:ring-[3px] focus:ring-marca-600/[.12] dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:focus:ring-marca-900";

export function Campo({ rotulo: r, children, ajuda, erro }: { rotulo: string; children: ReactNode; ajuda?: string; erro?: string }) {
  return (
    <label className="block text-xs">
      <span className="mb-[7px] block text-[11px] font-medium text-slate-600 dark:text-slate-200">{r}</span>
      {children}
      {ajuda && !erro && <span className="mt-1 block text-xs text-slate-500">{ajuda}</span>}
      {erro && <span className="mt-1 block text-xs text-rose-600">{erro}</span>}
    </label>
  );
}

export function Titulo({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: ReactNode }) {
  return (
    <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
      <div>
        <p className="mb-[7px] text-[10px] font-bold tracking-[1.5px] text-marca-600">VISÃO OPERACIONAL</p>
        <h1 className="text-xl font-bold tracking-[-.3px] text-slate-900 dark:text-white">{titulo}</h1>
        {descricao && <p className="mt-[7px] max-w-3xl text-[13px] leading-relaxed text-slate-500">{descricao}</p>}
      </div>
      {acoes && <div className="flex flex-wrap gap-2.5">{acoes}</div>}
    </div>
  );
}

// ------------------------------------------------------------------ toasts
type Toast = { id: number; tipo: "ok" | "erro"; texto: string };
const ToastCtx = createContext<(tipo: Toast["tipo"], texto: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [itens, setItens] = useState<Toast[]>([]);
  const add = useCallback((tipo: Toast["tipo"], texto: string) => {
    const id = Date.now() + Math.random();
    setItens((l) => [...l, { id, tipo, texto }]);
    setTimeout(() => setItens((l) => l.filter((t) => t.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={add}>
      {children}
      <div className="fixed bottom-4 right-4 z-[60] flex max-w-sm flex-col gap-2" aria-live="polite">
        {itens.map((t) => (
          <div key={t.id} className={cn("flex items-start gap-2 rounded-lg px-4 py-3 text-xs font-medium text-white shadow-lg", t.tipo === "ok" ? "bg-[#15803d]" : "bg-[#dc2626]")}>
            {t.tipo === "ok" ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />}
            <span className="whitespace-pre-line">{t.texto}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ------------------------------------------------------------------- hook
export function useCarregar<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [dados, setDados] = useState<T | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const recarregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setDados(await fn());
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setCarregando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { recarregar(); }, [recarregar]);
  return { dados, erro, carregando, recarregar, setDados };
}

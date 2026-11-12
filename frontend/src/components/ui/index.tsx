"use client";

import { AlertTriangle, CheckCircle2, Inbox, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { cn, rotulo, tomStatus } from "@/lib/utils";

export function Botao({ variante = "primario", className, carregando, children, ...p }:
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "primario" | "secundario" | "perigo" | "fantasma"; carregando?: boolean }) {
  const v = {
    primario: "bg-marca-700 text-white hover:bg-marca-800 disabled:bg-marca-700/50",
    secundario: "border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700",
    perigo: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-600/50",
    fantasma: "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
  }[variante];
  return (
    <button {...p} disabled={p.disabled || carregando}
      className={cn("inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed", v, className)}>
      {carregando && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
}

export function Cartao({ titulo, acoes, children, className }: { titulo?: ReactNode; acoes?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900", className)}>
      {(titulo || acoes) && (
        <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {titulo && <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">{titulo}</h2>}
          {acoes}
        </header>
      )}
      {children}
    </section>
  );
}

export function Kpi({ titulo, valor, sub, tom = "marca" }: { titulo: string; valor: ReactNode; sub?: string; tom?: "marca" | "ambar" | "rose" }) {
  const barra = { marca: "bg-marca-500", ambar: "bg-ambar-400", rose: "bg-rose-500" }[tom];
  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      <span className={cn("absolute inset-y-0 left-0 w-1", barra)} />
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{titulo}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-white">{valor}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

export function Selo({ valor, className }: { valor: unknown; className?: string }) {
  return <span className={cn("inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium", tomStatus(valor), className)}>{rotulo(valor)}</span>;
}

export function Carregando({ texto = "Carregando..." }: { texto?: string }) {
  return <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />{texto}</div>;
}

export function Vazio({ texto = "Nenhum registro encontrado." }: { texto?: string }) {
  return <div className="flex flex-col items-center gap-2 py-10 text-sm text-slate-500"><Inbox className="h-6 w-6" />{texto}</div>;
}

export function Erro({ texto, tentar }: { texto: string; tentar?: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-200">
      <AlertTriangle className="h-4 w-4" />{texto}
      {tentar && <button onClick={tentar} className="underline">Tentar novamente</button>}
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
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-900/50 p-4" onMouseDown={onFechar}>
      <div role="dialog" aria-modal aria-label={titulo} onMouseDown={(e) => e.stopPropagation()}
        className={cn("mt-10 w-full rounded-xl bg-white shadow-xl dark:bg-slate-900", largura)}>
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-700">
          <h3 className="font-semibold text-slate-900 dark:text-white">{titulo}</h3>
          <button onClick={onFechar} aria-label="Fechar" className="rounded p-1 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="h-4 w-4" /></button>
        </header>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export const inputCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-marca-500 focus:ring-2 focus:ring-marca-200 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:focus:ring-marca-900";

export function Campo({ rotulo: r, children, ajuda, erro }: { rotulo: string; children: ReactNode; ajuda?: string; erro?: string }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700 dark:text-slate-200">{r}</span>
      {children}
      {ajuda && !erro && <span className="mt-1 block text-xs text-slate-500">{ajuda}</span>}
      {erro && <span className="mt-1 block text-xs text-rose-600">{erro}</span>}
    </label>
  );
}

export function Titulo({ titulo, descricao, acoes }: { titulo: string; descricao?: string; acoes?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-white">{titulo}</h1>
        {descricao && <p className="mt-1 max-w-3xl text-sm text-slate-500">{descricao}</p>}
      </div>
      {acoes && <div className="flex flex-wrap gap-2">{acoes}</div>}
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
          <div key={t.id} className={cn("flex items-start gap-2 rounded-lg px-4 py-3 text-sm text-white shadow-lg", t.tipo === "ok" ? "bg-marca-700" : "bg-rose-600")}>
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

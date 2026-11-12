"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bell, ChevronDown, Home, LogOut, Menu, Moon, Search, Sun, UserCircle2, X } from "lucide-react";
import { Logo } from "./Logo";
import { api } from "@/lib/api";
import { getSessao, pode, setSessao, type Sessao } from "@/lib/auth";
import { NAV, type ItemNav } from "@/lib/nav";
import { cn, fmtDataHora } from "@/lib/utils";

type Notif = { id: number; titulo: string; texto: string; link: string | null; lida: boolean; em: string };

export function Shell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [sessao, setS] = useState<Sessao | null>(null);
  const [menuMobile, setMenuMobile] = useState(false);
  const [busca, setBusca] = useState(false);

  useEffect(() => {
    const s = getSessao();
    if (!s) router.replace("/login");
    else setS(s);
  }, [router]);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setBusca(true); }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  useEffect(() => setMenuMobile(false), [pathname]);

  const secoes = useMemo(() => NAV.map((s) => ({ ...s, itens: s.itens.filter((i) => pode(i.permission, sessao)) })).filter((s) => s.itens.length), [sessao]);

  if (!sessao) return null;

  const menu = (
    <nav aria-label="Navegação principal" className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between px-4"><Logo /></div>
      <button onClick={() => setBusca(true)} className="mx-3 mb-3 flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-left text-sm text-slate-500 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
        <Search className="h-4 w-4" /> Buscar tela <kbd className="ml-auto rounded bg-slate-100 px-1.5 text-[10px] dark:bg-slate-800">Ctrl K</kbd>
      </button>
      <div className="flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        {sessao.user.perfil !== "consulta_360" && <ItemMenu item={{ label: "Início", href: "/home", icon: Home }} ativo={pathname === "/home"} />}
        {secoes.map((s) => <Secao key={s.id} label={s.label} Icone={s.icon} itens={s.itens} pathname={pathname} />)}
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:block">{menu}</aside>
      {menuMobile && (
        <div className="fixed inset-0 z-40 bg-slate-900/50 lg:hidden" onClick={() => setMenuMobile(false)}>
          <aside className="h-full w-72 bg-white dark:bg-slate-900" onClick={(e) => e.stopPropagation()}>{menu}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Cabecalho sessao={sessao} abrirMenu={() => setMenuMobile(true)} sair={() => { setSessao(null); router.replace("/login"); }} />
        <main className="mx-auto w-full max-w-[1500px] flex-1 p-4 md:p-6">{children}</main>
      </div>
      {busca && <Paleta itens={secoes.flatMap((s) => s.itens.map((i) => ({ ...i, grupo: s.label })))} fechar={() => setBusca(false)} />}
    </div>
  );
}

function ItemMenu({ item, ativo }: { item: ItemNav; ativo: boolean }) {
  const I = item.icon;
  return (
    <Link href={item.href} aria-current={ativo ? "page" : undefined}
      className={cn("flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm", ativo ? "bg-marca-100 font-medium text-marca-800 dark:bg-marca-900/60 dark:text-marca-100" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800")}>
      <I className="h-4 w-4 shrink-0" /><span className="truncate">{item.label}</span>
    </Link>
  );
}

function Secao({ label, Icone, itens, pathname }: { label: string; Icone: ItemNav["icon"]; itens: ItemNav[]; pathname: string }) {
  const ativo = itens.some((i) => pathname === i.href);
  const [aberta, setAberta] = useState(ativo);
  useEffect(() => { if (ativo) setAberta(true); }, [ativo]);
  return (
    <div>
      <button onClick={() => setAberta(!aberta)} aria-expanded={aberta}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800">
        <Icone className="h-4 w-4" /><span className="flex-1 text-left">{label}</span>
        <ChevronDown className={cn("h-3 w-3 transition", aberta && "rotate-180")} />
      </button>
      {aberta && <div className="ml-2 space-y-0.5 border-l border-slate-200 pl-2 dark:border-slate-700">{itens.map((i) => <ItemMenu key={i.href} item={i} ativo={pathname === i.href} />)}</div>}
    </div>
  );
}

function Cabecalho({ sessao, abrirMenu, sair }: { sessao: Sessao; abrirMenu: () => void; sair: () => void }) {
  const [notifs, setNotifs] = useState<{ nao_lidas: number; itens: Notif[] }>({ nao_lidas: 0, itens: [] });
  const [aberto, setAberto] = useState<"sino" | "usuario" | null>(null);
  const [escuro, setEscuro] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const carregar = useCallback(() => api("/api/notificacoes").then(setNotifs).catch(() => {}), []);
  useEffect(() => {
    carregar();
    setEscuro(document.documentElement.classList.contains("dark"));
    const t = setInterval(carregar, 30000);
    return () => clearInterval(t);
  }, [carregar]);
  useEffect(() => {
    const f = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setAberto(null); };
    document.addEventListener("mousedown", f);
    return () => document.removeEventListener("mousedown", f);
  }, []);

  function alternarTema() {
    const novo = !escuro;
    setEscuro(novo);
    document.documentElement.classList.toggle("dark", novo);
    try { localStorage.setItem("ohmnia.tema", novo ? "dark" : "light"); } catch { /* sem storage */ }
  }

  async function abrirNotif(n: Notif) {
    await api(`/api/notificacoes/${n.id}/lida`, { method: "PUT" }).catch(() => {});
    setAberto(null);
    carregar();
    if (n.link) router.push(n.link);
  }

  return (
    <header ref={ref} className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
      <button className="rounded p-2 hover:bg-slate-100 dark:hover:bg-slate-800 lg:hidden" onClick={abrirMenu} aria-label="Abrir menu"><Menu className="h-5 w-5" /></button>
      <div className="lg:hidden"><Logo compacto /></div>
      <div className="ml-auto flex items-center gap-1">
        <button onClick={alternarTema} className="rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Alternar tema">
          {escuro ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
        <div className="relative">
          <button onClick={() => setAberto(aberto === "sino" ? null : "sino")} className="relative rounded-lg p-2 hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Notificações">
            <Bell className="h-5 w-5" />
            {notifs.nao_lidas > 0 && <span className="absolute right-1 top-1 min-w-4 rounded-full bg-ambar-500 px-1 text-[10px] font-bold text-white">{notifs.nao_lidas}</span>}
          </button>
          {aberto === "sino" && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 text-sm font-semibold dark:border-slate-700">
                Notificações
                <button className="text-xs font-normal text-marca-700 dark:text-marca-400" onClick={() => api("/api/notificacoes/lidas", { method: "PUT" }).then(carregar)}>Marcar todas como lidas</button>
              </div>
              <ul className="max-h-96 overflow-y-auto">
                {notifs.itens.length === 0 && <li className="p-4 text-sm text-slate-500">Sem notificações.</li>}
                {notifs.itens.map((n) => (
                  <li key={n.id}>
                    <button onClick={() => abrirNotif(n)} className={cn("block w-full px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800", !n.lida && "bg-marca-50/70 dark:bg-marca-900/30")}>
                      <span className="block font-medium">{n.titulo}</span>
                      <span className="block text-xs text-slate-500">{n.texto}</span>
                      <span className="block text-[10px] text-slate-400">{fmtDataHora(n.em)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="relative">
          <button onClick={() => setAberto(aberto === "usuario" ? null : "usuario")} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">
            <UserCircle2 className="h-6 w-6 text-marca-700 dark:text-marca-400" />
            <span className="hidden text-left leading-tight sm:block"><span className="block font-medium">{sessao.user.nome}</span><span className="block text-xs text-slate-500">{sessao.user.perfil_nome}</span></span>
          </button>
          {aberto === "usuario" && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <Link href="/conta" onClick={() => setAberto(null)} className="block rounded-lg px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800">Minha conta</Link>
              <button onClick={sair} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950"><LogOut className="h-4 w-4" />Sair</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function Paleta({ itens, fechar }: { itens: (ItemNav & { grupo: string })[]; fechar: () => void }) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const router = useRouter();
  const lista = itens.filter((i) => `${i.label} ${i.grupo}`.toLocaleLowerCase("pt-BR").includes(q.toLocaleLowerCase("pt-BR"))).slice(0, 12);
  const ir = (i: ItemNav) => { fechar(); router.push(i.href); };
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/50 p-4" onMouseDown={fechar}>
      <div className="mt-20 w-full max-w-lg rounded-xl bg-white shadow-xl dark:bg-slate-900" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-slate-200 px-3 dark:border-slate-700">
          <Search className="h-4 w-4 text-slate-400" />
          <input autoFocus value={q} onChange={(e) => { setQ(e.target.value); setSel(0); }} placeholder="Ir para..." className="h-12 flex-1 bg-transparent text-sm outline-none"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") setSel((s) => Math.min(s + 1, lista.length - 1));
              if (e.key === "ArrowUp") setSel((s) => Math.max(s - 1, 0));
              if (e.key === "Enter" && lista[sel]) ir(lista[sel]);
              if (e.key === "Escape") fechar();
            }} />
          <button onClick={fechar} aria-label="Fechar"><X className="h-4 w-4" /></button>
        </div>
        <ul className="max-h-80 overflow-y-auto p-1">
          {lista.length === 0 && <li className="p-3 text-sm text-slate-500">Nada encontrado.</li>}
          {lista.map((i, k) => {
            const I = i.icon;
            return (
              <li key={i.href}>
                <button onClick={() => ir(i)} onMouseEnter={() => setSel(k)} className={cn("flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm", k === sel && "bg-marca-50 dark:bg-slate-800")}>
                  <I className="h-4 w-4 text-marca-700" />{i.label}<span className="ml-auto text-xs text-slate-400">{i.grupo}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

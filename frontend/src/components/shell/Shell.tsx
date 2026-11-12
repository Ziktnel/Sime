"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bell, ChevronDown, Home, LogOut, Menu, Moon, Search, Sun, X } from "lucide-react";
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
    <nav aria-label="Navegação principal" className="flex h-full flex-col px-[18px] pt-[30px]">
      <Link href={sessao.user.perfil === "consulta_360" ? "/visao-360" : "/home"} className="mb-8 flex items-center px-3"><Logo /></Link>
      <button onClick={() => setBusca(true)} className="mb-6 flex min-h-[39px] items-center gap-2 rounded-lg border border-slate-900/[.12] bg-white px-3 py-2 text-left text-xs text-[#96a0b1] hover:border-marca-600 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
        <Search className="h-4 w-4 text-slate-400" /> Buscar tela <kbd className="ml-auto rounded-md border border-sime-borda bg-[#fafbfc] px-1.5 py-0.5 text-[10px] text-slate-500 dark:bg-slate-800">Ctrl K</kbd>
      </button>
      <span className="mb-3.5 px-3.5 text-[10px] font-semibold tracking-[1.3px] text-[#8993a6]">ESPAÇO DE TRABALHO</span>
      <div className="-mx-1 flex-1 space-y-1.5 overflow-y-auto px-1 pb-4">
        {sessao.user.perfil !== "consulta_360" && <ItemMenu item={{ label: "Início", href: "/home", icon: Home }} ativo={pathname === "/home"} />}
        {secoes.map((s) => <Secao key={s.id} label={s.label} Icone={s.icon} itens={s.itens} pathname={pathname} />)}
      </div>
      <div className="mt-auto">
        <div className="mb-5 rounded-[10px] border border-sime-borda bg-[#f7f8fc] [@media(max-height:820px)]:hidden px-[13px] py-[15px] text-xs font-semibold dark:border-slate-700 dark:bg-slate-800">
          <span className="mr-2 inline-block h-[5px] w-[5px] rounded-full bg-marca-600 align-middle" />Projeto acadêmico
          <small className="mt-2 block text-[12px] font-normal leading-normal text-slate-500">Informações simuladas para demonstração</small>
        </div>
        <div className="flex items-center gap-[11px] border-t border-sime-borda py-5 dark:border-slate-700">
          <Avatar nome={sessao.user.nome} />
          <span className="min-w-0"><strong className="block truncate text-xs">{sessao.user.nome}</strong><small className="mt-1 block truncate text-[10px] text-slate-500">{sessao.user.perfil_nome}</small></span>
        </div>
      </div>
    </nav>
  );
  const atual = secoes.flatMap((s) => s.itens).find((i) => i.href === pathname)?.label ?? (pathname === "/home" ? "Início" : pathname === "/conta" ? "Minha conta" : "Painel");

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 hidden h-screen w-[260px] shrink-0 border-r border-sime-borda bg-white dark:border-slate-800 dark:bg-slate-900 lg:block">{menu}</aside>
      {menuMobile && (
        <div className="fixed inset-0 z-40 bg-slate-900/35 lg:hidden" onClick={() => setMenuMobile(false)}>
          <aside className="h-full w-[260px] bg-white dark:bg-slate-900" onClick={(e) => e.stopPropagation()}>{menu}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Cabecalho sessao={sessao} atual={atual} abrirMenu={() => setMenuMobile(true)} sair={() => { setSessao(null); router.replace("/login"); }} />
        <main id="conteudo" className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 md:p-6">{children}</main>
      </div>
      {busca && <Paleta itens={secoes.flatMap((s) => s.itens.map((i) => ({ ...i, grupo: s.label })))} fechar={() => setBusca(false)} />}
    </div>
  );
}

function ItemMenu({ item, ativo }: { item: ItemNav; ativo: boolean }) {
  const I = item.icon;
  return (
    <Link href={item.href} aria-current={ativo ? "page" : undefined}
      className={cn("flex items-center gap-3 rounded-lg px-3.5 py-2.5 text-[13px] font-medium", ativo ? "bg-marca-600/[.08] text-marca-600 dark:bg-marca-600/20 dark:text-marca-300" : "text-slate-500 hover:bg-[#f4f6f9] dark:text-slate-300 dark:hover:bg-slate-800")}>
      <I className="h-[18px] w-[18px] shrink-0" strokeWidth={1.7} /><span className="truncate">{item.label}</span>
      {ativo && <span className="ml-auto h-1.5 w-1.5 shrink-0 rounded-full bg-marca-600" />}
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
        className={cn("flex w-full items-center gap-3 rounded-lg px-3.5 py-2.5 text-[13px] font-medium hover:bg-[#f4f6f9] dark:hover:bg-slate-800", ativo ? "text-slate-900 dark:text-white" : "text-slate-500 dark:text-slate-300")}>
        <Icone className="h-[18px] w-[18px]" strokeWidth={1.7} /><span className="flex-1 text-left">{label}</span>
        <ChevronDown className={cn("h-3 w-3 transition", aberta && "rotate-180")} />
      </button>
      {aberta && <div className="ml-[23px] mt-1 space-y-1 border-l border-sime-borda pl-2 dark:border-slate-700">{itens.map((i) => <ItemMenu key={i.href} item={i} ativo={pathname === i.href} />)}</div>}
    </div>
  );
}

function Cabecalho({ sessao, atual, abrirMenu, sair }: { sessao: Sessao; atual: string; abrirMenu: () => void; sair: () => void }) {
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
    <header ref={ref} className="sticky top-0 z-30 flex h-14 items-center gap-4 border-b border-sime-borda bg-[#f4f6f9]/95 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90 md:px-8">
      <button className="grid h-[33px] w-[33px] place-items-center rounded-[7px] text-slate-500 hover:bg-[#edf0f5] dark:hover:bg-slate-800 lg:hidden" onClick={abrirMenu} aria-label="Abrir menu"><Menu className="h-5 w-5" /></button>
      <div className="flex min-w-0 items-center gap-2.5 text-xs text-slate-500 md:gap-4">
        <span>SIME</span><span className="text-[#b6bdcb]">/</span><strong className="truncate font-medium text-slate-900 dark:text-white">{atual}</strong>
      </div>
      <div className="ml-auto flex items-center gap-1">
        <button onClick={alternarTema} className="grid h-[33px] w-[33px] place-items-center rounded-[7px] text-slate-500 hover:bg-[#edf0f5] dark:hover:bg-slate-800" aria-label="Alternar tema">
          {escuro ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
        <div className="relative">
          <button onClick={() => setAberto(aberto === "sino" ? null : "sino")} className="relative grid h-[33px] w-[33px] place-items-center rounded-[7px] text-slate-500 hover:bg-[#edf0f5] dark:hover:bg-slate-800" aria-label="Notificações">
            <Bell className="h-5 w-5" />
            {notifs.nao_lidas > 0 && <span className="absolute right-1 top-1 min-w-4 rounded-full bg-[#dc2626] px-1 text-[10px] font-bold text-white">{notifs.nao_lidas}</span>}
          </button>
          {aberto === "sino" && (
            <div className="absolute right-0 mt-2 w-80 rounded-xl border border-sime-borda bg-white shadow-[0_16px_64px_rgba(15,23,42,.12)] dark:border-slate-700 dark:bg-slate-900">
              <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2 text-sm font-semibold dark:border-slate-700">
                Notificações
                <button className="text-xs font-medium text-marca-600 dark:text-marca-400" onClick={() => api("/api/notificacoes/lidas", { method: "PUT" }).then(carregar)}>Marcar todas como lidas</button>
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
          <button onClick={() => setAberto(aberto === "usuario" ? null : "usuario")} className="flex items-center gap-2.5 rounded-lg px-2 py-1 text-[11px] text-slate-500 hover:bg-[#edf0f5] dark:hover:bg-slate-800">
            <span className="hidden sm:block">Painel operacional</span>
            <Avatar nome={sessao.user.nome} pequeno />
          </button>
          {aberto === "usuario" && (
            <div className="absolute right-0 mt-2 w-56 rounded-xl border border-sime-borda bg-white p-1 shadow-[0_16px_64px_rgba(15,23,42,.12)] dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-sime-borda px-3 py-2 dark:border-slate-700"><strong className="block text-xs text-slate-900 dark:text-white">{sessao.user.nome}</strong><small className="text-[10px] text-slate-500">{sessao.user.perfil_nome}</small></div>
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

function Avatar({ nome, pequeno = false }: { nome: string; pequeno?: boolean }) {
  const iniciais = nome.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
  return <span className={cn("grid shrink-0 place-items-center rounded-full bg-[#edf0fb] text-[11px] font-bold text-marca-600 dark:bg-marca-900/60 dark:text-marca-200", pequeno ? "h-[30px] w-[30px]" : "h-[37px] w-[37px]")}>{iniciais}</span>;
}

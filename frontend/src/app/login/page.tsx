"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Botao, Campo, inputCls } from "@/components/ui";
import { Logo } from "@/components/shell/Logo";
import { api } from "@/lib/api";
import { setSessao, type Sessao } from "@/lib/auth";

const DEMO = [
  ["OH0001", "Administrador"], ["OH0002", "Gestor operacional"], ["OH0003", "Analista de laboratório"],
  ["OH0004", "Operador de campo"], ["OH0005", "Consulta Visão 360"],
];

function Formulario() {
  const router = useRouter();
  const params = useSearchParams();
  const [matricula, setMatricula] = useState("OH0001");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(params.get("expirada") ? "Sua sessão expirou. Entre novamente." : null);
  const [carregando, setCarregando] = useState(false);

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const s = await api<Sessao>("/api/auth/login", { method: "POST", body: { matricula, senha } });
      setSessao(s);
      router.replace(s.user.perfil === "consulta_360" ? "/visao-360" : "/home");
    } catch (err) {
      setErro((err as Error).message);
    } finally {
      setCarregando(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-gradient-to-br from-marca-800 via-marca-700 to-marca-600 p-10 text-white lg:flex">
        <Logo />
        <div>
          <h1 className="text-3xl font-semibold leading-tight">Medição, comunicação e laboratório<br />em um só lugar.</h1>
          <p className="mt-3 max-w-md text-marca-100">Projeto acadêmico com base de dados 100% sintética e integrações simuladas.</p>
        </div>
        <p className="text-xs text-marca-200">Nenhum dado real é utilizado nesta aplicação.</p>
      </section>
      <section className="flex items-center justify-center p-6">
        <form onSubmit={entrar} className="w-full max-w-sm space-y-4">
          <div className="lg:hidden"><Logo /></div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Entrar</h2>
          <Campo rotulo="Matrícula">
            <input className={inputCls} value={matricula} onChange={(e) => setMatricula(e.target.value.toUpperCase())} autoComplete="username" required />
          </Campo>
          <Campo rotulo="Senha">
            <input className={inputCls} type="password" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" required />
          </Campo>
          {erro && <p role="alert" className="rounded-lg bg-rose-50 p-2 text-sm text-rose-700 dark:bg-rose-950 dark:text-rose-200">{erro}</p>}
          <Botao type="submit" carregando={carregando} className="w-full">Entrar</Botao>
          <details className="rounded-lg border border-slate-200 p-3 text-xs text-slate-600 dark:border-slate-700 dark:text-slate-300">
            <summary className="cursor-pointer font-medium">Usuários de demonstração</summary>
            <p className="mt-2">Senha de todos: <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">Ohmnia@2026</code></p>
            <ul className="mt-2 space-y-1">
              {DEMO.map(([m, p]) => (
                <li key={m}><button type="button" className="text-marca-700 underline dark:text-marca-400" onClick={() => setMatricula(m)}>{m}</button> — {p}</li>
              ))}
            </ul>
          </details>
        </form>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense><Formulario /></Suspense>;
}

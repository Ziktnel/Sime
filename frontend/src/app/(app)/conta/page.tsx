"use client";

import { useEffect, useState } from "react";
import { Botao, Campo, Cartao, Titulo, inputCls, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { getSessao, type Sessao } from "@/lib/auth";

export default function Conta() {
  const toast = useToast();
  const [s, setS] = useState<Sessao | null>(null);
  const [f, setF] = useState({ senha_atual: "", nova_senha: "", confirmar: "" });
  useEffect(() => setS(getSessao()), []);
  async function trocar(e: React.FormEvent) {
    e.preventDefault();
    if (f.nova_senha !== f.confirmar) { toast("erro", "A confirmação não confere."); return; }
    try { await api("/api/auth/senha", { method: "PUT", body: { senha_atual: f.senha_atual, nova_senha: f.nova_senha } }); toast("ok", "Senha alterada."); setF({ senha_atual: "", nova_senha: "", confirmar: "" }); }
    catch (err) { toast("erro", (err as Error).message); }
  }
  if (!s) return null;
  return (
    <div className="max-w-2xl">
      <Titulo titulo="Minha conta" />
      <Cartao titulo="Dados">
        <dl className="grid grid-cols-3 gap-2 text-sm"><dt className="text-slate-500">Matrícula</dt><dd className="col-span-2">{s.user.matricula}</dd>
          <dt className="text-slate-500">Nome</dt><dd className="col-span-2">{s.user.nome}</dd><dt className="text-slate-500">Perfil</dt><dd className="col-span-2">{s.user.perfil_nome}</dd>
          <dt className="text-slate-500">Permissões</dt><dd className="col-span-2 font-mono text-xs">{s.user.permissoes.join(", ")}</dd></dl>
      </Cartao>
      <Cartao titulo="Trocar senha" className="mt-4">
        <form onSubmit={trocar} className="space-y-3">
          <Campo rotulo="Senha atual"><input type="password" className={inputCls} value={f.senha_atual} onChange={(e) => setF({ ...f, senha_atual: e.target.value })} required /></Campo>
          <Campo rotulo="Nova senha" ajuda="Mínimo 8 caracteres, com letras e números."><input type="password" className={inputCls} value={f.nova_senha} onChange={(e) => setF({ ...f, nova_senha: e.target.value })} required /></Campo>
          <Campo rotulo="Confirmar nova senha"><input type="password" className={inputCls} value={f.confirmar} onChange={(e) => setF({ ...f, confirmar: e.target.value })} required /></Campo>
          <Botao type="submit">Alterar senha</Botao>
        </form>
      </Cartao>
    </div>
  );
}

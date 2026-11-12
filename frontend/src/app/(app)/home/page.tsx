"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Cartao, Titulo } from "@/components/ui";
import { getSessao, pode, type Sessao } from "@/lib/auth";
import { NAV } from "@/lib/nav";

export default function Home() {
  const [s, setS] = useState<Sessao | null>(null);
  useEffect(() => setS(getSessao()), []);
  if (!s) return null;
  const secoes = NAV.map((x) => ({ ...x, itens: x.itens.filter((i) => pode(i.permission, s)) })).filter((x) => x.itens.length);
  return (
    <div>
      <Titulo titulo={`Olá, ${s.user.nome.split(" ")[0]}`}
        descricao={`Perfil ${s.user.perfil_nome}. Escolha um módulo abaixo ou use Ctrl+K para buscar uma tela.`} />
      <div className="mb-6 rounded-xl border border-ambar-300 bg-ambar-300/20 p-4 text-sm text-slate-700 dark:text-slate-200">
        <b>Ambiente acadêmico.</b> Todos os clientes, medidores, torres e históricos são sintéticos. As integrações externas
        (ERP, MDM, head-end, câmara de comercialização, bot e diretório) são simuladas e podem ser colocadas em modo de falha em
        Gerenciamento → Integrações simuladas.
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {secoes.map((sec) => {
          const I = sec.icon;
          return (
            <Cartao key={sec.id} titulo={<span className="flex items-center gap-2"><I className="h-4 w-4 text-marca-600" />{sec.label}</span>}>
              <ul className="space-y-1 text-sm">
                {sec.itens.map((i) => <li key={i.href}><Link className="text-marca-700 hover:underline dark:text-marca-400" href={i.href}>{i.label}</Link></li>)}
              </ul>
            </Cartao>
          );
        })}
      </div>
    </div>
  );
}

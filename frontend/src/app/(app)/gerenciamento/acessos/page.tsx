"use client";

import { Check, Minus } from "lucide-react";
import { Cartao, Carregando, Erro, Titulo, useCarregar } from "@/components/ui";
import { api } from "@/lib/api";

export default function Acessos() {
  const { dados: d, erro } = useCarregar<any>(() => api("/api/admin/acessos"));
  if (erro) return <Erro texto={erro} />;
  if (!d) return <Carregando />;
  const perfis = Object.entries(d.perfis) as [string, string][];
  return (
    <div>
      <Titulo titulo="Acessos por perfil" descricao="Matriz calculada pelo mesmo motor de permissões usado pela API (padrões com curinga, ex.: smc:* ou *:visualizar)." />
      <Cartao>
        <div className="overflow-x-auto"><table className="tabela">
          <thead><tr><th>Tela</th><th>Permissão</th>{perfis.map(([k, v]) => <th key={k} className="text-center">{v}</th>)}</tr></thead>
          <tbody>{d.telas.map((t: any) => (
            <tr key={t.permissao + t.tela}><td>{t.tela}</td><td><code className="text-xs">{t.permissao}</code></td>
              {perfis.map(([k]) => <td key={k} className="text-center">{t[k] ? <Check className="mx-auto h-4 w-4 text-marca-600" /> : <Minus className="mx-auto h-4 w-4 text-slate-300" />}</td>)}</tr>))}</tbody>
        </table></div>
      </Cartao>
    </div>
  );
}

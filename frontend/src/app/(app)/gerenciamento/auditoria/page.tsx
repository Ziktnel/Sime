"use client";

import { useState } from "react";
import { Cartao, Carregando, Erro, Titulo, inputCls, useCarregar } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { cn, fmtDataHora, rotulo } from "@/lib/utils";

export default function Auditoria() {
  const [entidade, setEntidade] = useState("");
  const [usuario, setUsuario] = useState("");
  const { dados, erro } = useCarregar<any[]>(() => api(`/api/admin/auditoria${qs({ entidade, usuario })}`), [entidade, usuario]);
  return (
    <div>
      <Titulo titulo="Trilha de auditoria" descricao="Toda criação, edição, exclusão, login, consulta à Visão 360 e execução de rotina fica registrada." />
      <div className="mb-3 flex gap-2">
        <input className={cn(inputCls, "max-w-xs")} placeholder="Entidade (ex.: analise, smc_recapacitacao)" value={entidade} onChange={(e) => setEntidade(e.target.value)} aria-label="Entidade" />
        <input className={cn(inputCls, "max-w-[10rem]")} placeholder="Matrícula" value={usuario} onChange={(e) => setUsuario(e.target.value)} aria-label="Usuário" />
      </div>
      {erro && <Erro texto={erro} />}
      {!dados ? <Carregando /> : (
        <Cartao>
          <div className="overflow-x-auto"><table className="tabela"><thead><tr><th>Quando</th><th>Usuário</th><th>Entidade</th><th>ID</th><th>Ação</th><th>Detalhe</th></tr></thead>
            <tbody>{dados.map((h) => (
              <tr key={h.id}><td>{fmtDataHora(h.em)}</td><td>{h.usuario}</td><td>{h.entidade}</td><td>{h.entidade_id || "—"}</td><td>{rotulo(h.acao)}</td>
                <td className="max-w-md truncate" title={h.texto || JSON.stringify(h.depois)}>{h.texto || (h.depois ? JSON.stringify(h.depois) : "—")}</td></tr>))}</tbody></table></div>
        </Cartao>
      )}
    </div>
  );
}

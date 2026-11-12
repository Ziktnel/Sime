"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Botao, Campo, Cartao, Carregando, Erro, Modal, Selo, Titulo, inputCls, useCarregar, useToast } from "@/components/ui";
import { api, qs } from "@/lib/api";
import { pode } from "@/lib/auth";
import { cn, fmtDataHora } from "@/lib/utils";

export default function Usuarios() {
  const toast = useToast();
  const [q, setQ] = useState("");
  const [edit, setEdit] = useState<any>(null);
  const { dados: d, erro, recarregar } = useCarregar<any>(() => api(`/api/admin/usuarios${qs({ q })}`), [q]);
  const { dados: vinc, recarregar: recVinc } = useCarregar<any>(() => api("/api/admin/auditoria-vinculos"));

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (edit.novo) await api("/api/admin/usuarios", { method: "POST", body: { matricula: edit.matricula, nome: edit.nome, email: edit.email, perfil: edit.perfil, area: edit.area, senha: edit.senha } });
      else await api(`/api/admin/usuarios/${edit.matricula}`, { method: "PUT", body: { nome: edit.nome, email: edit.email, perfil: edit.perfil, area: edit.area, ativo: edit.ativo, nova_senha: edit.senha || null } });
      toast("ok", "Usuário salvo."); setEdit(null); recarregar(); recVinc();
    } catch (err) { toast("erro", (err as Error).message); }
  }

  return (
    <div>
      <Titulo titulo="Usuários" descricao="Autenticação local com senha em hash bcrypt. Após 5 tentativas erradas a conta é bloqueada por 15 minutos."
        acoes={pode("gerenciamento:usuarios:criar") && <Botao onClick={() => setEdit({ novo: true, perfil: "operador_campo", ativo: true })}><Plus className="h-4 w-4" />Novo usuário</Botao>} />
      {vinc && vinc.desligados_com_acesso.length > 0 && (
        <div className="mb-4 rounded-lg border border-ambar-400 bg-ambar-300/20 p-3 text-sm">
          <b>Auditoria de vínculos:</b> {vinc.desligados_com_acesso.length} usuário(s) com vínculo encerrado no diretório simulado ainda têm acesso
          ({vinc.desligados_com_acesso.map((u: any) => u.matricula).join(", ")}). A rotina &quot;Auditoria de vínculos&quot; revoga esses acessos.
        </div>
      )}
      <input className={cn(inputCls, "mb-3 max-w-xs")} placeholder="Matrícula, nome ou e-mail" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Pesquisar" />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {!d ? <Carregando /> : (
        <Cartao>
          <div className="overflow-x-auto"><table className="tabela"><thead><tr><th>Matrícula</th><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Área</th><th>Situação</th><th>Último login</th><th /></tr></thead>
            <tbody>{d.itens.map((u: any) => (
              <tr key={u.matricula}><td className="font-medium">{u.matricula}</td><td>{u.nome}</td><td>{u.email}</td><td>{d.perfis[u.perfil]}</td><td>{u.area}</td>
                <td><Selo valor={u.ativo ? "ATIVO" : "INATIVO"} />{!u.vinculo_ativo && <Selo valor="vínculo encerrado" className="ml-1" />}{u.bloqueado && <Selo valor="BLOQUEADO" className="ml-1" />}</td>
                <td>{fmtDataHora(u.ultimo_login)}</td>
                <td>{pode("gerenciamento:usuarios:editar") && <Botao variante="fantasma" onClick={() => setEdit({ ...u, senha: "" })}>Editar</Botao>}</td></tr>))}</tbody></table></div>
        </Cartao>
      )}
      <Modal aberto={!!edit} titulo={edit?.novo ? "Novo usuário" : `Editar ${edit?.matricula}`} onFechar={() => setEdit(null)}>
        {edit && d && (
          <form onSubmit={salvar} className="grid gap-3 sm:grid-cols-2">
            <Campo rotulo="Matrícula" ajuda="2 letras + 4 dígitos"><input className={inputCls} value={edit.matricula || ""} disabled={!edit.novo} onChange={(e) => setEdit({ ...edit, matricula: e.target.value.toUpperCase() })} required /></Campo>
            <Campo rotulo="Nome"><input className={inputCls} value={edit.nome || ""} onChange={(e) => setEdit({ ...edit, nome: e.target.value })} required /></Campo>
            <Campo rotulo="E-mail"><input type="email" className={inputCls} value={edit.email || ""} onChange={(e) => setEdit({ ...edit, email: e.target.value })} required /></Campo>
            <Campo rotulo="Perfil"><select className={inputCls} value={edit.perfil} onChange={(e) => setEdit({ ...edit, perfil: e.target.value })}>{Object.entries(d.perfis).map(([k, v]) => <option key={k} value={k}>{String(v)}</option>)}</select></Campo>
            <Campo rotulo="Área"><input className={inputCls} value={edit.area || ""} onChange={(e) => setEdit({ ...edit, area: e.target.value })} /></Campo>
            <Campo rotulo={edit.novo ? "Senha" : "Nova senha (opcional)"} ajuda="Mínimo 8 caracteres com letras e números"><input type="password" className={inputCls} value={edit.senha} onChange={(e) => setEdit({ ...edit, senha: e.target.value })} required={edit.novo} /></Campo>
            {!edit.novo && <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={edit.ativo} onChange={(e) => setEdit({ ...edit, ativo: e.target.checked })} />Usuário ativo</label>}
            <div className="flex justify-end gap-2 sm:col-span-2"><Botao type="button" variante="secundario" onClick={() => setEdit(null)}>Cancelar</Botao><Botao type="submit">Salvar</Botao></div>
          </form>
        )}
      </Modal>
    </div>
  );
}

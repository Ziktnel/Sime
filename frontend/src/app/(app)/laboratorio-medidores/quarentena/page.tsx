"use client";

import { useState } from "react";
import { Botao, Carregando, Erro, Modal, Selo, Titulo, Vazio, inputCls, useCarregar, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { pode } from "@/lib/auth";

export default function Quarentena() {
  const toast = useToast();
  const [alvo, setAlvo] = useState<any>(null);
  const [nota, setNota] = useState("");
  const { dados, erro, recarregar } = useCarregar<any[]>(() => api("/api/analise-medidores/quarentena"));
  async function vincular() {
    try { await api(`/api/analise-medidores/${alvo.id}/quarentena/vincular`, { method: "POST", body: { nota_irregularidade: nota } }); toast("ok", "Medidor vinculado e liberado para descarte."); setAlvo(null); setNota(""); recarregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }
  return (
    <div>
      <Titulo titulo="Quarentena" descricao="Medidores com laudo IRREGULAR ficam retidos até serem vinculados a uma nota de irregularidade; depois seguem para descarte." />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {!dados ? <Carregando /> : dados.length === 0 ? <Vazio /> : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <table className="tabela"><thead><tr><th>Laudo</th><th>Medidor</th><th>Irregularidade</th><th>Instalação</th><th>Vínculo</th><th /></tr></thead>
            <tbody>{dados.map((a) => (
              <tr key={a.id}><td className="font-medium">{a.numero_laudo}</td><td>{a.medidor}</td><td>{a.irregularidade}</td><td>{a.instalacao}</td><td><Selo valor={a.quarentena} /></td>
                <td>{a.quarentena === "PENDENTE" && pode("analise-medidores:quarentena:editar") && <Botao variante="fantasma" onClick={() => setAlvo(a)}>Vincular nota</Botao>}</td></tr>))}</tbody></table>
        </div>
      )}
      <Modal aberto={!!alvo} titulo={`Vincular ${alvo?.medidor}`} onFechar={() => setAlvo(null)}>
        <input className={inputCls} placeholder="Nota de irregularidade (8 a 10 dígitos)" value={nota} onChange={(e) => setNota(e.target.value)} />
        <div className="mt-3 flex justify-end gap-2"><Botao variante="secundario" onClick={() => setAlvo(null)}>Cancelar</Botao><Botao onClick={vincular} disabled={!/^\d{8,10}$/.test(nota)}>Vincular</Botao></div>
      </Modal>
    </div>
  );
}

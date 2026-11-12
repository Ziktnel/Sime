"use client";

import { useState } from "react";
import { Botao, Carregando, Erro, Modal, Selo, Titulo, Vazio, inputCls, useCarregar, useToast } from "@/components/ui";
import { api } from "@/lib/api";
import { fmtData } from "@/lib/utils";

export default function Aprovacoes() {
  const toast = useToast();
  const [sel, setSel] = useState<number[]>([]);
  const [reabrir, setReabrir] = useState<any>(null);
  const [motivo, setMotivo] = useState("");
  const { dados, erro, recarregar } = useCarregar<any[]>(() => api("/api/analise-medidores/aprovacoes/pendentes"));

  async function aprovar() {
    try {
      const r = await api("/api/analise-medidores/aprovacoes/aprovar-lote", { method: "POST", body: { ids: sel } });
      toast(r.falhas.length ? "erro" : "ok", `${r.aprovadas} aprovada(s): ${r.laudos.join(", ") || "—"}` + (r.falhas.length ? `\nRecusadas: ${r.falhas.map((f: any) => f.erro).join("; ")}` : ""));
      setSel([]); recarregar();
    } catch (e) { toast("erro", (e as Error).message); }
  }
  async function confirmarReabertura() {
    try { await api(`/api/analise-medidores/${reabrir.id}/reabrir`, { method: "POST", body: { motivo } }); toast("ok", "Análise devolvida ao examinador."); setReabrir(null); setMotivo(""); recarregar(); }
    catch (e) { toast("erro", (e as Error).message); }
  }

  return (
    <div>
      <Titulo titulo="Aprovações de análise" descricao="Aprovação em lote gera o número do laudo. Quem examinou não pode aprovar a própria análise (segregação de função)."
        acoes={<Botao disabled={!sel.length} onClick={aprovar}>Aprovar {sel.length || ""} selecionada(s)</Botao>} />
      {erro && <Erro texto={erro} tentar={recarregar} />}
      {!dados ? <Carregando /> : dados.length === 0 ? <Vazio texto="Nenhuma análise aguardando aprovação." /> : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
          <table className="tabela">
            <thead><tr><th><input type="checkbox" aria-label="Selecionar todas" checked={sel.length === dados.length} onChange={(e) => setSel(e.target.checked ? dados.map((a) => a.id) : [])} /></th>
              <th>Protocolo</th><th>Medidor</th><th>Examinador</th><th>Data</th><th>Resultado</th><th>Erro %</th><th>Lacre</th><th>Irregularidade</th><th /></tr></thead>
            <tbody>{dados.map((a) => (
              <tr key={a.id}>
                <td><input type="checkbox" aria-label={`Selecionar ${a.protocolo}`} checked={sel.includes(a.id)} onChange={(e) => setSel((s) => e.target.checked ? [...s, a.id] : s.filter((x) => x !== a.id))} /></td>
                <td className="font-medium">{a.protocolo}</td><td>{a.medidor}</td><td>{a.examinador}</td><td>{fmtData(a.dt_analise)}</td>
                <td><Selo valor={a.resultado} /></td><td>{a.erro_percentual}</td><td>{a.lacre_numero} {a.lacre_integro ? "(íntegro)" : "(violado)"}</td><td>{a.irregularidade ?? "—"}</td>
                <td><Botao variante="fantasma" onClick={() => setReabrir(a)}>Reabrir</Botao></td>
              </tr>))}</tbody>
          </table>
        </div>
      )}
      <Modal aberto={!!reabrir} titulo={`Reabrir ${reabrir?.protocolo}`} onFechar={() => setReabrir(null)}>
        <textarea className={inputCls} rows={3} placeholder="Motivo (mínimo 5 caracteres)" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <div className="mt-3 flex justify-end gap-2"><Botao variante="secundario" onClick={() => setReabrir(null)}>Cancelar</Botao><Botao variante="perigo" onClick={confirmarReabertura} disabled={motivo.trim().length < 5}>Reabrir</Botao></div>
      </Modal>
    </div>
  );
}

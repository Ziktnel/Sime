import clsx, { type ClassValue } from "clsx";

export const cn = (...v: ClassValue[]) => clsx(v);

export const fmtNum = (v: number | null | undefined, casas = 0) =>
  v === null || v === undefined ? "—" : v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const fmtData = (v: string | null | undefined) => {
  if (!v) return "—";
  const [d] = v.split("T");
  const [a, m, dia] = d.split("-");
  return dia ? `${dia}/${m}/${a}` : v;
};

export const fmtDataHora = (v: string | null | undefined) => (v ? new Date(v).toLocaleString("pt-BR") : "—");

/** Rótulo legível a partir de códigos em CAIXA_ALTA ou snake_case. */
export const rotulo = (v: unknown) =>
  v === null || v === undefined || v === "" ? "—" : String(v).replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());

const TOM: Record<string, string> = {
  ok: "bg-[#eef9f1] text-[#15803d] dark:bg-emerald-900/40 dark:text-emerald-300",
  alerta: "bg-[#fff8e5] text-[#a16207] dark:bg-amber-900/40 dark:text-amber-300",
  erro: "bg-[#fef0ef] text-[#b91c1c] dark:bg-rose-900/40 dark:text-rose-300",
  info: "bg-[#eef2ff] text-[#4263c5] dark:bg-marca-900/50 dark:text-marca-200",
  neutro: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
};
const OK = /^(comunicando|concluid|concluido|finalizada|aprovada|executad|regular|ativo|corrigido|reativado|substituido|success|lida|lido|apto|vinculado|ok|disponivel|reenviado|encerrada|executado)/i;
const ERRO = /^(sem comunica|medidor nao|irregular|erro|error|falha|critico|cancel|interrompida|suspenso|descart|timeout|reprov|alto|nao_lido|atrasada|defeito|inativo|devolvida)/i;
const ALERTA = /^(intermitente|pendente|aguardando|em_|programad|aberta|aberto|relogio|reaberta|atencao|medio|media|running|fila|planejado|retorno|recebida|triada)/i;

export function tomStatus(v: unknown): string {
  const s = String(v ?? "");
  if (OK.test(s)) return TOM.ok;
  if (ERRO.test(s)) return TOM.erro;
  if (ALERTA.test(s)) return TOM.alerta;
  return s ? TOM.info : TOM.neutro;
}

export const CORES_GRAFICO = ["#5270da", "#ca8a04", "#16a34a", "#dc2626", "#0ea5e9", "#8b5cf6", "#94a3b8"];

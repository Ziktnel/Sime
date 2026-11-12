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
  ok: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  alerta: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  erro: "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300",
  info: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300",
  neutro: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
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

export const CORES_GRAFICO = ["#14786d", "#f2a541", "#3fb3a3", "#e0607e", "#5b7fd6", "#8e6cc9", "#7a8a8a"];

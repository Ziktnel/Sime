import { getSessao, setSessao } from "./auth";

export class ApiError extends Error {
  constructor(public status: number, message: string, public detalhes: string[] = []) {
    super(message);
  }
}

function headers(extra?: HeadersInit): HeadersInit {
  const t = getSessao()?.access_token;
  return { "Content-Type": "application/json", ...(t ? { Authorization: `Bearer ${t}` } : {}), ...extra };
}

async function tratar(r: Response) {
  if (r.status === 401 && typeof window !== "undefined" && !r.url.includes("/api/auth/login")) {
    setSessao(null);
    window.location.href = "/login?expirada=1";
  }
  let data: unknown = null;
  try {
    data = await r.json();
  } catch {
    /* corpo vazio */
  }
  const detail = (data as { detail?: unknown } | null)?.detail;
  const lista = Array.isArray(detail) ? detail.map(String) : [];
  const msg = typeof detail === "string" ? detail : lista[0] || `Erro ${r.status}`;
  throw new ApiError(r.status, msg, lista);
}

export async function api<T = any>(caminho: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const r = await fetch(caminho, {
    method: opts.method || "GET",
    headers: headers(),
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  if (!r.ok) await tratar(r);
  return (await r.json()) as T;
}

/** Baixa um arquivo autenticado (CSV etc.) e dispara o download no navegador. */
export async function baixar(caminho: string, nome: string, opts: { method?: string; body?: unknown } = {}) {
  const r = await fetch(caminho, { method: opts.method || "GET", headers: headers(), body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) await tratar(r);
  const blob = await r.blob();
  baixarBlob(blob, nome);
}

export function baixarBlob(blob: Blob, nome: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nome;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

/** Abre uma página HTML autenticada (ex.: laudo) numa nova aba. */
export async function abrirHtml(caminho: string) {
  const r = await fetch(caminho, { headers: headers() });
  if (!r.ok) await tratar(r);
  const url = URL.createObjectURL(new Blob([await r.text()], { type: "text/html" }));
  window.open(url, "_blank");
}

export function qs(params: Record<string, string | number | undefined | null>) {
  const u = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  });
  const s = u.toString();
  return s ? `?${s}` : "";
}

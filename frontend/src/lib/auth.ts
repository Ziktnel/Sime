export type Sessao = {
  access_token: string;
  user: { matricula: string; nome: string; email: string; perfil: string; perfil_nome: string; area: string; permissoes: string[] };
};

const CHAVE = "ohmnia.sessao";

export function getSessao(): Sessao | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(CHAVE);
    return raw ? (JSON.parse(raw) as Sessao) : null;
  } catch {
    return null;
  }
}

export function setSessao(s: Sessao | null) {
  try {
    if (s) window.localStorage.setItem(CHAVE, JSON.stringify(s));
    else window.localStorage.removeItem(CHAVE);
  } catch {
    /* navegador sem storage: a sessão dura só esta aba */
  }
}

/** Mesmo algoritmo de curingas do backend (app/core/security.py). */
export function casa(padrao: string, permissao: string): boolean {
  const p = padrao.split(":");
  const a = permissao.split(":");
  if (p.length === 1 && p[0] === "*") return true;
  if (p.length === 2 && p[0] === "*") return a[a.length - 1] === p[1];
  if (p[p.length - 1] === "*") {
    const pre = p.slice(0, -1);
    return a.length > pre.length && pre.every((x, i) => x === "*" || x === a[i]);
  }
  return p.length === a.length && p.every((x, i) => x === "*" || x === a[i]);
}

export function pode(permissao: string | string[] | undefined, s: Sessao | null = getSessao()): boolean {
  if (!permissao) return true;
  if (!s) return false;
  const lista = Array.isArray(permissao) ? permissao : [permissao];
  return lista.some((perm) => s.user.permissoes.some((p) => casa(p, perm)));
}

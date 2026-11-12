// Verifica que todo item do menu aponta para uma página existente e que
// todo recurso genérico usado no menu existe no registro do backend.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const raiz = join(import.meta.dirname, "..");
const nav = readFileSync(join(raiz, "src/lib/nav.ts"), "utf8");
const recursosPy = readFileSync(join(raiz, "../backend/app/recursos.py"), "utf8");

test("rotas fixas do menu têm page.tsx", () => {
  const rotas = [...nav.matchAll(/href: "([^"]+)"/g)].map((m) => m[1]);
  assert.ok(rotas.length > 10);
  for (const r of rotas) {
    const arquivo = join(raiz, "src/app/(app)", r, "page.tsx");
    assert.ok(existsSync(arquivo), `sem página para ${r}`);
  }
});

test("recursos do menu existem no backend", () => {
  const chaves = [...nav.matchAll(/r\("([a-z_]+)"\)/g)].map((m) => m[1]);
  assert.ok(chaves.length > 20);
  for (const c of chaves) assert.match(recursosPy, new RegExp(`"${c}"`), `recurso ${c} ausente no backend`);
});

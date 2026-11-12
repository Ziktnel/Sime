/** Marca original da Ohmnia: um "Ω" estilizado dentro de um hexágono (sem relação com marcas existentes). */
export function Logo({ compacto = false }: { compacto?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <path d="M16 2 28 9v14l-12 7L4 23V9z" fill="#0f5e5c" />
        <path d="M10 22h4v-2.2A6 6 0 1 1 18 19.8V22h4" fill="none" stroke="#f2a541" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {!compacto && (
        <span className="leading-tight">
          <span className="block text-base font-bold tracking-tight text-slate-900 dark:text-white">Ohmnia</span>
          <span className="block text-[10px] uppercase tracking-widest text-slate-500">operação de medição</span>
        </span>
      )}
    </span>
  );
}

import { Zap } from "lucide-react";

/** Marca SIME: símbolo azul com raio e o nome "SIME." (identidade do projeto de referência). */
export function Logo({ compacto = false, claro = false }: { compacto?: boolean; claro?: boolean }) {
  return (
    <span className="inline-flex items-center gap-3">
      <span className={claro ? "grid h-[42px] w-[38px] place-items-center rounded-[10px] bg-white text-marca-600" : "grid h-[42px] w-[38px] place-items-center rounded-[10px] bg-marca-600 text-white"}>
        <Zap className="h-[25px] w-[25px]" strokeWidth={1.7} aria-hidden />
      </span>
      {!compacto && (
        <span className="leading-tight">
          <strong className={claro ? "block text-[25px] font-bold tracking-[.7px] text-white" : "block text-[25px] font-bold tracking-[.7px] text-slate-900 dark:text-white"}>
            SIME<span className={claro ? "text-marca-200" : "text-marca-600"}>.</span>
          </strong>
          <small className={claro ? "mt-0.5 block text-[11px] text-marca-100" : "mt-0.5 block text-[11px] text-slate-500"}>Gestão operacional</small>
        </span>
      )}
    </span>
  );
}

"use client";

import { use } from "react";
import { RecursoPage } from "@/components/RecursoPage";

export default function Page({ params }: { params: Promise<{ recurso: string }> }) {
  const { recurso } = use(params);
  return <RecursoPage chave={recurso} />;
}

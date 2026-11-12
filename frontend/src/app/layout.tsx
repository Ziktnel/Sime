import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui";

export const metadata: Metadata = {
  title: "Ohmnia — Plataforma Operacional",
  description: "Aplicação acadêmica de operação de medição com dados sintéticos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: "try{if(localStorage.getItem('ohmnia.tema')==='dark')document.documentElement.classList.add('dark')}catch(e){}" }} />
      </head>
      <body><ToastProvider>{children}</ToastProvider></body>
    </html>
  );
}

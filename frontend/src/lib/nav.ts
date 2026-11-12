import {
  Activity, BarChart3, Bell, Bot, Building2, CalendarDays, ClipboardCheck, ClipboardList, Cpu, FileOutput, FlaskConical,
  Gauge, HardDrive, History, KeyRound, LayoutDashboard, ListChecks, MapPinned, MessageSquarePlus, Network, Plug, Radio,
  RotateCcw, ScrollText, Search, Settings, ShieldCheck, Sliders, Stethoscope, Truck, UserCheck, Users, Warehouse, Wrench, Zap,
  type LucideIcon,
} from "lucide-react";

export type ItemNav = { label: string; href: string; icon: LucideIcon; permission?: string };
export type SecaoNav = { id: string; label: string; icon: LucideIcon; itens: ItemNav[] };

const r = (chave: string) => `/r/${chave}`;

export const NAV: SecaoNav[] = [
  { id: "geral", label: "Visão geral", icon: LayoutDashboard, itens: [
    { label: "Painel", href: "/painel", icon: LayoutDashboard, permission: "dashboard:visualizar" },
    { label: "Visão 360 da Instalação", href: "/visao-360", icon: Search, permission: "visao-360:visualizar" },
    { label: "Console de Telemetria", href: "/telemetria", icon: Radio, permission: "telemetria:visualizar" },
  ] },
  { id: "medicao", label: "Medição", icon: Gauge, itens: [
    { label: "Clientes Livres", href: r("medicao_clientes_livres"), icon: Users, permission: "medicao:clientes-livres:visualizar" },
    { label: "Base Telemedidos", href: r("medicao_base_telemedidos"), icon: HardDrive, permission: "medicao:base-telemedidos:visualizar" },
    { label: "Constantes KE", href: r("medicao_kes"), icon: Sliders, permission: "medicao:kes:visualizar" },
    { label: "Simplificadas", href: r("medicao_simplificadas"), icon: ListChecks, permission: "medicao:simplificadas:visualizar" },
    { label: "Consulta CCEE", href: "/medicao/ccee", icon: Zap, permission: "medicao:ccee:visualizar" },
    { label: "Subestações", href: r("medicao_subestacoes"), icon: Building2, permission: "medicao:subestacao:visualizar" },
  ] },
  { id: "smc", label: "Medição Centralizada", icon: Network, itens: [
    { label: "Agrupamentos", href: r("smc_agrupamentos"), icon: Network, permission: "smc:agrupamento:visualizar" },
    { label: "Base MDM", href: r("smc_base_mdm"), icon: HardDrive, permission: "smc:base-mdm:visualizar" },
    { label: "Controle Cadastral", href: r("smc_controle_cadastral"), icon: ClipboardList, permission: "smc:controle-cadastral:visualizar" },
    { label: "Comissionamento", href: "/smc/comissionamento", icon: FileOutput, permission: "smc:comissionamento:visualizar" },
    { label: "Programações de Nota", href: r("smc_programacoes_nota"), icon: ClipboardCheck, permission: "smc:programacoes-nota:visualizar" },
    { label: "Recapacitação", href: r("smc_recapacitacao"), icon: RotateCcw, permission: "smc:recapacitacao:visualizar" },
  ] },
  { id: "equipes", label: "Equipes de Campo", icon: Truck, itens: [
    { label: "Notas BT", href: r("equipes_notas"), icon: ClipboardList, permission: "equipes:programa-bt:visualizar" },
    { label: "Equipes em Campo", href: r("equipes_campo"), icon: Truck, permission: "equipes:programa-bt:visualizar" },
  ] },
  { id: "lab", label: "Laboratório de Medidores", icon: FlaskConical, itens: [
    { label: "Análises", href: "/laboratorio-medidores", icon: FlaskConical, permission: "analise-medidores:entrada-manual:visualizar" },
    { label: "Calendário", href: "/laboratorio-medidores/calendario", icon: CalendarDays, permission: "analise-medidores:calendario:visualizar" },
    { label: "Aprovações", href: "/laboratorio-medidores/aprovacoes", icon: ShieldCheck, permission: "analise-medidores:aprovar" },
    { label: "Importar bancada", href: "/laboratorio-medidores/bancada", icon: Cpu, permission: "analise-medidores:bancada:visualizar" },
    { label: "Indicadores", href: "/laboratorio-medidores/indicadores", icon: BarChart3, permission: "analise-medidores:indicadores:visualizar" },
    { label: "Quarentena", href: "/laboratorio-medidores/quarentena", icon: Warehouse, permission: "analise-medidores:quarentena:visualizar" },
    { label: "Notas de Aferição", href: r("am_notas_afericao"), icon: ScrollText, permission: "analise-medidores:notas-afericao:visualizar" },
    { label: "Configurações", href: r("am_catalogos"), icon: Settings, permission: "analise-medidores:configuracoes:visualizar" },
  ] },
  { id: "campo", label: "Comunicação de Campo", icon: Wrench, itens: [
    { label: "Cativo — Projeto", href: r("com_cativo_projeto"), icon: Wrench, permission: "comunicacao-campo:projeto:visualizar" },
    { label: "Cativo — Manutenção", href: r("com_cativo_manutencao"), icon: History, permission: "comunicacao-campo:manutencao:visualizar" },
    { label: "Cativo — Programa BT", href: r("com_cativo_programa_bt"), icon: Zap, permission: "comunicacao-campo:programa-bt:visualizar" },
    { label: "Cativo — Outros", href: r("com_cativo_outros"), icon: ClipboardList, permission: "comunicacao-campo:outros:visualizar" },
    { label: "Livre — Manutenção", href: r("com_livre_manutencao"), icon: History, permission: "comunicacao-campo:manutencao:visualizar" },
    { label: "Substituição de CS", href: r("com_substituicao_cs"), icon: RotateCcw, permission: "comunicacao-campo:substituicao-cs:visualizar" },
    { label: "Equipes do bot", href: r("com_equipes_bot"), icon: UserCheck, permission: "comunicacao-campo:cadastro-equipes:visualizar" },
    { label: "Logs do bot", href: r("com_logs_bot"), icon: Bot, permission: "comunicacao-campo:logs-bot:visualizar" },
    { label: "CPU e memória do bot", href: "/comunicacao/monitoramento-bot", icon: Activity, permission: "comunicacao-campo:monitoramento-bot:visualizar" },
  ] },
  { id: "telecom", label: "Laboratório de Telecom", icon: Radio, itens: [
    { label: "Triagem de remotas", href: r("lab_triagem_remotas"), icon: Radio, permission: "laboratorio:triagem-remotas:visualizar" },
    { label: "Simcards suspensos", href: r("lab_simcards_suspensos"), icon: Radio, permission: "laboratorio:simcards-suspensos:visualizar" },
  ] },
  { id: "mt", label: "Gestão MT", icon: Stethoscope, itens: [
    { label: "Painel MT", href: "/gestao-mt", icon: LayoutDashboard, permission: "gestao-mt:dashboard:visualizar" },
    { label: "Diagnóstico", href: "/gestao-mt/diagnostico", icon: Stethoscope, permission: "gestao-mt:diagnostico:visualizar" },
    { label: "Mapa", href: "/gestao-mt/mapa", icon: MapPinned, permission: "gestao-mt:mapa:visualizar" },
    { label: "Plano de Campo", href: r("mt_plano_campo"), icon: ClipboardCheck, permission: "gestao-mt:plano-campo:visualizar" },
    { label: "Controle de Notas", href: r("mt_controle_notas"), icon: ClipboardList, permission: "gestao-mt:controle-notas:visualizar" },
    { label: "Triagem de faturamento", href: r("fat_triagem"), icon: ListChecks, permission: "faturamento-mt:triagem:visualizar" },
    { label: "Agenda de leitura", href: r("fat_agenda"), icon: CalendarDays, permission: "faturamento-mt:triagem:visualizar" },
    { label: "Campo (D 10:00)", href: r("fat_campo"), icon: MapPinned, permission: "faturamento-mt:triagem:visualizar" },
    { label: "Não enviados ao MDM", href: r("fat_exportacao"), icon: FileOutput, permission: "faturamento-mt:exportacao:visualizar" },
    { label: "Correção cadastral", href: r("fat_cadastro"), icon: ClipboardCheck, permission: "faturamento-mt:cadastro:visualizar" },
  ] },
  { id: "ger", label: "Gerenciamento", icon: Settings, itens: [
    { label: "Rotinas", href: "/gerenciamento/tarefas", icon: ListChecks, permission: "gerenciamento:tarefas:visualizar" },
    { label: "Usuários", href: "/gerenciamento/usuarios", icon: Users, permission: "gerenciamento:usuarios:visualizar" },
    { label: "Acessos por perfil", href: "/gerenciamento/acessos", icon: KeyRound, permission: "gerenciamento:usuarios:visualizar" },
    { label: "Auditoria", href: "/gerenciamento/auditoria", icon: ScrollText, permission: "gerenciamento:usuarios:visualizar" },
    { label: "Integrações simuladas", href: "/gerenciamento/integracoes", icon: Plug, permission: "gerenciamento:integracoes:visualizar" },
    { label: "Agenda do laboratório", href: r("ger_lab_agenda"), icon: CalendarDays, permission: "gerenciamento:lab-agenda:visualizar" },
    { label: "Sugestões e bugs", href: r("sugestoes"), icon: MessageSquarePlus, permission: "sugestoes:visualizar" },
  ] },
];

export const ICONE_NOTIFICACAO = Bell;

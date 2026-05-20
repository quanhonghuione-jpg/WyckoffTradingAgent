import { useEffect } from 'react'
import { useLocation } from 'react-router'
import { AlertTriangle, BarChart3, Bot, Briefcase, CalendarDays, CheckCircle2, CloudCog, Download, ExternalLink, GitBranch, MessageSquare, Moon, RadioTower, Rocket, Settings, Terminal, TrendingUp, Users, type LucideIcon } from 'lucide-react'
import { usePreferences, type Locale, type TranslationKey } from '@/lib/preferences'

const workflows = [
  {
    icon: MessageSquare,
    titleKey: 'guide.workflow.chat.title',
    descKey: 'guide.workflow.chat.desc',
  },
  {
    icon: BarChart3,
    titleKey: 'guide.workflow.analysis.title',
    descKey: 'guide.workflow.analysis.desc',
  },
  {
    icon: Briefcase,
    titleKey: 'guide.workflow.portfolio.title',
    descKey: 'guide.workflow.portfolio.desc',
  },
] satisfies { icon: LucideIcon; titleKey: TranslationKey; descKey: TranslationKey }[]

const tools = [
  { nameKey: 'guide.tool.market', detailKey: 'guide.tool.market.detail' },
  { nameKey: 'guide.tool.tracking', detailKey: 'guide.tool.tracking.detail' },
  { nameKey: 'guide.tool.signal', detailKey: 'guide.tool.signal.detail' },
  { nameKey: 'guide.tool.tail', detailKey: 'guide.tool.tail.detail' },
  { nameKey: 'guide.tool.export', detailKey: 'guide.tool.export.detail' },
  { nameKey: 'guide.tool.model', detailKey: 'guide.tool.model.detail' },
] satisfies { nameKey: TranslationKey; detailKey: TranslationKey }[]

const playbooks = [
  {
    labelKey: 'guide.playbook.pre',
    icon: RadioTower,
    textKey: 'guide.playbook.pre.text',
  },
  {
    labelKey: 'guide.playbook.mid',
    icon: TrendingUp,
    textKey: 'guide.playbook.mid.text',
  },
  {
    labelKey: 'guide.playbook.tail',
    icon: Moon,
    textKey: 'guide.playbook.tail.text',
  },
  {
    labelKey: 'guide.playbook.review',
    icon: Download,
    textKey: 'guide.playbook.review.text',
  },
] satisfies { labelKey: TranslationKey; icon: LucideIcon; textKey: TranslationKey }[]

const capabilityCopy = {
  'zh-CN': {
    eyebrow: '能力边界',
    title: '系统已经很强，但 Web 只是驾驶舱',
    intro: '有些能力适合在网页里点一点就用；有些能力需要 GitHub Actions、本地 CLI 或后台任务来承载。这里把“系统有，但 Web 端暂未完整接入”的部分摊开，避免你以为功能消失了。',
    webTitle: 'Web 端已经覆盖',
    webItems: ['单股 320 日结构图与模型分析', '读盘室自然语言工具调用', '推荐跟踪、尾盘记录、持仓诊断查看', '单标的数据导出与基础配置'],
    gapTitle: '系统有，但 Web 端不完整',
    whyTitle: '为什么不全塞进 Web',
    costLinkText: '成本详见：COST_MODEL.md',
    accessTitle: '当前入口',
  },
  'en-US': {
    eyebrow: 'Capability Map',
    title: 'The system is deeper than the web cockpit',
    intro: 'Some workflows belong in the browser. Others need GitHub Actions, local CLI, or background jobs. This map shows what exists in the system but is not fully wired into the web UI yet.',
    webTitle: 'Covered by the web UI',
    webItems: ['Single-stock 320-day structure chart and model analysis', 'Natural-language tool use in Reading Room', 'Recommendation tracking, tail-buy logs, and portfolio diagnosis views', 'Single-symbol export and basic configuration'],
    gapTitle: 'Available in the system, partial or missing on web',
    whyTitle: 'Why not put everything in the browser',
    costLinkText: 'Cost details: COST_MODEL.md',
    accessTitle: 'Where to use them today',
  },
} satisfies Record<Locale, {
  eyebrow: string
  title: string
  intro: string
  webTitle: string
  webItems: string[]
  gapTitle: string
  whyTitle: string
  costLinkText: string
  accessTitle: string
}>

const capabilityGaps = {
  'zh-CN': [
    ['全市场漏斗任务', 'A股、港股、美股每日全市场扫描、L1-L4 分层、信号写库与飞书推送仍主要跑在 GitHub Actions。'],
    ['单票漏斗复盘诊断', '输入一只股票和日期区间，逐日解释为什么没进漏斗、卡在哪层、哪天被选中。'],
    ['回测与参数网格', '牛熊周期、TopN、止损/止盈/持仓天数等批量计算适合后台长任务，Web 目前只展示部分结果。'],
    ['信号生命周期与补价回刷', 'pending/confirmed/expired、推荐表现回刷、现价同步、MFE/MAE 统计都在后台维护。'],
    ['本地自动化与 CLI Agent', 'OpenClaw 本地 cron、CLI/TUI、长上下文 Agent、文件产物和本机环境变量不适合直接暴露给浏览器。'],
    ['维护与数据库任务', '缓存清理、RLS/服务端密钥操作、日志 artifact、批量导出属于运维能力，Web 只保留安全入口。'],
  ],
  'en-US': [
    ['Full-market funnel jobs', 'A-share, HK, and US market scans, L1-L4 layering, signal writes, and Feishu pushes mainly run in GitHub Actions.'],
    ['Single-symbol funnel diagnosis', 'Given one symbol and a date range, replay each day to explain where the symbol failed and when it was selected.'],
    ['Backtests and parameter grids', 'Bull/bear windows, TopN, stop-loss, take-profit, and holding-day grids are long-running backend workloads.'],
    ['Signal lifecycle and repricing', 'pending/confirmed/expired updates, recommendation repricing, live price sync, MFE/MAE stats run in background jobs.'],
    ['Local automation and CLI Agent', 'OpenClaw cron, CLI/TUI, long-context agents, local files, and env vars should stay on the user machine.'],
    ['Maintenance and database jobs', 'Cache cleanup, service-role operations, log artifacts, and bulk exports are operational tools, not browser-first UI.'],
  ],
} satisfies Record<Locale, [string, string][]>

const capabilityReasons = {
  'zh-CN': ['全市场漏斗、回测网格、逐日复盘诊断都属于长时间计算；如果全部在线化，需要持续计算资源和排队能力。', '320 日日线、多市场结果、分钟线、回刷统计会带来大数据量存储；如果全部给 Web 即时查询，需要更高数据库与缓存成本。'],
  'en-US': ['Full-market funnels, backtest grids, and day-by-day replay diagnosis are long-running computations that require persistent compute and queue capacity when fully online.', '320-day bars, multi-market results, intraday data, and repricing stats create large storage needs that raise database and cache costs for instant web queries.'],
} satisfies Record<Locale, string[]>

const capabilityLaunch = {
  'zh-CN': {
    kicker: '开放预告',
    date: '2026-06-03',
    title: '将开放知识星球、闲鱼等加入方式',
    desc: '如果你对这个项目感兴趣，可以和我一起使用漏斗、回测、单票复盘、尾盘策略、持仓诊断等完整能力，而不只停留在 Web 端的轻量入口。',
    badge: '完整能力',
    tags: ['完整漏斗能力', '回测与复盘', '多市场数据', '一起迭代'],
  },
  'en-US': {
    kicker: 'Access preview',
    date: '2026-06-03',
    title: 'Knowledge Planet, Xianyu, and similar access channels will open',
    desc: 'If this project resonates with you, you can join me to use the full funnel, backtest, replay, tail-buy, and portfolio diagnosis workflows beyond the lightweight web cockpit.',
    badge: 'Full Access',
    tags: ['Full funnel', 'Backtest & replay', 'Multi-market data', 'Build together'],
  },
} satisfies Record<Locale, {
  kicker: string
  date: string
  title: string
  desc: string
  badge: string
  tags: string[]
}>

const capabilityAccess = {
  'zh-CN': [
    ['GitHub Actions', '漏斗、回测、单票诊断、回刷、维护任务'],
    ['本地 CLI / OpenClaw', '准点触发、长任务、本地密钥和文件工作流'],
    ['运维脚本 / 数据库控制台', '偏后台的配置、调试和数据库维护能力'],
    ['Web 端', '高频查看、轻量分析、配置和用户安全入口'],
  ],
  'en-US': [
    ['GitHub Actions', 'Funnel, backtest, symbol diagnosis, repricing, maintenance jobs'],
    ['Local CLI / OpenClaw', 'On-time triggers, long jobs, local secrets and file workflows'],
    ['Ops scripts / database console', 'Admin-like configuration, debugging, and database maintenance'],
    ['Web UI', 'Frequent viewing, lightweight analysis, settings, and safe user entry points'],
  ],
} satisfies Record<Locale, [string, string][]>

export function FeatureGuidePage() {
  const { locale, t } = usePreferences()
  const location = useLocation()

  useEffect(() => {
    if (location.hash !== '#capability-boundary') return
    requestAnimationFrame(() => document.getElementById('capability-boundary')?.scrollIntoView({ block: 'start' }))
  }, [location.hash])

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 p-6">
      <header className="border-b border-border pb-5">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Bot size={22} />
          </span>
          <div>
            <h1 className="text-xl font-semibold">{t('guide.title')}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {t('guide.subtitle')}
            </p>
          </div>
        </div>
      </header>

      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold">{t('guide.core')}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t('guide.coreDesc')}</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {workflows.map(({ icon: Icon, titleKey, descKey }) => (
            <article key={titleKey} className="rounded-lg border border-border bg-background p-4 shadow-sm shadow-primary/5">
              <Icon className="mb-3 text-primary" size={20} />
              <h3 className="text-sm font-semibold">{t(titleKey)}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{t(descKey)}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div>
          <h2 className="mb-4 text-base font-semibold">{t('guide.modules')}</h2>
          <div className="overflow-hidden rounded-lg border border-border bg-background">
            <table className="w-full text-sm">
              <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 font-medium">{t('guide.module')}</th>
                  <th className="px-4 py-3 font-medium">{t('guide.description')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {tools.map((tool) => (
                  <tr key={tool.nameKey}>
                    <td className="whitespace-nowrap px-4 py-3 font-medium">{t(tool.nameKey)}</td>
                    <td className="px-4 py-3 leading-6 text-muted-foreground">{t(tool.detailKey)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside>
          <h2 className="mb-4 text-base font-semibold">{t('guide.rhythm')}</h2>
          <div className="space-y-3">
            {playbooks.map(({ icon: Icon, labelKey, textKey }) => (
              <div key={labelKey} className="rounded-lg border border-border bg-sidebar p-4">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Icon size={16} className="text-primary" />
                  {t(labelKey)}
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{t(textKey)}</p>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <CapabilityBoundarySection locale={locale} />

      <section className="rounded-lg border border-border bg-primary/5 p-5">
        <div className="flex items-start gap-3">
          <Settings className="mt-0.5 text-primary" size={18} />
          <div>
            <h2 className="text-sm font-semibold">{t('guide.configEntry')}</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {t('guide.configDesc')}
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

function CapabilityBoundarySection({ locale }: { locale: Locale }) {
  const copy = capabilityCopy[locale]
  return (
    <section id="capability-boundary" className="scroll-mt-6 overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-sidebar via-background to-primary/5 p-5 shadow-sm">
      <div className="mb-5 max-w-3xl">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary">{copy.eyebrow}</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">{copy.title}</h2>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{copy.intro}</p>
      </div>
      <CapabilityLaunchBanner locale={locale} />
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.4fr]">
        <CapabilityWebCard copy={copy} />
        <CapabilityGapCard title={copy.gapTitle} locale={locale} />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <CapabilityListCard icon={AlertTriangle} title={copy.whyTitle} items={capabilityReasons[locale]} costLinkText={copy.costLinkText} tone="warning" />
        <CapabilityAccessCard title={copy.accessTitle} locale={locale} />
      </div>
    </section>
  )
}

function CapabilityLaunchBanner({ locale }: { locale: Locale }) {
  const copy = capabilityLaunch[locale]
  return (
    <article className="relative mb-5 overflow-hidden rounded-2xl border border-amber-300/50 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.26),transparent_36%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(88,28,135,0.85)_48%,rgba(180,83,9,0.88))] p-5 text-white shadow-lg shadow-amber-900/10">
      <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full border border-white/20 bg-white/10 blur-sm" />
      <div className="relative grid gap-5 lg:grid-cols-[1fr_280px] lg:items-center">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1 rounded-full border border-white/20 bg-white/15 px-3 py-1 text-xs font-semibold backdrop-blur">
              <Rocket size={13} />
              {copy.kicker}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-300 px-3 py-1 text-xs font-bold text-slate-950">
              <CalendarDays size={13} />
              {copy.date}
            </span>
          </div>
          <h3 className="mt-4 text-2xl font-semibold tracking-tight">{copy.title}</h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-white/78">{copy.desc}</p>
        </div>
        <div className="rounded-2xl border border-white/15 bg-white/10 p-4 backdrop-blur">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            <Users size={16} />
            {copy.badge}
          </div>
          <div className="flex flex-wrap gap-2">
            {copy.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-white/15 px-3 py-1 text-xs text-white/90">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </article>
  )
}

function CapabilityWebCard({ copy }: { copy: (typeof capabilityCopy)[Locale] }) {
  return (
    <article className="rounded-xl border border-primary/20 bg-primary/10 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-primary">
        <CheckCircle2 size={17} />
        {copy.webTitle}
      </div>
      <ul className="space-y-2 text-sm leading-6 text-muted-foreground">
        {copy.webItems.map((item) => <li key={item}>• {item}</li>)}
      </ul>
    </article>
  )
}

function CapabilityGapCard({ title, locale }: { title: string; locale: Locale }) {
  return (
    <article className="rounded-xl border border-border bg-background/80 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <CloudCog size={17} className="text-primary" />
        {title}
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {capabilityGaps[locale].map(([name, desc]) => (
          <div key={name} className="rounded-lg border border-border bg-sidebar/70 p-3">
            <h3 className="text-sm font-semibold">{name}</h3>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{desc}</p>
          </div>
        ))}
      </div>
    </article>
  )
}

function CapabilityListCard({ icon: Icon, title, items, costLinkText, tone }: { icon: LucideIcon; title: string; items: string[]; costLinkText: string; tone: 'warning' }) {
  return (
    <article className="rounded-xl border border-border bg-background/80 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <Icon size={17} className={tone === 'warning' ? 'text-warning' : 'text-primary'} />
        {title}
      </div>
      <ul className="space-y-2 text-sm leading-6 text-muted-foreground">
        {items.map((item) => <li key={item}>• {item}</li>)}
      </ul>
      <a
        className="mt-3 inline-flex items-center gap-1 rounded-full border border-warning/30 bg-warning/10 px-3 py-1.5 text-xs font-medium text-warning transition hover:bg-warning/15"
        href="https://github.com/YoungCan-Wang/WyckoffTradingAgent/blob/main/docs/COST_MODEL.md"
        rel="noreferrer"
        target="_blank"
      >
        {costLinkText}
        <ExternalLink size={13} />
      </a>
    </article>
  )
}

function CapabilityAccessCard({ title, locale }: { title: string; locale: Locale }) {
  const icons = [GitBranch, Terminal, Settings, Bot]
  return (
    <article className="rounded-xl border border-border bg-background/80 p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
        <GitBranch size={17} className="text-primary" />
        {title}
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {capabilityAccess[locale].map(([name, desc], index) => {
          const Icon = icons[index] ?? Bot
          return (
            <div key={name} className="rounded-lg bg-muted/60 p-3">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <Icon size={15} className="text-primary" />
                {name}
              </div>
              <p className="mt-1 text-xs leading-5 text-muted-foreground">{desc}</p>
            </div>
          )
        })}
      </div>
    </article>
  )
}

import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useState,
  useTransition,
} from 'react'

import { Banner } from './components/Banner'
import { DataList } from './components/DataList'
import { api } from './lib/api'
import type {
  BarkConfigRecord,
  CollectorDiagnosticsResponse,
  CookieProfileRecord,
  DashboardOverviewResponse,
  JobRunRecord,
  ManualSyncResponse,
  ModelProviderRecord,
  OptionalBarkConfigResponse,
  OptionalTelegramConfigResponse,
  TelegramConfigRecord,
  TestTelegramPushResponse,
  TrackedAccountRecord,
} from './lib/types'

type Screen = 'loading' | 'setup' | 'login' | 'dashboard'

const initialAccountForm = {
  display_name: '',
  account_handle: '',
  profile_url: '',
  notes: '',
}

const initialCookieForm = {
  label: '',
  cookie_value: '',
}

const initialProviderForm = {
  name: '',
  base_url: '',
  api_key: '',
  summary_model: '',
  translation_model: '',
  ocr_model: '',
  transcription_model: '',
  understanding_model: '',
  is_default: true,
}

const initialBarkForm = {
  label: 'Primary Bark',
  server_url: 'https://api.day.app',
  device_key: '',
  is_enabled: true,
}

const initialTelegramForm = {
  label: 'Primary Telegram',
  api_base_url: 'https://api.telegram.org',
  chat_id: '',
  bot_token: '',
  is_enabled: true,
}

const initialDiagnosticsForm = {
  target_url: 'https://www.xiaohongshu.com/',
  cookie_profile_id: '',
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('loading')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [submittingLabel, setSubmittingLabel] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const [authForm, setAuthForm] = useState({ username: '', password: '' })
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null)
  const [accounts, setAccounts] = useState<TrackedAccountRecord[]>([])
  const [cookieProfiles, setCookieProfiles] = useState<CookieProfileRecord[]>([])
  const [modelProviders, setModelProviders] = useState<ModelProviderRecord[]>([])
  const [barkConfig, setBarkConfig] = useState<BarkConfigRecord | null>(null)
  const [telegramConfig, setTelegramConfig] = useState<TelegramConfigRecord | null>(null)
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([])
  const [manualSyncResult, setManualSyncResult] = useState<ManualSyncResponse | null>(null)
  const [jobRuns, setJobRuns] = useState<JobRunRecord[]>([])
  const [collectorDiagnostics, setCollectorDiagnostics] =
    useState<CollectorDiagnosticsResponse | null>(null)

  const [accountForm, setAccountForm] = useState(initialAccountForm)
  const [cookieForm, setCookieForm] = useState(initialCookieForm)
  const [providerForm, setProviderForm] = useState(initialProviderForm)
  const [barkForm, setBarkForm] = useState(initialBarkForm)
  const [telegramForm, setTelegramForm] = useState(initialTelegramForm)
  const [diagnosticsForm, setDiagnosticsForm] = useState(initialDiagnosticsForm)

  useEffect(() => {
    void bootstrap()
  }, [])

  const securityReady = overview?.security_ready ?? false
  const interfaceBusy = submittingLabel !== null || isPending

  const metrics = useMemo(
    () => [
      ['监控账号', overview?.tracked_accounts ?? 0],
      ['Cookie 配置', overview?.cookie_profiles ?? 0],
      ['模型配置', overview?.model_providers ?? 0],
      ['已存内容', overview?.contents ?? 0],
      ['推送日志', overview?.push_logs ?? 0],
    ],
    [overview],
  )

  async function bootstrap() {
    setError(null)

    try {
      const status = await api.bootstrapStatus()
      setAuthForm((current) => ({
        ...current,
        username: current.username || status.default_admin_username,
      }))
      if (status.needs_setup) {
        setScreen('setup')
        return
      }

      try {
        await refreshDashboard()
      } catch {
        setScreen('login')
      }
    } catch (reason) {
      setError(readError(reason))
      setScreen('login')
    }
  }

  async function refreshDashboard() {
    setSubmittingLabel('正在刷新面板')
    setError(null)

    try {
      const [overviewData, accountsData, cookiesData, providersData, barkData, telegramData, runsData] =
        await Promise.all([
          api.overview(),
          api.listAccounts(),
          api.listCookieProfiles(),
          api.listModelProviders(),
          api.getBarkConfig(),
          api.getTelegramConfig(),
          api.listRuns(),
        ])

      startTransition(() => {
        setOverview(overviewData)
        setAccounts(accountsData)
        setCookieProfiles(cookiesData)
        setModelProviders(providersData)
        setBarkConfig(barkData.data)
        setTelegramConfig(telegramData.data)
        syncBarkForm(barkData)
        syncTelegramForm(telegramData)
        setJobRuns(runsData)
        setScreen('dashboard')
      })
    } finally {
      setSubmittingLabel(null)
    }
  }

  function syncBarkForm(payload: OptionalBarkConfigResponse) {
    if (!payload.data) {
      setBarkForm(initialBarkForm)
      return
    }

    setBarkForm({
      label: payload.data.label,
      server_url: payload.data.server_url,
      device_key: '',
      is_enabled: payload.data.is_enabled,
    })
  }

  function syncTelegramForm(payload: OptionalTelegramConfigResponse) {
    if (!payload.data) {
      setTelegramForm(initialTelegramForm)
      return
    }

    setTelegramForm({
      label: payload.data.label,
      api_base_url: payload.data.api_base_url,
      chat_id: payload.data.chat_id,
      bot_token: '',
      is_enabled: payload.data.is_enabled,
    })
  }

  async function handleSetup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在创建管理员', async () => {
      await api.setup(authForm)
      await refreshDashboard()
      setNotice('本地管理员账号已创建。')
      setAuthForm((current) => ({ ...current, password: '' }))
    })
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在登录', async () => {
      await api.login(authForm)
      await refreshDashboard()
      setNotice('已进入控制台。')
      setAuthForm((current) => ({ ...current, password: '' }))
    })
  }

  async function handleAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在保存账号', async () => {
      await api.createAccount({
        display_name: accountForm.display_name,
        account_handle: accountForm.account_handle,
        profile_url: accountForm.profile_url,
        notes: accountForm.notes,
        is_active: true,
      })
      setAccountForm(initialAccountForm)
      await refreshDashboard()
      setNotice('账号已加入监控列表。')
    })
  }

  async function handleCookie(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在保存 Cookie', async () => {
      await api.createCookieProfile({
        label: cookieForm.label,
        cookie_value: cookieForm.cookie_value,
        is_active: true,
      })
      setCookieForm(initialCookieForm)
      await refreshDashboard()
      setNotice('Cookie 配置已加密保存。')
    })
  }

  async function handleProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在保存模型提供方', async () => {
      await api.createModelProvider({
        ...providerForm,
        is_default: providerForm.is_default,
      })
      setProviderForm(initialProviderForm)
      await refreshDashboard()
      setNotice('模型提供方已保存。')
    })
  }

  async function handleBark(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在保存 Bark 配置', async () => {
      await api.saveBarkConfig({
        ...barkForm,
        is_enabled: barkForm.is_enabled,
      })
      await refreshDashboard()
      setBarkForm((current) => ({ ...current, device_key: '' }))
      setNotice('Bark 配置已更新。')
    })
  }

  async function handleTelegram(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('Saving Telegram configuration', async () => {
      await api.saveTelegramConfig({
        ...telegramForm,
        is_enabled: telegramForm.is_enabled,
      })
      await refreshDashboard()
      setTelegramForm((current) => ({ ...current, bot_token: '' }))
      setNotice('Telegram configuration updated.')
    })
  }

  async function handleTelegramTest() {
    await runAction('Sending Telegram test message', async () => {
      const response: TestTelegramPushResponse = await api.testTelegramPush()
      setNotice(`Telegram test sent: ${response.message_preview}`)
    })
  }

  async function handleDiscoverModels() {
    await runAction('正在获取模型列表', async () => {
      const response = await api.discoverModels({
        base_url: providerForm.base_url,
        api_key: providerForm.api_key,
      })
      setDiscoveredModels(response.models)
      setNotice(
        response.models.length > 0
          ? `已获取 ${response.models.length} 个模型，可直接从下拉候选中选择。`
          : '接口返回成功，但没有返回可用模型。',
      )
    })
  }

  async function handleManualSync() {
    await runAction('正在执行手动同步预检', async () => {
      const response = await api.manualSync()
      const runs = await api.listRuns()
      setManualSyncResult(response)
      setJobRuns(runs)
      setNotice(response.readiness.message)
    })
  }

  async function handleCollectorDiagnostics(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await runAction('正在执行抓取诊断', async () => {
      const response = await api.collectorDiagnostics({
        target_url: diagnosticsForm.target_url,
        cookie_profile_id: diagnosticsForm.cookie_profile_id || undefined,
      })
      setCollectorDiagnostics(response)
      setNotice(`抓取诊断完成，HTTP ${response.status}。`)
    })
  }

  async function handleLogout() {
    await runAction('正在退出', async () => {
      await api.logout()
      setOverview(null)
      setAccounts([])
      setCookieProfiles([])
      setModelProviders([])
      setBarkConfig(null)
      setTelegramConfig(null)
      setJobRuns([])
      setScreen('login')
      setNotice('会话已退出。')
    })
  }

  async function runAction(label: string, action: () => Promise<void>) {
    setSubmittingLabel(label)
    setError(null)

    try {
      await action()
    } catch (reason) {
      setError(readError(reason))
    } finally {
      setSubmittingLabel(null)
    }
  }

  if (screen === 'loading') {
    return <AuthShell title="正在加载本地后台" subtitle="正在检查初始化状态与当前会话。" />
  }

  if (screen === 'setup' || screen === 'login') {
    return (
      <div className="auth-shell">
        <div className="auth-panel auth-panel--wide">
          <div className="auth-copy">
            <p className="eyebrow">Xiaohongshu Watchtower</p>
            <h1>To Know Everything</h1>
            <p className="lede">
              本地运行的内容监控面板，先保证账号安全、再保证抓取稳定，最后再接 Bark 推送。
            </p>
            <div className="status-strip">
              <span className="status-chip">Rust backend</span>
              <span className="status-chip">React admin</span>
              <span className="status-chip">Bark first</span>
            </div>
          </div>

          <form
            className="panel-card auth-form"
            onSubmit={screen === 'setup' ? handleSetup : handleLogin}
          >
            <p className="section-kicker">
              {screen === 'setup' ? '初始化管理员' : '管理员登录'}
            </p>
            <h2>{screen === 'setup' ? '创建首个本地账号' : '进入控制台'}</h2>
            <InputField
              label="用户名"
              value={authForm.username}
              onChange={(value) =>
                setAuthForm((current) => ({ ...current, username: value }))
              }
              placeholder="admin"
            />
            <InputField
              label="密码"
              value={authForm.password}
              onChange={(value) =>
                setAuthForm((current) => ({ ...current, password: value }))
              }
              placeholder="至少 10 位"
              type="password"
            />
            {notice ? <Banner tone="good" text={notice} /> : null}
            {error ? <Banner tone="danger" text={error} /> : null}
            <button className="button button--primary" disabled={interfaceBusy}>
              {submittingLabel ?? (screen === 'setup' ? '创建管理员' : '登录')}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="dashboard-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local-only Monitoring Console</p>
          <h1>To Know Everything</h1>
          <p className="lede lede--compact">
            当前阶段聚焦小红书单账号、低风控抓取、AI 理解与 Bark 推送。
          </p>
        </div>
        <div className="topbar-actions">
          <div className="user-badge">
            <span>登录用户</span>
            <strong>{overview?.user.username}</strong>
          </div>
          <button className="button button--ghost" onClick={() => void refreshDashboard()}>
            刷新
          </button>
          <button className="button button--ghost" onClick={() => void handleLogout()}>
            退出
          </button>
        </div>
      </header>

      {notice ? <Banner tone="good" text={notice} /> : null}
      {error ? <Banner tone="danger" text={error} /> : null}
      {!securityReady ? (
        <Banner
          tone="warning"
          text="当前未启用安全存储。先设置 TKE_MASTER_PASSWORD，再保存 Cookie、API Key 和 Bark 设备码。"
        />
      ) : null}

      <div className="dashboard-grid">
        <aside className="panel-card side-rail">
          <p className="section-kicker">导航</p>
          <nav className="rail-nav">
            <a href="#overview">概览</a>
            <a href="#collector">抓取诊断</a>
            <a href="#runs">运行记录</a>
            <a href="#accounts">监控账号</a>
            <a href="#cookies">Cookie</a>
            <a href="#models">模型配置</a>
            <a href="#bark">Bark</a>
            <a href="#telegram">Telegram</a>
          </nav>
          <div className="rail-note">
            <p className="section-kicker">当前状态</p>
            <strong>{submittingLabel ?? '空闲'}</strong>
            <p>敏感内容默认只在本地保存与使用。</p>
          </div>
        </aside>

        <main className="content-column">
          <section id="overview" className="panel-card">
            <p className="section-kicker">Overview</p>
            <h2>当前控制面板</h2>
            <div className="metric-grid">
              {metrics.map(([label, value], index) => (
                <article
                  key={label}
                  className={`metric-card ${index % 2 === 0 ? 'metric-card--warm' : 'metric-card--cool'}`}
                >
                  <span>{label}</span>
                  <strong>{value}</strong>
                </article>
              ))}
            </div>
            <div className="action-bar">
              <button
                className="button button--primary"
                disabled={interfaceBusy}
                onClick={() => void handleManualSync()}
              >
                手动同步预检
              </button>
              {manualSyncResult ? (
                <div className="preflight-card">
                  <strong>
                    最近预检: {manualSyncResult.status} · {manualSyncResult.job_run_id}
                  </strong>
                  <span>{manualSyncResult.readiness.message}</span>
                  <p>
                    安全存储 {flag(manualSyncResult.readiness.security_ready)} / 账号{' '}
                    {flag(manualSyncResult.readiness.has_account)} / Cookie{' '}
                    {flag(manualSyncResult.readiness.has_cookie_profile)} / 模型{' '}
                    {flag(manualSyncResult.readiness.has_model_provider)} / Bark{' '}
                    {flag(manualSyncResult.readiness.bark_enabled)} / 抓取器{' '}
                    {manualSyncResult.readiness.collector_status}
                  </p>
                </div>
              ) : null}
            </div>
          </section>

          <FormSection
            id="collector"
            title="抓取诊断"
            kicker="Low-risk PoC"
            badge="单次 GET 探测"
            form={
              <form className="form-grid" onSubmit={handleCollectorDiagnostics}>
                <InputField
                  label="目标 URL"
                  value={diagnosticsForm.target_url}
                  onChange={(value) =>
                    setDiagnosticsForm((current) => ({ ...current, target_url: value }))
                  }
                  placeholder="https://www.xiaohongshu.com/..."
                  wide
                />
                <SelectField
                  label="Cookie 配置"
                  value={diagnosticsForm.cookie_profile_id}
                  onChange={(value) =>
                    setDiagnosticsForm((current) => ({
                      ...current,
                      cookie_profile_id: value,
                    }))
                  }
                  options={[
                    { label: '不使用 Cookie', value: '' },
                    ...cookieProfiles.map((cookie) => ({
                      label: `${cookie.label} · ${cookie.cookie_preview}`,
                      value: cookie.id,
                    })),
                  ]}
                />
                <div className="field">
                  <span>说明</span>
                  <div className="inline-note">
                    只做一次低频页面请求，用于确认公开页是否可达、是否出现验证页、以及页面里是否存在可解析标记。
                  </div>
                </div>
                <button className="button button--primary" disabled={interfaceBusy}>
                  开始诊断
                </button>
              </form>
            }
            list={
              collectorDiagnostics ? (
                <article className="diagnostics-card">
                  <strong>
                    HTTP {collectorDiagnostics.status} ·{' '}
                    {collectorDiagnostics.title ?? '无标题'}
                  </strong>
                  <span>页面类型：{collectorDiagnostics.page_type}</span>
                  <span>目标 URL：{collectorDiagnostics.target_url}</span>
                  <span>最终 URL：{collectorDiagnostics.final_url}</span>
                  <span>
                    Content-Type：{collectorDiagnostics.content_type ?? '未知'}
                  </span>
                  <span>Meta 标题：{collectorDiagnostics.meta_title ?? '无'}</span>
                  <span>
                    Meta 描述：{collectorDiagnostics.meta_description ?? '无'}
                  </span>
                  <span>
                    Cookie：{collectorDiagnostics.cookie_profile_used ?? '未使用'}
                  </span>
                  <span>规范 URL：{collectorDiagnostics.canonical_url ?? '无'}</span>
                  <span>规范 noteId：{collectorDiagnostics.canonical_note_id ?? '无'}</span>
                  <span>规范 userId：{collectorDiagnostics.canonical_user_id ?? '无'}</span>
                  <p>
                    结构化块：Initial State {collectorDiagnostics.initial_state_blocks} / JSON-LD{' '}
                    {collectorDiagnostics.json_ld_blocks}
                  </p>
                  <p>
                    页面信号：
                    {[
                      collectorDiagnostics.page_signals.has_initial_state
                        ? ' INITIAL_STATE'
                        : null,
                      collectorDiagnostics.page_signals.has_json_ld ? ' JSON-LD' : null,
                      collectorDiagnostics.page_signals.has_note_cards ? ' NOTE_CARDS' : null,
                      collectorDiagnostics.page_signals.has_xsec_token ? ' XSEC_TOKEN' : null,
                      collectorDiagnostics.page_signals.looks_like_video ? ' VIDEO' : null,
                      collectorDiagnostics.page_signals.looks_like_image_gallery
                        ? ' IMAGE_GALLERY'
                        : null,
                      collectorDiagnostics.page_signals.auth_wall_detected ? ' AUTH_WALL' : null,
                      collectorDiagnostics.page_signals.challenge_detected ? ' CHALLENGE' : null,
                    ]
                      .filter(Boolean)
                      .join(' / ') || ' 无'}
                  </p>
                  <p>
                    标记命中：
                    {collectorDiagnostics.marker_hits.length > 0
                      ? collectorDiagnostics.marker_hits.join(' / ')
                      : ' 无'}
                  </p>
                  <p>
                    候选 noteId：
                    {collectorDiagnostics.note_id_candidates.length > 0
                      ? collectorDiagnostics.note_id_candidates.join(' / ')
                      : ' 无'}
                  </p>
                  <p>
                    候选 userId：
                    {collectorDiagnostics.user_id_candidates.length > 0
                      ? collectorDiagnostics.user_id_candidates.join(' / ')
                      : ' 无'}
                  </p>
                  <div className="candidate-grid">
                    <div>
                      <strong>笔记预览</strong>
                      {collectorDiagnostics.note_preview ? (
                        <div className="detail-stack">
                          <p>noteId：{collectorDiagnostics.note_preview.note_id ?? '无'}</p>
                          <p>标题：{collectorDiagnostics.note_preview.title ?? '无'}</p>
                          <p>作者：{collectorDiagnostics.note_preview.author ?? '无'}</p>
                          <p>
                            视频：{collectorDiagnostics.note_preview.has_video ? '是' : '否'}
                          </p>
                          <p>
                            图片数提示：
                            {collectorDiagnostics.note_preview.image_count_hint ?? '无'}
                          </p>
                          <p>
                            发布时间候选：
                            {collectorDiagnostics.note_preview.publish_time_candidates.length > 0
                              ? collectorDiagnostics.note_preview.publish_time_candidates.join(
                                  ' / ',
                                )
                              : ' 无'}
                          </p>
                          <p>
                            正文：
                            {collectorDiagnostics.note_preview.description ?? '无'}
                          </p>
                        </div>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                    <div>
                      <strong>主页预览</strong>
                      {collectorDiagnostics.profile_preview ? (
                        <div className="detail-stack">
                          <p>userId：{collectorDiagnostics.profile_preview.user_id ?? '无'}</p>
                          <p>昵称：{collectorDiagnostics.profile_preview.nickname ?? '无'}</p>
                          <p>
                            主页链接：
                            {collectorDiagnostics.profile_preview.profile_url ?? '无'}
                          </p>
                          <p>
                            最近笔记候选数：
                            {collectorDiagnostics.profile_preview.recent_note_count}
                          </p>
                        </div>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                  </div>
                  <div className="candidate-grid">
                    <div>
                      <strong>候选标题</strong>
                      {collectorDiagnostics.title_candidates.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.title_candidates.map((value) => (
                            <li key={value}>{value}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                    <div>
                      <strong>候选作者</strong>
                      {collectorDiagnostics.author_candidates.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.author_candidates.map((value) => (
                            <li key={value}>{value}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                  </div>
                  <div className="candidate-grid">
                    <div>
                      <strong>候选正文</strong>
                      {collectorDiagnostics.description_candidates.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.description_candidates.map((value) => (
                            <li key={value}>{value}</li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                    <div>
                      <strong>候选笔记卡片</strong>
                      {collectorDiagnostics.note_cards.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.note_cards.map((card) => (
                            <li key={card.url}>
                              <a href={card.url} rel="noreferrer" target="_blank">
                                {card.note_id ? `${card.note_id} · ` : ''}
                                {card.url}
                              </a>
                              {card.title_hint ? <p>{card.title_hint}</p> : null}
                              {card.author_hint || card.description_hint || card.xsec_token_present ? (
                                <small className="list-meta">
                                  {[
                                    card.author_hint,
                                    card.xsec_token_present ? 'xsec_token' : null,
                                    card.description_hint,
                                  ]
                                    .filter(Boolean)
                                    .join(' · ')}
                                </small>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                  </div>
                  <div className="candidate-grid">
                    <div>
                      <strong>候选笔记链接</strong>
                      {collectorDiagnostics.note_link_candidates.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.note_link_candidates.map((link) => (
                            <li key={link}>
                              <a href={link} rel="noreferrer" target="_blank">
                                {link}
                              </a>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                    <div>
                      <strong>候选用户链接</strong>
                      {collectorDiagnostics.user_link_candidates.length > 0 ? (
                        <ul className="candidate-list">
                          {collectorDiagnostics.user_link_candidates.map((link) => (
                            <li key={link}>
                              <a href={link} rel="noreferrer" target="_blank">
                                {link}
                              </a>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p>无</p>
                      )}
                    </div>
                  </div>
                  <pre>{collectorDiagnostics.html_excerpt}</pre>
                </article>
              ) : (
                <div className="empty-state">
                  <strong>还没有诊断结果</strong>
                  <p>先输入一个公开页面 URL，再决定是否附带 Cookie 做低风控探测。</p>
                </div>
              )
            }
          />

          <FormSection
            id="runs"
            title="任务运行记录"
            kicker="Run History"
            badge="最近 20 条"
            form={null}
            list={
              <DataList
                emptyTitle="还没有运行记录"
                emptyBody="触发一次手动同步预检后，这里会留下最近的运行状态。"
                items={jobRuns.map((run) => ({
                  title: `${run.job_name} · ${run.status}`,
                  meta: formatTimestamp(run.started_at),
                  note: run.error_message ?? '无错误信息',
                }))}
              />
            }
          />

          <FormSection
            id="accounts"
            title="监控账号"
            kicker="Targets"
            badge="平台固定为小红书"
            form={
              <form className="form-grid" onSubmit={handleAccount}>
                <InputField
                  label="显示名称"
                  value={accountForm.display_name}
                  onChange={(value) =>
                    setAccountForm((current) => ({ ...current, display_name: value }))
                  }
                  placeholder="例如：某博主"
                />
                <InputField
                  label="账号标识"
                  value={accountForm.account_handle}
                  onChange={(value) =>
                    setAccountForm((current) => ({ ...current, account_handle: value }))
                  }
                  placeholder="主页 handle 或唯一标识"
                />
                <InputField
                  label="主页链接"
                  value={accountForm.profile_url}
                  onChange={(value) =>
                    setAccountForm((current) => ({ ...current, profile_url: value }))
                  }
                  placeholder="https://www.xiaohongshu.com/..."
                  wide
                />
                <TextField
                  label="备注"
                  value={accountForm.notes}
                  onChange={(value) =>
                    setAccountForm((current) => ({ ...current, notes: value }))
                  }
                  placeholder="例如：先做单账号链路验证"
                  rows={3}
                />
                <button className="button button--primary" disabled={interfaceBusy}>
                  保存监控账号
                </button>
              </form>
            }
            list={
              <DataList
                emptyTitle="还没有监控账号"
                emptyBody="先录入 1 个账号，把抓取、摘要和 Bark 的主链路跑通。"
                items={accounts.map((account) => ({
                  title: `${account.display_name} · ${account.account_handle}`,
                  meta: account.profile_url ?? '未填写主页链接',
                  note: account.notes ?? '无备注',
                }))}
              />
            }
          />

          <FormSection
            id="cookies"
            title="Cookie 管理"
            kicker="Session Material"
            badge={securityReady ? '支持本地加密保存' : '等待安全存储启用'}
            form={
              <form className="form-grid" onSubmit={handleCookie}>
                <InputField
                  label="标签"
                  value={cookieForm.label}
                  onChange={(value) =>
                    setCookieForm((current) => ({ ...current, label: value }))
                  }
                  placeholder="例如：主账号 Cookie"
                />
                <TextField
                  label="Cookie 字符串"
                  value={cookieForm.cookie_value}
                  onChange={(value) =>
                    setCookieForm((current) => ({ ...current, cookie_value: value }))
                  }
                  placeholder="粘贴完整 Cookie"
                  rows={4}
                />
                <button
                  className="button button--primary"
                  disabled={interfaceBusy || !securityReady}
                >
                  保存 Cookie
                </button>
              </form>
            }
            list={
              <DataList
                emptyTitle="还没有 Cookie 配置"
                emptyBody="如果小红书需要登录态，先在这里录入 1 份低风险 Cookie。"
                items={cookieProfiles.map((cookie) => ({
                  title: cookie.label,
                  meta: cookie.cookie_preview,
                  note: cookie.platform,
                }))}
              />
            }
          />

          <FormSection
            id="models"
            title="模型配置"
            kicker="OpenAI-compatible Providers"
            badge="支持按任务分配不同模型"
            form={
              <form className="form-grid" onSubmit={handleProvider}>
                <InputField
                  label="名称"
                  value={providerForm.name}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, name: value }))
                  }
                  placeholder="例如：Primary Provider"
                />
                <InputField
                  label="Base URL"
                  value={providerForm.base_url}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, base_url: value }))
                  }
                  placeholder="https://example.com/v1"
                />
                <InputField
                  label="API Key"
                  value={providerForm.api_key}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, api_key: value }))
                  }
                  placeholder="sk-..."
                  type="password"
                  wide
                />
                <div className="field field--wide field-actions">
                  <span>模型发现</span>
                  <div className="inline-actions">
                    <button
                      className="button button--ghost"
                      disabled={interfaceBusy}
                      type="button"
                      onClick={() => void handleDiscoverModels()}
                    >
                      获取模型列表
                    </button>
                    {discoveredModels.length > 0 ? (
                      <small>已载入 {discoveredModels.length} 个候选模型</small>
                    ) : (
                      <small>先用当前 Base URL 和 API Key 拉取 /models</small>
                    )}
                  </div>
                </div>
                <InputField
                  label="摘要模型"
                  value={providerForm.summary_model}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, summary_model: value }))
                  }
                  placeholder="gpt-..."
                  listId={discoveredModels.length > 0 ? 'provider-model-options' : undefined}
                />
                <InputField
                  label="翻译模型"
                  value={providerForm.translation_model}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, translation_model: value }))
                  }
                  placeholder="gpt-..."
                  listId={discoveredModels.length > 0 ? 'provider-model-options' : undefined}
                />
                <InputField
                  label="OCR 模型"
                  value={providerForm.ocr_model}
                  onChange={(value) =>
                    setProviderForm((current) => ({ ...current, ocr_model: value }))
                  }
                  placeholder="vision model"
                  listId={discoveredModels.length > 0 ? 'provider-model-options' : undefined}
                />
                <InputField
                  label="转写模型"
                  value={providerForm.transcription_model}
                  onChange={(value) =>
                    setProviderForm((current) => ({
                      ...current,
                      transcription_model: value,
                    }))
                  }
                  placeholder="audio model"
                  listId={discoveredModels.length > 0 ? 'provider-model-options' : undefined}
                />
                <InputField
                  label="视频理解模型"
                  value={providerForm.understanding_model}
                  onChange={(value) =>
                    setProviderForm((current) => ({
                      ...current,
                      understanding_model: value,
                    }))
                  }
                  placeholder="analysis model"
                  wide
                  listId={discoveredModels.length > 0 ? 'provider-model-options' : undefined}
                />
                {discoveredModels.length > 0 ? (
                  <datalist id="provider-model-options">
                    {discoveredModels.map((model) => (
                      <option key={model} value={model} />
                    ))}
                  </datalist>
                ) : null}
                <label className="toggle">
                  <input
                    checked={providerForm.is_default}
                    type="checkbox"
                    onChange={(event) =>
                      setProviderForm((current) => ({
                        ...current,
                        is_default: event.target.checked,
                      }))
                    }
                  />
                  <span>设为默认提供方</span>
                </label>
                <button
                  className="button button--primary"
                  disabled={interfaceBusy || !securityReady}
                >
                  保存模型提供方
                </button>
              </form>
            }
            list={
              <DataList
                emptyTitle="还没有模型提供方"
                emptyBody="先保存 1 条兼容接口配置，后端才能继续接摘要、OCR 和转写能力。"
                items={modelProviders.map((provider) => ({
                  title: provider.name,
                  meta: `${provider.base_url} · ${provider.api_key_preview}`,
                  note:
                    [
                      provider.summary_model,
                      provider.translation_model,
                      provider.ocr_model,
                      provider.transcription_model,
                      provider.understanding_model,
                    ]
                      .filter(Boolean)
                      .join(' / ') || '未分配具体模型',
                }))}
              />
            }
          />

          <FormSection
            id="bark"
            title="Bark 配置"
            kicker="Push Delivery"
            badge="默认 iPhone Bark App 地址"
            form={
              <form className="form-grid" onSubmit={handleBark}>
                <InputField
                  label="标签"
                  value={barkForm.label}
                  onChange={(value) =>
                    setBarkForm((current) => ({ ...current, label: value }))
                  }
                />
                <InputField
                  label="推送地址"
                  value={barkForm.server_url}
                  onChange={(value) =>
                    setBarkForm((current) => ({ ...current, server_url: value }))
                  }
                />
                <InputField
                  label="设备 Key"
                  value={barkForm.device_key}
                  onChange={(value) =>
                    setBarkForm((current) => ({ ...current, device_key: value }))
                  }
                  type="password"
                  placeholder={
                    barkConfig
                      ? `已保存：${barkConfig.device_key_preview}`
                      : '输入 Bark 设备 Key'
                  }
                  wide
                />
                <label className="toggle">
                  <input
                    checked={barkForm.is_enabled}
                    type="checkbox"
                    onChange={(event) =>
                      setBarkForm((current) => ({
                        ...current,
                        is_enabled: event.target.checked,
                      }))
                    }
                  />
                  <span>启用 Bark 推送</span>
                </label>
                <button
                  className="button button--primary"
                  disabled={interfaceBusy || !securityReady}
                >
                  保存 Bark 配置
                </button>
              </form>
            }
            list={
              <DataList
                emptyTitle="还没有 Bark 配置"
                emptyBody="先保存 1 条 Bark 设备配置，后续手动和定时推送都会走它。"
                items={
                  barkConfig
                    ? [
                        {
                          title: barkConfig.label,
                          meta: barkConfig.server_url,
                          note: barkConfig.device_key_preview,
                        },
                      ]
                    : []
                }
              />
            }
          />
          <FormSection
            id="telegram"
            title="Telegram Config"
            kicker="Push Delivery"
            badge="Bot API"
            form={
              <form className="form-grid" onSubmit={handleTelegram}>
                <InputField
                  label="Label"
                  value={telegramForm.label}
                  onChange={(value) =>
                    setTelegramForm((current) => ({ ...current, label: value }))
                  }
                />
                <InputField
                  label="API Base URL"
                  value={telegramForm.api_base_url}
                  onChange={(value) =>
                    setTelegramForm((current) => ({ ...current, api_base_url: value }))
                  }
                  placeholder="https://api.telegram.org"
                />
                <InputField
                  label="Chat ID"
                  value={telegramForm.chat_id}
                  onChange={(value) =>
                    setTelegramForm((current) => ({ ...current, chat_id: value }))
                  }
                  placeholder="123456789 or @channel_name"
                />
                <InputField
                  label="Bot Token"
                  value={telegramForm.bot_token}
                  onChange={(value) =>
                    setTelegramForm((current) => ({ ...current, bot_token: value }))
                  }
                  type="password"
                  placeholder={
                    telegramConfig
                      ? `Saved: ${telegramConfig.bot_token_preview}`
                      : 'Enter Telegram bot token'
                  }
                  wide
                />
                <label className="toggle">
                  <input
                    checked={telegramForm.is_enabled}
                    type="checkbox"
                    onChange={(event) =>
                      setTelegramForm((current) => ({
                        ...current,
                        is_enabled: event.target.checked,
                      }))
                    }
                  />
                  <span>Enable Telegram push</span>
                </label>
                <div className="field field--wide field-actions">
                  <span>Verify</span>
                  <div className="inline-actions">
                    <button
                      className="button button--primary"
                      disabled={interfaceBusy || !securityReady}
                    >
                      Save Telegram config
                    </button>
                    <button
                      className="button button--ghost"
                      disabled={interfaceBusy || !securityReady || !telegramConfig}
                      type="button"
                      onClick={() => void handleTelegramTest()}
                    >
                      Send test message
                    </button>
                  </div>
                </div>
              </form>
            }
            list={
              <DataList
                emptyTitle="No Telegram config yet"
                emptyBody="Save one Telegram Bot configuration, then send a test message to verify delivery."
                items={
                  telegramConfig
                    ? [
                        {
                          title: telegramConfig.label,
                          meta: `${telegramConfig.api_base_url} · ${telegramConfig.chat_id}`,
                          note: telegramConfig.bot_token_preview,
                        },
                      ]
                    : []
                }
              />
            }
          />
        </main>
      </div>
    </div>
  )
}

function AuthShell({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="auth-shell">
      <div className="auth-panel">
        <div className="auth-copy">
          <p className="eyebrow">Local Control Surface</p>
          <h1>{title}</h1>
          <p className="lede">{subtitle}</p>
        </div>
      </div>
    </div>
  )
}

function FormSection({
  id,
  title,
  kicker,
  badge,
  form,
  list,
}: {
  id: string
  title: string
  kicker: string
  badge: string
  form: ReactNode
  list: ReactNode
}) {
  return (
    <section id={id} className="panel-card">
      <div className="section-head">
        <div>
          <p className="section-kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        <span className="status-chip">{badge}</span>
      </div>
      {form}
      {list}
    </section>
  )
}

function InputField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
  wide = false,
  listId,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  type?: 'text' | 'password'
  wide?: boolean
  listId?: string
}) {
  return (
    <label className={`field ${wide ? 'field--wide' : ''}`}>
      <span>{label}</span>
      <input
        list={listId}
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  rows,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
  rows: number
}) {
  return (
    <label className="field field--wide">
      <span>{label}</span>
      <textarea
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  )
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: Array<{ label: string; value: string }>
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={`${option.value}-${option.label}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

function readError(reason: unknown) {
  return reason instanceof Error ? reason.message : '出现了未预期的错误。'
}

function flag(value: boolean) {
  return value ? 'OK' : '缺失'
}

function formatTimestamp(value: number) {
  return new Date(value * 1000).toLocaleString('zh-CN', {
    hour12: false,
  })
}

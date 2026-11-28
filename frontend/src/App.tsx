
import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import {
  LayoutDashboard, CreditCard, ReceiptText, RefreshCw, ShieldCheck,
  Sparkles, Settings, Search, Bell, ArrowUpRight,
  Plus, MoreHorizontal, CalendarDays, Menu, X, ArrowRight,
  Activity, CircleHelp, SlidersHorizontal
} from 'lucide-react'
import './App.css'
import { api, money, dateLabel } from './lib/api'
import FinancialOrb from './components/FinancialOrb'
import BillSense from './components/BillSense'
import { Payments, Subscriptions, Recovery } from './components/WorkspaceModules'

const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'BillSense', icon: ReceiptText },
  { label: 'Payments', icon: CreditCard },
  { label: 'Subscriptions', icon: RefreshCw },
  { label: 'Recovery', icon: ShieldCheck },
]

type DashboardPayment = {
  id: string
  merchant: string
  provider: string
  amount: number
  currency: string
  category: string
  payment_date: string
  status: string
  transaction_ref?: string
}

type DashboardRenewal = {
  subscription_id: string
  name: string
  amount: number
  currency: string
  due_date: string
  days_remaining: number
}

function App() {
  const [active, setActive] = useState('Overview')
  const [period, setPeriod] = useState('This month')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notifications, setNotifications] = useState(false)

  const [dashboardPayments, setDashboardPayments] = useState<DashboardPayment[]>([])
  const [dashboardRenewals, setDashboardRenewals] = useState<DashboardRenewal[]>([])
  const [dashboardLoading, setDashboardLoading] = useState(true)
  const [dashboardError, setDashboardError] = useState('')

  useEffect(() => {
    let alive = true

    async function loadDashboard() {
      setDashboardLoading(true)
      setDashboardError('')

      const results = await Promise.allSettled([
        api<{ items: DashboardPayment[]; total: number }>(
          '/api/payments?limit=100&offset=0'
        ),
        api<{ upcoming_payments?: DashboardRenewal[] }>(
          '/api/subscriptions/summary'
        ),
      ])

      if (!alive) return

      const paymentResult = results[0]
      const renewalResult = results[1]
      const errors: string[] = []

      if (paymentResult.status === 'fulfilled') {
        setDashboardPayments(paymentResult.value.items || [])
      } else {
        setDashboardPayments([])
        errors.push(`Payments: ${paymentResult.reason?.message || 'Unable to load'}`)
      }

      if (renewalResult.status === 'fulfilled') {
        setDashboardRenewals(renewalResult.value.upcoming_payments || [])
      } else {
        setDashboardRenewals([])
        errors.push(`Renewals: ${renewalResult.reason?.message || 'Unable to load'}`)
      }

      setDashboardError(errors.join(' | '))
      setDashboardLoading(false)
    }

    loadDashboard()

    return () => {
      alive = false
    }
  }, [])

  const now = new Date()
  const periodStart = new Date(now)

  if (period === 'Last month') {
    periodStart.setDate(1)
    periodStart.setMonth(periodStart.getMonth() - 1)
  } else if (period === 'Last 7 days') {
    periodStart.setDate(periodStart.getDate() - 6)
  } else {
    periodStart.setDate(1)
  }

  const periodEnd = new Date(now)
  if (period === 'Last month') {
    periodEnd.setDate(0)
  }

  const periodPayments = dashboardPayments.filter(payment => {
    if (payment.status?.toLowerCase() !== 'completed') return false
    const date = new Date(payment.payment_date)
    return !Number.isNaN(date.getTime()) &&
      date >= periodStart &&
      date <= periodEnd
  })

  const periodSpend = periodPayments.reduce(
    (total, payment) => total + Number(payment.amount || 0),
    0
  )

  const upcomingTotal = dashboardRenewals.reduce(
    (total, renewal) => total + Number(renewal.amount || 0),
    0
  )

  const dashboardTransactions = dashboardPayments.slice(0, 5).map(payment => ({
    id: payment.id,
    name: payment.merchant,
    category: payment.category || payment.provider,
    date: dateLabel(payment.payment_date),
    amount: `−${money(payment.amount, payment.currency || 'INR')}`,
    icon: (payment.merchant || '?').slice(0, 1).toUpperCase(),
    color: 'blue',
    status: payment.status,
  }))

  const categoryTotals = periodPayments.reduce<Record<string, number>>(
    (totals, payment) => {
      const category = payment.category || 'other'
      totals[category] = (totals[category] || 0) + Number(payment.amount || 0)
      return totals
    },
    {}
  )

  const largestCategory = Math.max(1, ...Object.values(categoryTotals))

  const pageTitle = active === 'Overview' ? 'Your financial command centre.' : active

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-symbol"><span /></div>
          <span>pay<span className="brand-light">pause</span></span>
          <button className="mobile-close" onClick={() => setMobileOpen(false)}><X size={19}/></button>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace">
          <div className="workspace-avatar">A</div>
          <div className="workspace-copy">
            <strong>Personal space</strong>
            <span>Free plan</span>
          </div>
        </div>

        <div className="nav-label">MENU</div>
        <nav className="main-nav">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              onClick={() => { setActive(label); setMobileOpen(false) }}
              className={`nav-item ${active === label ? 'active' : ''}`}
            >
              <Icon size={18} strokeWidth={1.8}/>
              <span>{label}</span>
              {label === 'Recovery' && <span className="nav-count">2</span>}
              {active === label && <span className="nav-indicator"/>}
            </button>
          ))}
        </nav>

        <div className="nav-label tools-label">INTELLIGENCE</div>
        <button
          className={`nav-item ${active === 'AI Assistant' ? 'active' : ''}`}
          onClick={() => setActive('AI Assistant')}
        >
          <Sparkles size={18}/>
          <span>AI Assistant</span>
          <span className="ai-tag">AI</span>
        </button>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => setActive('Settings')}>
            <Settings size={18}/>
            <span>Settings</span>
          </button>
          <button className="nav-item" onClick={() => setActive('Help')}>
            <CircleHelp size={18}/>
            <span>Help & support</span>
          </button>
          <div className="profile">
            <div className="profile-avatar">AA</div>
            <div className="profile-copy">
              <strong>Ayush Aryaman</strong>
              <span>Personal account</span>
            </div>
            <MoreHorizontal size={19} className="muted"/>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="mobile-overlay" onClick={() => setMobileOpen(false)}/>
      )}

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <button className="mobile-menu" onClick={() => setMobileOpen(true)}>
              <Menu size={21}/>
            </button>
            <span>Workspace</span>
            <span className="crumb-slash">/</span>
            <strong>{active}</strong>
          </div>

          <div className="top-actions">
            <button className="search-button" onClick={() => setActive('Search')}>
              <Search size={16}/>
              <span>Search anything</span>
              <kbd>Ctrl + K</kbd>
            </button>

            <div className="notification-wrap">
              <button
                className="icon-button notification-button"
                onClick={() => setNotifications(!notifications)}
              >
                <Bell size={18}/>
                <i/>
              </button>
              {notifications && (
                <div className="notification-popover">
                  <strong>Notifications</strong>
                  <p>Open your workspace to review your latest records.</p>
                  <p>Review the Recovery workspace for reported incidents.</p>
                </div>
              )}
            </div>

            <div className="top-avatar">AA</div>
          </div>
        </header>

        <div className={`page-content ${active === 'BillSense' ? 'billsense-mode' : ''}`}>
          <motion.div
            className="welcome-row"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .5 }}
          >
            <div>
              <div className="eyebrow">
                <span className="live-dot"/> YOUR MONEY, IN CONTROL
              </div>
              <h1>
                {active === 'Overview'
                  ? <>Good evening, <span>Ayush.</span></>
                  : pageTitle}
              </h1>
              <p className="welcome-subtitle">
                {active === 'Overview'
                  ? 'A clearer picture of your financial life starts here.'
                  : `Your ${active.toLowerCase()} workspace. More clarity, less financial friction.`}
              </p>
            </div>
            <button className="primary-button" onClick={() => setActive('Payments')}>
              <Plus size={17}/> New payment
            </button>
          </motion.div>

          {active === 'BillSense' && <BillSense />}
          {active === 'Payments' && <Payments />}
          {active === 'Subscriptions' && <Subscriptions />}
          {active === 'Recovery' && <Recovery />}

          {['AI Assistant', 'Plans', 'Settings', 'Help', 'Search'].includes(active) && (
            <div className="module-notice">
              <Sparkles size={20}/>
              <div>
                <strong>{active}</strong>
                <p>This workspace will be connected when its dedicated backend functionality is available.</p>
              </div>
            </div>
          )}

          {active === 'Overview' && (
            <>
              <motion.section
                className="hero-grid"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: .1, duration: .55 }}
              >
                <div className="balance-card">
                  <div className="balance-top">
                    <div>
                      <span className="card-overline">ACCOUNT BALANCE</span>
                      <div className="balance-value">Not linked</div>
                    </div>
                    <div className="balance-chip"><Activity size={13}/> No bank connection</div>
                  </div>

                  <div className="balance-bottom">
                    <div>
                      <span className="balance-caption">Compared to last month</span>
                      <div className="positive-change">
                        <span>Balance trends unavailable</span>
                      </div>
                    </div>
                    <div className="orb-scene" aria-hidden="true">
                      <FinancialOrb />
                    </div>
                  </div>
                  <div className="balance-glow"/>
                </div>

                <div className="stat-card">
                  <div className="stat-heading">
                    <span>MONTHLY SPENDING</span>
                    <div className="stat-icon violet"><ArrowUpRight size={17}/></div>
                  </div>
                  <div className="stat-value">{dashboardLoading ? "Loading..." : money(periodSpend)}</div>
                  <div className="stat-foot">
                    <span className="neutral-change">{periodPayments.length} completed</span>
                    <span>recorded in selected period</span>
                  </div>
                </div>

                <div className="stat-card">
                  <div className="stat-heading">
                    <span>UPCOMING BILLS</span>
                    <div className="stat-icon cyan"><CalendarDays size={17}/></div>
                  </div>
                  <div className="stat-value">{dashboardLoading ? "Loading..." : money(upcomingTotal)}</div>
                  <div className="stat-foot">
                    <span className="neutral-change">{dashboardRenewals.length} upcoming</span>
                    <span>due this week</span>
                  </div>
                  {dashboardRenewals.slice(0, 2).map(renewal => (
                    <div className="upcoming-line" key={renewal.subscription_id}>
                      <div className="upcoming-icon">{renewal.name.slice(0, 1).toUpperCase()}</div>
                      <div><strong>{renewal.name}</strong><span>{dateLabel(renewal.due_date)}</span></div>
                      <b>{money(renewal.amount, renewal.currency || "INR")}</b>
                    </div>
                  ))}
                  {!dashboardLoading && dashboardRenewals.length === 0 && <p>No upcoming renewals recorded.</p>}
                </div>
              </motion.section>

              <section className="middle-grid">
                <motion.div
                  className="panel spending-panel"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: .2 }}
                >
                  <div className="panel-heading">
                    <div>
                      <div className="panel-kicker">YOUR MONEY FLOW</div>
                      <h2>Spending analytics</h2>
                      <p>Completed payments for the selected period.</p>
                    </div>
                    <select
                      value={period}
                      onChange={e => setPeriod(e.target.value)}
                      className="period-select"
                    >
                      <option>This month</option>
                      <option>Last month</option>
                      <option>Last 7 days</option>
                    </select>
                  </div>

                  <div className="chart-summary">
                    <div><span>Total spent</span><strong>{dashboardLoading ? "Loading..." : money(periodSpend)}</strong></div>
                    <div className="chart-legend"><i/> Spending</div>
                  </div>
                                    <div className="echarts-spending">
                    {Object.entries(categoryTotals).length === 0 ? (
                      <p>No completed payments in this period.</p>
                    ) : (
                      Object.entries(categoryTotals)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 6)
                        .map(([category, amount]) => (
                          <div key={category} style={{ marginBottom: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                              <span>{category.replaceAll('_', ' ')}</span>
                              <strong>{money(amount)}</strong>
                            </div>
                            <div style={{ height: 6, background: 'rgba(127,127,127,.18)', borderRadius: 8, overflow: 'hidden', marginTop: 5 }}>
                              <div style={{ height: '100%', width: `${Math.min(100, amount / largestCategory * 100)}%`, background: 'var(--accent, #8b7cf6)', borderRadius: 8 }} />
                            </div>
                          </div>
                        ))
                    )}
                  </div>
                  <div className="chart-footer">
                    <span>{period}</span>
                    <span><span className="footer-dot"/> Completed recorded payments</span>
                  </div>
                </motion.div>

                <motion.div
                  className="panel insights-panel"
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: .3 }}
                >
                  <div className="panel-heading">
                    <div>
                      <div className="panel-kicker">SMART INTELLIGENCE</div>
                      <h2>PayPause insights</h2>
                      <p>Small changes. Better finances.</p>
                    </div>
                    <div className="insight-spark"><Sparkles size={17}/></div>
                  </div>

                  <div className="insight-feature">
                    <div className="insight-orb"><Sparkles size={21}/></div>
                    <div>
                      <span className="insight-label">OPPORTUNITY DETECTED</span>
                      <h3>Potential savings opportunity</h3>
                      <p>We spotted recurring subscriptions you may not be using.</p>
                    </div>
                  </div>

                  <div className="insight-divider"/>
                  <div className="insight-row">
                    <div className="insight-row-icon"><RefreshCw size={16}/></div>
                    <div><strong>Subscription check</strong><span>Review 2 recurring payments</span></div>
                    <ArrowRight size={16}/>
                  </div>
                  <div className="insight-row">
                    <div className="insight-row-icon"><ShieldCheck size={16}/></div>
                    <div><strong>Payment protection</strong><span>Review your recorded payment activity</span></div>
                    <ArrowRight size={16}/>
                  </div>
                  <button className="insight-action" onClick={() => setActive('AI Assistant')}>
                    Explore AI insights <ArrowUpRight size={15}/>
                  </button>
                </motion.div>
              </section>

              <motion.section
                className="panel transactions-panel"
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: .4 }}
              >
                <div className="transactions-heading">
                  <div>
                    <div className="panel-kicker">RECENT ACTIVITY</div>
                    <h2>Recent transactions</h2>
                    <p>Recent payments recorded in PayPause.</p>
                  </div>
                  <div className="transaction-actions">
                    <button className="filter-button"><SlidersHorizontal size={15}/> Filter</button>
                    <button className="text-button" onClick={() => setActive('Payments')}>
                      View all <ArrowRight size={15}/>
                    </button>
                  </div>
                </div>

                {dashboardError && <p role="alert">{dashboardError}</p>}
                {dashboardLoading && <p>Loading dashboard records...</p>}
                <div className="transaction-table">
                  <div className="transaction-head">
                    <span>TRANSACTION</span><span>DATE</span><span>AMOUNT</span><span>STATUS</span><span/>
                  </div>
                  {dashboardTransactions.map((t) => (
                    <div className="transaction-row" key={t.id}>
                      <div className="transaction-name">
                        <div className={`merchant-icon ${t.color}`}>{t.icon}</div>
                        <div><strong>{t.name}</strong><span>{t.category}</span></div>
                      </div>
                      <span className="transaction-date">{t.date}</span>
                      <strong className={`transaction-amount ${t.amount.startsWith('+') ? 'income' : ''}`}>
                        {t.amount}
                      </strong>
                      <span className="status-pill"><i/>{t.status}</span>
                      <button className="row-more"><MoreHorizontal size={18}/></button>
                    </div>
                  ))}
                </div>
              </motion.section>

              <footer className="footer">
                <span>© 2026 PayPause Technologies</span>
                <span><i/> Preview data — API verification required</span>
                <span>Built for financial clarity.</span>
              </footer>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
import { useState } from 'react'
import { motion } from 'motion/react'
import {
  LayoutDashboard, CreditCard, ReceiptText, RefreshCw, ShieldCheck,
  Sparkles, Settings, Search, Bell, ChevronDown, ArrowUpRight,
  Plus, MoreHorizontal, TrendingUp, CalendarDays, Menu, X, ArrowRight,
  Zap, Activity, CircleHelp, SlidersHorizontal
} from 'lucide-react'
import './App.css'
import FinancialOrb from './components/FinancialOrb'
import SpendingChart from './components/SpendingChart'
import BillSense from './components/BillSense'
import { Payments, Subscriptions, Recovery } from './components/WorkspaceModules'

const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'BillSense', icon: ReceiptText },
  { label: 'Payments', icon: CreditCard },
  { label: 'Subscriptions', icon: RefreshCw },
  { label: 'Recovery', icon: ShieldCheck },
]

const transactions = [
  { name: 'Netflix Premium', category: 'Entertainment', date: 'Today, 10:42 AM', amount: '-â‚¹649', icon: 'N', color: 'red', status: 'Completed' },
  { name: 'Spotify', category: 'Music subscription', date: 'Today, 09:18 AM', amount: '-â‚¹119', icon: 'S', color: 'green', status: 'Completed' },
  { name: 'Amazon India', category: 'Shopping', date: 'Yesterday', amount: '-â‚¹2,499', icon: 'a', color: 'orange', status: 'Completed' },
  { name: 'Salary credited', category: 'Income', date: 'Nov 25, 2026', amount: '+â‚¹65,000', icon: 'â‚¹', color: 'blue', status: 'Received' },
]

function App() {
  const [active, setActive] = useState('Overview')
  const [period, setPeriod] = useState('This month')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notifications, setNotifications] = useState(false)

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
          <div className="workspace-copy"><strong>Personal space</strong><span>Free plan</span></div>
          <ChevronDown size={15} className="muted"/>
        </div>

        <div className="nav-label">MENU</div>
        <nav className="main-nav">
          {navigation.map(({ label, icon: Icon }) => (
            <button key={label} onClick={() => { setActive(label); setMobileOpen(false) }} className={`nav-item ${active === label ? 'active' : ''}`}>
              <Icon size={18} strokeWidth={1.8}/>
              <span>{label}</span>
              {label === 'Recovery' && <span className="nav-count">2</span>}
              {active === label && <span className="nav-indicator"/>}
            </button>
          ))}
        </nav>

        <div className="nav-label tools-label">INTELLIGENCE</div>
        <button className={`nav-item ${active === 'AI Assistant' ? 'active' : ''}`} onClick={() => setActive('AI Assistant')}>
          <Sparkles size={18}/><span>AI Assistant</span><span className="ai-tag">AI</span>
        </button>

        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <div className="upgrade-icon"><Zap size={17}/></div>
            <strong>Take control of your money.</strong>
            <p>Unlock smarter insights and automated protection.</p>
            <button onClick={() => setActive('Plans')}>Explore plans <ArrowRight size={14}/></button>
          </div>
          <button className="nav-item" onClick={() => setActive('Settings')}><Settings size={18}/><span>Settings</span></button>
          <button className="nav-item" onClick={() => setActive('Help')}><CircleHelp size={18}/><span>Help & support</span></button>
          <div className="profile">
            <div className="profile-avatar">AA</div>
            <div className="profile-copy"><strong>Ayush Aryaman</strong><span>Personal account</span></div>
            <MoreHorizontal size={19} className="muted"/>
          </div>
        </div>
      </aside>

      {mobileOpen && <div className="mobile-overlay" onClick={() => setMobileOpen(false)}/>}

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb">
            <button className="mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={21}/></button>
            <span>Workspace</span><span className="crumb-slash">/</span><strong>{active}</strong>
          </div>
          <div className="top-actions">
            <button className="search-button" onClick={() => setActive('Search')}><Search size={16}/><span>Search anything</span><kbd>âŒ˜ K</kbd></button>
            <div className="notification-wrap">
              <button className="icon-button notification-button" onClick={() => setNotifications(!notifications)}><Bell size={18}/><i/></button>
              {notifications && <div className="notification-popover"><strong>Notifications</strong><p>Your financial overview is up to date.</p><p>2 recovery items need attention.</p></div>}
            </div>
            <div className="top-avatar">AA</div>
          </div>
        </header>

        <div className={`page-content ${active === 'BillSense' ? 'billsense-mode' : ''}`}>
          <motion.div className="welcome-row" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .5 }}>
            <div>
              <div className="eyebrow"><span className="live-dot"/> YOUR MONEY, IN CONTROL</div>
              <h1>{active === 'Overview' ? <>Good evening, <span>Ayush.</span></> : pageTitle}</h1>
              <p className="welcome-subtitle">{active === 'Overview' ? 'A clearer picture of your financial life starts here.' : `Your ${active.toLowerCase()} workspace. More clarity, less financial friction.`}</p>
            </div>
            <button className="primary-button" onClick={() => setActive('Payments')}><Plus size={17}/> New payment</button>
          </motion.div>

          {active === 'BillSense' && <BillSense />}
          {active === 'Payments' && <Payments />}
          {active === 'Subscriptions' && <Subscriptions />}
          {active === 'Recovery' && <Recovery />}
          {['AI Assistant','Plans','Settings','Help','Search'].includes(active) && (
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

          {active !== 'Overview' && active !== 'BillSense' && (
            <motion.div className="module-notice" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Sparkles size={20}/><div><strong>{active} workspace</strong><p>This section is ready for its dedicated module. The overview below is our initial dashboard preview.</p></div>
            </motion.div>
          )}

          <motion.section className="hero-grid" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .1, duration: .55 }}>
            <div className="balance-card">
              <div className="balance-top">
                <div><span className="card-overline">TOTAL AVAILABLE BALANCE</span><div className="balance-value">â‚¹84,<span>250</span><small>.00</small></div></div>
                <div className="balance-chip"><Activity size={13}/> Live overview</div>
              </div>
              <div className="balance-bottom">
                <div><span className="balance-caption">Compared to last month</span><div className="positive-change"><TrendingUp size={14}/> +12.8% <span>this month</span></div></div>
                <div className="orb-scene" aria-hidden="true">
                  <FinancialOrb />
                </div>
              </div>
              <div className="balance-glow"/>
            </div>

            <div className="stat-card">
              <div className="stat-heading"><span>MONTHLY SPENDING</span><div className="stat-icon violet"><ArrowUpRight size={17}/></div></div>
              <div className="stat-value">â‚¹18,420</div>
              <div className="stat-foot"><span className="positive-change"><TrendingUp size={13}/> 8.2%</span><span>less than last month</span></div>
              <div className="mini-bars">{[32,48,38,65,45,70,54,85,58,73,46,62,82,53,68,45,78,57,91,65].map((h,i)=><i key={i} style={{height:`${h}%`}}/>)}</div>
            </div>

            <div className="stat-card">
              <div className="stat-heading"><span>UPCOMING BILLS</span><div className="stat-icon cyan"><CalendarDays size={17}/></div></div>
              <div className="stat-value">â‚¹3,249</div>
              <div className="stat-foot"><span className="neutral-change">3 payments</span><span>due this week</span></div>
              <div className="upcoming-line"><div className="upcoming-icon netflix">N</div><div><strong>Netflix</strong><span>Tomorrow</span></div><b>â‚¹649</b></div>
              <div className="upcoming-line"><div className="upcoming-icon spotify">S</div><div><strong>Spotify</strong><span>Nov 30</span></div><b>â‚¹119</b></div>
            </div>
          </motion.section>

          <section className="middle-grid">
            <motion.div className="panel spending-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .2 }}>
              <div className="panel-heading">
                <div><div className="panel-kicker">YOUR MONEY FLOW</div><h2>Spending analytics</h2><p>Track where your money goes.</p></div>
                <select value={period} onChange={e => setPeriod(e.target.value)} className="period-select"><option>This month</option><option>Last month</option><option>Last 7 days</option></select>
              </div>
              <div className="chart-summary"><div><span>Total spent</span><strong>â‚¹18,420</strong></div><div className="chart-legend"><i/> Spending</div></div>
              <div className="echarts-spending">
                <SpendingChart />
              </div>              <div className="chart-footer"><span>November 2026</span><span><span className="footer-dot"/> Daily expenditure</span></div>
            </motion.div>

            <motion.div className="panel insights-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .3 }}>
              <div className="panel-heading"><div><div className="panel-kicker">SMART INTELLIGENCE</div><h2>PayPause insights</h2><p>Small changes. Better finances.</p></div><div className="insight-spark"><Sparkles size={17}/></div></div>
              <div className="insight-feature">
                <div className="insight-orb"><Sparkles size={21}/></div>
                <div><span className="insight-label">OPPORTUNITY DETECTED</span><h3>You could save â‚¹768</h3><p>We spotted recurring subscriptions you may not be using.</p></div>
              </div>
              <div className="insight-divider"/>
              <div className="insight-row"><div className="insight-row-icon"><RefreshCw size={16}/></div><div><strong>Subscription check</strong><span>Review 2 recurring payments</span></div><ArrowRight size={16}/></div>
              <div className="insight-row"><div className="insight-row-icon"><ShieldCheck size={16}/></div><div><strong>Payment protection</strong><span>Your payment monitoring is active</span></div><ArrowRight size={16}/></div>
              <button className="insight-action" onClick={() => setActive('AI Assistant')}>Explore AI insights <ArrowUpRight size={15}/></button>
            </motion.div>
          </section>

          <motion.section className="panel transactions-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .4 }}>
            <div className="transactions-heading">
              <div><div className="panel-kicker">RECENT ACTIVITY</div><h2>Recent transactions</h2><p>Your latest financial movements.</p></div>
              <div className="transaction-actions"><button className="filter-button"><SlidersHorizontal size={15}/> Filter</button><button className="text-button" onClick={() => setActive('Payments')}>View all <ArrowRight size={15}/></button></div>
            </div>
            <div className="transaction-table">
              <div className="transaction-head"><span>TRANSACTION</span><span>DATE</span><span>AMOUNT</span><span>STATUS</span><span/></div>
              {transactions.map((t,i)=><div className="transaction-row" key={i}>
                <div className="transaction-name"><div className={`merchant-icon ${t.color}`}>{t.icon}</div><div><strong>{t.name}</strong><span>{t.category}</span></div></div>
                <span className="transaction-date">{t.date}</span>
                <strong className={`transaction-amount ${t.amount.startsWith('+')?'income':''}`}>{t.amount}</strong>
                <span className="status-pill"><i/>{t.status}</span>
                <button className="row-more"><MoreHorizontal size={18}/></button>
              </div>)}
            </div>
          </motion.section>

          <footer className="footer"><span>© 2026 PayPause Technologies</span><span><i/> All systems operational</span><span>Built for financial clarity.</span></footer>
          </>)}
        </div>
      </main>
    </div>
  )
}

export default App

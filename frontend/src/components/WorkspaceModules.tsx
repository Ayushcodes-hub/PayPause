import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { motion } from 'motion/react'
import {
  Activity, AlertCircle, ArrowDownLeft, ArrowRight, ArrowUpRight,
  CalendarDays, Check, CheckCircle2, Clock3,
  CreditCard, FileText, Filter, LoaderCircle, Plus, RefreshCw,
  Search, ShieldAlert, ShieldCheck, Trash2, Wallet, X, Zap,
} from 'lucide-react'
import { api, money, dateLabel } from '../lib/api'
import './WorkspaceModules.css'

type Payment = {
  id: string
  transaction_ref?: string
  provider: string
  merchant: string
  amount: number
  currency: string
  category: string
  payment_date: string
  status: string
  refund_status: string
  refund_reference?: string
  notes?: string
}

type Subscription = {
  id: string
  name: string
  amount: number
  currency: string
  frequency: string
  start_date: string
  next_expected_date: string
  category: string
  provider?: string
  is_active: boolean
  monthly_equivalent_cost: number
  cancellation_reminder_days: number
  notes?: string
}

type Incident = {
  id: string
  category: string
  incident_datetime: string
  provider: string
  transaction_ref?: string
  amount: number
  currency: string
  description: string
  status: string
  follow_up_date?: string
  evidence_references: any[]
  timeline: any[]
}

type Summary = Record<string, any>

function useWorkspace<T>(
  endpoint: string,
  initial: T
) {
  const [data, setData] = useState<T>(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => setRefreshKey(v => v + 1), [])

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')

    api<T>(endpoint)
      .then(value => {
        if (alive) setData(value)
      })
      .catch(err => {
        if (alive) setError(err.message || 'Unable to load data.')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })

    return () => { alive = false }
  }, [endpoint, refreshKey])

  return { data, setData, loading, error, refresh }
}

function PageHeading({
  eyebrow, title, description, action
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="wm-heading">
      <div>
        <div className="wm-eyebrow"><span />{eyebrow}</div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

function Metric({
  label, value, detail, icon: Icon, tone = 'blue'
}: {
  label: string
  value: string
  detail: string
  icon: any
  tone?: string
}) {
  return (
    <motion.div className="wm-metric" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <div className={`wm-metric-icon ${tone}`}><Icon size={19}/></div>
      <span className="wm-metric-label">{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </motion.div>
  )
}

function Notice({ error, onRetry }: { error: string; onRetry: () => void }) {
  if (!error) return null
  return (
    <div className="wm-error">
      <AlertCircle size={18}/>
      <span>{error}</span>
      <button onClick={onRetry}>Retry</button>
    </div>
  )
}

function Loading() {
  return <div className="wm-loading"><LoaderCircle size={22}/> Loading your financial data...</div>
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="wm-empty">
      <div><Wallet size={24}/></div>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  )
}

function Modal({
  title, close, children
}: {
  title: string
  close: () => void
  children: ReactNode
}) {
  return (
    <div className="wm-modal-backdrop" onMouseDown={e => {
      if (e.target === e.currentTarget) close()
    }}>
      <motion.div className="wm-modal" initial={{ opacity: 0, y: 18, scale: .98 }} animate={{ opacity: 1, y: 0 }}>
        <div className="wm-modal-heading">
          <h3>{title}</h3>
          <button onClick={close} aria-label="Close"><X size={19}/></button>
        </div>
        {children}
      </motion.div>
    </div>
  )
}

function Field({
  label, children
}: { label: string; children: ReactNode }) {
  return <label className="wm-field"><span>{label}</span>{children}</label>
}

function Input({
  label, ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <Field label={label}><input {...props}/></Field>
}

function SelectField({
  label, children, ...props
}: React.SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  children: ReactNode
}) {
  return <Field label={label}><select {...props}>{children}</select></Field>
}

function FormActions({
  busy, close, label = 'Save'
}: { busy: boolean; close: () => void; label?: string }) {
  return (
    <div className="wm-form-actions">
      <button type="button" className="wm-secondary" onClick={close}>Cancel</button>
      <button className="wm-primary" disabled={busy}>
        {busy ? <LoaderCircle size={16} className="wm-spin"/> : <Check size={16}/>}
        {busy ? 'Saving...' : label}
      </button>
    </div>
  )
}

// ============================================================
// PAYMENTS
// ============================================================

export function Payments() {
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const { data: list, loading, error, refresh } =
    useWorkspace<{ items: Payment[]; total: number }>('/api/payments?limit=100&offset=0', { items: [], total: 0 })
  const { data: summary, refresh: refreshSummary } =
    useWorkspace<Summary>('/api/payments/summary', {})

  const [form, setForm] = useState({
    provider: 'UPI',
    merchant: '',
    amount: '',
    currency: 'INR',
    category: 'general',
    payment_date: new Date().toISOString().slice(0, 10),
    status: 'completed',
    transaction_ref: '',
    notes: '',
  })

  const rows = (list.items || []).filter(p => {
    const matchesFilter = filter === 'all' ||
      (filter === 'refunds' ? p.refund_status !== 'not_requested' : p.status === filter)
    const matchesSearch = `${p.merchant} ${p.provider} ${p.transaction_ref || ''} ${p.category}`
      .toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  async function createPayment(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setFormError('')
    try {
      await api('/api/payments', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          amount: Number(form.amount),
          transaction_ref: form.transaction_ref || null,
          notes: form.notes || null,
        }),
      })
      setShowForm(false)
      setForm(f => ({ ...f, merchant: '', amount: '', transaction_ref: '', notes: '' }))
      refresh()
      refreshSummary()
    } catch (err: any) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function updateRefund(payment: Payment) {
    const next = payment.refund_status === 'not_requested' ? 'requested' : 'processing'
    if (!confirm(`Update refund status for ${payment.merchant} to "${next}"?`)) return
    try {
      await api(`/api/payments/${payment.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ refund_status: next }),
      })
      refresh()
      refreshSummary()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="wm-page">
      <PageHeading
        eyebrow="PAYMENT INTELLIGENCE"
        title="Every transaction. One clear picture."
        description="Track your payments, understand your spending and stay on top of refunds."
        action={<button className="wm-primary" onClick={() => setShowForm(true)}><Plus size={17}/> Add payment</button>}
      />

      <div className="wm-metrics">
        <Metric label="TOTAL TRANSACTIONS" value={String(summary.total_transactions ?? list.total ?? 0)} detail="Recorded payments" icon={CreditCard}/>
        <Metric label="TOTAL SPENDING" value={money(summary.total_spend || 0)} detail="Across recorded transactions" icon={Wallet} tone="violet"/>
        <Metric label="PENDING REFUNDS" value={String(summary.pending_refunds_count ?? 0)} detail="Awaiting resolution" icon={RefreshCw} tone="amber"/>
        <Metric label="REFUND VALUE" value={money(summary.pending_refunds_amount || 0)} detail="Currently pending" icon={ArrowDownLeft} tone="green"/>
      </div>

      <Notice error={error} onRetry={() => { refresh(); refreshSummary() }}/>

      <section className="wm-panel">
        <div className="wm-panel-head">
          <div><span className="wm-panel-kicker">TRANSACTION LEDGER</span><h3>Payment history</h3><p>{list.total || 0} recorded transactions</p></div>
          <div className="wm-search"><Search size={16}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search merchant, UTR..."/></div>
        </div>

        <div className="wm-toolbar">
          <div className="wm-tabs">
            {[['all','All'],['completed','Completed'],['pending','Pending'],['failed','Failed'],['refunds','Refunds']].map(([key,label]) =>
              <button key={key} className={filter === key ? 'selected' : ''} onClick={() => setFilter(key)}>{label}</button>
            )}
          </div>
          <span className="wm-result-count"><Filter size={14}/> {rows.length} results</span>
        </div>

        {loading ? <Loading/> : rows.length === 0 ? (
          <Empty title="No payments found" detail="Add a payment to start building your transaction history."/>
        ) : (
          <div className="wm-table-wrap">
            <table className="wm-table">
              <thead><tr><th>MERCHANT</th><th>PROVIDER</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th><th>REFUND</th><th/></tr></thead>
              <tbody>
                {rows.map(p => (
                  <tr key={p.id}>
                    <td><strong>{p.merchant}</strong><small>{p.transaction_ref || p.category}</small></td>
                    <td>{p.provider}</td>
                    <td>{dateLabel(p.payment_date)}</td>
                    <td className="wm-amount">{money(p.amount, p.currency)}</td>
                    <td><span className={`wm-status ${p.status}`}>{p.status}</span></td>
                    <td>
                      {p.refund_status === 'not_requested'
                        ? <button className="wm-inline-action" onClick={() => updateRefund(p)}>Request</button>
                        : <span className={`wm-status ${p.refund_status}`}>{p.refund_status.replaceAll('_',' ')}</span>}
                    </td>
                    <td><button className="wm-icon-action" title="Update refund" onClick={() => updateRefund(p)}><ArrowUpRight size={16}/></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="wm-lower-grid">
        <div className="wm-panel">
          <span className="wm-panel-kicker">SPENDING BREAKDOWN</span>
          <h3>Where your money goes</h3>
          <div className="wm-breakdown">
            {Object.entries(summary.category_breakdown || {}).length === 0
              ? <p className="wm-muted">Category insights will appear when payments are recorded.</p>
              : Object.entries(summary.category_breakdown || {}).sort((a,b) => Number(b[1])-Number(a[1])).map(([name,value]) => (
                <div className="wm-break-row" key={name}><span>{name.replaceAll('_',' ')}</span><strong>{money(Number(value))}</strong></div>
              ))}
          </div>
        </div>
        <div className="wm-panel wm-callout">
          <div className="wm-callout-icon"><ShieldCheck size={22}/></div>
          <span className="wm-panel-kicker">PAYMENT PROTECTION</span>
          <h3>Keep your financial records organised.</h3>
          <p>Track disputed transactions and connect them to a Recovery Desk incident when something goes wrong.</p>
        </div>
      </section>

      {showForm && <Modal title="Record a payment" close={() => setShowForm(false)}>
        <form onSubmit={createPayment} className="wm-form">
          <div className="wm-form-grid">
            <Input label="Merchant / beneficiary" required minLength={2} value={form.merchant} onChange={e => setForm({...form,merchant:e.target.value})} placeholder="e.g. Amazon India"/>
            <Input label="Amount (₹)" required type="number" min="0.01" step="0.01" value={form.amount} onChange={e => setForm({...form,amount:e.target.value})} placeholder="0.00"/>
            <Input label="Payment provider" required value={form.provider} onChange={e => setForm({...form,provider:e.target.value})}/>
            <SelectField label="Category" value={form.category} onChange={e => setForm({...form,category:e.target.value})}>
              {['general','food','utilities','shopping','subscription','transfer','travel','health','education'].map(v => <option key={v}>{v}</option>)}
            </SelectField>
            <Input label="Payment date" type="date" required value={form.payment_date} onChange={e => setForm({...form,payment_date:e.target.value})}/>
            <SelectField label="Status" value={form.status} onChange={e => setForm({...form,status:e.target.value})}>
              <option value="completed">Completed</option><option value="pending">Pending</option><option value="failed">Failed</option>
            </SelectField>
            <Input label="Transaction reference / UTR" value={form.transaction_ref} onChange={e => setForm({...form,transaction_ref:e.target.value})}/>
            <Input label="Notes" value={form.notes} onChange={e => setForm({...form,notes:e.target.value})}/>
          </div>
          {formError && <div className="wm-form-error">{formError}</div>}
          <FormActions busy={busy} close={() => setShowForm(false)} label="Record payment"/>
        </form>
      </Modal>}
    </div>
  )
}

// ============================================================
// SUBSCRIPTIONS
// ============================================================

export function Subscriptions() {
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Subscription | null>(null)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const { data: list, loading, error, refresh } =
    useWorkspace<{items: Subscription[]; total: number}>('/api/subscriptions?limit=100&offset=0', {items:[],total:0})
  const { data: summary, refresh: refreshSummary } =
    useWorkspace<Summary>('/api/subscriptions/summary', {})

  const blank = {
    name: '', amount: '', currency: 'INR', frequency: 'monthly',
    start_date: new Date().toISOString().slice(0,10),
    next_expected_date: new Date(Date.now()+30*86400000).toISOString().slice(0,10),
    category: 'entertainment', provider: '', cancellation_reminder_days: '3', notes: '',
  }
  const [form, setForm] = useState(blank)

  function openCreate() {
    setEditing(null)
    setForm(blank)
    setFormError('')
    setShowForm(true)
  }

  function openEdit(s: Subscription) {
    setEditing(s)
    setForm({
      name: s.name, amount: String(s.amount), currency: s.currency,
      frequency: s.frequency, start_date: s.start_date,
      next_expected_date: s.next_expected_date, category: s.category,
      provider: s.provider || '',
      cancellation_reminder_days: String(s.cancellation_reminder_days),
      notes: s.notes || '',
    })
    setFormError('')
    setShowForm(true)
  }

  async function save(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setFormError('')
    try {
      const payload: any = {
        ...form,
        amount: Number(form.amount),
        cancellation_reminder_days: Number(form.cancellation_reminder_days),
        provider: form.provider || null,
        notes: form.notes || null,
      }
      delete payload.start_date
      if (editing) {
        await api(`/api/subscriptions/${editing.id}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
      } else {
        payload.start_date = form.start_date
        await api('/api/subscriptions', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
      }
      setShowForm(false)
      refresh()
      refreshSummary()
    } catch (err: any) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function toggle(s: Subscription) {
    try {
      await api(`/api/subscriptions/${s.id}/${s.is_active ? 'pause' : 'resume'}`, {method:'POST'})
      refresh()
      refreshSummary()
    } catch (err: any) {
      alert(err.message)
    }
  }

  async function remove(s: Subscription) {
    if (!confirm(`Delete the subscription "${s.name}"? This cannot be undone.`)) return
    try {
      await api(`/api/subscriptions/${s.id}`, {method:'DELETE'})
      refresh()
      refreshSummary()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="wm-page">
      <PageHeading
        eyebrow="RECURRING PAYMENT CONTROL"
        title="Subscriptions, without surprises."
        description="Know what renews, when it renews and how much your recurring commitments cost."
        action={<button className="wm-primary" onClick={openCreate}><Plus size={17}/> Add subscription</button>}
      />

      <div className="wm-metrics">
        <Metric label="TOTAL SUBSCRIPTIONS" value={String(summary.total_subscriptions ?? list.total ?? 0)} detail="All recorded services" icon={RefreshCw}/>
        <Metric label="ACTIVE" value={String(summary.active_subscriptions ?? 0)} detail="Currently running" icon={CheckCircle2} tone="green"/>
        <Metric label="MONTHLY COMMITMENT" value={money(summary.total_monthly_commitment || 0)} detail="Normalised monthly cost" icon={Wallet} tone="violet"/>
        <Metric label="NEXT 30 DAYS" value={money(summary.upcoming_30_days_total || 0)} detail="Expected renewals" icon={CalendarDays} tone="amber"/>
      </div>

      <Notice error={error} onRetry={() => {refresh();refreshSummary()}}/>

      <section className="wm-panel">
        <div className="wm-panel-head">
          <div><span className="wm-panel-kicker">YOUR RECURRING COMMITMENTS</span><h3>Subscription manager</h3><p>Manage and review every recurring expense.</p></div>
        </div>

        {loading ? <Loading/> : list.items.length === 0 ? (
          <Empty title="No subscriptions yet" detail="Add services such as streaming, cloud storage, mobile plans or memberships."/>
        ) : (
          <div className="wm-sub-list">
            {list.items.map(s => (
              <motion.div className="wm-sub-item" key={s.id} layout>
                <div className="wm-sub-logo">{s.name.slice(0,1).toUpperCase()}</div>
                <div className="wm-sub-main">
                  <strong>{s.name}</strong>
                  <span>{s.category} · {s.provider || s.frequency}</span>
                </div>
                <div className="wm-sub-next"><small>NEXT RENEWAL</small><strong>{dateLabel(s.next_expected_date)}</strong></div>
                <div className="wm-sub-price"><strong>{money(s.amount,s.currency)}</strong><small>/{s.frequency}</small></div>
                <span className={`wm-status ${s.is_active ? 'completed' : 'paused'}`}>{s.is_active ? 'Active' : 'Paused'}</span>
                <div className="wm-sub-actions">
                  <button className="wm-inline-action" onClick={() => openEdit(s)}>Edit</button>
                  <button className="wm-icon-action" title={s.is_active ? 'Pause' : 'Resume'} onClick={() => toggle(s)}><Zap size={16}/></button>
                  <button className="wm-icon-action danger" title="Delete" onClick={() => remove(s)}><Trash2 size={16}/></button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </section>

      <section className="wm-lower-grid">
        <div className="wm-panel">
          <span className="wm-panel-kicker">UPCOMING RENEWALS</span>
          <h3>What is coming up?</h3>
          {(summary.upcoming_payments || []).length === 0
            ? <p className="wm-muted">No upcoming renewals in the next 30 days.</p>
            : <div className="wm-breakdown">{summary.upcoming_payments.map((p: any) => (
              <div className="wm-break-row" key={p.subscription_id}>
                <span><strong>{p.name}</strong><small>{dateLabel(p.due_date)} · {p.days_remaining} days</small></span>
                <strong>{money(p.amount,p.currency)}</strong>
              </div>
            ))}</div>}
        </div>
        <div className="wm-panel wm-callout">
          <div className="wm-callout-icon"><Activity size={22}/></div>
          <span className="wm-panel-kicker">SUBSCRIPTION INTELLIGENCE</span>
          <h3>Understand your recurring costs.</h3>
          <p>Monthly equivalents make weekly, quarterly and annual plans easier to compare. Review inactive services before their next renewal.</p>
        </div>
      </section>

      {showForm && <Modal title={editing ? 'Edit subscription' : 'Add subscription'} close={() => setShowForm(false)}>
        <form className="wm-form" onSubmit={save}>
          <div className="wm-form-grid">
            <Input label="Service name" required minLength={2} value={form.name} onChange={e => setForm({...form,name:e.target.value})} placeholder="e.g. Netflix"/>
            <Input label="Amount (₹)" required type="number" min="0.01" step="0.01" value={form.amount} onChange={e => setForm({...form,amount:e.target.value})}/>
            <SelectField label="Billing frequency" value={form.frequency} onChange={e => setForm({...form,frequency:e.target.value})}>
              {['weekly','monthly','quarterly','yearly'].map(v => <option key={v}>{v}</option>)}
            </SelectField>
            <SelectField label="Category" value={form.category} onChange={e => setForm({...form,category:e.target.value})}>
              {['entertainment','utilities','software','shopping','education','health','other'].map(v => <option key={v}>{v}</option>)}
            </SelectField>
            {!editing && <Input label="Start date" type="date" required value={form.start_date} onChange={e => setForm({...form,start_date:e.target.value})}/>}
            <Input label="Next renewal date" type="date" required value={form.next_expected_date} onChange={e => setForm({...form,next_expected_date:e.target.value})}/>
            <Input label="Provider / payment method" value={form.provider} onChange={e => setForm({...form,provider:e.target.value})}/>
            <Input label="Reminder days before renewal" type="number" min="0" max="30" value={form.cancellation_reminder_days} onChange={e => setForm({...form,cancellation_reminder_days:e.target.value})}/>
          </div>
          <Input label="Notes" value={form.notes} onChange={e => setForm({...form,notes:e.target.value})}/>
          {formError && <div className="wm-form-error">{formError}</div>}
          <FormActions busy={busy} close={() => setShowForm(false)} label={editing ? 'Save changes' : 'Create subscription'}/>
        </form>
      </Modal>}
    </div>
  )
}

// ============================================================
// RECOVERY DESK
// ============================================================

const incidentCategories = [
  ['suspicious_upi','Suspicious UPI activity'],
  ['failed_payment','Failed payment'],
  ['suspected_fraud','Suspected fraud'],
  ['unauthorised_transaction','Unauthorised transaction'],
  ['duplicate_payment','Duplicate payment'],
  ['delayed_refund','Delayed refund'],
  ['other_dispute','Other dispute'],
]

export function Recovery() {
  const [showForm, setShowForm] = useState(false)
  const [selected, setSelected] = useState<Incident | null>(null)
  const [complaint, setComplaint] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [formError, setFormError] = useState('')
  const [complaintLoading, setComplaintLoading] = useState(false)
  const { data: list, loading, error, refresh } =
    useWorkspace<{items: Incident[]; total: number}>('/api/recovery/incidents?limit=100&offset=0', {items:[],total:0})

  const blank = {
    category: 'failed_payment',
    incident_datetime: new Date().toISOString().slice(0,16),
    provider: 'UPI',
    transaction_ref: '',
    amount: '',
    currency: 'INR',
    description: '',
    follow_up_date: '',
    credentials_disclosed: 'not_sure',
  }
  const [form, setForm] = useState(blank)

  async function createIncident(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setFormError('')
    try {
      await api('/api/recovery/incidents', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          incident_datetime: new Date(form.incident_datetime).toISOString(),
          amount: Number(form.amount),
          transaction_ref: form.transaction_ref || null,
          follow_up_date: form.follow_up_date || null,
          credentials_disclosed: form.credentials_disclosed,
          evidence_references: [],
        }),
      })
      setShowForm(false)
      setForm(blank)
      refresh()
    } catch (err: any) {
      setFormError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function changeStatus(incident: Incident, status: string) {
    try {
      const updated = await api<Incident>(`/api/recovery/incidents/${incident.id}`, {
        method: 'PATCH',
        body: JSON.stringify({status}),
      })
      setSelected(updated)
      refresh()
    } catch (err: any) {
      alert(err.message)
    }
  }

  async function generateComplaint(incident: Incident) {
    setComplaintLoading(true)
    setComplaint(null)
    try {
      const result = await api(`/api/recovery/incidents/${incident.id}/complaint-draft`, {method:'POST'})
      setComplaint(result)
    } catch (err: any) {
      alert(err.message)
    } finally {
      setComplaintLoading(false)
    }
  }

  async function addEvidence(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!selected) return
    const fd = new FormData(e.currentTarget)
    const title = String(fd.get('title') || '')
    const id = `evidence-${Date.now()}`
    try {
      const updated = await api<Incident>(`/api/recovery/incidents/${selected.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          add_evidence: [{id,title,description: String(fd.get('description') || '') || null}],
        }),
      })
      setSelected(updated)
      refresh()
      e.currentTarget.reset()
    } catch (err: any) {
      alert(err.message)
    }
  }

  async function deleteEvidence(evidenceId: string) {
    if (!selected || !confirm('Remove this evidence reference?')) return
    try {
      const updated = await api<Incident>(`/api/recovery/incidents/${selected.id}/evidence/${evidenceId}`, {method:'DELETE'})
      setSelected(updated)
      refresh()
    } catch (err: any) {
      alert(err.message)
    }
  }

  return (
    <div className="wm-page">
      <PageHeading
        eyebrow="FINANCIAL SAFETY & DISPUTE MANAGEMENT"
        title="When something goes wrong, act."
        description="Document suspicious transactions, organise evidence and prepare formal complaint drafts."
        action={<button className="wm-primary" onClick={() => setShowForm(true)}><Plus size={17}/> Report incident</button>}
      />

      <div className="wm-metrics">
        <Metric label="TOTAL INCIDENTS" value={String(list.total || 0)} detail="Recorded cases" icon={ShieldAlert}/>
        <Metric label="UNDER INVESTIGATION" value={String(list.items.filter(i => i.status === 'under_investigation').length)} detail="Currently being reviewed" icon={Activity} tone="amber"/>
        <Metric label="AWAITING ACTION" value={String(list.items.filter(i => ['reported','grievance_filed'].includes(i.status)).length)} detail="Cases requiring attention" icon={Clock3} tone="violet"/>
        <Metric label="RESOLVED" value={String(list.items.filter(i => ['resolved','closed'].includes(i.status)).length)} detail="Closed or resolved cases" icon={CheckCircle2} tone="green"/>
      </div>

      <Notice error={error} onRetry={refresh}/>

      <section className="wm-panel">
        <div className="wm-panel-head">
          <div><span className="wm-panel-kicker">INCIDENT MANAGEMENT</span><h3>Recovery casebook</h3><p>Maintain a structured record of every dispute.</p></div>
        </div>

        {loading ? <Loading/> : list.items.length === 0 ? (
          <Empty title="No recovery incidents" detail="If a payment fails, a refund is delayed or you suspect fraud, report it here."/>
        ) : (
          <div className="wm-case-list">
            {list.items.map(i => (
              <button className="wm-case" key={i.id} onClick={() => {setSelected(i);setComplaint(null)}}>
                <div className="wm-case-icon"><ShieldAlert size={19}/></div>
                <div className="wm-case-main">
                  <strong>{i.category.replaceAll('_',' ')}</strong>
                  <span>{i.provider} · {dateLabel(i.incident_datetime)}</span>
                  <small>{i.description}</small>
                </div>
                <div className="wm-case-amount">{money(i.amount,i.currency)}</div>
                <span className={`wm-status ${i.status}`}>{i.status.replaceAll('_',' ')}</span>
                <ArrowRight size={17}/>
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="wm-panel wm-safety-note">
        <ShieldCheck size={22}/>
        <div><strong>Stay safe while documenting an incident.</strong><p>Never enter your UPI PIN, card PIN, OTP, CVV or banking password into a complaint description or evidence notes. PayPause does not need these credentials.</p></div>
      </section>

      {showForm && <Modal title="Report a financial incident" close={() => setShowForm(false)}>
        <form className="wm-form" onSubmit={createIncident}>
          <div className="wm-form-grid">
            <SelectField label="Incident type" value={form.category} onChange={e => setForm({...form,category:e.target.value})}>
              {incidentCategories.map(([v,l]) => <option value={v} key={v}>{l}</option>)}
            </SelectField>
            <Input label="Payment provider" required minLength={2} value={form.provider} onChange={e => setForm({...form,provider:e.target.value})} placeholder="GPay, PhonePe, SBI..."/>
            <Input label="Amount in dispute (₹)" required type="number" min="0.01" step="0.01" value={form.amount} onChange={e => setForm({...form,amount:e.target.value})}/>
            <Input label="Transaction reference / UTR" value={form.transaction_ref} onChange={e => setForm({...form,transaction_ref:e.target.value})}/>
            <Input label="Incident date and time" required type="datetime-local" value={form.incident_datetime} onChange={e => setForm({...form,incident_datetime:e.target.value})}/>
            <Input label="Follow-up date" type="date" value={form.follow_up_date} onChange={e => setForm({...form,follow_up_date:e.target.value})}/>
            <SelectField label="Did you disclose credentials?" value={form.credentials_disclosed} onChange={e => setForm({...form,credentials_disclosed:e.target.value})}>
              <option value="yes">Yes</option><option value="no">No</option><option value="not_sure">Not sure</option><option value="prefer_not_to_say">Prefer not to say</option>
            </SelectField>
          </div>
          <Field label="Describe what happened">
            <textarea required minLength={10} maxLength={2000} rows={5} value={form.description} onChange={e => setForm({...form,description:e.target.value})} placeholder="Explain the transaction, what happened, and any communication received. Do not include PINs, OTPs or passwords."/>
          </Field>
          {formError && <div className="wm-form-error">{formError}</div>}
          <FormActions busy={busy} close={() => setShowForm(false)} label="Submit incident"/>
        </form>
      </Modal>}

      {selected && <Modal title="Recovery case details" close={() => setSelected(null)}>
        <div className="wm-case-detail">
          <div className="wm-case-detail-top">
            <span className={`wm-status ${selected.status}`}>{selected.status.replaceAll('_',' ')}</span>
            <strong>{money(selected.amount,selected.currency)}</strong>
          </div>
          <h3>{selected.category.replaceAll('_',' ')}</h3>
          <p>{selected.description}</p>
          <div className="wm-detail-grid">
            <div><small>PROVIDER</small><strong>{selected.provider}</strong></div>
            <div><small>INCIDENT DATE</small><strong>{dateLabel(selected.incident_datetime)}</strong></div>
            <div><small>TRANSACTION REF</small><strong>{selected.transaction_ref || 'Not supplied'}</strong></div>
            <div><small>FOLLOW-UP</small><strong>{dateLabel(selected.follow_up_date)}</strong></div>
          </div>

          <Field label="Update case status">
            <select value={selected.status} onChange={e => changeStatus(selected,e.target.value)}>
              {['reported','under_investigation','grievance_filed','resolved','closed'].map(s => <option key={s} value={s}>{s.replaceAll('_',' ')}</option>)}
            </select>
          </Field>

          <div className="wm-evidence-heading"><strong>Evidence references</strong><span>{selected.evidence_references?.length || 0} items</span></div>
          {(selected.evidence_references || []).map((item:any) => (
            <div className="wm-evidence" key={item.id}>
              <FileText size={17}/><div><strong>{item.title}</strong><small>{item.description || 'No description'}</small></div>
              <button onClick={() => deleteEvidence(item.id)} title="Remove evidence"><Trash2 size={16}/></button>
            </div>
          ))}
          <form className="wm-evidence-form" onSubmit={addEvidence}>
            <input name="title" required minLength={3} placeholder="Evidence title (e.g. Bank debit SMS)"/>
            <input name="description" placeholder="Short description (optional)"/>
            <button className="wm-secondary"><Plus size={15}/> Add reference</button>
          </form>
          <p className="wm-muted">Evidence references organise records; this form does not upload or store actual files.</p>

          <button className="wm-primary wm-full" disabled={complaintLoading} onClick={() => generateComplaint(selected)}>
            {complaintLoading ? <LoaderCircle size={16} className="wm-spin"/> : <FileText size={16}/>}
            Generate complaint draft
          </button>

          {complaint && (
            <div className="wm-complaint">
              <span className="wm-panel-kicker">GENERATED DOCUMENT · DRAFT ONLY</span>
              <h3>{complaint.draft_title}</h3>
              <p className="wm-muted">{complaint.disclaimer}</p>
              <pre>{complaint.formal_letter_body}</pre>
              <button className="wm-secondary" onClick={() => navigator.clipboard.writeText(complaint.formal_letter_body)}>
                Copy complaint text
              </button>
              {complaint.recommended_evidence_checklist?.length > 0 && (
                <div className="wm-checklist">
                  <strong>Recommended evidence checklist</strong>
                  {complaint.recommended_evidence_checklist.map((item:any,i:number) => (
                    <div key={i}><CheckCircle2 size={15}/><span>{item.item_name}{item.is_mandatory ? ' · Required' : ''}<small>{item.description}</small></span></div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>}
    </div>
  )
}

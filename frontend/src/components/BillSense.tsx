import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  UploadCloud, FileText, Zap, ShieldCheck, AlertTriangle,
  CheckCircle2, LoaderCircle, Sparkles, Activity,
  Gauge, IndianRupee, ChevronDown, Eye,
  RefreshCw, Info, LockKeyhole, ArrowUpRight, FileCheck2
} from 'lucide-react'
import ReactECharts from 'echarts-for-react'
import { type Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import './BillSense.css'

type BillField = {
  value: string | number | null
  source_text: string | null
  confidence: number | null
}

type BillAssessment = {
  document_type: string
  fields: Record<string, BillField>
  is_valid: boolean
  validation_issues: { code: string; message: string; severity: string }[]
  consumption: {
    units_consumed_kwh: number | null
    is_derived: boolean
    daily_average_kwh: number | null
    billing_days: number | null
    previous_consumption_kwh: number | null
    change_percentage: number | null
    usage_status: string
    observations: string[]
  }
  extracted_text: string
  ocr_pages: number
  average_ocr_confidence: number | null
  processing_time_ms: number
  ai_insights: { explanation: string; recommendations: string[] } | null
  disclaimer: string
}

type ApiResponse = {
  success: boolean
  message: string
  data: BillAssessment | null
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const fieldLabels: Record<string, string> = {
  provider: 'Electricity provider',
  consumer_number: 'Consumer number',
  consumer_name: 'Consumer name',
  bill_number: 'Bill number',
  billing_period: 'Billing period',
  issue_date: 'Issue date',
  due_date: 'Due date',
  units_consumed_kwh: 'Units consumed',
  previous_reading: 'Previous meter reading',
  current_reading: 'Current meter reading',
  total_amount_inr: 'Total bill amount',
  energy_charges_inr: 'Energy charges',
  fixed_charges_inr: 'Fixed charges',
  taxes_inr: 'Taxes',
  late_fee_inr: 'Late fee',
}

const moneyFields = new Set([
  'total_amount_inr', 'energy_charges_inr',
  'fixed_charges_inr', 'taxes_inr', 'late_fee_inr'
])

function displayValue(value: string | number | null | undefined, key: string) {
  if (value === null || value === undefined || value === '') return 'Not detected'
  if (moneyFields.has(key)) {
    const number = Number(value)
    return Number.isFinite(number) ? `₹${number.toLocaleString('en-IN')}` : String(value)
  }
  if (key === 'units_consumed_kwh') return `${value} kWh`
  return String(value)
}

function confidenceLabel(value: number | null) {
  if (value === null || value === undefined) return 'Unavailable'
  if (value >= 0.85) return 'High confidence'
  if (value >= 0.60) return 'Moderate confidence'
  return 'Low confidence'
}

export default function BillSense() {
  const fileInput = useRef<HTMLInputElement>(null)

  // Supabase authentication state
  const [session, setSession] = useState<Session | null>(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [authBusy, setAuthBusy] = useState(false)
  const [authError, setAuthError] = useState('')
  const [authMessage, setAuthMessage] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<BillAssessment | null>(null)
  const [history, setHistory] = useState<{ name: string; result: BillAssessment; time: string }[]>([])
  const [showText, setShowText] = useState(false)

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return
      if (error) setAuthError(error.message)
      setSession(data.session)
      setAuthLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, nextSession) => {
        setSession(nextSession)
        setAuthLoading(false)
        if (!nextSession) setResult(null)
      }
    )

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [])

  const authenticate = async (mode: 'signin' | 'signup') => {
    setAuthBusy(true)
    setAuthError('')
    setAuthMessage('')

    try {
      const { data, error } = mode === 'signin'
        ? await supabase.auth.signInWithPassword({ email: email.trim(), password })
        : await supabase.auth.signUp({ email: email.trim(), password })

      if (error) throw error

      if (mode === 'signup' && !data.session) {
        setAuthMessage('Account created. Check your email to confirm your address, then sign in.')
      } else {
        setAuthMessage(mode === 'signup' ? 'Your account is ready.' : 'Signed in successfully.')
      }
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Authentication failed.')
    } finally {
      setAuthBusy(false)
    }
  }

  const signOut = async () => {
    setAuthError('')
    const { error } = await supabase.auth.signOut()
    if (error) setAuthError(error.message)
    else {
      setSession(null)
      setResult(null)
      setFile(null)
    }
  }

  const selectFile = (selected?: File) => {
    if (!selected) return
    setError('')
    setResult(null)

    if (!['application/pdf', 'image/jpeg', 'image/png', 'image/webp'].includes(selected.type)) {
      setFile(null)
      setError('Choose a PDF, JPG, PNG or WEBP electricity bill.')
      return
    }
    if (selected.size > 10 * 1024 * 1024) {
      setFile(null)
      setError('The file exceeds the 10 MB upload limit.')
      return
    }
    setFile(selected)
  }

  const analyze = async () => {
    if (!file) {
      setError('Select an electricity bill before starting analysis.')
      return
    }
    if (!session?.access_token) {
      setError('Sign in to your PayPause account before analyzing a bill.')
      return
    }

    setLoading(true)
    setError('')
    setResult(null)

    try {
      const form = new FormData()
      form.append('bill_file', file)

      const response = await fetch(`${API_BASE}/api/v1/billsense/analyze`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
        body: form,
      })

      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        const message =
          payload?.error?.message ||
          payload?.detail ||
          payload?.message ||
          `Analysis failed with HTTP ${response.status}.`
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
      }

      const data = (payload as ApiResponse)?.data
      if (!payload?.success || !data) {
        throw new Error(payload?.message || 'The server returned an unexpected response.')
      }

      setResult(data)
      setHistory(previous => [
        { name: file.name, result: data, time: new Date().toLocaleTimeString() },
        ...previous,
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to analyze this bill.')
    } finally {
      setLoading(false)
    }
  }

  const consumption = result?.consumption
  const confidence = result?.average_ocr_confidence
  const chartOption = {
    animationDuration: 900,
    grid: { top: 18, right: 18, bottom: 28, left: 42 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#172438',
      borderColor: '#405778',
      textStyle: { color: '#edf3ff' },
      formatter: (params: { value: number }[]) =>
        `Consumption<br/><strong>${params[0]?.value ?? 0} kWh</strong>`,
    },
    xAxis: {
      type: 'category',
      data: ['Previous period', 'Current period'],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#8c9bb2', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: 'kWh',
      nameTextStyle: { color: '#8292aa' },
      axisLabel: { color: '#8292aa' },
      splitLine: { lineStyle: { color: 'rgba(143,164,198,.12)', type: 'dashed' } },
    },
    series: [{
      type: 'bar',
      barWidth: 42,
      data: [
        consumption?.previous_consumption_kwh ?? 0,
        consumption?.units_consumed_kwh ?? 0,
      ],
      itemStyle: {
        borderRadius: [7, 7, 2, 2],
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#91b7ff' },
            { offset: 1, color: '#426ac1' },
          ],
        },
      },
    }],
  }

  return (
    <div className="billsense-workspace">
      <div className="bs-intro">
        <div>
          <div className="bs-eyebrow"><Sparkles size={13}/> DOCUMENT INTELLIGENCE</div>
          <h2>Understand every <span>unit.</span></h2>
          <p>Turn an electricity bill into clear, actionable financial intelligence.</p>
        </div>
        <div className="bs-intro-mark"><FileCheck2 size={30}/><span>AI + OCR</span></div>
      </div>

      <div className="bs-feature-strip">
        <div><ScanIcon/><span>Local OCR extraction</span></div>
        <div><ShieldCheck size={16}/><span>Deterministic validation</span></div>
        <div><Activity size={16}/><span>Consumption intelligence</span></div>
        <div><LockKeyhole size={16}/><span>Authenticated analysis</span></div>
      </div>

      <div className="bs-main-grid">
        <section className="bs-panel bs-upload-panel">
          <div className="bs-panel-heading">
            <div><span className="bs-kicker">01 / INPUT</span><h3>Upload your bill</h3><p>Start with an electricity bill document.</p></div>
            <div className="bs-heading-icon"><UploadCloud size={19}/></div>
          </div>

          <div
            className={`bs-dropzone ${dragging ? 'is-dragging' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); selectFile(e.dataTransfer.files[0]) }}
            onClick={() => fileInput.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') fileInput.current?.click() }}
          >
            <input
              ref={fileInput}
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
              hidden
              onChange={e => selectFile(e.target.files?.[0])}
            />
            <div className="bs-upload-icon"><UploadCloud size={27}/></div>
            {file ? (
              <>
                <strong>{file.name}</strong>
                <span>{(file.size / 1024 / 1024).toFixed(2)} MB · Ready for analysis</span>
                <button className="bs-clear-file" onClick={e => { e.stopPropagation(); setFile(null); setResult(null) }}>Remove file</button>
              </>
            ) : (
              <>
                <strong>Drop your bill here</strong>
                <span>or <b>browse files</b> from your device</span>
                <small>PDF, JPG, PNG or WEBP · Maximum 10 MB</small>
              </>
            )}
          </div>

          <div className="bs-auth-card">
            {authLoading ? (
              <div className="bs-auth-status"><LoaderCircle className="bs-spin" size={17}/> Checking your secure session...</div>
            ) : session ? (
              <div className="bs-session-active">
                <div className="bs-session-icon"><ShieldCheck size={19}/></div>
                <div className="bs-session-copy">
                  <strong>Secure session active</strong>
                  <span>{session.user.email || 'Authenticated PayPause user'}</span>
                </div>
                <button type="button" className="bs-signout" onClick={() => void signOut()}>Sign out</button>
              </div>
            ) : (
              <div className="bs-auth-form">
                <div className="bs-auth-title">
                  <LockKeyhole size={17}/>
                  <div><strong>Sign in to analyze</strong><span>Your bill analysis is tied to your authenticated account.</span></div>
                </div>
                <label htmlFor="bs-email">EMAIL ADDRESS</label>
                <input id="bs-email" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email"/>
                <label htmlFor="bs-password">PASSWORD</label>
                <input id="bs-password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Your account password" autoComplete="current-password"/>
                <div className="bs-auth-actions">
                  <button type="button" disabled={authBusy || !email.trim() || !password} onClick={() => void authenticate('signin')}>
                    {authBusy ? <LoaderCircle className="bs-spin" size={15}/> : null} Sign in
                  </button>
                  <button type="button" className="bs-create-account" disabled={authBusy || !email.trim() || password.length < 6} onClick={() => void authenticate('signup')}>Create account</button>
                </div>
              </div>
            )}
            {authError && <div className="bs-auth-error"><AlertTriangle size={14}/>{authError}</div>}
            {authMessage && <div className="bs-auth-message"><CheckCircle2 size={14}/>{authMessage}</div>}
          </div>
          <button className="bs-analyze-button" disabled={loading || !file || !session?.access_token || authLoading} onClick={analyze}>
            {loading ? <><LoaderCircle className="bs-spin" size={17}/> Analyzing document...</> : <><Sparkles size={17}/> Analyze electricity bill <ArrowUpRight size={16}/></>}
          </button>

          <div className="bs-security-note"><ShieldCheck size={15}/><span>Your document is processed by the configured backend OCR pipeline. Analysis requires a verified Supabase session.</span></div>

          {error && (
            <motion.div className="bs-error" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <AlertTriangle size={17}/><span>{error}</span>
            </motion.div>
          )}
        </section>

        <section className="bs-panel bs-process-panel">
          <div className="bs-panel-heading">
            <div><span className="bs-kicker">HOW IT WORKS</span><h3>From document to decisions</h3><p>A transparent, multi-stage analysis pipeline.</p></div>
          </div>
          <div className="bs-pipeline">
            {[
              { icon: FileText, title: 'Document intake', desc: 'File type and size validation', tag: 'INPUT' },
              { icon: Eye, title: 'OCR extraction', desc: 'Read bill text and document pages', tag: 'EXTRACT' },
              { icon: ShieldCheck, title: 'Financial validation', desc: 'Check extracted fields and issues', tag: 'VERIFY' },
              { icon: Activity, title: 'Consumption analysis', desc: 'Calculate usage and daily average', tag: 'ANALYZE' },
              { icon: Sparkles, title: 'AI explanation', desc: 'Optional recommendations from results', tag: 'INSIGHT' },
            ].map((step, i) => {
              const Icon = step.icon
              return (
                <div className="bs-pipeline-step" key={step.tag}>
                  <div className="bs-pipeline-icon"><Icon size={17}/></div>
                  <div><strong>{step.title}</strong><span>{step.desc}</span></div>
                  <small>{step.tag}</small>
                  {i < 4 && <i className="bs-pipeline-line"/>}
                </div>
              )
            })}
          </div>
          <div className="bs-process-foot"><Zap size={15}/><span>AI insights are optional. Core extraction and validation are performed by the backend pipeline.</span></div>
        </section>
      </div>

      <AnimatePresence>
        {result && (
          <motion.section className="bs-results" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }}>
            <div className="bs-results-heading">
              <div><span className="bs-kicker">02 / ANALYSIS COMPLETE</span><h2>Your bill intelligence report</h2><p>Extracted data and calculated insights from the uploaded document.</p></div>
              <div className={`bs-validity ${result.is_valid ? 'valid' : 'invalid'}`}>
                {result.is_valid ? <CheckCircle2 size={16}/> : <AlertTriangle size={16}/>}
                {result.is_valid ? 'Validation passed' : 'Review required'}
              </div>
            </div>

            <div className="bs-metric-grid">
              <div className="bs-metric-card"><div><span>TOTAL BILL AMOUNT</span><IndianRupee size={17}/></div><strong>{displayValue(result.fields.total_amount_inr?.value, 'total_amount_inr')}</strong><small>Extracted from document</small></div>
              <div className="bs-metric-card"><div><span>ENERGY CONSUMPTION</span><Activity size={17}/></div><strong>{consumption?.units_consumed_kwh ?? '—'} <em>kWh</em></strong><small>{consumption?.is_derived ? 'Derived from meter readings' : 'Extracted consumption'}</small></div>
              <div className="bs-metric-card"><div><span>DAILY AVERAGE</span><Gauge size={17}/></div><strong>{consumption?.daily_average_kwh ?? '—'} <em>kWh</em></strong><small>{consumption?.billing_days ?? '—'} billing days</small></div>
              <div className="bs-metric-card"><div><span>OCR CONFIDENCE</span><Eye size={17}/></div><strong>{confidence == null ? '—' : `${(confidence * 100).toFixed(0)}%`}</strong><small>{confidenceLabel(confidence ?? null)}</small></div>
            </div>

            <div className="bs-result-grid">
              <div className="bs-panel">
                <div className="bs-panel-heading"><div><span className="bs-kicker">EXTRACTED DATA</span><h3>Bill details</h3><p>Field values detected in your document.</p></div></div>
                <div className="bs-field-grid">
                  {Object.entries(fieldLabels).map(([key, label]) => {
                    const field = result.fields[key]
                    return (
                      <div className="bs-field" key={key}>
                        <span>{label}</span>
                        <strong>{displayValue(field?.value, key)}</strong>
                        <div className="bs-field-meta">
                          <span>{field?.confidence == null ? 'No confidence score' : `${(field.confidence * 100).toFixed(0)}% confidence`}</span>
                          {field?.confidence != null && <i><b style={{ width: `${Math.max(0, Math.min(100, field.confidence * 100))}%` }}/></i>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="bs-panel">
                <div className="bs-panel-heading"><div><span className="bs-kicker">CONSUMPTION INTELLIGENCE</span><h3>Usage analysis</h3><p>Current and previous consumption, when available.</p></div></div>
                <div className="bs-usage-status"><span>USAGE STATUS</span><strong>{consumption?.usage_status || 'Not available'}</strong></div>
                <ReactECharts option={chartOption} notMerge lazyUpdate opts={{ renderer: 'canvas' }} style={{ height: 230, width: '100%' }}/>
                {consumption?.change_percentage != null && (
                  <div className="bs-usage-change"><span>Change from previous period</span><strong className={consumption.change_percentage > 0 ? 'up' : 'down'}>{consumption.change_percentage > 0 ? '+' : ''}{consumption.change_percentage.toFixed(1)}%</strong></div>
                )}
                {consumption?.observations?.map((item, i) => <div className="bs-observation" key={i}><Info size={14}/>{item}</div>)}
              </div>
            </div>

            <div className="bs-result-grid">
              <div className="bs-panel">
                <div className="bs-panel-heading"><div><span className="bs-kicker">VALIDATION ENGINE</span><h3>Document screening</h3></div></div>
                {result.validation_issues.length === 0 ? (
                  <div className="bs-no-issues"><CheckCircle2 size={18}/> No validation issues were reported.</div>
                ) : result.validation_issues.map((issue, i) => (
                  <div className={`bs-issue ${issue.severity.toLowerCase()}`} key={`${issue.code}-${i}`}>
                    <AlertTriangle size={16}/><div><strong>{issue.severity} · {issue.code}</strong><p>{issue.message}</p></div>
                  </div>
                ))}
                <p className="bs-disclaimer">{result.disclaimer}</p>
              </div>

              <div className="bs-panel">
                <div className="bs-panel-heading"><div><span className="bs-kicker">AI EXPLANATION</span><h3>Recommendations</h3></div><div className="bs-heading-icon"><Sparkles size={17}/></div></div>
                {result.ai_insights ? (
                  <>
                    <p className="bs-ai-explanation">{result.ai_insights.explanation}</p>
                    {result.ai_insights.recommendations.map((item, i) => <div className="bs-recommendation" key={i}><span>{String(i + 1).padStart(2, '0')}</span><p>{item}</p></div>)}
                  </>
                ) : (
                  <div className="bs-no-issues"><Info size={17}/> AI insights are unavailable for this analysis. The deterministic OCR and validation results are still available.</div>
                )}
              </div>
            </div>

            <div className="bs-panel bs-raw-panel">
              <button className="bs-raw-toggle" onClick={() => setShowText(!showText)}>
                <div><FileText size={17}/><span><strong>Extracted document text</strong><small>{result.ocr_pages} page(s) · {result.processing_time_ms.toFixed(0)} ms processing time</small></span></div>
                <ChevronDown size={17} className={showText ? 'rotated' : ''}/>
              </button>
              {showText && <pre className="bs-extracted-text">{result.extracted_text || 'No extracted text returned.'}</pre>}
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {history.length > 0 && (
        <section className="bs-history">
          <div className="bs-panel-heading"><div><span className="bs-kicker">THIS SESSION</span><h3>Recent analyses</h3><p>Results are held in this page session only.</p></div></div>
          {history.map((item, i) => (
            <button className="bs-history-row" key={`${item.name}-${i}`} onClick={() => setResult(item.result)}>
              <div className="bs-history-icon"><FileCheck2 size={17}/></div>
              <span><strong>{item.name}</strong><small>{item.time}</small></span>
              <b>{displayValue(item.result.fields.total_amount_inr?.value, 'total_amount_inr')}</b>
              <ArrowUpRight size={16}/>
            </button>
          ))}
        </section>
      )}
    </div>
  )
}

function ScanIcon() {
  return <RefreshCw size={16}/>
}

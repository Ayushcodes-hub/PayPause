$path = ".\src\App.tsx"
$content = Get-Content $path -Raw

$content = $content.Replace(
  "import BillSense from './components/BillSense'",
  "import BillSense from './components/BillSense'`r`nimport { Payments, Subscriptions, Recovery } from './components/WorkspaceModules'"
)

$content = $content.Replace(
  "          {active === 'BillSense' && <BillSense />}",
  @"
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
"@
)

$content = $content.Replace(
  '          <footer className="footer"><span>Â© 2026 PayPause Technologies</span><span><i/> All systems operational</span><span>Built for financial clarity.</span></footer>',
  '          <footer className="footer"><span>© 2026 PayPause Technologies</span><span><i/> All systems operational</span><span>Built for financial clarity.</span></footer>' + "`r`n          </>)"
)

Set-Content -Path $path -Value $content -Encoding UTF8
Write-Host "Dashboard integration applied." -ForegroundColor Green

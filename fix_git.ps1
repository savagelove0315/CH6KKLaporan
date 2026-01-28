$ignoreLine = 'ch6-koko-system-b10a2206d91a.json'
if (!(Test-Path .gitignore)) { New-Item -ItemType File -Name .gitignore | Out-Null }
if (-not (Select-String -Path .gitignore -Pattern [regex]::Escape($ignoreLine) -Quiet)) {
  Add-Content -Path .gitignore -Value $ignoreLine
}

New-Item -ItemType Directory -Force ..\_local_secrets | Out-Null
if (Test-Path $ignoreLine) { Move-Item $ignoreLine ..\_local_secrets\ -Force }

if (Test-Path .git) { Remove-Item -Recurse -Force .git }

git init
git branch -M main
git add .
git commit -m "initial commit (remove secrets)"
git remote add origin https://github.com/savagelove0315/CH6KKLaporan.git
git fetch origin
git merge origin/main --allow-unrelated-histories -m "merge GitHub main"
git push -u origin main

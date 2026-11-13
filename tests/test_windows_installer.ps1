$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $root "install_windows.ps1"), [ref]$tokens, [ref]$parseErrors
)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
foreach ($function in $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    Invoke-Expression $function.Extent.Text
}

function Assert-True($condition, $message) {
    if (-not $condition) { throw $message }
}

function Get-CimInstance { param($ClassName, $ErrorAction) @() }
$runtime = Detect-TorchRuntime
Assert-True ($runtime.Choice -eq 4 -and $runtime.Suffix -eq "cpu") "No GPU must select CPU."
function Get-CimInstance {
    param($ClassName, $ErrorAction)
    [pscustomobject]@{ Name = "NVIDIA test GPU"; DriverVersion = "536.12" }
}
$runtime = Detect-TorchRuntime
Assert-True ($runtime.Choice -eq 2) "An NVIDIA GPU with a 536 driver must select CUDA 12.1."

function FakeBadPython { $global:LASTEXITCODE = 1 }
$rejected = $false
try { Ensure-Python -Executable "FakeBadPython" } catch { $rejected = $true }
Assert-True $rejected "A Python command with a nonzero exit code must be rejected."

function FakeGoodPython { $global:LASTEXITCODE = 0 }
$selected = @(Ensure-Python -Executable "FakeGoodPython")
Assert-True ($selected.Count -eq 1 -and $selected[0] -eq "FakeGoodPython") "A valid explicit interpreter must be selected."

function py {
    if ($args[0] -eq "-3.12") { $global:LASTEXITCODE = 0 } else { $global:LASTEXITCODE = 1 }
}
$selected = @(Ensure-Python -Executable "py")
Assert-True ($selected.Count -eq 2 -and $selected[1] -eq "-3.12") "Python discovery must skip failed candidates."

if ($IsLinux) {
    $envDir = Join-Path ([System.IO.Path]::GetTempPath()) ("polyvox-installer-test-" + [guid]::NewGuid())
    $scripts = Join-Path $envDir "Scripts"
    New-Item -ItemType Directory -Path $scripts | Out-Null
    $pythonExe = Join-Path $scripts "python.exe"
    $fakePython = @'
#!/bin/sh
case "$1" in
  -c) exit 0 ;;
  -m)
    if [ "$2" = "pip" ]; then
      if [ "$MOCK_ALL_FAIL" = "1" ]; then exit 1; fi
      case "$*" in *download.pytorch.org/whl/cpu*) exit 0 ;; esac
      exit 1
    fi
    exit 7
    ;;
esac
exit 1
'@
    try {
        [System.IO.File]::WriteAllText($pythonExe, $fakePython.Replace("`r`n", "`n") + "`n")
        & chmod +x $pythonExe
        Test-Venv
        $failed = $false
        try { Invoke-InEnv "missing" @() } catch { $failed = $true }
        Assert-True $failed "A failed Python module must stop installation."
        $failed = $false
        $newEnvDir = Join-Path $envDir "new-environment"
        $oldEnvDir = $envDir
        $envDir = $newEnvDir
        try { New-Venv -PyCmd @($pythonExe) } catch { $failed = $true } finally { $envDir = $oldEnvDir }
        Assert-True $failed "A failed venv creation must stop installation."
        $runtime = Get-RuntimeOption "2"
        Install-Torch $runtime
        Assert-True ($runtime.Suffix -eq "cpu" -and $runtime.Index -match "/cpu$") "CPU fallback must be reported correctly."
        $env:MOCK_ALL_FAIL = "1"
        $failed = $false
        try { Install-Torch (Get-RuntimeOption "2") } catch { $failed = $true }
        Assert-True $failed "A failed CPU fallback must stop installation."
    } finally {
        Remove-Item Env:MOCK_ALL_FAIL -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $pythonExe -Force
        Remove-Item -LiteralPath $scripts -Force
        Remove-Item -LiteralPath $envDir -Force
    }
}

Write-Host "Windows installer checks passed."

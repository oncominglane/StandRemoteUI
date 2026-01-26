# make_bundle.ps1
# Creates stand_bundle.zip containing:
#   - server/build/MarathonWS.exe
#   - client/dist/app.exe
#   - PCANBasic.dll (from build or System32)
#   - MSVC runtime DLLs (msvcp140.dll, vcruntime140.dll, vcruntime140_1.dll) from VS Redist
#
# Output:
#   C:\work\StandRemoteUI\bundle_out\stand_bundle.zip
#   C:\work\StandRemoteUI\bundle_out\manifest.txt
#
# Notes:
# - Does NOT copy System32 DLLs except PCANBasic.dll (if needed).
# - Ignores api-ms-win-*/ext-ms-* entries (api-set, not real files to ship).

$ErrorActionPreference = "Stop"

# === CONFIG ===
$Dumpbin = "C:\Program Files\Microsoft Visual Studio\2022\Preview\VC\Tools\MSVC\14.44.35207\bin\Hostx64\x64\dumpbin.exe"

$ServerExe = "C:\work\StandRemoteUI\server\build\MarathonWS.exe"
$ClientExe = "C:\work\StandRemoteUI\client\dist\app.exe"

$VcpkgRoot = "C:\vcpkg"

$OutDir   = "C:\work\StandRemoteUI\bundle_out"
$StageDir = Join-Path $OutDir "stage"
$DistDir  = Join-Path $StageDir "dist"
$ZipOut   = Join-Path $OutDir "stand_bundle.zip"
$Manifest = Join-Path $OutDir "manifest.txt"

# === HELPERS ===
function Ensure-Exists([string]$path, [string]$label) {
  if (-not (Test-Path $path)) { throw "$label not found: $path" }
}

function Get-DumpbinDependents([string]$exePath) {
  $out = & $Dumpbin /nologo /dependents $exePath 2>$null
  if (-not $out) { return @() }

  $dlls = @()
  foreach ($line in $out) {
    $m = [regex]::Match($line, "^\s*([A-Za-z0-9._-]+\.dll)\s*$", "IgnoreCase")
    if ($m.Success) { $dlls += $m.Groups[1].Value }
  }
  return $dlls | Sort-Object -Unique
}

function Is-SystemDllName([string]$dll) {
  $n = $dll.ToLowerInvariant()
  return @(
    "kernel32.dll","ws2_32.dll","user32.dll","gdi32.dll","advapi32.dll","comctl32.dll"
  ) -contains $n
}

function Is-ApiSetName([string]$dll) {
  $n = $dll.ToLowerInvariant()
  return ($n.StartsWith("api-ms-win-") -or $n.StartsWith("ext-ms-"))
}

function Find-FileInDirs([string]$file, [string[]]$dirs) {
  foreach ($d in $dirs) {
    if (-not $d) { continue }
    $cand = Join-Path $d $file
    if (Test-Path $cand) { return (Resolve-Path $cand).Path }
  }
  return $null
}

function Where-First([string]$name) {
  try {
    $res = & where.exe $name 2>$null
    if ($res) {
      foreach ($r in $res) {
        if ($r -and (Test-Path $r)) { return (Resolve-Path $r).Path }
      }
    }
  } catch {}
  return $null
}

function Find-MsvcCrtRedistDir() {
  # Prefer the known VS Preview path; fall back to searching possible roots
  $roots = @(
    "C:\Program Files\Microsoft Visual Studio\2022\Preview\VC\Redist\MSVC",
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Redist\MSVC",
    "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Redist\MSVC",
    "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Redist\MSVC",
    "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Redist\MSVC"
  )

  foreach ($root in $roots) {
    if (-not (Test-Path $root)) { continue }

    $verDirs = Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($v in $verDirs) {
      # Usually this folder exists:
      #   <root>\<ver>\x64\Microsoft.VC143.CRT
      $cand = Join-Path $v.FullName "x64\Microsoft.VC143.CRT"
      if (Test-Path $cand) { return $cand }

      # Some installs also have:
      #   <root>\<ver>\onecore\x64\Microsoft.VC143.CRT
      $cand2 = Join-Path $v.FullName "onecore\x64\Microsoft.VC143.CRT"
      if (Test-Path $cand2) { return $cand2 }
    }
  }

  return $null
}

# === START ===
Write-Host "make_bundle: start"

Ensure-Exists $Dumpbin  "dumpbin.exe"
Ensure-Exists $ServerExe "Server EXE"
Ensure-Exists $ClientExe "Client EXE"

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
if (Test-Path $StageDir) { Remove-Item $StageDir -Recurse -Force }
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

# Copy EXEs
Copy-Item $ServerExe (Join-Path $DistDir "MarathonWS.exe") -Force
Copy-Item $ClientExe (Join-Path $DistDir "app.exe") -Force

# Dependency lists (top-level only)
$serverDeps = Get-DumpbinDependents $ServerExe
$clientDeps = Get-DumpbinDependents $ClientExe

Write-Host "Server deps: $($serverDeps -join ', ')"
Write-Host "Client deps: $($clientDeps -join ', ')"

$need = @()
$need += $serverDeps
$need += $clientDeps
$need = $need | Sort-Object -Unique

# Search paths for non-system DLLs (no System32 here!)
$searchDirs = @(
  (Split-Path $ServerExe -Parent),
  (Split-Path $ClientExe -Parent),
  (Join-Path $VcpkgRoot "installed\x64-windows\bin"),
  (Join-Path $VcpkgRoot "installed\x64-windows\debug\bin")
)

$system32 = "$env:WINDIR\System32"

$copied = New-Object System.Collections.Generic.List[string]
$missing = New-Object System.Collections.Generic.List[string]

# Copy required non-system DLLs
foreach ($dll in $need) {
  if (Is-SystemDllName $dll) { continue }
  if (Is-ApiSetName $dll) { continue }

  $dllLower = $dll.ToLowerInvariant()
  $path = $null

  $path = Find-FileInDirs $dll $searchDirs
  if (-not $path) { $path = Where-First $dll }

  # Special-case: PCANBasic.dll may be in System32 or in PCAN install directory
  if (-not $path -and $dllLower -eq "pcanbasic.dll") {
    $path = Find-FileInDirs $dll @($system32)
  }

  if (-not $path) {
    $missing.Add($dll) | Out-Null
    continue
  }

  # Do NOT copy arbitrary System32 DLLs
  if ($path.ToLowerInvariant().StartsWith($system32.ToLowerInvariant()) -and $dllLower -ne "pcanbasic.dll") {
    continue
  }

  Copy-Item $path (Join-Path $DistDir (Split-Path $path -Leaf)) -Force
  $copied.Add("$dll <- $path") | Out-Null
}

# Force-copy MSVC runtime DLLs from MSVC CRT redist folder (preferred)
$crtDir = Find-MsvcCrtRedistDir
if ($crtDir) {
  foreach ($r in @("msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll")) {
    $p = Join-Path $crtDir $r
    if (Test-Path $p) {
      Copy-Item $p (Join-Path $DistDir $r) -Force
      $copied.Add("$r <- $p") | Out-Null
    } else {
      Write-Warning "Runtime DLL not found in CRT dir: $p"
    }
  }
} else {
  Write-Warning "CRT redist folder not found; runtime DLLs not bundled"
}

# Manifest
$lines = @()
$lines += "Created: $(Get-Date -Format s)"
$lines += "Dumpbin: $Dumpbin"
$lines += "ServerExe: $ServerExe"
$lines += "ClientExe: $ClientExe"
$lines += ""
$lines += "Files in dist:"
Get-ChildItem $DistDir | Sort-Object Name | ForEach-Object { $lines += "  - " + $_.Name }
$lines += ""
$lines += "Copied DLLs:"
if ($copied.Count -gt 0) { $copied | ForEach-Object { $lines += "  " + $_ } } else { $lines += "  (none)" }
$lines += ""
if ($missing.Count -gt 0) {
  $lines += "MISSING DLLs:"
  ($missing | Sort-Object -Unique) | ForEach-Object { $lines += "  - " + $_ }
} else {
  $lines += "Missing DLLs: none"
}

$lines | Set-Content -Encoding ASCII $Manifest

# Zip
if (Test-Path $ZipOut) { Remove-Item $ZipOut -Force }
Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ZipOut -Force

Write-Host "make_bundle: OK"
Write-Host "ZIP: $ZipOut"
Write-Host "Manifest: $Manifest"

if ($missing.Count -gt 0) {
  Write-Warning "Missing DLLs exist. Check manifest.txt"
}
  
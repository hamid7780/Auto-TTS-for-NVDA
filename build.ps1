param(
	[string]$OutputDirectory = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
python (Join-Path $PSScriptRoot "build.py") --output-dir $OutputDirectory
if ($LASTEXITCODE -ne 0) {
	throw "Auto TTS build failed with exit code $LASTEXITCODE"
}

param(
    [ValidateSet('start','stop','status')][string]$Action = 'status',
    [string]$Bin = 'C:\Program Files\PostgreSQL\17\bin',
    [int]$Port = 55432
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$clusterRoot = Join-Path $projectRoot 'private_data\postgres'
$logPath = Join-Path $projectRoot 'private_data\postgres-server.log'
if (-not (Test-Path -LiteralPath (Join-Path $clusterRoot 'PG_VERSION'))) {
    throw 'Cluster is not initialized. See README; this script never initializes or deletes data.'
}
if ($Action -eq 'start') {
    & (Join-Path $Bin 'pg_ctl.exe') -D $clusterRoot -l $logPath -o "-h 127.0.0.1 -p $Port" start
} elseif ($Action -eq 'stop') {
    & (Join-Path $Bin 'pg_ctl.exe') -D $clusterRoot -m fast stop
} else {
    & (Join-Path $Bin 'pg_ctl.exe') -D $clusterRoot status
}
exit $LASTEXITCODE

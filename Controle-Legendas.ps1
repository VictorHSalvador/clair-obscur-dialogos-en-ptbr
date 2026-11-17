[CmdletBinding()]
param(
    [ValidateSet('Ativar', 'Desativar', 'Status')]
    [string]$Acao = 'Status',
    [string]$PastaJogo = ''
)

$ErrorActionPreference = 'Stop'
$nomeMod = 'zzz_ClairObscur_EN_PT_Dialogos_P.pak'
$arquivoPacote = Join-Path $PSScriptRoot 'pacote.json'
if (!(Test-Path -LiteralPath $arquivoPacote -PathType Leaf)) { throw 'pacote.json nao encontrado.' }
$pacote = Get-Content -LiteralPath $arquivoPacote -Raw -Encoding UTF8 | ConvertFrom-Json
$arquivoConfigLocal = Join-Path $PSScriptRoot 'config.local.json'
if ([string]::IsNullOrWhiteSpace($PastaJogo) -and (Test-Path -LiteralPath $arquivoConfigLocal -PathType Leaf)) {
    try {
        $configLocal = Get-Content -LiteralPath $arquivoConfigLocal -Raw -Encoding UTF8 | ConvertFrom-Json
        if (Test-Path -LiteralPath $configLocal.pasta_jogo -PathType Container) { $PastaJogo = $configLocal.pasta_jogo }
    } catch { Write-Verbose 'Configuracao local invalida; selecione a pasta novamente.' }
}
if ([string]::IsNullOrWhiteSpace($PastaJogo)) {
    Add-Type -AssemblyName System.Windows.Forms
    $seletor = New-Object System.Windows.Forms.FolderBrowserDialog
    $seletor.Description = 'Selecione a pasta do jogo que contem a pasta Sandfall (nao a propria pasta Sandfall).'
    $seletor.ShowNewFolderButton = $false
    try {
        if ($seletor.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { Write-Host 'Operacao cancelada; nenhum arquivo foi alterado.'; exit 0 }
        $PastaJogo = $seletor.SelectedPath
    } finally { $seletor.Dispose() }
}
$pastaResolvida = (Resolve-Path -LiteralPath $PastaJogo).Path
$executavel = Join-Path $pastaResolvida 'Sandfall\Binaries\Win64\SandFall-Win64-Shipping.exe'
$pastaPaks = Join-Path $pastaResolvida 'Sandfall\Content\Paks'
if (!(Test-Path -LiteralPath $executavel -PathType Leaf) -or !(Test-Path -LiteralPath $pastaPaks -PathType Container)) {
    throw 'A pasta informada nao corresponde a uma instalacao de Clair Obscur.'
}
@{pasta_jogo=$pastaResolvida} | ConvertTo-Json | Set-Content -LiteralPath $arquivoConfigLocal -Encoding UTF8
$pastaMods = Join-Path $pastaPaks '~mods'
$destino = Join-Path $pastaMods $nomeMod
$desativado = $destino + '.desativado'
$origem = Join-Path $PSScriptRoot $nomeMod

function Confirmar-ArquivoMod([string]$Caminho) {
    if (!(Test-Path -LiteralPath $Caminho -PathType Leaf)) { throw ('Arquivo ausente: ' + $Caminho) }
    $hashAtual = (Get-FileHash -LiteralPath $Caminho -Algorithm SHA256).Hash
    if ($hashAtual -ne $pacote.sha256) { throw ('O arquivo difere deste pacote; nenhuma alteracao foi feita: ' + $Caminho) }
}

if ($Acao -eq 'Status') {
    if (Test-Path -LiteralPath $destino) { Confirmar-ArquivoMod $destino; Write-Host 'Legendas bilingues ATIVAS.' }
    elseif (Test-Path -LiteralPath $desativado) { Confirmar-ArquivoMod $desativado; Write-Host 'Legendas bilingues DESATIVADAS.' }
    else { Write-Host 'Mod ainda nao instalado.' }
    Write-Host ('Pasta do jogo: ' + $pastaResolvida)
    exit 0
}

if (Get-Process -Name 'SandFall-Win64-Shipping' -ErrorAction SilentlyContinue) {
    throw 'Feche o jogo antes de ativar ou desativar as legendas.'
}
if ((Test-Path -LiteralPath $destino) -and (Test-Path -LiteralPath $desativado)) {
    throw 'Existem duas copias do mod na pasta do jogo; nenhuma foi alterada.'
}

if ($Acao -eq 'Ativar') {
    Confirmar-ArquivoMod $origem
    if (Test-Path -LiteralPath $destino) {
        Confirmar-ArquivoMod $destino
        Write-Host 'As legendas bilingues ja estao ativas.'
    } elseif (Test-Path -LiteralPath $desativado) {
        Confirmar-ArquivoMod $desativado
        Move-Item -LiteralPath $desativado -Destination $destino
        Write-Host 'Legendas bilingues ativadas.'
    } else {
        if (!(Test-Path -LiteralPath $pastaMods)) { New-Item -ItemType Directory -Path $pastaMods | Out-Null }
        Copy-Item -LiteralPath $origem -Destination $destino
        Confirmar-ArquivoMod $destino
        Write-Host 'Legendas bilingues instaladas e ativadas.'
    }
    Write-Host 'No jogo: texto Portugues (Brasil), audio Ingles e legendas ativadas.'
} else {
    if (Test-Path -LiteralPath $destino) {
        Confirmar-ArquivoMod $destino
        Move-Item -LiteralPath $destino -Destination $desativado
        Write-Host 'Legendas bilingues desativadas. O texto original sera usado ao abrir o jogo.'
    } elseif (Test-Path -LiteralPath $desativado) {
        Confirmar-ArquivoMod $desativado
        Write-Host 'As legendas bilingues ja estao desativadas.'
    } else {
        Write-Host 'Mod ainda nao instalado; nada foi alterado.'
    }
}

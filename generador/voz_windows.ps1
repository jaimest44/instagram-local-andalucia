# Voz provisional de Windows (OneCore) para las muestras de los reels con voz.
# Uso: powershell -File voz_windows.ps1 -Texto "..." -Salida audio.wav [-Voz Pablo]
param([string]$Texto, [string]$TextoArchivo, [string]$Salida, [string]$Voz = "Pablo")

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]

function Esperar($op, [Type]$tipo) {
  $m = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
  $t = $m.MakeGenericMethod($tipo).Invoke($null, @($op))
  $t.Wait() | Out-Null
  return $t.Result
}

if ($TextoArchivo) { $Texto = [IO.File]::ReadAllText($TextoArchivo, [Text.Encoding]::UTF8) }
$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$s.Voice = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -like "*$Voz*" } | Select-Object -First 1
$s.Options.SpeakingRate = 1.08
$flujo = Esperar ($s.SynthesizeTextToStreamAsync($Texto)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$lector = New-Object Windows.Storage.Streams.DataReader($flujo.GetInputStreamAt(0))
$n = Esperar ($lector.LoadAsync([uint32]$flujo.Size)) ([uint32])
$bytes = New-Object byte[] $n
$lector.ReadBytes($bytes)
[IO.File]::WriteAllBytes($Salida, $bytes)

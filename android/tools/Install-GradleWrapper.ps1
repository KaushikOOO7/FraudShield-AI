$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$wrapperDirectory = Join-Path $taskRoot 'gradle\wrapper'
$wrapperJar = Join-Path $wrapperDirectory 'gradle-wrapper.jar'
$wrapperDownload = Join-Path $wrapperDirectory 'gradle-wrapper.jar.download'
$propertiesPath = Join-Path $wrapperDirectory 'gradle-wrapper.properties'
try {
    $wrapperChecksum = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri 'https://services.gradle.org/distributions/gradle-8.7-wrapper.jar.sha256').Content.Trim().ToLowerInvariant()
    $distributionChecksum = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -Uri 'https://services.gradle.org/distributions/gradle-8.7-bin.zip.sha256').Content.Trim().ToLowerInvariant()
    if ($wrapperChecksum -notmatch '^[a-f0-9]{64}$' -or $distributionChecksum -notmatch '^[a-f0-9]{64}$') {
        throw 'Invalid checksum response from Gradle.'
    }
    Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 -Uri 'https://raw.githubusercontent.com/gradle/gradle/v8.7.0/gradle/wrapper/gradle-wrapper.jar' -OutFile $wrapperDownload
    if ((Get-FileHash -LiteralPath $wrapperDownload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $wrapperChecksum) {
        throw 'Gradle wrapper SHA-256 verification failed.'
    }
    $properties = Get-Content -LiteralPath $propertiesPath | Where-Object { $_ -notmatch '^distributionSha256Sum=' }
    $properties += "distributionSha256Sum=$distributionChecksum"
    [IO.File]::WriteAllLines($propertiesPath, $properties, [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $wrapperDownload -Destination $wrapperJar -Force
    Write-Output 'Official Gradle 8.7 wrapper installed and verified. Commit the JAR and pinned distribution checksum.'
} catch {
    Write-Error ('Cannot bootstrap the Gradle wrapper: ' + $_.Exception.Message)
    exit 1
}

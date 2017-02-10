# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # APPVEYOR DOWNLOADER                                                 # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

$URL = $args[0]
$DST = $args[1]

# try download up to 3 times in case of network transient errors
$webclient = (New-Object System.Net.WebClient)
$retry_attempts = 3
for ($i = 0; $i -Lt $retry_attempts; $i++) {
    try {
        $webclient.DownloadFile("$URL", "$DST")
        break
    } catch [Exception] {
        if ($i + 1 -Eq $retry_attempts) {
            throw
        } else {
            Start-Sleep 1
        }
    }
}

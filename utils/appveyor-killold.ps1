# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # APPVEYOR KILL OLD                                                   # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

# If there is a newer build queued for the same PR, cancel this one.
# The AppVeyor 'rollout builds' option is supposed to serve the same
# purpose but it is problematic because it tends to cancel builds pushed
# directly to master instead of just PR builds (or the converse).
# credits: JuliaLang developers.
$_NEWEST = "https://ci.appveyor.com/api/projects/${env:APPVEYOR_ACCOUNT_NAME}/${env:APPVEYOR_PROJECT_SLUG}/history?recordsNumber=50"
$_NEWEST = ((Invoke-RestMethod $_NEWEST).builds | Where-Object pullRequestId)
$_NEWEST = ($_NEWEST -Eq $env:APPVEYOR_PULL_REQUEST_NUMBER)[0].buildNumber
if ($env:APPVEYOR_PULL_REQUEST_NUMBER -And $env:APPVEYOR_BUILD_NUMBER -Ne $_NEWEST) {
    throw "There are newer queued builds for this pull request, failing early."
}

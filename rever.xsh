$ACTIVITIES = [
    "authors",
    "changelog",
]

#
# Basic settings
#
$PROJECT = $GITHUB_REPO = "conda"
$GITHUB_ORG = "conda"
$AUTHORS_FILENAME = "AUTHORS.md"
$AUTHORS_SORTBY = 'alpha'

#
# Changelog settings
#
$CHANGELOG_FILENAME = "CHANGELOG.md"
$CHANGELOG_PATTERN = "[//]: # (current developments)"
$CHANGELOG_HEADER = """[//]: # (current developments)

## $VERSION ($RELEASE_DATE)

"""
$CHANGELOG_CATEGORIES = (
    "Enhancements",
    "Bug fixes",
    "Deprecations",
    "Docs",
    "Other",
)
$CHANGELOG_CATEGORY_TITLE_FORMAT = '### {category}\n\n'

$CHANGELOG_AUTHORS_TITLE = "Contributors"
$CHANGELOG_AUTHORS_FORMAT = "* @{name}\n"

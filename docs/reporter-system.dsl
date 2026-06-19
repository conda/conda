workspace "conda Reporter System" "Models the conda reporter system across C4 levels: System Context, Container, and Component." {

    model {

        # --- Actors / External elements ---

        user = person "conda User" "A developer or system script that invokes conda commands (install, update, search, etc.)."

        # --- Software Systems ---

        condaSystem = softwareSystem "conda Process" "The conda package manager process. Resolves, downloads, and installs packages." {

            # --- Containers ---

            businessLogic = container "Business Logic" "Performs core conda operations: solving the package graph, downloading and extracting packages, linking into environments, and driving the CLI." "Python (conda.solve, conda.install, conda.cli, ...)"

            reporterSingleton = container "CondaReporter" "Process-wide singleton. Holds a reference to the active renderer, owns the event dispatch table, serialises fetch-progress events via a threading.Lock, and exposes send() and prompt()." "Python (conda.reporters)" {

                # --- Components ---

                dispatchTable = component "Dispatch Table (_DISPATCH)" "Maps each event type to the corresponding render_* method name on the active renderer. Single point of routing for all events."
                lock = component "Threading Lock" "Serialises concurrent FetchTaskProgressEvent calls from worker threads so tqdm state is never corrupted."
                moduleHelpers = component "Module-level Helpers" "get_reporter(), get_spinner(), render(), confirm_yn() — convenience wrappers used by business logic."
                promptMethod = component "prompt()" "Synchronous, returns a value. Not routed through send() because it has a different interaction shape (request/response rather than fire-and-forget)."
            }

            rendererBase = container "ReporterRendererBase" "Abstract base class — the plugin contract. Defines ten render_* no-op defaults plus one abstract prompt(). Plugin authors implement this interface." "Python (conda.plugins.types)" {

                renderData = component "render_data()" "Renders arbitrary structured data to the output medium."
                renderDetailView = component "render_detail_view()" "Renders a detailed key/value view of a single item."
                renderEnvsList = component "render_envs_list()" "Renders the list of conda environments."
                renderSpinner = component "render_spinner_start/end()" "Starts and stops an indeterminate progress spinner."
                renderFetchSection = component "render_fetch_section_start/end()" "Opens and closes the fetch progress section (e.g. 'Downloading and Extracting Packages:')."
                renderFetchTask = component "render_fetch_task_start/progress/end()" "Creates, updates (0–100%), and finalises a single per-package progress bar."
            }

            eventRegistry = container "Event Registry" "Frozen dataclasses — safe to pass across threads. Canonical registry of all typed events the system understands." "Python (conda.plugins.reporter_backends.events)" {

                outputEvents = component "Output Events" "RenderDataEvent · DetailViewEvent · EnvsListEvent"
                spinnerEvents = component "Spinner Events" "SpinnerStartEvent · SpinnerEndEvent"
                fetchEvents = component "Fetch Events" "FetchSectionStartEvent · FetchSectionEndEvent · FetchTaskStartEvent · FetchTaskProgressEvent · FetchTaskEndEvent"
            }

            consoleRenderer = container "ConsoleReporterRenderer" "Default TTY renderer ('classic' backend). Uses tqdm progress bars and animated spinners. Falls back gracefully in quiet mode." "Python (conda.plugins.reporter_backends.console)"

            jsonRenderer = container "JSONReporterRenderer" "Machine-readable newline-delimited JSON output ('json' backend, activated by --json). Silent spinners. No-op prompts." "Python (conda.plugins.reporter_backends.json)"

            richRenderer = container "RichReporterRenderer" "Rich terminal UI ('rich' backend, opt-in via .condarc console: rich). Animated spinners, unified progress panel, Rich prompts." "Python (conda_rich.hooks)"

            pluggyHookspec = container "pluggy Hookspec" "conda_reporter_backends registration point. Plugin authors register new ReporterRendererBase implementations here." "Python (conda.plugins.hookspec)"

            stdout = container "stdout / stderr" "Terminal output streams that renderers write to." "OS I/O"
        }

        dotCondarc = softwareSystem ".condarc / CLI flags" "User configuration. 'console: rich' selects the Rich backend; '--json' selects JSON. Drives backend selection when CondaReporter is (re-)initialised." "External"

        # --- Relationships ---

        # Context level
        user -> condaSystem "Runs conda commands"
        dotCondarc -> condaSystem "Configures active renderer backend"

        # Business logic → reporter
        businessLogic -> reporterSingleton "Calls get_reporter(), send(event), get_spinner()" "Python function call"

        # Reporter → renderer dispatch
        reporterSingleton -> rendererBase "Dispatches render_* calls to active renderer instance" "Dynamic method dispatch"

        # Reporter internals
        moduleHelpers -> dispatchTable "Looks up method name for event type"
        moduleHelpers -> lock "Acquires lock before calling renderer for fetch-progress events"
        dispatchTable -> rendererBase "Resolves to render_* method"

        # Event flow
        businessLogic -> eventRegistry "Constructs and emits typed events" "dataclass instantiation"
        reporterSingleton -> eventRegistry "Receives events via send()"

        # Renderer implementations
        rendererBase -> consoleRenderer "Implemented by"
        rendererBase -> jsonRenderer "Implemented by"
        rendererBase -> richRenderer "Implemented by"

        # Renderers → output
        consoleRenderer -> stdout "Writes tqdm bars and spinner text"
        jsonRenderer -> stdout "Writes newline-delimited JSON"
        richRenderer -> stdout "Writes Rich-rendered panels"

        # Plugin registration
        consoleRenderer -> pluggyHookspec "Registered via CondaReporterBackend hook"
        jsonRenderer -> pluggyHookspec "Registered via CondaReporterBackend hook"
        richRenderer -> pluggyHookspec "Registered via CondaReporterBackend hook"
        reporterSingleton -> pluggyHookspec "Queries for available backends on initialisation"

        # Context → reporter (backend selection)
        dotCondarc -> reporterSingleton "Selects backend; triggers singleton reset"
    }

    views {

        # C4 Level 1 — System Context
        systemContext condaSystem "SystemContext" "C4 Level 1 — System Context: conda and its external actors." {
            include *
            autoLayout
        }

        # C4 Level 2 — Container
        container condaSystem "Containers" "C4 Level 2 — Containers inside the conda process." {
            include *
            autoLayout
        }

        # C4 Level 3 — Component: CondaReporter
        component reporterSingleton "Components_CondaReporter" "C4 Level 3 — Internal components of CondaReporter." {
            include *
            autoLayout
        }

        # C4 Level 3 — Component: ReporterRendererBase
        component rendererBase "Components_RendererBase" "C4 Level 3 — Render methods defined by ReporterRendererBase." {
            include *
            autoLayout
        }

        # C4 Level 3 — Component: Event Registry
        component eventRegistry "Components_EventRegistry" "C4 Level 3 — Typed event dataclasses in the event registry." {
            include *
            autoLayout
        }

        styles {
            element "Person" {
                shape Person
                background #08427B
                color #ffffff
            }
            element "Software System" {
                background #1168BD
                color #ffffff
            }
            element "Container" {
                background #438DD5
                color #ffffff
            }
            element "Component" {
                background #85BBF0
                color #000000
            }
            element "External" {
                background #999999
                color #ffffff
            }
        }
    }

}

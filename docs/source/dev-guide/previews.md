# Previews

Previews in conda help ensure maintainers can develop in an agile and nimble manner
that increases the velocity of releasing new features. These features are hidden
behind a configuration variable called, `preview`, and allow users to opt in
to new functionality. During the preview stage of development, we'll typically
solicit lots of user feedback that will be directly fed into our development
process. When we're finally confident that we've got something everyone will
love, we'll integrate the preview as a core component of conda.

The previews themselves reside in the {mod}`conda._preview` module. Within
this module, you'll find various feature modules that we're experimenting
with (e.g. {mod}`conda._preview.env_setup` contains a set of new commands overriding
the traditional environment creation and management process). Preview modules
can mirror the top-level `conda` module where that makes graduation easier, but
CLI entry points should still be wired through conda's plugin framework.


:::{warning}

Everything in the preview modules should be regarded as highly-experimental. These
APIs are not stable and should not be relied upon!

:::

To enable these modules, we make use of the `preview` configuration parameter that
holds a list of preview features to enable. Shown below is a `.condarc` file with
the `env-setup` feature enabled:

```yaml
preview:
  - env-setup
```

## Guidelines for creating previews

1. It is highly recommended to first draft a proposal as a feature request
   or as a collection of issues before creating a preview.
2. When creating your own preview feature, please use snake-case for the module name and
   kebab-case for the name that appears in the configuration file.
3. Preview subcommands should be exposed through `conda.plugins.previews`, which gates
   bundled preview hook implementations with their matching preview label.

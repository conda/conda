# Releasing

Conda's releases may be performed via the [rever command](https://regro.github.io/rever-docs/).
Rever is configured to perform the activities for a typical conda release.
To cut a release, simply run `rever <X.Y.Z>` where `<X.Y.Z>` is the
release number that you want bump to. For example, `rever 1.2.3`.

However, it is always good idea to make sure that the you have permissions
everywhere to actually perform the release. So it is customary to run
`rever check` before the release, just to make sure.

The standard workflow is thus:

```bash
$ rever check
$ rever 1.2.3
```

If for some reason a release fails partway through, or you want to claw back a
release that you have made, rever allows you to undo activities. If you find yourself
in this pickle, you can pass the `--undo` option a comma-separated list of
activities you'd like to undo. For example:

```bash
$ rever --undo tag,changelog,authors 1.2.3
```

Happy releasing!

```python
from argparse import _SubParsersAction, Namespace, ArgumentParser

from dialog_match.cli.util.str_utils import dals


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    descr = "..."
    example = dals(
        """
        Examples:
            ...
        """
    )
    p = sub_parsers.add_parser(
        "...", description=descr, help=descr, epilog=example, **kwargs
    )

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    ...
    return 0
```

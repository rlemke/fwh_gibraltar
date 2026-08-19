"""Handler registration aggregator for the gibraltar domain."""

__all__ = ["register_all_handlers", "register_all_registry_handlers"]


def register_all_handlers(poller) -> None:
    from .gibraltar_handlers import register_gibraltar_handlers as reg

    reg(poller)


def register_all_registry_handlers(runner) -> None:
    from .gibraltar_handlers import register_handlers as reg

    reg(runner)

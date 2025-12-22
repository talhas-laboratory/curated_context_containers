"""Services package for MCP server."""

# Avoid eager imports to prevent circular/module load issues during test discovery,
# but still expose submodules when accessed.
__all__ = [
    "admin",
    "agent_tracking",
    "collaboration",
    "containers",
    "diagnostics",
    "documents",
    "fusion",
    "graph",
    "graph_nl2cypher",
    "jobs",
    "lifecycle",
    "manifests",
    "search",
]

_lazy_modules = set(__all__)


def __getattr__(name):
    if name in _lazy_modules:
        import importlib

        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals().keys()) + list(_lazy_modules))


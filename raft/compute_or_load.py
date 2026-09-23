"""``compute_or_load`` decorator, shared by Project and Experiment scopes."""

import functools


def make_compute_or_load(scope):
    """Build a ``compute_or_load`` decorator bound to a specific scope.

    The returned decorator takes an artifact name and wraps a zero-arg
    function. First call runs the function, saves the result via ``scope.save``,
    and returns it. Later calls return ``scope.load`` of the same artifact.

    Parameters
    ----------
    scope : Project or Experiment
        Provides ``save``, ``load``, and ``has`` methods.

    Returns
    -------
    callable
        Decorator: ``@scope.compute_or_load("name")``.
    """
    def decorator(artifact_name):
        def wrap(fn):
            @functools.wraps(fn)
            def wrapper():
                if scope.has(artifact_name):
                    return scope.load(artifact_name)
                value = fn()
                scope.save(value, artifact_name)
                return value
            return wrapper
        return wrap
    return decorator

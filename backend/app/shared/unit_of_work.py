from contextlib import contextmanager

@contextmanager
def unit_of_work(factory):
    """One use case owns one transaction. Exceptions always roll it back."""
    with factory() as session:
        with session.begin():
            yield session

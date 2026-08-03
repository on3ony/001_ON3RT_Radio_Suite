"""
Tests de libraries/cat/cat_adapters/base.py (CatAdapter).

Contrat minimal : une sous-classe concrète doit implémenter start() et
stop(). La classe de base elle-même ne fait rien d'utilisable --
lève NotImplementedError, comme LiveDataSource
(apps/dashboard/data_sources/base.py).
"""

import pytest

from libraries.cat.cat_adapters import CatAdapter


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_start_raises_not_implemented_on_the_base_contract(qapp):
    adapter = CatAdapter()

    with pytest.raises(NotImplementedError):
        adapter.start()


def test_stop_raises_not_implemented_on_the_base_contract(qapp):
    adapter = CatAdapter()

    with pytest.raises(NotImplementedError):
        adapter.stop()

from src.domain.entities.matrix import Matrix
from src.infrastructure.selection.configured_selection import ConfiguredMatrixSelection
from tests.application.conftest import make_matrix


def test_configured_selection_all():
    sel = ConfiguredMatrixSelection(names="*")
    matrices = [make_matrix("A"), make_matrix("B")]
    assert sel.select(matrices) == ["A", "B"]


def test_configured_selection_filtered():
    sel = ConfiguredMatrixSelection(names="A")
    matrices = [make_matrix("A"), make_matrix("B")]
    assert sel.select(matrices) == ["A"]

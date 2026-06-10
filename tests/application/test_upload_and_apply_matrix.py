import asyncio
from datetime import datetime

from src.application.use_cases.deploy.upload_and_apply_matrix import UploadAndApplyMatrixUseCase
from src.domain.exceptions import UploadMatrixError
from tests.application.conftest import (
    FakeApplyPort,
    FakeBindPort,
    FakeDownloadPort,
    FakeUploadPort,
    make_machine,
    make_matrix,
)


def test_upload_and_apply_happy_path():
    upload = FakeUploadPort()
    bind = FakeBindPort()
    download = FakeDownloadPort()
    apply_port = FakeApplyPort()
    uc = UploadAndApplyMatrixUseCase(
        upload_matrix_port=upload,
        bind_matrix_to_machine_port=bind,
        download_matrix_to_machine_port=download,
        apply_matrix_to_machine_port=apply_port,
        validate_matrices=True,
    )
    asyncio.run(uc.execute(make_matrix(), [make_machine()], datetime(2026, 6, 10)))
    assert len(upload.calls) == 1
    assert bind.calls == 1
    assert download.calls == 1
    assert apply_port.calls == 1


def test_upload_failure_raises():
    upload = FakeUploadPort(result=None)
    uc = UploadAndApplyMatrixUseCase(
        upload_matrix_port=upload,
        bind_matrix_to_machine_port=FakeBindPort(),
        download_matrix_to_machine_port=FakeDownloadPort(),
        apply_matrix_to_machine_port=FakeApplyPort(),
        validate_matrices=False,
    )
    try:
        asyncio.run(uc.execute(make_matrix(), [make_machine()], datetime(2026, 6, 10)))
        assert False, "expected UploadMatrixError"
    except UploadMatrixError:
        pass

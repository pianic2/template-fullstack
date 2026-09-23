from django.conf import settings


def test_request_and_upload_limits_are_bounded():
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE == 2_621_440
    assert settings.DATA_UPLOAD_MAX_NUMBER_FIELDS == 1_000
    assert settings.DATA_UPLOAD_MAX_NUMBER_FILES == 20
    assert settings.FILE_UPLOAD_MAX_MEMORY_SIZE == 2_621_440

import json
import pathlib
from unittest import mock

import pytest

from music.models import Song


@pytest.fixture
def gcs_bucket_mock(monkeypatch):
    # Patch the gcs_bucket used in models to use a mock
    bucket_mock = mock.Mock()
    monkeypatch.setattr("music.models.gcs_bucket", bucket_mock)
    return bucket_mock


@pytest.fixture
def song_factory(db):
    def factory(files):
        return Song.objects.create(
            name="Test Song",
            slug="test-song",
            files=json.dumps(files),
        )

    return factory


def test_file_urls_mixed_files_params(gcs_bucket_mock, song_factory):
    files = ["score.pdf", "audio.mp3"]
    song = song_factory(files)

    # Each file gets its own blob mock
    pdf_blob_mock = mock.Mock()
    pdf_blob_mock.generate_signed_url.return_value = "signed-url-pdf"
    mp3_blob_mock = mock.Mock()
    mp3_blob_mock.generate_signed_url.return_value = "signed-url-mp3"

    def blob_side_effect(file):
        if file == "score.pdf":
            return pdf_blob_mock
        elif file == "audio.mp3":
            return mp3_blob_mock
        else:
            raise ValueError("Unexpected file")

    gcs_bucket_mock.blob.side_effect = blob_side_effect

    result = song.file_urls

    # PDF: two calls with correct params
    expected_pdf_calls = [
        mock.call(response_disposition="attachment", expiration=mock.ANY),
        mock.call(response_disposition="inline", expiration=mock.ANY),
    ]
    pdf_blob_mock.generate_signed_url.assert_has_calls(
        expected_pdf_calls,
        any_order=False
    )

    # MP3: one call with correct params
    mp3_blob_mock.generate_signed_url.assert_called_once_with(
        response_disposition="attachment",
        expiration=mock.ANY
    )

    expected = [
        {
            "url": "signed-url-pdf",
            "path": pathlib.Path("score.pdf"),
            "preview": "signed-url-pdf",
        },
        {
            "url": "signed-url-mp3",
            "path": pathlib.Path("audio.mp3"),
        },
    ]
    assert result == expected


def test_file_urls_sorts_pdf_first_and_by_name(gcs_bucket_mock, song_factory):
    files = ["b.mp3", "a.pdf", "c.pdf", "a.mp3"]
    song = song_factory(files)

    # Create a blob mock for each file
    blob_mocks = {fname: mock.Mock() for fname in files}
    for fname, blob in blob_mocks.items():
        blob.generate_signed_url.return_value = f"signed-{fname}"

    def blob_side_effect(fname):
        return blob_mocks[fname]

    gcs_bucket_mock.blob.side_effect = blob_side_effect

    result = song.file_urls
    sorted_paths = [entry["path"].name for entry in result]

    # Expected: PDFs first, sorted by name; then MP3s, sorted by name
    expected_order = ["a.pdf", "c.pdf", "a.mp3", "b.mp3"]
    assert sorted_paths == expected_order

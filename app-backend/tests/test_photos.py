import io
from datetime import date

import pytest
from PIL import ExifTags, Image

from core.errors import InvalidInput
from core.storage.local import LocalPhotoStore
from models import Task, TaskAssignment, TaskSubmission
from services import photos, rate_limits
from tests.factories import count

ORIENTATION = 0x0112


def image_bytes(size=(40, 20), format="JPEG", mode="RGB", exif=None, **options):
    out = io.BytesIO()
    image = Image.new(mode, size, "red" if mode == "RGB" else 0)
    if exif is not None:
        options["exif"] = exif
    image.save(out, format, **options)
    return out.getvalue()


def phone_photo():
    """A JPEG with a GPS location, taken with the phone turned sideways."""
    exif = Image.Exif()
    exif[ORIENTATION] = 6
    exif.get_ifd(ExifTags.IFD.GPSInfo).update(
        {
            ExifTags.GPS.GPSLatitudeRef: "N",
            ExifTags.GPS.GPSLatitude: (59.0, 19.0, 46.0),
        }
    )
    return image_bytes((40, 20), exif=exif)


class TestClean:
    def test_drops_metadata_and_applies_rotation(self):
        cleaned = photos.clean(phone_photo())

        image = Image.open(io.BytesIO(cleaned))
        assert image.format == "JPEG"
        assert image.size == (20, 40)
        assert dict(image.getexif()) == {}
        assert b"Exif" not in cleaned

    def test_shrinks_to_the_longest_side(self):
        cleaned = photos.clean(image_bytes((4096, 1024)))

        assert Image.open(io.BytesIO(cleaned)).size == (2048, 512)

    @pytest.mark.parametrize("format", ["PNG", "WEBP"])
    def test_converts_to_jpeg(self, format):
        cleaned = photos.clean(image_bytes(format=format, mode="RGBA"))

        image = Image.open(io.BytesIO(cleaned))
        assert (image.format, image.mode) == ("JPEG", "RGB")

    @pytest.mark.parametrize(
        "data",
        [b"not an image", image_bytes(format="GIF"), image_bytes()[:200]],
        ids=["text", "gif", "truncated"],
    )
    def test_rejects_other_files(self, data):
        with pytest.raises(InvalidInput):
            photos.clean(data)

    def test_rejects_too_many_pixels(self):
        with pytest.raises(InvalidInput, match="too many pixels"):
            photos.clean(image_bytes((8000, 8000), format="PNG", mode="1"))

    def test_read_upload_rejects_large_files(self):
        with pytest.raises(InvalidInput, match="10 MB"):
            photos.read_upload(io.BytesIO(b"x" * (photos.MAX_BYTES + 1)))


class TestLocalStore:
    def test_saves_reads_and_deletes(self, tmp_path):
        store = LocalPhotoStore(tmp_path)

        store.save("home/one.jpg", b"photo")
        assert store.read("home/one.jpg") == b"photo"
        store.delete(["home/one.jpg", "home/missing.jpg"])
        assert store.read("home/one.jpg") is None

    def test_rejects_paths_outside_the_folder(self, tmp_path):
        store = LocalPhotoStore(tmp_path / "photos")

        with pytest.raises(ValueError):
            store.save("../secret.jpg", b"photo")


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com")


@pytest.fixture
def household(mom, make_household):
    return make_household(mom)


@pytest.fixture
def lia(make_kid, household):
    return make_kid(household)


@pytest.fixture
def task(db, household, lia):
    task = Task(
        household_id=household.id,
        title="Dishes",
        reward=5,
        starts_on=date(2026, 1, 1),
        assignments=[TaskAssignment(kid_id=lia.id)],
    )
    db.add(task)
    db.commit()
    return task


@pytest.fixture
def submit(client, household, lia, task, auth_headers):
    def send(photo, task_id=None):
        return client.post(
            f"/households/{household.id}/me/tasks/{task_id or task.id}/submissions",
            files={"photo": ("photo.jpg", photo, "image/jpeg")},
            headers=auth_headers(lia),
        )

    return send


def photo_url(household, submission_id):
    return f"/households/{household.id}/task-submissions/{submission_id}/photo"


def test_submit_with_a_photo_stores_a_clean_copy(
    client, db, submit, household, photo_store, mom, auth_headers
):
    response = submit(phone_photo())

    assert response.status_code == 201
    assert response.json()["has_photo"] is True
    submission = db.get(TaskSubmission, response.json()["id"])
    assert submission.photo_path == f"{household.id}/{submission.id}.jpg"
    stored = photo_store.files[submission.photo_path]
    assert b"Exif" not in stored

    photo = client.get(photo_url(household, submission.id), headers=auth_headers(mom))
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.content == stored
    parent_view = client.get(
        f"/households/{household.id}/task-submissions/{submission.id}",
        headers=auth_headers(mom),
    )
    assert parent_view.json()["has_photo"] is True


def test_submit_with_a_file_that_is_not_an_image(db, submit, photo_store, task):
    response = submit(b"<html></html>")

    assert response.status_code == 422
    assert response.json()["detail"] == photos.NOT_AN_IMAGE
    assert count(db, TaskSubmission, task_id=task.id) == 0
    assert photo_store.files == {}


def test_submit_with_a_file_that_is_too_large(submit):
    response = submit(b"x" * (photos.MAX_BYTES + 1))

    assert response.status_code == 422
    assert response.json()["detail"] == photos.TOO_LARGE


def test_photo_uploads_are_limited_per_kid(db, submit, lia):
    for _ in range(rate_limits.PHOTO_UPLOADS_PER_KID.max_events):
        rate_limits.record(db, rate_limits.PHOTO_UPLOADS_PER_KID, str(lia.id))
    db.commit()

    assert submit(image_bytes()).status_code == 429


def test_photo_of_a_submission_without_one_gives_404(
    client, db, household, lia, task, mom, auth_headers
):
    submission = TaskSubmission(
        task_id=task.id, kid_id=lia.id, period_start=task.starts_on
    )
    db.add(submission)
    db.commit()

    response = client.get(
        photo_url(household, submission.id), headers=auth_headers(mom)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "This submission has no photo"


def test_removing_a_kid_deletes_their_photos(
    client, submit, household, lia, mom, auth_headers, photo_store
):
    submit(image_bytes())
    assert len(photo_store.files) == 1

    client.delete(
        f"/households/{household.id}/kids/{lia.id}", headers=auth_headers(mom)
    )

    assert photo_store.files == {}


def test_deleting_a_household_deletes_its_photos(
    client, submit, household, mom, auth_headers, photo_store
):
    submit(image_bytes())
    photo_store.save("another-household/photo.jpg", b"photo")

    response = client.request(
        "DELETE",
        f"/households/{household.id}",
        json={"confirm_name": household.name},
        headers=auth_headers(mom),
    )

    assert response.status_code == 204
    assert list(photo_store.files) == ["another-household/photo.jpg"]

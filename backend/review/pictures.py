"""
The pictures of a review (#105): the limits and the writes, shared by the review creation and
`POST /api/reviews/{id}/pictures`. Every picture is a `ReviewPicture` row whose `WebPImageField` converts the
upload to WebP and stores it under `reviews/<review_id>/` (AD-003).
"""
from hairmatch.problems import body_error

from .models import ReviewPicture

MAX_REVIEW_PICTURES = 5
REVIEW_PICTURE_MAX_SIZE = 5 * 1024 * 1024
INVALID_REVIEW_PICTURE_DETAIL = 'The review picture is not a valid image.'


def picture_errors(files, existing=0, required=False):
    """
    The `errors` items for the uploaded `files` of a review that already has `existing` pictures: none, or
    the first of "required", "too many" and "too big". It never opens a file, so a big upload costs nothing.
    """
    if required and not files:
        return [body_error('pictures', 'This field is required.')]
    if existing + len(files) > MAX_REVIEW_PICTURES:
        return [body_error('pictures', f'A review can have at most {MAX_REVIEW_PICTURES} pictures.')]
    if any(file.size > REVIEW_PICTURE_MAX_SIZE for file in files):
        return [body_error('pictures', 'Each picture must have at most 5 MB.')]
    return []


def add_review_pictures(review, files, saved_names):
    """
    Stores `files`, in order, as pictures of `review`. Each stored name is appended to `saved_names` right after
    its row is created, so the caller can delete the objects of a request that fails later. An undecodable file
    raises InvalidImage.
    """
    for file in files:
        picture = ReviewPicture.objects.create(review=review, picture=file)
        saved_names.append(picture.picture.name)


def picture_names(queryset):
    """The storage names of the pictures in `queryset`."""
    return [name for name in queryset.values_list('picture', flat=True) if name]

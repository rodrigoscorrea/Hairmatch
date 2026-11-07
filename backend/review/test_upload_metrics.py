from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from hairmatch import testing_telemetry
from hairmatch.image_fixtures import make_upload
from review.models import Review, ReviewPicture
from review.pictures import MAX_REVIEW_PICTURES, REVIEW_PICTURE_MAX_SIZE
from review.tests import ReviewsTestCase

NOT_AN_IMAGE = b'this is not an image' * 10


def png(name='a.png'):
    return make_upload(name, fmt='PNG')


class ReviewUploadCounterTests(testing_telemetry.TelemetryMixin, ReviewsTestCase):
    """TEL-56 for the pictures of a review: when the review is created and when pictures are added."""

    def setUp(self):
        super().setUp()
        self.login_as_customer()
        self.client.raise_request_exception = False
        self.review = Review.objects.create(rating=5, customer=self.customer, hairdresser=self.hairdresser)
        self.add_url = reverse('review_pictures', args=[self.review.id])
        testing_telemetry.clear()

    def uploads(self):
        return sorted((a['kind'], a['outcome'], value) for a, value in self.points('hairmatch.uploads'))

    def add(self, files):
        return self.client.post(self.add_url, data={'pictures': files} if files is not None else {})

    def create(self, files=None):
        data = {'rating': 5, 'comment': 'ok', 'hairdresser': self.hairdresser.id, 'reserve': self.reserve.id}
        if files is not None:
            data['pictures'] = files
        return self.client.post(self.create_url, data=data)

    def test_adding_valid_pictures_counts_one_review_stored(self):
        self.assertEqual(self.add([png('a.png'), png('b.png')]).status_code, 201)
        self.assertEqual(self.uploads(), [('review', 'stored', 1)])

    def test_adding_a_file_that_is_no_image_counts_invalid_image(self):
        bad = SimpleUploadedFile('a.png', NOT_AN_IMAGE, content_type='image/png')
        self.assertEqual(self.add([bad]).status_code, 400)
        self.assertEqual(self.uploads(), [('review', 'invalid_image', 1)])

    def test_adding_a_file_over_5_mb_counts_invalid_image_once(self):
        big = SimpleUploadedFile('a.png', b'\0' * (REVIEW_PICTURE_MAX_SIZE + 1), content_type='image/png')
        self.assertEqual(self.add([big]).status_code, 400)
        self.assertEqual(self.uploads(), [('review', 'invalid_image', 1)])

    def test_a_save_that_breaks_counts_failed(self):
        with patch.object(ReviewPicture.objects, 'create', side_effect=RuntimeError('db down')):
            self.assertEqual(self.add([png()]).status_code, 500)
        self.assertEqual(self.uploads(), [('review', 'failed', 1)])

    def test_refusals_by_the_rules_count_nothing(self):
        too_many = [png(f'{i}.png') for i in range(MAX_REVIEW_PICTURES + 1)]
        self.assertEqual(self.add(too_many).status_code, 400)
        missing_review = reverse('review_pictures', args=[self.review.id + 999])
        self.assertEqual(self.client.post(missing_review, data={'pictures': [png()]}).status_code, 404)
        self.assertEqual(self.add(None).status_code, 400)
        self.assertEqual(self.uploads(), [])

    def test_a_review_created_with_pictures_counts_one_stored(self):
        self.assertEqual(self.create([png('a.png'), png('b.png')]).status_code, 201)
        self.assertEqual(self.uploads(), [('review', 'stored', 1)])

    def test_a_review_created_without_pictures_is_not_an_upload(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.uploads(), [])

    def test_a_review_created_with_a_bad_picture_counts_invalid_image(self):
        bad = SimpleUploadedFile('a.png', NOT_AN_IMAGE, content_type='image/png')
        self.assertEqual(self.create([bad]).status_code, 400)
        self.assertEqual(self.uploads(), [('review', 'invalid_image', 1)])
        self.assertEqual(Review.objects.count(), 1)  # only the one of setUp

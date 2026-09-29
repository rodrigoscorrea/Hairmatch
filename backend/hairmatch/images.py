import io
import os

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.fields.files import ImageFieldFile
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_SIDE = 1080
WEBP_QUALITY = 80

ALPHA_MODES = ('RGBA', 'LA', 'La', 'PA', 'RGBa')


class InvalidImage(ValueError):
    """The upload is not an image Pillow can decode (or is truncated or too large)."""


def webp_name(name):
    return os.path.splitext(name)[0] + '.webp'


def _rgb_icc_profile(info):
    # The output is always RGB(A), so a CMYK or gray profile would mislabel its colors.
    # SPEC_DEVIATION: the spec keeps the ICC profile unconditionally.
    # Reason: a profile of another color space is invalid for the RGB output.
    profile = info.get('icc_profile')
    if profile and profile[16:20] == b'RGB ':
        return profile
    return None


def to_webp(content):
    """Convert an uploaded image into a static WebP of at most MAX_SIDE px."""
    content.seek(0)
    try:
        with Image.open(content) as original:
            # Only affects JPEG: decodes at a reduced scale, always above the target size.
            original.draft('RGB', (MAX_SIDE, MAX_SIDE))
            icc_profile = _rgb_icc_profile(original.info)
            image = ImageOps.exif_transpose(original)

        has_alpha = image.mode in ALPHA_MODES or 'transparency' in image.info
        image = image.convert('RGBA' if has_alpha else 'RGB')
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)

        # exif_transpose leaves the EXIF (GPS included) in image.info, so it is dropped explicitly.
        options = {'quality': WEBP_QUALITY, 'method': 4, 'exif': b''}
        if icc_profile:
            options['icc_profile'] = icc_profile
        buffer = io.BytesIO()
        image.save(buffer, 'WEBP', **options)
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise InvalidImage(str(exc)) from exc
    return ContentFile(buffer.getvalue())


class WebPImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True):
        # Converts before the storage sees the file, so the original is never uploaded.
        super().save(webp_name(name), to_webp(content), save)


class WebPImageField(models.ImageField):
    """ImageField that stores every uploaded image as WebP."""

    attr_class = WebPImageFieldFile

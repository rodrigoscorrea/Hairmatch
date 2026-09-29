"""
Real in-memory images for tests, so no binary files live in the repository.

This is not a `test*` module on purpose: importing helpers from another app's
tests.py would make the Django runner execute those test classes twice.
"""
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

EXIF_ORIENTATION = 0x0112
EXIF_MAKE = 0x010F
EXIF_GPS_INFO = 0x8825

_TRANSPARENT_INDEX = 0
# Semi-transparent on purpose: libwebp drops an alpha channel that is fully opaque.
_ALPHA = 128


def _exif_bytes(orientation, gps):
    exif = Image.Exif()
    exif[EXIF_MAKE] = 'Hairmatch'
    if orientation:
        exif[EXIF_ORIENTATION] = orientation
    if gps:
        exif[EXIF_GPS_INFO] = {1: 'S', 2: (3.0, 7.0, 0.0), 3: 'W', 4: (60.0, 1.0, 0.0)}
    return exif.tobytes()


def _frame(size, mode, index):
    # Each frame gets a distinct color, otherwise Pillow merges identical GIF frames.
    color = (40 * index % 256, 90, 200 - 40 * index % 200)
    if mode == 'P':
        image = Image.new('P', size, _TRANSPARENT_INDEX + index)
        image.putpalette([c for i in range(256) for c in (i, 255 - i, 128)])
        return image
    if mode in ('L', 'LA'):
        return Image.new(mode, size, 60 * index + 30 if mode == 'L' else (60 * index + 30, _ALPHA))
    if mode == 'CMYK':
        return Image.new(mode, size, (color[0], color[1], color[2], 0))
    return Image.new(mode, size, color + (_ALPHA,) if mode == 'RGBA' else color)


def make_image_bytes(
    size=(20, 10),
    mode='RGB',
    fmt='JPEG',
    orientation=None,
    frames=1,
    gps=False,
    icc_profile=None,
):
    """Encode a solid-color image. `frames > 1` builds an animation (GIF or WEBP)."""
    images = [_frame(size, mode, index) for index in range(frames)]
    options = {}
    if orientation or gps:
        options['exif'] = _exif_bytes(orientation, gps)
    if icc_profile:
        options['icc_profile'] = icc_profile
    if mode == 'P' and fmt == 'PNG':
        options['transparency'] = _TRANSPARENT_INDEX
    if frames > 1:
        options.update(save_all=True, append_images=images[1:], duration=100, loop=0)

    buf = io.BytesIO()
    images[0].save(buf, fmt, **options)
    return buf.getvalue()


def make_upload(name='profile.jpg', **kwargs):
    content_type = Image.MIME.get(kwargs.get('fmt', 'JPEG'))
    return SimpleUploadedFile(name, make_image_bytes(**kwargs), content_type=content_type)

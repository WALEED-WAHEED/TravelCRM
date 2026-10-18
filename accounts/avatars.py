"""Profile pictures: validated, square-cropped and shrunk before they are stored."""
import io
import uuid

from django.core.files.base import ContentFile
from django.utils.translation import gettext

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
SIZE = 320  # px, plenty for the 34-120px places it is shown


class AvatarError(ValueError):
    pass


def avatar_upload_to(instance, filename):
    return f"avatars/user-{instance.pk or 'new'}-{uuid.uuid4().hex[:10]}.jpg"


def process_avatar(uploaded):
    """Return a small square JPEG ContentFile for an uploaded picture, or raise AvatarError."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if uploaded.size > MAX_UPLOAD_BYTES:
        raise AvatarError(gettext("That picture is too large (5 MB at most)."))
    try:
        img = Image.open(uploaded)
        img.verify()
        uploaded.seek(0)
        img = Image.open(uploaded)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        else:
            img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise AvatarError(gettext("That file isn't a valid picture. Use a JPG, PNG or WebP image.")) from None
    img = ImageOps.fit(img, (SIZE, SIZE), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88, optimize=True)
    return ContentFile(out.getvalue())

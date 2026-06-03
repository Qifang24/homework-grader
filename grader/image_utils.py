"""图片预处理：上传/评测共用，保证评测与线上走完全相同的处理流程。

长边压到 max_dim、统一转 JPEG，降低传输体积和模型调用成本，
并把 PNG 透明通道转白底避免 JPEG 报错。

分辨率/画质直接决定手写体（分数线、根号、正负号、零）能不能被认清，
是批改准确率的地基——压太狠会把细笔画糊掉，导致模型误读学生答案。
所以这里取相对保守的高分辨率与较高 JPEG 质量，宁可多花一点 token。
"""
import base64
from io import BytesIO

from PIL import Image

MAX_DIM = 3072
JPEG_QUALITY = 92


def encode_image_bytes(raw: bytes, max_dim: int = MAX_DIM) -> tuple[str, str]:
    """原始图片字节 → (base64 字符串, media_type)。"""
    img = Image.open(BytesIO(raw))
    if img.mode != "RGB":  # PNG 透明通道转白底
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=JPEG_QUALITY)
    return base64.standard_b64encode(buf.getvalue()).decode(), "image/jpeg"

import numpy as np
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image


class ImageLoader:
    @staticmethod
    def pil_to_qpixmap(pil_image):
        pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(
            data,
            pil_image.width,
            pil_image.height,
            pil_image.width * 4,
            QImage.Format.Format_RGBA8888
        )
        return QPixmap.fromImage(qimage.copy())

    @staticmethod
    def load_pixmap(file_path: str) -> QPixmap:
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            return pixmap

        try:
            with Image.open(file_path) as img:
                return ImageLoader.pil_to_qpixmap(img)
        except Exception:
            return QPixmap()

    @staticmethod
    def load_numpy_gray(file_path: str):
        with Image.open(file_path) as img:
            gray = img.convert("L")
            return np.array(gray, dtype=np.uint8)
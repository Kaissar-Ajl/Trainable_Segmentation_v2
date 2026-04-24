import numpy as np
from scipy import ndimage as ndi
from skimage.filters import sobel, gaussian, laplace


class FeatureExtractor:
    @staticmethod
    def normalize_image(image: np.ndarray) -> np.ndarray:
        image = image.astype(np.float32)
        if image.max() > 1.0:
            image = image / 255.0
        return image

    @staticmethod
    def extract_features(image: np.ndarray) -> tuple[np.ndarray, list[str]]:
        """
        Returns:
            feature_stack: (H, W, F)
            feature_names: list[str]
        """
        image = FeatureExtractor.normalize_image(image)

        features = []
        names = []

        # Raw intensity
        features.append(image)
        names.append("intensity")
        
        # Gaussian blur - Glättung in verschiedenen Größen.
        # Hilft, Strukturen auf mehreren Skalen zu erkennen.

        g1 = gaussian(image, sigma=1, preserve_range=True)
        g2 = gaussian(image, sigma=2, preserve_range=True)
        g4 = gaussian(image, sigma=4, preserve_range=True)

        features.extend([g1, g2, g4])
        names.extend([
            "gaussian_sigma_1",
            "gaussian_sigma_2",
            "gaussian_sigma_4"
        ])

        # Sobel edge Erkennt Kanten und Richtungsänderungen.
        s = sobel(image)
        features.append(s)
        names.append("sobel")

        # Laplace Betont Übergänge.
        l = laplace(image, ksize=3)
        features.append(l)
        names.append("laplace")

        # Difference of Gaussians 
        dog_1_2 = g1 - g2
        dog_2_4 = g2 - g4
        features.extend([dog_1_2, dog_2_4])
        names.extend(["dog_1_2", "dog_2_4"])

        # Median
        m3 = ndi.median_filter(image, size=3)
        features.append(m3)
        names.append("median_3")

        # Gradient magnitude
        grad = ndi.gaussian_gradient_magnitude(image, sigma=2)
        features.append(grad)
        names.append("gaussian_gradient_magnitude_2")

        feature_stack = np.stack(features, axis=-1).astype(np.float32)
        return feature_stack, names
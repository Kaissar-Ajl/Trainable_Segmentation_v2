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
    def extract_features(image: np.ndarray, selected_features=None) -> tuple[np.ndarray, list[str]]:
        image = FeatureExtractor.normalize_image(image)

        if selected_features is None:
            selected_features = [
                "intensity",
                "gaussian_sigma_1",
                "gaussian_sigma_2",
                "gaussian_sigma_4",
                "sobel",
                "laplace",
                "dog_1_2",
                "dog_2_4",
                "median_3",
                "gaussian_gradient_magnitude_2",
            ]

        features = []
        names = []

        g1 = g2 = g4 = None

        def add_feature(name, arr):
            if name in selected_features:
                features.append(arr)
                names.append(name)

        add_feature("intensity", image)

        if any(f in selected_features for f in ["gaussian_sigma_1", "dog_1_2"]):
            g1 = gaussian(image, sigma=1, preserve_range=True)

        if any(f in selected_features for f in ["gaussian_sigma_2", "dog_1_2", "dog_2_4"]):
            g2 = gaussian(image, sigma=2, preserve_range=True)

        if any(f in selected_features for f in ["gaussian_sigma_4", "dog_2_4"]):
            g4 = gaussian(image, sigma=4, preserve_range=True)

        if g1 is not None:
            add_feature("gaussian_sigma_1", g1)

        if g2 is not None:
            add_feature("gaussian_sigma_2", g2)

        if g4 is not None:
            add_feature("gaussian_sigma_4", g4)

        if "sobel" in selected_features:
            add_feature("sobel", sobel(image))

        if "laplace" in selected_features:
            add_feature("laplace", laplace(image, ksize=3))

        if "dog_1_2" in selected_features:
            add_feature("dog_1_2", g1 - g2)

        if "dog_2_4" in selected_features:
            add_feature("dog_2_4", g2 - g4)

        if "median_3" in selected_features:
            add_feature("median_3", ndi.median_filter(image, size=3))

        if "gaussian_gradient_magnitude_2" in selected_features:
            add_feature(
                "gaussian_gradient_magnitude_2",
                ndi.gaussian_gradient_magnitude(image, sigma=2)
            )

        if not features:
            raise ValueError("Es wurde kein Feature ausgewählt.")

        feature_stack = np.stack(features, axis=-1).astype(np.float32)
        return feature_stack, names
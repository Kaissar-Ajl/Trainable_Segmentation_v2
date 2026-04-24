import numpy as np
from sklearn.ensemble import RandomForestClassifier


class TrainingEngine:
    @staticmethod
    def build_training_set(feature_stack: np.ndarray, label_mask: np.ndarray):
        """
        feature_stack: (H, W, F)
        label_mask:    (H, W), -1 = unlabeled
        """
        labeled = label_mask >= 0

        if not np.any(labeled):
            raise ValueError("Keine markierten Pixel vorhanden.")

        X = feature_stack[labeled]
        y = label_mask[labeled]

        if X.shape[0] == 0:
            raise ValueError("Keine Trainingsdaten vorhanden.")

        unique_classes = np.unique(y)
        if len(unique_classes) < 2:
            raise ValueError("Mindestens 2 Klassen mit Markierungen sind erforderlich.")

        return X, y

    @staticmethod
    def train_random_forest(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
        clf = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced_subsample"
    )
        clf.fit(X, y)
        return clf

    @staticmethod
    def predict_full_image(feature_stack: np.ndarray, clf):
        h, w, f = feature_stack.shape
        X_all = feature_stack.reshape(-1, f)
        y_pred = clf.predict(X_all)
        return y_pred.reshape(h, w)

    @staticmethod
    def predict_probabilities(feature_stack: np.ndarray, clf):
        h, w, f = feature_stack.shape
        X_all = feature_stack.reshape(-1, f)

        if not hasattr(clf, "predict_proba"):
            raise ValueError("Dieses Modell unterstützt keine Wahrscheinlichkeiten.")

        probs = clf.predict_proba(X_all)
        return probs.reshape(h, w, -1)
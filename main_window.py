import os
import math
import numpy as np
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog,
    QGraphicsScene, QGraphicsPixmapItem,
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QComboBox, QInputDialog, QColorDialog, QMessageBox, QLabel,
    QHeaderView, QAbstractItemView, QSpinBox
)
from PyQt6.QtGui import QColor, QPixmap, QImage
from PyQt6.QtCore import Qt

from project_data import create_default_project, AnnotationStroke
from image_loader import ImageLoader
from project_io import ProjectIO
from graphics_view import GraphicsView
from feature_extractor import FeatureExtractor
from training_engine import TrainingEngine


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mehrklassen-Markierung + Segmentierung")
        self.resize(1400, 900)

        self.project = create_default_project()
        self.pixmap_item = None
        self.current_class_index = 0
        self.hovered_stroke = None

        self.image_array = None
        self.label_mask = None
        self.feature_stack = None
        self.feature_names = []
        self.classifier = None
        self.prediction_mask = None
        self.probability_map = None

        self.brush_size = 8

        self.overlay_item = None
        self.overlay_visible = True
        self.overlay_opacity = 0.5

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Class", "Points", "Brush", "Pixels"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.change_active_class)

        self.active_class_label = QLabel()

        self.brush_spin = QSpinBox()
        self.brush_spin.setRange(1, 100)
        self.brush_spin.setValue(self.brush_size)
        self.brush_spin.valueChanged.connect(self.change_brush_size)

        rename_button = QPushButton("Klasse umbenennen")
        rename_button.clicked.connect(self.rename_class)

        color_button = QPushButton("Farbe ändern")
        color_button.clicked.connect(self.change_class_color)

        load_image_button = QPushButton("Bild laden")
        load_image_button.clicked.connect(self.load_image)

        save_button = QPushButton("Projekt speichern")
        save_button.clicked.connect(self.save_project)

        load_project_button = QPushButton("Projekt laden")
        load_project_button.clicked.connect(self.load_project)

        clear_class_button = QPushButton("Aktive Klasse löschen")
        clear_class_button.clicked.connect(self.clear_active_class)

        rebuild_mask_button = QPushButton("Maske neu aufbauen")
        rebuild_mask_button.clicked.connect(self.rebuild_label_mask_from_strokes)

        extract_features_button = QPushButton("Features berechnen")
        extract_features_button.clicked.connect(self.extract_features)

        train_button = QPushButton("Trainieren")
        train_button.clicked.connect(self.train_model)

        predict_button = QPushButton("Segmentieren")
        predict_button.clicked.connect(self.predict_segmentation)

        toggle_overlay_button = QPushButton("Overlay AN/AUS")
        toggle_overlay_button.clicked.connect(self.toggle_overlay)

        opacity_button = QPushButton("Transparenz ändern")
        opacity_button.clicked.connect(self.change_overlay_opacity)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Aktive Klasse:"))
        top_layout.addWidget(self.class_combo)
        top_layout.addWidget(self.active_class_label)
        top_layout.addSpacing(10)
        top_layout.addWidget(QLabel("Brush:"))
        top_layout.addWidget(self.brush_spin)
        top_layout.addWidget(rename_button)
        top_layout.addWidget(color_button)
        top_layout.addWidget(load_image_button)
        top_layout.addWidget(save_button)
        top_layout.addWidget(load_project_button)
        top_layout.addWidget(clear_class_button)
        top_layout.addWidget(rebuild_mask_button)
        top_layout.addWidget(extract_features_button)
        top_layout.addWidget(train_button)
        top_layout.addWidget(predict_button)
        top_layout.addWidget(toggle_overlay_button)
        top_layout.addWidget(opacity_button)

        layout = QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.view, 3)
        layout.addWidget(self.table, 1)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.update_class_combo()
        self.update_active_class_label()
        self.refresh_table()

    def has_image(self):
        return self.pixmap_item is not None and self.image_array is not None

    def update_class_combo(self):
        self.class_combo.blockSignals(True)
        self.class_combo.clear()

        for i, class_info in enumerate(self.project.classes):
            self.class_combo.addItem(f"{i + 1}: {class_info.name}")

        self.class_combo.setCurrentIndex(self.current_class_index)
        self.class_combo.blockSignals(False)

    def update_active_class_label(self):
        color = self.project.classes[self.current_class_index].color
        name = self.project.classes[self.current_class_index].name
        self.active_class_label.setText(f"{name} ({color})")
        self.active_class_label.setStyleSheet(
            f"padding: 4px; border: 1px solid black; background-color: {color};"
        )

    def change_active_class(self, index):
        if 0 <= index < len(self.project.classes):
            self.current_class_index = index
            self.update_active_class_label()
            self.view.viewport().update()

    def change_brush_size(self, value):
        self.brush_size = int(value)
        self.view.viewport().update()

    def rename_class(self):
        current_name = self.project.classes[self.current_class_index].name

        new_name, ok = QInputDialog.getText(
            self,
            "Klasse umbenennen",
            "Neuer Klassenname:",
            text=current_name
        )

        if ok and new_name.strip():
            self.project.classes[self.current_class_index].name = new_name.strip()
            self.update_class_combo()
            self.update_active_class_label()
            self.refresh_table()

    def change_class_color(self):
        current_color = QColor(self.project.classes[self.current_class_index].color)
        color = QColorDialog.getColor(current_color, self, "Farbe wählen")

        if color.isValid():
            self.project.classes[self.current_class_index].color = color.name()
            self.update_active_class_label()
            self.view.viewport().update()
            if self.prediction_mask is not None:
                self.show_overlay()

    def clear_all_strokes(self):
        for class_info in self.project.classes:
            class_info.strokes = []

        self.hovered_stroke = None
        self.reset_label_mask()

    def reset_label_mask(self):
        if self.image_array is None:
            self.label_mask = None
            return

        h, w = self.image_array.shape[:2]
        self.label_mask = np.full((h, w), -1, dtype=np.int32)

    def reset_ml_state(self):
        self.feature_stack = None
        self.feature_names = []
        self.classifier = None
        self.prediction_mask = None
        self.probability_map = None
        self.clear_overlay()

    def reset_prediction_only(self):
        self.classifier = None
        self.prediction_mask = None
        self.probability_map = None
        self.clear_overlay()

    def display_pixmap(self, pixmap):
        self.scene.clear()
        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.view.resetTransform()
        self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.view.centerOn(self.pixmap_item)
        self.scene.update()
        self.view.viewport().update()

    def add_stroke_to_current_class(self, path_points):
        coords = [(float(p.x()), float(p.y())) for p in path_points]

        if len(coords) < 2:
            return

        stroke = AnnotationStroke(
            points=coords,
            brush_size=self.brush_size
        )
        self.project.classes[self.current_class_index].strokes.append(stroke)

        self.paint_stroke_into_label_mask(stroke, self.current_class_index)
        self.reset_prediction_only()
        self.refresh_table()
        self.view.viewport().update()

    def load_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Bild wählen",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )
        if not file:
            return

        pixmap = ImageLoader.load_pixmap(file)
        if pixmap.isNull():
            QMessageBox.warning(self, "Fehler", f"Bild konnte nicht geladen werden:\n{file}")
            return

        try:
            image_array = ImageLoader.load_numpy_gray(file)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Bild konnte nicht als NumPy-Array geladen werden:\n{e}")
            return

        self.project.image_path = file
        self.image_array = image_array
        self.clear_all_strokes()
        self.reset_ml_state()
        self.refresh_table()
        self.display_pixmap(pixmap)

    def refresh_table(self):
        self.table.setRowCount(0)

        for class_info in self.project.classes:
            for stroke in class_info.strokes:
                row = self.table.rowCount()
                self.table.insertRow(row)

                points_count = len(stroke.points)
                brush = stroke.brush_size
                pixel_count = self.estimate_stroke_pixels(stroke)

                self.table.setItem(row, 0, QTableWidgetItem(class_info.name))
                self.table.setItem(row, 1, QTableWidgetItem(str(points_count)))
                self.table.setItem(row, 2, QTableWidgetItem(str(brush)))
                self.table.setItem(row, 3, QTableWidgetItem(str(pixel_count)))

    def estimate_stroke_pixels(self, stroke):
        if self.image_array is None:
            return 0

        temp = Image.new("L", (self.image_array.shape[1], self.image_array.shape[0]), 0)
        draw = ImageDraw.Draw(temp)

        pts = [(int(round(x)), int(round(y))) for x, y in stroke.points]
        if len(pts) == 1:
            r = max(1, stroke.brush_size // 2)
            x, y = pts[0]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        else:
            draw.line(pts, fill=255, width=stroke.brush_size)

        arr = np.array(temp, dtype=np.uint8)
        return int(np.count_nonzero(arr))

    def clear_active_class(self):
        self.project.classes[self.current_class_index].strokes = []

        if self.hovered_stroke is not None and self.hovered_stroke[0] == self.current_class_index:
            self.hovered_stroke = None

        self.rebuild_label_mask_from_strokes()
        self.reset_prediction_only()
        self.refresh_table()
        self.view.viewport().update()

    def save_project(self):
        if not self.project.image_path:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        file, _ = QFileDialog.getSaveFileName(
            self,
            "Projekt speichern",
            "",
            "JSON Files (*.json)"
        )
        if not file:
            return

        try:
            ProjectIO.save(self.project, file)
            QMessageBox.information(self, "Gespeichert", "Projekt wurde gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")

    def load_project(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Projekt laden",
            "",
            "JSON Files (*.json)"
        )
        if not file:
            return

        try:
            loaded_project = ProjectIO.load(file)

            if len(loaded_project.classes) != 8:
                QMessageBox.warning(self, "Warnung", "Die Datei enthält nicht genau 8 Klassen.")
                return

            if not os.path.exists(loaded_project.image_path):
                QMessageBox.warning(self, "Fehler", f"Bilddatei nicht gefunden:\n{loaded_project.image_path}")
                return

            pixmap = ImageLoader.load_pixmap(loaded_project.image_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Fehler", f"Bild konnte nicht geladen werden:\n{loaded_project.image_path}")
                return

            image_array = ImageLoader.load_numpy_gray(loaded_project.image_path)

            self.project = loaded_project
            self.image_array = image_array
            self.current_class_index = 0
            self.hovered_stroke = None
            self.reset_ml_state()

            self.update_class_combo()
            self.update_active_class_label()
            self.display_pixmap(pixmap)
            self.rebuild_label_mask_from_strokes()
            self.refresh_table()

            QMessageBox.information(self, "Geladen", "Projekt wurde geladen.")

        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Laden fehlgeschlagen:\n{e}")

    def set_hovered_stroke(self, stroke_id):
        self.hovered_stroke = stroke_id
        self.view.viewport().update()

    def delete_stroke_by_id(self, stroke_id):
        if stroke_id is None:
            return

        class_index, stroke_index = stroke_id

        if class_index < 0 or class_index >= len(self.project.classes):
            self.hovered_stroke = None
            return

        strokes = self.project.classes[class_index].strokes

        if stroke_index < 0 or stroke_index >= len(strokes):
            self.hovered_stroke = None
            return

        del strokes[stroke_index]
        self.hovered_stroke = None
        self.rebuild_label_mask_from_strokes()
        self.reset_prediction_only()
        self.refresh_table()
        self.view.viewport().update()

    def distance_point_to_segment(self, p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b

        dx = bx - ax
        dy = by - ay

        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)

        t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))

        closest_x = ax + t * dx
        closest_y = ay + t * dy

        return math.hypot(px - closest_x, py - closest_y)

    def find_nearest_stroke(self, scene_pos):
        px = scene_pos.x()
        py = scene_pos.y()

        screen_threshold_px = 60

        current_scale = self.view.transform().m11()
        if current_scale <= 0:
            current_scale = 1.0

        threshold_scene = screen_threshold_px / current_scale

        best = None
        best_dist = float("inf")

        for class_index, class_info in enumerate(self.project.classes):
            for stroke_index, stroke in enumerate(class_info.strokes):
                points = stroke.points
                if len(points) < 2:
                    continue

                for i in range(len(points) - 1):
                    dist = self.distance_point_to_segment(
                        (px, py),
                        points[i],
                        points[i + 1]
                    )

                    dist = max(0.0, dist - stroke.brush_size / 2)

                    if dist < best_dist:
                        best_dist = dist
                        best = (class_index, stroke_index)

        if best_dist <= threshold_scene:
            return best

        return None

    def paint_stroke_into_label_mask(self, stroke, class_index):
        if self.label_mask is None:
            return

        h, w = self.label_mask.shape
        temp = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(temp)

        pts = [(int(round(x)), int(round(y))) for x, y in stroke.points]

        if len(pts) == 1:
            r = max(1, stroke.brush_size // 2)
            x, y = pts[0]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
        else:
            draw.line(pts, fill=255, width=stroke.brush_size)

        mask = np.array(temp, dtype=np.uint8) > 0
        self.label_mask[mask] = class_index

    def rebuild_label_mask_from_strokes(self):
        self.reset_label_mask()

        if self.label_mask is None:
            QMessageBox.warning(self, "Fehler", "Keine Bilddaten vorhanden.")
            return

        stroke_count = 0

        for class_index, class_info in enumerate(self.project.classes):
            for stroke in class_info.strokes:
                self.paint_stroke_into_label_mask(stroke, class_index)
                stroke_count += 1

        QMessageBox.information(
            self,
            "Maske neu aufgebaut",
            f"Fertig!\n\n"
            f"{stroke_count} Strokes verarbeitet.\n"
            f"Maske wurde erfolgreich aktualisiert."
        )

    def extract_features(self):
        if self.image_array is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        try:
            self.feature_stack, self.feature_names = FeatureExtractor.extract_features(self.image_array)

            QMessageBox.information(
                self,
                "Features berechnet",
                f"{len(self.feature_names)} Features wurden berechnet:\n\n" +
                "\n".join(self.feature_names)
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Feature-Berechnung fehlgeschlagen:\n{e}")

    def train_model(self):
        if self.image_array is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        if self.label_mask is None:
            QMessageBox.warning(self, "Fehler", "Keine Label-Maske vorhanden.")
            return

        if self.feature_stack is None:
            QMessageBox.information(self, "Hinweis", "Features werden zuerst berechnet.")
            self.extract_features()

            if self.feature_stack is None:
                return

        try:
            X, y = TrainingEngine.build_training_set(self.feature_stack, self.label_mask)
            self.classifier = TrainingEngine.train_random_forest(X, y)

            class_counts = {}
            for class_id in np.unique(y):
                class_counts[int(class_id)] = int(np.sum(y == class_id))

            info = "\n".join(
                f"{self.project.classes[class_id].name}: {count} Pixel"
                for class_id, count in class_counts.items()
            )

            QMessageBox.information(
                self,
                "Training erfolgreich",
                f"Modell wurde trainiert.\n\nTrainingspixel pro Klasse:\n{info}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Training fehlgeschlagen:\n{e}")

    def predict_segmentation(self):
        if self.image_array is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        if self.classifier is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst trainieren.")
            return

        if self.feature_stack is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst Features berechnen.")
            return

        try:
            self.prediction_mask = TrainingEngine.predict_full_image(
                self.feature_stack,
                self.classifier
            )

            self.overlay_visible = True
            self.show_overlay()

            QMessageBox.information(
                self,
                "Segmentierung fertig",
                f"Vorhersage berechnet: {self.prediction_mask.shape[1]} x {self.prediction_mask.shape[0]}"
            )

            self.show_prediction_summary()

        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Segmentierung fehlgeschlagen:\n{e}")

    def show_prediction_summary(self):
        if self.prediction_mask is None:
            return

        unique_classes, counts = np.unique(self.prediction_mask, return_counts=True)

        lines = []
        for class_id, count in zip(unique_classes, counts):
            if 0 <= int(class_id) < len(self.project.classes):
                class_name = self.project.classes[int(class_id)].name
            else:
                class_name = f"Class {class_id}"

            lines.append(f"{class_name}: {int(count)} Pixel")

        QMessageBox.information(
            self,
            "Vorhersage-Zusammenfassung",
            "\n".join(lines)
        )

    def create_overlay_pixmap(self):
        if self.prediction_mask is None:
            return None

        h, w = self.prediction_mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        for class_index, class_info in enumerate(self.project.classes):
            color = QColor(class_info.color)
            r, g, b = color.red(), color.green(), color.blue()

            mask = self.prediction_mask == class_index
            rgba[mask, 0] = r
            rgba[mask, 1] = g
            rgba[mask, 2] = b
            rgba[mask, 3] = int(255 * self.overlay_opacity)

        qimage = QImage(
            rgba.data,
            w,
            h,
            4 * w,
            QImage.Format.Format_RGBA8888
        )

        return QPixmap.fromImage(qimage.copy())

    def show_overlay(self):
        if self.prediction_mask is None:
            return

        pixmap = self.create_overlay_pixmap()
        if pixmap is None:
            return

        if self.overlay_item is not None:
            self.scene.removeItem(self.overlay_item)
            self.overlay_item = None

        self.overlay_item = QGraphicsPixmapItem(pixmap)
        self.overlay_item.setZValue(10)
        self.overlay_item.setVisible(self.overlay_visible)
        self.scene.addItem(self.overlay_item)

    def clear_overlay(self):
        if self.overlay_item is not None:
            self.scene.removeItem(self.overlay_item)
            self.overlay_item = None

    def toggle_overlay(self):
        if self.overlay_item is None:
            return

        self.overlay_visible = not self.overlay_visible
        self.overlay_item.setVisible(self.overlay_visible)

    def change_overlay_opacity(self):
        value, ok = QInputDialog.getDouble(
            self,
            "Transparenz",
            "Wert (0.0 - 1.0):",
            value=self.overlay_opacity,
            min=0.0,
            max=1.0,
            decimals=2
        )

        if ok:
            self.overlay_opacity = float(value)
            if self.prediction_mask is not None:
                self.show_overlay()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.hovered_stroke = None
            self.view.viewport().update()

        super().keyReleaseEvent(event)
import os
import math
import joblib
from openpyxl import Workbook
import numpy as np
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog,
    QGraphicsScene, QGraphicsPixmapItem,
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QComboBox, QInputDialog, QColorDialog, QMessageBox, QLabel,
    QHeaderView, QAbstractItemView, QSpinBox, QDialog, QFormLayout, QDialogButtonBox, QCheckBox
)
from PyQt6.QtGui import QColor, QPixmap, QImage, QPainter
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
        self.crop_background_color = "#000000"
        self.crop_mode = False
        self.crop_points = []

        # Dynamische Klassifikator-Einstellungen
        self.rf_n_estimators = 500
        self.rf_max_features = "sqrt"
        self.rf_class_weight = "balanced"

        # Dynamische Feature-Auswahl
        self.feature_options = {
            "intensity": True,
            "gaussian_sigma_1": True,
            "gaussian_sigma_2": True,
            "gaussian_sigma_4": True,
            "sobel": True,
            "laplace": True,
            "dog_1_2": True,
            "dog_2_4": True,
            "median_3": True,
            "gaussian_gradient_magnitude_2": True,
        }

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Class", "Type", "Points", "Brush", "Pixels"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
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

        # Sichtbare Segmentierungs-Buttons
        train_button = QPushButton("Trainieren")
        train_button.clicked.connect(self.train_model)

        predict_button = QPushButton("Segmentieren")
        predict_button.clicked.connect(self.predict_segmentation)

        batch_button = QPushButton("Mehrere Bilder segmentieren")
        batch_button.clicked.connect(self.batch_segment_images)

        self.crop_mode_button = QPushButton("Crop-Modus AUS")
        self.crop_mode_button.setCheckable(True)
        self.crop_mode_button.clicked.connect(self.toggle_crop_mode)

        crop_button = QPushButton("Croppen")
        crop_button.clicked.connect(self.crop_image_from_crop_points)

        toggle_overlay_button = QPushButton("Overlay AN/AUS")
        toggle_overlay_button.clicked.connect(self.toggle_overlay)

        opacity_button = QPushButton("Transparenz ändern")
        opacity_button.clicked.connect(self.change_overlay_opacity)

        self.create_menus()

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Aktive Klasse:"))
        top_layout.addWidget(self.class_combo)
        top_layout.addWidget(self.active_class_label)
        top_layout.addSpacing(20)
        top_layout.addWidget(QLabel("Brush:"))
        top_layout.addWidget(self.brush_spin)
        top_layout.addSpacing(20)
        top_layout.addWidget(train_button)
        top_layout.addWidget(predict_button)
        top_layout.addWidget(batch_button)
        top_layout.addWidget(self.crop_mode_button)
        top_layout.addWidget(crop_button)
        top_layout.addWidget(toggle_overlay_button)
        top_layout.addWidget(opacity_button)
        top_layout.addStretch()

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

    # =====================================================
    # MENÜ
    # =====================================================
    def create_menus(self):
        menu_bar = self.menuBar()

        # Datei
        file_menu = menu_bar.addMenu("Datei")

        action_load_image = file_menu.addAction("Bild laden")
        action_load_image.triggered.connect(self.load_image)

        action_save_project = file_menu.addAction("Projekt speichern")
        action_save_project.triggered.connect(self.save_project)

        action_load_project = file_menu.addAction("Projekt laden")
        action_load_project.triggered.connect(self.load_project)

        file_menu.addSeparator()

        action_save_classifier = file_menu.addAction("Klassifikator speichern")
        action_save_classifier.triggered.connect(self.save_classifier)

        action_load_classifier = file_menu.addAction("Klassifikator laden")
        action_load_classifier.triggered.connect(self.load_classifier)

        file_menu.addSeparator()

        action_batch_segment = file_menu.addAction("Mehrere Bilder segmentieren")
        action_batch_segment.triggered.connect(self.batch_segment_images)

        file_menu.addSeparator()

        action_choose_crop_bg = file_menu.addAction("Crop-Hintergrundfarbe wählen")
        action_choose_crop_bg.triggered.connect(self.choose_crop_background_color)

        action_toggle_crop_mode = file_menu.addAction("Crop-Modus AN/AUS")
        action_toggle_crop_mode.triggered.connect(self.toggle_crop_mode)

        action_crop_image = file_menu.addAction("Bild mit Crop-Umrandung croppen")
        action_crop_image.triggered.connect(self.crop_image_from_crop_points)

        file_menu.addSeparator()

        action_save_segmented = file_menu.addAction("Segmentiertes Bild speichern")
        action_save_segmented.triggered.connect(self.save_segmented_image)

        # Einstellungen
        settings_menu = menu_bar.addMenu("Einstellungen")

        action_training_settings = settings_menu.addAction("Klassifikator und Features einstellen")
        action_training_settings.triggered.connect(self.open_training_settings_dialog)

        # Klassen
        class_menu = menu_bar.addMenu("Klassen")

        action_rename = class_menu.addAction("Klasse umbenennen")
        action_rename.triggered.connect(self.rename_class)

        action_color = class_menu.addAction("Farbe ändern")
        action_color.triggered.connect(self.change_class_color)

        action_delete = class_menu.addAction("Aktive Klasse löschen")
        action_delete.triggered.connect(self.clear_active_class)

    # =====================================================
    # BASIS
    # =====================================================
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
            f"padding:4px; border:1px solid black; background-color:{color};"
        )

    def change_active_class(self, index):
        if 0 <= index < len(self.project.classes):
            self.current_class_index = index
            self.update_active_class_label()
            self.view.viewport().update()

    def change_brush_size(self, value):
        self.brush_size = int(value)
        self.view.viewport().update()

    # =====================================================
    # EINSTELLUNGEN
    # =====================================================
    def open_training_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Klassifikator und Features einstellen")

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        n_estimators_spin = QSpinBox()
        n_estimators_spin.setRange(50, 2000)
        n_estimators_spin.setSingleStep(50)
        n_estimators_spin.setValue(self.rf_n_estimators)
        form.addRow("Anzahl Bäume:", n_estimators_spin)

        max_features_combo = QComboBox()
        max_features_combo.addItems(["sqrt", "log2", "None"])
        max_features_combo.setCurrentText(str(self.rf_max_features))
        form.addRow("Max Features:", max_features_combo)

        class_weight_combo = QComboBox()
        class_weight_combo.addItems(["balanced", "balanced_subsample", "None"])
        class_weight_combo.setCurrentText(str(self.rf_class_weight))
        form.addRow("Class Weight:", class_weight_combo)

        layout.addLayout(form)

        layout.addWidget(QLabel("Features auswählen:"))
        feature_checkboxes = {}

        for feature_name, enabled in self.feature_options.items():
            checkbox = QCheckBox(feature_name)
            checkbox.setChecked(enabled)
            feature_checkboxes[feature_name] = checkbox
            layout.addWidget(checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_count = sum(1 for checkbox in feature_checkboxes.values() if checkbox.isChecked())

            if selected_count == 0:
                QMessageBox.warning(self, "Fehler", "Bitte mindestens ein Feature auswählen.")
                return

            self.rf_n_estimators = int(n_estimators_spin.value())

            max_features_value = max_features_combo.currentText()
            self.rf_max_features = None if max_features_value == "None" else max_features_value

            class_weight_value = class_weight_combo.currentText()
            self.rf_class_weight = None if class_weight_value == "None" else class_weight_value

            for feature_name, checkbox in feature_checkboxes.items():
                self.feature_options[feature_name] = checkbox.isChecked()

            # Wenn Features geändert wurden, müssen sie beim nächsten Training neu berechnet werden.
            self.feature_stack = None
            self.feature_names = []
            self.reset_prediction_only()

            QMessageBox.information(self, "OK", "Einstellungen wurden übernommen.")

    def get_selected_feature_names(self):
        return [
            feature_name
            for feature_name, enabled in self.feature_options.items()
            if enabled
        ]

    # =====================================================
    # CROP / ROI
    # =====================================================
    def toggle_crop_mode(self):
        self.crop_mode = not self.crop_mode
        self.crop_points = []

        if hasattr(self, "crop_mode_button"):
            self.crop_mode_button.setChecked(self.crop_mode)
            self.crop_mode_button.setText("Crop-Modus AN" if self.crop_mode else "Crop-Modus AUS")

        self.view.current_path = []
        self.view.viewport().update()

    def choose_crop_background_color(self):
        current_color = QColor(self.crop_background_color)
        color = QColorDialog.getColor(current_color, self, "Crop-Hintergrundfarbe wählen")

        if color.isValid():
            self.crop_background_color = color.name()
            QMessageBox.information(
                self,
                "Hintergrundfarbe",
                f"Crop-Hintergrundfarbe gesetzt auf: {self.crop_background_color}"
            )

    def add_crop_point(self, scene_pos):
        self.crop_points.append((float(scene_pos.x()), float(scene_pos.y())))
        self.view.viewport().update()

    def set_crop_points(self, path_points):
        self.crop_points = [(float(p.x()), float(p.y())) for p in path_points]
        self.view.viewport().update()

    def clear_crop_points(self):
        self.crop_points = []
        self.view.viewport().update()

    def crop_points_are_closed(self):
        if len(self.crop_points) < 3:
            return False

        x1, y1 = self.crop_points[0]
        x2, y2 = self.crop_points[-1]
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

        return dist <= max(12, self.brush_size * 3)

    def crop_image_from_crop_points(self):
        if self.image_array is None or not self.project.image_path:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        if len(self.crop_points) < 3:
            QMessageBox.warning(
                self,
                "Fehler",
                "Bitte zuerst im Crop-Modus eine geschlossene Umrandung zeichnen."
            )
            return

        if not self.crop_points_are_closed():
            QMessageBox.warning(
                self,
                "Fehler",
                "Die Crop-Umrandung ist nicht geschlossen.\n"
                "Der letzte Punkt muss in der Nähe des ersten Punktes enden."
                
            )
            return

        try:
            with Image.open(self.project.image_path) as img:
                original = img.convert("RGB")

            w, h = original.size

            pts = [(int(round(x)), int(round(y))) for x, y in self.crop_points]
            pts = [
                (max(0, min(w - 1, x)), max(0, min(h - 1, y)))
                for x, y in pts
            ]

            roi_mask_img = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(roi_mask_img)
            draw.polygon(pts, fill=255)
            roi_mask = np.array(roi_mask_img) > 0

            if not np.any(roi_mask):
                QMessageBox.warning(self, "Fehler", "Die Crop-Maske ist leer.")
                return

            color = QColor(self.crop_background_color)
            bg_rgb = np.array([color.red(), color.green(), color.blue()], dtype=np.uint8)

            result = np.array(original, dtype=np.uint8)
            result[~roi_mask] = bg_rgb

            ys, xs = np.where(roi_mask)
            x_min, x_max = int(xs.min()), int(xs.max())
            y_min, y_max = int(ys.min()), int(ys.max())

            cropped = result[y_min:y_max + 1, x_min:x_max + 1]
            cropped_image = Image.fromarray(cropped, mode="RGB")

            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Gecropptes Bild speichern",
                "cropped.png",
                "PNG Files (*.png);;TIFF Files (*.tif *.tiff);;JPEG Files (*.jpg *.jpeg)"
            )

            if save_path:
                cropped_image.save(save_path)
                self.project.image_path = save_path
            else:
                self.project.image_path = ""

            self.image_array = np.array(cropped_image.convert("L"), dtype=np.uint8)

            self.clear_all_strokes()
            self.clear_crop_points()
            self.reset_ml_state()
            self.refresh_table()
            self.display_pixmap(ImageLoader.pil_to_qpixmap(cropped_image))

            if self.crop_mode:
                self.toggle_crop_mode()

            QMessageBox.information(self, "Cropping", "Bild wurde erfolgreich gecroppt.")

        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # =====================================================
    # KLASSEN
    # =====================================================
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

    def clear_active_class(self):
        self.project.classes[self.current_class_index].strokes = []

        if self.hovered_stroke is not None:
            if self.hovered_stroke[0] == self.current_class_index:
                self.hovered_stroke = None

        # Keine Masken-Neuberechnung hier.
        # Erst beim nächsten Trainieren wird die Label-Maske neu erzeugt.
        self.reset_prediction_only()
        self.refresh_table()
        self.view.viewport().update()

    # =====================================================
    # IMAGE / PROJECT
    # =====================================================
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
            QMessageBox.warning(self, "Fehler", "Bild konnte nicht geladen werden.")
            return

        try:
            image_array = ImageLoader.load_numpy_gray(file)
        except Exception as e:
            QMessageBox.warning(self, "Fehler", str(e))
            return

        self.project.image_path = file
        self.image_array = image_array

        self.clear_all_strokes()
        self.reset_ml_state()
        self.refresh_table()
        self.display_pixmap(pixmap)

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
            QMessageBox.information(self, "Gespeichert", "Projekt gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

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

            pixmap = ImageLoader.load_pixmap(loaded_project.image_path)
            image_array = ImageLoader.load_numpy_gray(loaded_project.image_path)

            self.project = loaded_project
            self.image_array = image_array
            self.current_class_index = 0
            self.hovered_stroke = None

            self.reset_ml_state()

            self.update_class_combo()
            self.update_active_class_label()
            self.display_pixmap(pixmap)
            self.rebuild_label_mask_from_strokes(show_message=False)
            self.refresh_table()

            QMessageBox.information(self, "Geladen", "Projekt geladen.")

        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # =====================================================
    # DRAWING
    # =====================================================
    def clear_all_strokes(self):
        for class_info in self.project.classes:
            class_info.strokes = []

        self.hovered_stroke = None
        self.reset_label_mask()

    def display_pixmap(self, pixmap):
        self.scene.clear()

        self.pixmap_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.pixmap_item)

        self.scene.setSceneRect(self.pixmap_item.boundingRect())
        self.view.resetTransform()
        self.view.fitInView(self.pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.view.centerOn(self.pixmap_item)

    def detect_stroke_type(self, points, brush_size):
        if len(points) < 3:
            return "Stroke"

        x1, y1 = points[0]
        x2, y2 = points[-1]

        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

        if dist <= max(8, brush_size * 2):
            return "ROI"

        return "Stroke"

    def add_stroke_to_current_class(self, path_points):
        coords = [(float(p.x()), float(p.y())) for p in path_points]

        if len(coords) < 2:
            return

        stroke = AnnotationStroke(
            points=coords,
            brush_size=self.brush_size,
            stroke_type=self.detect_stroke_type(coords, self.brush_size)
        )

        self.project.classes[self.current_class_index].strokes.append(stroke)

        # WICHTIG FÜR GROSSE BILDER:
        # Die Label-Maske wird hier NICHT mehr direkt aktualisiert.
        # Sonst kann das Programm beim Markieren großer Bilder hängen.
        # Die Maske wird erst beim Klick auf "Trainieren" komplett neu aufgebaut.
        self.reset_prediction_only()
        self.refresh_table()
        self.view.viewport().update()

    def set_hovered_stroke(self, stroke_id):
        self.hovered_stroke = stroke_id
        self.view.viewport().update()

    def delete_stroke_by_id(self, stroke_id):
        if stroke_id is None:
            return

        class_index, stroke_index = stroke_id

        try:
            del self.project.classes[class_index].strokes[stroke_index]
        except Exception:
            return

        self.hovered_stroke = None
        # Keine Masken-Neuberechnung hier.
        # Erst beim nächsten Trainieren wird die Label-Maske neu erzeugt.
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

    # =====================================================
    # MASK
    # =====================================================
    def reset_label_mask(self):
        if self.image_array is None:
            self.label_mask = None
            return

        h, w = self.image_array.shape[:2]
        self.label_mask = np.full((h, w), -1, dtype=np.int32)

    def paint_stroke_into_label_mask(self, stroke, class_index):
        if self.label_mask is None:
            return

        h, w = self.label_mask.shape
        temp = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(temp)

        pts = [(int(round(x)), int(round(y))) for x, y in stroke.points]

        if stroke.stroke_type == "ROI":
            draw.polygon(pts, fill=255)
        else:
            draw.line(pts, fill=255, width=stroke.brush_size)

        mask = np.array(temp) > 0
        self.label_mask[mask] = class_index

    def rebuild_label_mask_from_strokes(self, show_message=True):
        self.reset_label_mask()

        if self.label_mask is None:
            return

        for class_index, class_info in enumerate(self.project.classes):
            for stroke in class_info.strokes:
                self.paint_stroke_into_label_mask(stroke, class_index)

        self.refresh_table()

        if show_message:
            QMessageBox.information(self, "OK", "Maske erfolgreich neu aufgebaut.")

    # =====================================================
    # TABLE
    # =====================================================
    def refresh_table(self):
        self.table.setRowCount(0)

        for class_info in self.project.classes:
            for stroke in class_info.strokes:
                row = self.table.rowCount()
                self.table.insertRow(row)

                # WICHTIG FÜR GROSSE BILDER:
                # Pixel werden hier nicht mehr live berechnet,
                # weil das bei großen Bildern sehr langsam werden kann.
                pixel_count = "-"

                self.table.setItem(row, 0, QTableWidgetItem(class_info.name))
                self.table.setItem(row, 1, QTableWidgetItem(stroke.stroke_type))
                self.table.setItem(row, 2, QTableWidgetItem(str(len(stroke.points))))
                self.table.setItem(row, 3, QTableWidgetItem(str(stroke.brush_size)))
                self.table.setItem(row, 4, QTableWidgetItem(str(pixel_count)))

    def estimate_stroke_pixels(self, stroke):
        if self.image_array is None:
            return 0

        temp = Image.new("L", (self.image_array.shape[1], self.image_array.shape[0]), 0)
        draw = ImageDraw.Draw(temp)

        pts = [(int(round(x)), int(round(y))) for x, y in stroke.points]

        if stroke.stroke_type == "ROI":
            draw.polygon(pts, fill=255)
        else:
            if len(pts) == 1:
                r = max(1, stroke.brush_size // 2)
                x, y = pts[0]
                draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
            else:
                draw.line(pts, fill=255, width=stroke.brush_size)

        arr = np.array(temp, dtype=np.uint8)
        return int(np.count_nonzero(arr))

    # =====================================================
    # ML
    # =====================================================
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

    def extract_features(self):
        if self.image_array is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        try:
            self.feature_stack, self.feature_names = FeatureExtractor.extract_features(
                self.image_array,
                selected_features=self.get_selected_feature_names()
            )
            QMessageBox.information(
                self,
                "Features",
                f"{len(self.feature_names)} Features berechnet."
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def train_model(self):
        if self.image_array is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst ein Bild laden.")
            return

        try:
            # Maske wird erst beim Trainieren aus allen aktuellen Markierungen neu aufgebaut.
            self.rebuild_label_mask_from_strokes(show_message=False)

            # Features nur berechnen, wenn noch keine vorhanden sind.
            # Beim Löschen/Ändern von Markierungen bleibt das Bild gleich,
            # daher können vorhandene Features weiterverwendet werden.
            if self.feature_stack is None:
                self.feature_stack, self.feature_names = FeatureExtractor.extract_features(
                    self.image_array,
                    selected_features=self.get_selected_feature_names()
                )

            X, y = TrainingEngine.build_training_set(self.feature_stack, self.label_mask)
            self.classifier = TrainingEngine.train_random_forest(
                X,
                y,
                n_estimators=self.rf_n_estimators,
                max_features=self.rf_max_features,
                class_weight=self.rf_class_weight
            )
            self.prediction_mask = None
            self.probability_map = None
            self.clear_overlay()

            QMessageBox.information(
                self,
                "Training",
                f"Training erfolgreich.\nFeatures: {len(self.feature_names)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def predict_segmentation(self):
        if self.classifier is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst trainieren oder Klassifikator laden.")
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
            QMessageBox.information(self, "Fertig", "Segmentierung abgeschlossen.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def save_classifier(self):
        if self.classifier is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst trainieren.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Klassifikator speichern",
            "classifier.pkl",
            "Pickle Files (*.pkl)"
        )

        if not file_path:
            return

        if not file_path.lower().endswith(".pkl"):
            file_path += ".pkl"

        try:
            model_data = {
                "classifier": self.classifier,
                "feature_names": self.feature_names,
                "class_names": [class_info.name for class_info in self.project.classes],
                "class_colors": [class_info.color for class_info in self.project.classes],
                "rf_n_estimators": self.rf_n_estimators,
                "rf_max_features": self.rf_max_features,
                "rf_class_weight": self.rf_class_weight,
                "feature_options": self.feature_options,
            }

            joblib.dump(model_data, file_path)
            QMessageBox.information(self, "Gespeichert", "Klassifikator wurde gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def load_classifier(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Klassifikator laden",
            "",
            "Pickle Files (*.pkl)"
        )

        if not file_path:
            return

        try:
            model_data = joblib.load(file_path)

            # Neues Format: Dictionary mit Klassifikator + Metadaten
            if isinstance(model_data, dict):
                self.classifier = model_data.get("classifier")
                self.feature_names = model_data.get("feature_names", [])
                class_names = model_data.get("class_names", [])
                class_colors = model_data.get("class_colors", [])

                self.rf_n_estimators = int(model_data.get("rf_n_estimators", self.rf_n_estimators))
                self.rf_max_features = model_data.get("rf_max_features", self.rf_max_features)
                self.rf_class_weight = model_data.get("rf_class_weight", self.rf_class_weight)

                loaded_feature_options = model_data.get("feature_options", None)
                if isinstance(loaded_feature_options, dict):
                    for feature_name in self.feature_options:
                        if feature_name in loaded_feature_options:
                            self.feature_options[feature_name] = bool(loaded_feature_options[feature_name])

                for i, name in enumerate(class_names):
                    if i < len(self.project.classes):
                        self.project.classes[i].name = name

                for i, color in enumerate(class_colors):
                    if i < len(self.project.classes):
                        self.project.classes[i].color = color

                self.update_class_combo()
                self.update_active_class_label()
            else:
                # Altes Format: direkt gespeicherter Klassifikator
                self.classifier = model_data

            if self.classifier is None:
                raise RuntimeError("In der Datei wurde kein gültiger Klassifikator gefunden.")

            self.prediction_mask = None
            self.probability_map = None
            self.clear_overlay()

            QMessageBox.information(self, "Geladen", "Klassifikator wurde geladen.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    def create_color_segmentation_image(self, prediction_mask):
        h, w = prediction_mask.shape
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        for class_index, class_info in enumerate(self.project.classes):
            color = QColor(class_info.color)
            mask = prediction_mask == class_index

            rgb[mask, 0] = color.red()
            rgb[mask, 1] = color.green()
            rgb[mask, 2] = color.blue()

        return Image.fromarray(rgb, mode="RGB")

    def batch_segment_images(self):
        if self.classifier is None:
            QMessageBox.warning(
                self,
                "Fehler",
                "Bitte zuerst trainieren oder einen Klassifikator laden."
            )
            return

        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Bilder auswählen",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"
        )

        if not image_paths:
            return

        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Zielordner auswählen"
        )

        if not output_dir:
            return

        saved_count = 0
        failed_files = []

        # Excel Workbook erzeugen
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Segmentierung"

        # Header
        headers = ["Bild"]
        for class_info in self.project.classes:
            # Klassenname direkt als Excel-Spalte verwenden
            headers.append(class_info.name)

        sheet.append(headers)

        for image_path in image_paths:
            try:
                image_array = ImageLoader.load_numpy_gray(image_path)
                feature_stack, _ = FeatureExtractor.extract_features(
                    image_array,
                    selected_features=self.get_selected_feature_names()
                )

                prediction_mask = TrainingEngine.predict_full_image(
                    feature_stack,
                    self.classifier
                )

                result_image = self.create_color_segmentation_image(prediction_mask)

                filename = os.path.basename(image_path)
                name, _ = os.path.splitext(filename)
                save_path = os.path.join(output_dir, f"{name}_segmentiert.png")

                result_image.save(save_path)
                saved_count += 1

                # Prozentwerte berechnen
                total_pixels = prediction_mask.size

                row = [filename]

                for class_index, class_info in enumerate(self.project.classes):
                    class_pixels = np.count_nonzero(prediction_mask == class_index)
                    percent = (class_pixels / total_pixels) * 100
                    row.append(round(percent, 2))

                sheet.append(row)

            except Exception as e:
                failed_files.append(f"{os.path.basename(image_path)}: {e}")

        # Excel speichern
        excel_path = os.path.join(output_dir, "segmentierung_auswertung.xlsx")
        workbook.save(excel_path)

        if failed_files:
            QMessageBox.warning(
                self,
                "Batch abgeschlossen mit Fehlern",
                f"Gespeichert: {saved_count} Bild(er).\n\nExcel: {excel_path}\n\nFehler:\n" + "\n".join(failed_files)
            )
        else:
            QMessageBox.information(
                self,
                "Batch fertig",
                f"Alle {saved_count} Bild(er) wurden segmentiert.\n\nExcel gespeichert:\n{excel_path}"
            )

    # =====================================================
    # OVERLAY
    # =====================================================
    def create_overlay_pixmap(self):
        if self.prediction_mask is None:
            return None

        h, w = self.prediction_mask.shape
        rgba = np.zeros((h, w, 4), dtype=np.uint8)

        for class_index, class_info in enumerate(self.project.classes):
            color = QColor(class_info.color)
            mask = self.prediction_mask == class_index

            rgba[mask, 0] = color.red()
            rgba[mask, 1] = color.green()
            rgba[mask, 2] = color.blue()
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
        pixmap = self.create_overlay_pixmap()
        if pixmap is None:
            return

        if self.overlay_item is not None:
            self.scene.removeItem(self.overlay_item)

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
            "Wert 0.0 - 1.0:",
            value=self.overlay_opacity,
            min=0.0,
            max=1.0,
            decimals=2
        )

        if ok:
            self.overlay_opacity = float(value)
            self.show_overlay()

    def save_segmented_image(self):
        if self.prediction_mask is None or self.pixmap_item is None:
            QMessageBox.warning(self, "Fehler", "Bitte zuerst segmentieren.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Speichern",
            "",
            "PNG Files (*.png);;JPEG Files (*.jpg *.jpeg);;BMP Files (*.bmp)"
        )

        if not file_path:
            return

        try:
            result = QPixmap(self.pixmap_item.pixmap().size())
            result.fill(Qt.GlobalColor.transparent)

            painter = QPainter(result)
            painter.drawPixmap(0, 0, self.pixmap_item.pixmap())

            overlay = self.create_overlay_pixmap()
            if overlay is not None:
                painter.drawPixmap(0, 0, overlay)

            painter.end()

            if not result.save(file_path):
                raise RuntimeError("Die Datei konnte nicht gespeichert werden.")

            QMessageBox.information(self, "Gespeichert", "Bild gespeichert.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # =====================================================
    # KEYBOARD
    # =====================================================
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.hovered_stroke = None
            self.view.viewport().update()

        super().keyReleaseEvent(event)

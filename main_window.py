import os
import math

from PyQt6.QtWidgets import (
    QMainWindow, QFileDialog,
    QGraphicsScene, QGraphicsPixmapItem,
    QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QHBoxLayout, QComboBox, QInputDialog, QColorDialog, QMessageBox, QLabel,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from project_data import create_default_project
from image_loader import ImageLoader
from project_io import ProjectIO
from graphics_view import GraphicsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mehrklassen-Markierung")
        self.resize(1300, 850)

        self.project = create_default_project()
        self.pixmap_item = None
        self.current_class_index = 0
        self.hovered_path = None

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene, self)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Class", "Points", "Coordinates"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.change_active_class)

        self.active_class_label = QLabel()

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

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Aktive Klasse:"))
        top_layout.addWidget(self.class_combo)
        top_layout.addWidget(self.active_class_label)
        top_layout.addWidget(rename_button)
        top_layout.addWidget(color_button)
        top_layout.addWidget(load_image_button)
        top_layout.addWidget(save_button)
        top_layout.addWidget(load_project_button)
        top_layout.addWidget(clear_class_button)

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
        return self.pixmap_item is not None

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
        self.current_class_index = index
        self.update_active_class_label()
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

    def clear_all_paths(self):
        for class_info in self.project.classes:
            class_info.paths = []

        self.hovered_path = None

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

    def add_path_to_current_class(self, path_points):
        coords = [(p.x(), p.y()) for p in path_points]

        # Sehr kurze "Klick"-Pfade ignorieren
        if len(coords) < 2:
            return

        self.project.classes[self.current_class_index].paths.append(coords)
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

        self.project.image_path = file
        self.clear_all_paths()
        self.refresh_table()
        self.display_pixmap(pixmap)

    def refresh_table(self):
        self.table.setRowCount(0)

        for class_info in self.project.classes:
            for path in class_info.paths:
                row = self.table.rowCount()
                self.table.insertRow(row)

                points_count = len(path)
                coords = [(int(p[0]), int(p[1])) for p in path]

                self.table.setItem(row, 0, QTableWidgetItem(class_info.name))
                self.table.setItem(row, 1, QTableWidgetItem(str(points_count)))
                self.table.setItem(row, 2, QTableWidgetItem(str(coords)))

    def clear_active_class(self):
        self.project.classes[self.current_class_index].paths = []

        if self.hovered_path is not None and self.hovered_path[0] == self.current_class_index:
            self.hovered_path = None

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

            self.project = loaded_project
            self.current_class_index = 0
            self.hovered_path = None

            self.update_class_combo()
            self.update_active_class_label()
            self.refresh_table()
            self.display_pixmap(pixmap)

            QMessageBox.information(self, "Geladen", "Projekt wurde geladen.")

        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Laden fehlgeschlagen:\n{e}")

    def set_hovered_path(self, path_id):
        self.hovered_path = path_id
        self.view.viewport().update()

    def delete_path_by_id(self, path_id):
        if path_id is None:
            return

        class_index, path_index = path_id

        if class_index < 0 or class_index >= len(self.project.classes):
            self.hovered_path = None
            return

        paths = self.project.classes[class_index].paths

        if path_index < 0 or path_index >= len(paths):
            self.hovered_path = None
            return

        del paths[path_index]
        self.hovered_path = None
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

    def find_nearest_path(self, scene_pos):
        px = scene_pos.x()
        py = scene_pos.y()

        # Fangbereich in Bildschirm-Pixeln
        screen_threshold_px = 60

        current_scale = self.view.transform().m11()
        if current_scale <= 0:
            current_scale = 1.0

        threshold_scene = screen_threshold_px / current_scale

        best = None
        best_dist = float("inf")

        for class_index, class_info in enumerate(self.project.classes):
            for path_index, path in enumerate(class_info.paths):
                if len(path) < 2:
                    continue

                for i in range(len(path) - 1):
                    dist = self.distance_point_to_segment(
                        (px, py),
                        path[i],
                        path[i + 1]
                    )

                    if dist < best_dist:
                        best_dist = dist
                        best = (class_index, path_index)

        if best_dist <= threshold_scene:
            return best

        return None

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.hovered_path = None
            self.view.viewport().update()

        super().keyReleaseEvent(event)
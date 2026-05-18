from PyQt6.QtWidgets import QGraphicsView, QApplication
from PyQt6.QtGui import QPainter, QPen, QMouseEvent, QColor
from PyQt6.QtCore import Qt, QPointF


class GraphicsView(QGraphicsView):
    def __init__(self, scene, main_window):
        super().__init__(scene)
        self.main_window = main_window

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.current_path = []
        self._panning = False
        self._last_pos = None

        self.setMouseTracking(True)

    def is_ctrl_mode(self):
        return bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.main_window.has_image():
                return

            if self.is_ctrl_mode():
                return

            scene_pos = self.mapToScene(event.position().toPoint())

            # Crop-Modus: jeder Klick setzt einen Punkt
            if self.main_window.crop_mode:
                self.main_window.add_crop_point(scene_pos)
                self.scene().update()
                return

            # Normaler Modus: gedrückt halten und Klasse markieren
            self.current_path = [scene_pos]
            self.scene().update()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            if not self.is_ctrl_mode():
                self._panning = True
                self._last_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        scene_pos = self.mapToScene(event.position().toPoint())

        if self._panning and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            return

        # Im Crop-Modus wird nicht frei gemalt
        if self.main_window.crop_mode:
            self.scene().update()
            return

        if self.current_path:
            self.current_path.append(scene_pos)
            self.scene().update()
            return

        if self.is_ctrl_mode():
            hovered = self.main_window.find_nearest_stroke(scene_pos)
            self.main_window.set_hovered_stroke(hovered)
        else:
            self.main_window.set_hovered_stroke(None)

        self.scene().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.current_path:
            if not self.main_window.crop_mode:
                self.main_window.add_stroke_to_current_class(self.current_path)

            self.current_path = []
            self.scene().update()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            if self.is_ctrl_mode():
                scene_pos = self.mapToScene(event.position().toPoint())
                hit = self.main_window.find_nearest_stroke(scene_pos)

                if hit is not None:
                    self.main_window.delete_stroke_by_id(hit)

                self.scene().update()
                return

            if self._panning:
                self._panning = False
                self._last_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.main_window.set_hovered_stroke(None)
        self.scene().update()
        super().leaveEvent(event)

    def drawForeground(self, painter, rect):
        project = self.main_window.project
        hovered = self.main_window.hovered_stroke

        # Normale Klassen-Markierungen zeichnen
        for class_index, class_info in enumerate(project.classes):
            normal_color = QColor(class_info.color)

            for stroke_index, stroke in enumerate(class_info.strokes):
                points = stroke.points
                if len(points) < 2:
                    continue

                stroke_id = (class_index, stroke_index)

                pen_color = normal_color
                pen_width = max(1, stroke.brush_size)

                if hovered == stroke_id:
                    pen_color = QColor("#ff8800")
                    pen_width = max(pen_width + 2, 6)

                painter.setPen(QPen(
                    pen_color,
                    pen_width,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin
                ))

                for i in range(len(points) - 1):
                    p1 = QPointF(points[i][0], points[i][1])
                    p2 = QPointF(points[i + 1][0], points[i + 1][1])
                    painter.drawLine(p1, p2)

        # Aktuelle freie Klassen-Markierung zeichnen
        if len(self.current_path) > 1:
            active_color = QColor(
                project.classes[self.main_window.current_class_index].color
            )
            painter.setPen(QPen(
                active_color,
                max(1, self.main_window.brush_size),
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))

            for i in range(len(self.current_path) - 1):
                painter.drawLine(self.current_path[i], self.current_path[i + 1])

        # Crop-Punkte zeichnen
        crop_points = self.main_window.crop_points

        if len(crop_points) > 0:
            painter.setPen(QPen(
                QColor("#00ffff"),
                4,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))

            for i in range(len(crop_points) - 1):
                p1 = QPointF(crop_points[i][0], crop_points[i][1])
                p2 = QPointF(crop_points[i + 1][0], crop_points[i + 1][1])
                painter.drawLine(p1, p2)

            # Punkte sichtbar machen
            painter.setPen(QPen(QColor("#ff0000"), 2))
            for x, y in crop_points:
                painter.drawEllipse(QPointF(x, y), 5, 5)

            # Wenn geschlossen, letzte Linie zum ersten Punkt anzeigen
            if len(crop_points) >= 3 and self.main_window.crop_points_are_closed():
                painter.setPen(QPen(
                    QColor("#00ff00"),
                    3,
                    Qt.PenStyle.DashLine
                ))
                p_last = QPointF(crop_points[-1][0], crop_points[-1][1])
                p_first = QPointF(crop_points[0][0], crop_points[0][1])
                painter.drawLine(p_last, p_first)
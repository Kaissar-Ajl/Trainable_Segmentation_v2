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

            # Mit Ctrl: kein Zeichnen
            if self.is_ctrl_mode():
                return

            scene_pos = self.mapToScene(event.position().toPoint())
            self.current_path = [scene_pos]
            self.scene().update()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            # Nur ohne Ctrl pannen
            if not self.is_ctrl_mode():
                self._panning = True
                self._last_pos = event.position()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                return

            # Mit Ctrl noch nichts tun, Löschen auf mouseRelease
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

        if self.current_path:
            self.current_path.append(scene_pos)
            self.scene().update()
            return

        # Hover nur im Ctrl-Modus
        if self.is_ctrl_mode():
            hovered = self.main_window.find_nearest_path(scene_pos)
            self.main_window.set_hovered_path(hovered)
        else:
            self.main_window.set_hovered_path(None)

        self.scene().update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.current_path:
            self.main_window.add_path_to_current_class(self.current_path)
            self.current_path = []
            self.scene().update()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            # Ctrl + Rechtsklick => direkt an Klickposition löschen
            if self.is_ctrl_mode():
                scene_pos = self.mapToScene(event.position().toPoint())
                hit = self.main_window.find_nearest_path(scene_pos)

                if hit is not None:
                    self.main_window.delete_path_by_id(hit)

                self.scene().update()
                return

            # Normales Panning beenden
            if self._panning:
                self._panning = False
                self._last_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                return

        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self.main_window.set_hovered_path(None)
        self.scene().update()
        super().leaveEvent(event)

    def drawForeground(self, painter, rect):
        project = self.main_window.project
        hovered = self.main_window.hovered_path

        for class_index, class_info in enumerate(project.classes):
            normal_color = QColor(class_info.color)

            for path_index, path in enumerate(class_info.paths):
                if len(path) < 2:
                    continue

                path_id = (class_index, path_index)

                pen_color = normal_color
                pen_width = 2

                if hovered == path_id:
                    pen_color = QColor("#ff8800")
                    pen_width = 6

                painter.setPen(QPen(pen_color, pen_width))

                for i in range(len(path) - 1):
                    p1 = QPointF(path[i][0], path[i][1])
                    p2 = QPointF(path[i + 1][0], path[i + 1][1])
                    painter.drawLine(p1, p2)

        # Aktuell gezeichneter Pfad
        if len(self.current_path) > 1:
            active_color = QColor(
                project.classes[self.main_window.current_class_index].color
            )
            painter.setPen(QPen(active_color, 2))

            for i in range(len(self.current_path) - 1):
                painter.drawLine(self.current_path[i], self.current_path[i + 1])
from PyQt6.QtWidgets import QGraphicsView
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

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if not self.main_window.has_image():
                return
            scene_pos = self.mapToScene(event.position().toPoint())
            self.current_path = [scene_pos]

        elif event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._panning and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )

        elif self.current_path:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.current_path.append(scene_pos)
            self.scene().update()

        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.current_path:
            self.main_window.add_path_to_current_class(self.current_path)
            self.current_path = []
            self.scene().update()

        elif event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            self._last_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)

        else:
            super().mouseReleaseEvent(event)

    def drawForeground(self, painter, rect):
        project = self.main_window.project

        for class_info in project.classes:
            color = QColor(class_info.color)
            pen = QPen(color, 2)
            painter.setPen(pen)

            for path in class_info.paths:
                if len(path) < 2:
                    continue

                for i in range(len(path) - 1):
                    p1 = QPointF(path[i][0], path[i][1])
                    p2 = QPointF(path[i + 1][0], path[i + 1][1])
                    painter.drawLine(p1, p2)

        if len(self.current_path) > 1:
            active_color = QColor(
                project.classes[self.main_window.current_class_index].color
            )
            pen = QPen(active_color, 2)
            painter.setPen(pen)

            for i in range(len(self.current_path) - 1):
                painter.drawLine(self.current_path[i], self.current_path[i + 1])
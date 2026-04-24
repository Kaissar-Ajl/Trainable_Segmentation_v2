import json
import os

from project_data import ProjectData, AnnotationClass, AnnotationStroke


class ProjectIO:
    @staticmethod
    def save(project: ProjectData, file_path: str):
        project_dir = os.path.dirname(file_path)
        relative_image_path = os.path.relpath(project.image_path, project_dir)

        data = {
            "version": 3,
            "image_path": relative_image_path,
            "classes": [
                {
                    "name": c.name,
                    "color": c.color,
                    "strokes": [
                        {
                            "points": stroke.points,
                            "brush_size": stroke.brush_size,
                            "stroke_type": stroke.stroke_type,
                        }
                        for stroke in c.strokes
                    ],
                }
                for c in project.classes
            ]
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load(file_path: str) -> ProjectData:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        project_dir = os.path.dirname(file_path)
        saved_image_path = data.get("image_path", "")
        resolved_image_path = os.path.abspath(
            os.path.join(project_dir, saved_image_path)
        )

        classes_raw = data.get("classes", [])
        classes = []

        for item in classes_raw:
            name = item.get("name", "Unnamed")
            color = item.get("color", "#ff0000")

            strokes = []

            # Neues Format
            for stroke_raw in item.get("strokes", []):
                points = stroke_raw.get("points", [])
                brush_size = int(stroke_raw.get("brush_size", 8))
                stroke_type = stroke_raw.get("stroke_type")

                if stroke_type not in ("ROI", "Stroke"):
                    stroke_type = ProjectIO.detect_stroke_type(points, brush_size)

                strokes.append(
                    AnnotationStroke(
                        points=points,
                        brush_size=brush_size,
                        stroke_type=stroke_type
                    )
                )

            # Altes Format kompatibel halten
            if not strokes:
                for old_path in item.get("paths", []):
                    strokes.append(
                        AnnotationStroke(
                            points=old_path,
                            brush_size=8,
                            stroke_type=ProjectIO.detect_stroke_type(old_path, 8)
                        )
                    )

            classes.append(
                AnnotationClass(
                    name=name,
                    color=color,
                    strokes=strokes
                )
            )

        return ProjectData(
            image_path=resolved_image_path,
            classes=classes
        )

    @staticmethod
    def detect_stroke_type(points, brush_size):
        pts = [(int(round(x)), int(round(y))) for x, y in points]

        if len(pts) < 3:
            return "Stroke"

        x1, y1 = pts[0]
        x2, y2 = pts[-1]

        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        close_threshold = max(8, brush_size * 2)

        if dist <= close_threshold:
            return "ROI"

        return "Stroke"
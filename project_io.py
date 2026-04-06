import json
import os

from project_data import ProjectData, AnnotationClass, AnnotationStroke


class ProjectIO:
    @staticmethod
    def save(project: ProjectData, file_path: str):
        project_dir = os.path.dirname(file_path)
        relative_image_path = os.path.relpath(project.image_path, project_dir)

        data = {
            "version": 2,
            "image_path": relative_image_path,
            "classes": [
                {
                    "name": c.name,
                    "color": c.color,
                    "strokes": [
                        {
                            "points": stroke.points,
                            "brush_size": stroke.brush_size,
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
                strokes.append(
                    AnnotationStroke(
                        points=stroke_raw.get("points", []),
                        brush_size=int(stroke_raw.get("brush_size", 8))
                    )
                )

            # Altes Format kompatibel halten: "paths"
            if not strokes:
                for old_path in item.get("paths", []):
                    strokes.append(
                        AnnotationStroke(
                            points=old_path,
                            brush_size=8
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
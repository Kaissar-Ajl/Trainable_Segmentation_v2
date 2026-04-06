import json
import os

from project_data import ProjectData, AnnotationClass


class ProjectIO:
    @staticmethod
    def save(project: ProjectData, file_path: str):
        project_dir = os.path.dirname(file_path)
        relative_image_path = os.path.relpath(project.image_path, project_dir)

        data = {
            "version": 1,
            "image_path": relative_image_path,
            "classes": [
                {
                    "name": c.name,
                    "color": c.color,
                    "paths": c.paths,
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
        classes = [
            AnnotationClass(
                name=item.get("name", "Unnamed"),
                color=item.get("color", "#ff0000"),
                paths=item.get("paths", [])
            )
            for item in classes_raw
        ]

        return ProjectData(
            image_path=resolved_image_path,
            classes=classes
        )
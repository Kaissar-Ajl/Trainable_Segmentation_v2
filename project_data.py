from dataclasses import dataclass, field


@dataclass
class AnnotationStroke:
    points: list = field(default_factory=list)   # [(x, y), ...]
    brush_size: int = 8


@dataclass
class AnnotationClass:
    name: str
    color: str
    strokes: list[AnnotationStroke] = field(default_factory=list)


@dataclass
class ProjectData:
    image_path: str = ""
    classes: list[AnnotationClass] = field(default_factory=list)


def create_default_project() -> ProjectData:
    default_colors = [
        "#ff0000",
        "#00aa00",
        "#0000ff",
        "#ffaa00",
        "#aa00ff",
        "#00aaaa",
        "#ff00aa",
        "#666666",
    ]

    classes = [
        AnnotationClass(name=f"Class {i + 1}", color=default_colors[i])
        for i in range(8)
    ]

    return ProjectData(image_path="", classes=classes)
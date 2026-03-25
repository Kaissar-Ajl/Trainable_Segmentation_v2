# Trainable_Segmentation_v2
A modern reimplementation of the Trainable Segmentation plugin for Fiji, focused on improved speed, maintainability, and a clean architecture. The project aims to provide a faster and more extensible foundation for interactive machine-learning–based image segmentation within the Fiji/ImageJ ecosystem



Idee:

Nach dem Durchschauen des Source Codes von Trainable Segmentation sind mir ein paar Stellen aufgefallen, an denen man den Algorithmus oder die Struktur verbessern könnte. Unten habe ich die Probleme und erste Verbesserungsvorschläge gesammelt. Sie sind erstmal als Ideen gedacht und sollten geprüft werden, solange nichts dagegen spricht.

Problem 1: Abhängigkeit von Fiji

Früher war es notwendig, Fiji zu nutzen – vor allem, weil Bildverarbeitung und Benutzeroberflächen damals viel komplizierter waren. Heute bringt diese Abhängigkeit aber einige Nachteile mit sich:

Speicherplatz: Die Nutzer müssen Fiji komplett installieren, obwohl viele Funktionen gar nicht gebraucht werden.
Komplexität für Nutzer: Fiji hat sehr viele Optionen und Zwischenschritte. Für neue Nutzer kann das schnell unübersichtlich werden, was die ersten Wochen der Nutzung erschwert.
Performance: Fiji selbst bringt alte Strukturen mit, die den RAM stark belasten und die Laufzeit verlängern. Das macht das Programm insgesamt langsamer, auch wenn nicht alles nur an Fiji liegt.

Verbesserungsvorschlag:
Eine Plattform unabhängige Program der die Optionen sehr stark eingrenzt, sodass z.b. neue Benutzer direkt starten können. 
aktuellere Benutzeroberflächen, die das Program moderner wirken lassen erstmal technische irrelevant jedoch den vielen Nutzer das Leben erleichtert. 
unnötige Komplezität vermeiden und sich auf das wesentlich und meist benutze Funktionen konzentrieren, jedoch gleichzeitig das einfügen von Funktionen zukunftig erleichtern und  

Problem 2: 
das Markieren der Ränder im Schritt "Image Preparation" ist zeitintensiv.

Verbesserungsvorschlag: (Überprüfbar jetzt schon auf die Fiji Version falls unnötig bzw. zu ungenau wird direkt missachtet)
Unter Benutzung von Python Bilotheken wie z.b. OpenCV oder scikit‑image den Prozess zu automatisieren. Dafür gibt es mehrere Algorithmen, die sich durchgesetzt haben. Sollte es automatisch nicht genau sein, kann man die händische Methode benutzen.

Problem 3: (Sollte der Schritt nicht immer gleich sein, ziehe ich dieses Problem raus.)
das Aufteilen von Bilder in 4x4 Stacks im Schritt "Image Preparation" ist ein extra Aufwand für den Nutzer und wiederholt sich jedes Mal.

Verbesserungsvorschlag: 
Das sollte autoamtisiert werden und im algorithmus intergriert werden. 

Problem 4:
das Auswählen des Bildes ist seperat von der Bildverarbeitung

Verbesserungsvorschlag: 
ein automatische Vorschlag der nach der Bild Bearbeitung angenommen werden kann und direkt zum Segmentation führt. 
Bei Ablehnung kann man die Option Segmentation jeder Zeit seperat beginnen. 

Problem 5:
das entfernen/umbenennen der Klassen im Schritt Weka Segmentation ist aufwendig

Verbesserungsvorschlag:
Durch Rechtklick bzw. Durch ein Feld nicht in der Einstellung

Problem 6:
Das Definieren von 10-15 Punkten pro Klasse ist zeitaufwendig

Verbesserungsvorschlag:
Das Ziel ist natürlich, dass diese Arbeitsschritte irgendwann automatisch erledigt werden, z. B. wenn unser Code dies selbstständig übernehmen kann. Das ist unser langfristiges Endziel. Sollte dies mit den aktuellen Deep-Learning-Algorithmen noch nicht vollständig umsetzbar sein, schlage ich vor, dass das Programm dem Nutzer vorab vordefinierte Klassen vorschlägt, die auf automatischen Erkennungssystemen basieren. Falls dies keine allzu großen Ressourcen beansprucht, könnten auch Bereichsvorschläge gemacht werden – zum Beispiel durch automatisch vormarkierte Punkte, die der Nutzer dann nur noch überprüfen und gegebenenfalls korrigieren muss.

Problem 7: 
Der Weg zum automatischen Segmentation ist unübersichtlich

Verbesserungsvorschlag:
eine automatische Anfrage des Programs nach Abschluss der Wekasegmentation, das direkt das Pogram ausführt. Falls nicht erwünscht kann das später seperat händisch gestartet werden.


Ab hier ist es nur noch für Programierer interessant:







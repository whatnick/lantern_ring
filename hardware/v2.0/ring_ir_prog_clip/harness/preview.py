"""Rasterize the Fritzing SVG exports using the repository's FreeCAD Qt runtime."""

import copy
import os
import xml.etree.ElementTree as ET

import FreeCAD
from PySide2 import QtCore, QtGui, QtSvg, QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))


def outline_white_wires(path):
    root = ET.parse(path)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    changed = 0
    for group in root.iter():
        if not group.get("partID"):
            continue
        strokes = [e for e in group if e.get("stroke")
                   and e.tag.rsplit("}", 1)[-1] in ("line", "path")]
        if len(strokes) in (1, 2) and strokes[-1].get("stroke") == "#ffffff":
            if len(strokes) == 1:
                outline = copy.deepcopy(strokes[0])
                outline.set("stroke-width", str(float(outline.get("stroke-width")) * 2))
                group.insert(list(group).index(strokes[0]), outline)
                strokes.insert(0, outline)
            strokes[0].set("stroke", "#607080")
            changed += 1
    if changed != 2:
        raise ValueError("Missing white VCC wire strokes in Fritzing export: " + path)
    root.write(path, encoding="utf-8", xml_declaration=True)


def main():
    app = QtWidgets.QApplication([])
    # This bundled Qt runtime needs explicit font registration in offscreen mode.
    for name in ("arial.ttf", "arialbd.ttf"):
        path = os.path.join(os.environ["WINDIR"], "Fonts", name)
        if QtGui.QFontDatabase.addApplicationFont(path) < 0:
            raise RuntimeError("Unable to load preview font: " + path)
    for name in ("arduino_isp_harness_breadboard", "arduino_isp_harness_schematic",
                 "wiring-reference"):
        if name != "wiring-reference":
            outline_white_wires(os.path.join(HERE, name + ".svg"))
        renderer = QtSvg.QSvgRenderer(os.path.join(HERE, name + ".svg"))
        if not renderer.isValid():
            raise ValueError("Invalid harness SVG: " + name)
        size = renderer.defaultSize()
        size.scale(1800, 1400, QtCore.Qt.KeepAspectRatio)
        image = QtGui.QImage(size, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.white)
        painter = QtGui.QPainter(image)
        renderer.render(painter)
        painter.end()
        if not image.save(os.path.join(HERE, name + ".png")):
            raise RuntimeError("Unable to save harness preview: " + name)
    app.quit()


if __name__ == "__main__":
    main()

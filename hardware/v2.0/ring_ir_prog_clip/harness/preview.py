"""Rasterize the Fritzing SVG exports using the repository's FreeCAD Qt runtime."""

import os

import FreeCAD
from PySide2 import QtCore, QtGui, QtSvg, QtWidgets

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    app = QtWidgets.QApplication([])
    # This bundled Qt runtime needs explicit font registration in offscreen mode.
    for name in ("arial.ttf", "arialbd.ttf"):
        path = os.path.join(os.environ["WINDIR"], "Fonts", name)
        if QtGui.QFontDatabase.addApplicationFont(path) < 0:
            raise RuntimeError("Unable to load preview font: " + path)
    for name in ("arduino_isp_harness_breadboard", "arduino_isp_harness_schematic",
                 "wiring-reference"):
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

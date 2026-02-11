import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from duplicatesFinderUI import DuplicateFinderUI
from utils import logger

if __name__ == '__main__':
    logger.info("----------------------------begin--------------------------------")
    try:
        app = QApplication(sys.argv)
        app.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        translator = FluentTranslator()
        app.installTranslator(translator)
        window = DuplicateFinderUI()
        window.show()
        sys.exit(app.exec())
    except BaseException as e:
        if isinstance(e, SystemExit) and e.code == 0:
            logger.info("-----------------------------end---------------------------------")
        else:
            logger.exception(f"未知错误: {e}")

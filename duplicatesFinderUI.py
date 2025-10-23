import sys
import _thread
import send2trash
from pathlib import Path
from utils import showFile, showImage, logger
from duplicatesFinder import DuplicateFinder

from PySide6.QtCore import Signal, Qt, QMargins
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QVBoxLayout, QApplication, QFileDialog, QFrame, QWidget, QStackedWidget, QLabel, QTableWidgetItem, QHBoxLayout, QSplitter, \
    QTableWidget
from qfluentwidgets import LineEdit, PushButton, MessageBox, TabBar, TabCloseButtonDisplayMode, FluentIcon, Icon, MSFluentTitleBar, CommandBarView, Action, \
    FlyoutAnimationType, Flyout, TableWidget, IndeterminateProgressBar, CheckBox, ComboBox, FluentTranslator
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow


class DuplicateFinderUI(FramelessWindow):
    signalPostProcess = Signal(object)
    PHASH = "整体结构感知"
    DHASH = "纹理边缘差异"
    WHASH = "多维空间分析"

    def __init__(self):
        super().__init__()
        self.duplicatesFinder = DuplicateFinder()
        self.highDpiScale = self.windowHandle().devicePixelRatio()
        self.signalPostProcess.connect(self.postprocess)
        self.__initUI()

    def __initUI(self):
        self.setContentsMargins(0, 35, 0, 10)
        self.setTitleBar(MSFluentTitleBar(self))
        self.setWindowTitle("重图检测( ･´ω`･ )")
        self.setWindowIcon(Icon(FluentIcon.SEARCH))
        self.setMaximumSize(1920, 1080)

        inputFrame = self.__initInputUI()

        imageFrame = self.__initImageUI()

        tableFrame = self.__initTableUI()

        self.splitFrame = QSplitter(Qt.Orientation.Vertical)
        self.splitFrame.addWidget(imageFrame)
        self.splitFrame.addWidget(tableFrame)
        self.splitFrame.setStretchFactor(0, 8)
        self.splitFrame.setStretchFactor(1, 2)

        self.switchLayout(False)

        vbox = QVBoxLayout()
        vbox.addWidget(inputFrame, stretch=15)
        vbox.addWidget(self.splitFrame, stretch=85)
        self.setLayout(vbox)

    def __initInputUI(self):
        singleWidget = QWidget()
        singleLayout = QVBoxLayout()
        self.dirLineEdit = PathLineEdit()
        self.dirLineEdit.setPlaceholderText('图片目录')
        singleLayout.addWidget(self.dirLineEdit)
        singleWidget.setLayout(singleLayout)

        bothWidget = QWidget()
        bothLayout = QVBoxLayout()
        self.srcLineEdit = PathLineEdit()
        self.srcLineEdit.setPlaceholderText('源头目录')
        self.tarLineEdit = PathLineEdit()
        self.tarLineEdit.setPlaceholderText('目标目录')
        bothLayout.addWidget(self.srcLineEdit)
        bothLayout.addStretch(2)
        bothLayout.addWidget(self.tarLineEdit)
        bothWidget.setLayout(bothLayout)

        self.pivotWidget = PivotWidget()
        self.pivotWidget.addWidget(singleWidget, 'dirLineEdit', '单目录', FluentIcon.FOLDER)
        self.pivotWidget.addWidget(bothWidget, 'bothLineEdit', '对比目录', FluentIcon.FOLDER_ADD)
        self.pivotWidget.setObjectName("inputPivot")
        self.pivotWidget.setStyleSheet(r"""#inputPivot{background-color: rgb(246, 246, 246);border-right: 1px solid rgba(0, 0, 0, 15)}""")

        self.startBtn = PushButton(FluentIcon.PLAY, "开始对比")
        self.startBtn.clicked.connect(self.start)
        self.progressBar = IndeterminateProgressBar(start=False)

        self.deepSeekBox = CheckBox(self.tr("检查深层目录"))
        self.deepSeekBox.setChecked(False)

        self.hashTypeBox = ComboBox()
        self.hashTypeBox.addItems([self.PHASH, self.DHASH, self.WHASH])

        controlPanel = QVBoxLayout()
        controlPanel.setContentsMargins(10, 5, 10, 5)
        controlPanel.addWidget(self.deepSeekBox)
        controlPanel.addWidget(self.hashTypeBox)
        controlPanel.addWidget(self.startBtn)
        controlPanel.addWidget(self.progressBar)

        hbox = QHBoxLayout()
        hbox.addWidget(self.pivotWidget, stretch=8)
        hbox.addLayout(controlPanel, stretch=2)

        inputFrame = CommonFrame()
        inputFrame.setContentsMargins(QMargins(5, 0, 5, 0))
        inputFrame.addLayout(hbox)
        return inputFrame

    def __initImageUI(self):
        imageFrame = CommonFrame()
        imageFrame.setContentsMargins(QMargins(15, 10, 15, 10))
        imageFrame.setObjectName("imageFrame")
        imageFrame.setStyleSheet('''#imageFrame {border: 1px solid rgba(0, 0, 0, 15);border-radius: 4px;background-color: rgba(250, 250, 250, 200);}''')

        self.srcImgFrame = ImageFrame(dpiScale=self.highDpiScale)
        self.srcImgFrame.signalFileRemoved.connect(self.onImageRemoved)

        self.tarImgFrame = ImageFrame(dpiScale=self.highDpiScale)
        self.tarImgFrame.signalFileRemoved.connect(self.onImageRemoved)

        hbox = QHBoxLayout()
        hbox.addWidget(self.srcImgFrame, stretch=5)
        hbox.addSpacing(10)
        hbox.addWidget(self.tarImgFrame, stretch=5)
        imageFrame.addLayout(hbox)
        return imageFrame

    def __initTableUI(self):
        self.tableFrame = TableFrame()
        self.tableFrame.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tableFrame.currentCellChanged.connect(self.setCompareImage)
        self.tableFrame.setObjectName("TableFrame")
        self.tableFrame.setStyleSheet(self.tableFrame.styleSheet() + """\n#TableFrame{background-color: rgba(250, 250, 250, 200);}""")
        return self.tableFrame

    def setInputStatus(self, enable: bool):
        if enable:
            self.progressBar.stop()
        else:
            self.progressBar.start()
        self.startBtn.setEnabled(enable)
        self.hashTypeBox.setEnabled(enable)
        self.deepSeekBox.setEnabled(enable)
        self.dirLineEdit.setEnabled(enable)
        self.srcLineEdit.setEnabled(enable)
        self.tarLineEdit.setEnabled(enable)

    def switchLayout(self, visible: bool):
        if visible:
            self.setMinimumSize(900, 900)
            self.resize(900, 900)
            self.splitFrame.setVisible(visible)
        else:
            self.setMinimumSize(400, 230)
            self.resize(700, 235)
            self.splitFrame.setVisible(visible)

    def start(self):
        self.setInputStatus(False)

        currentName = self.pivotWidget.getCurrentWidgetObjectName()
        isDeepSeek = self.deepSeekBox.isChecked()
        hashType, hashSize, threshold = {
            self.PHASH: ("phash", 8, 12),
            self.DHASH: ("dhash", 8, 10),
            self.WHASH: ("whash", 8, 12)
        }.get(self.hashTypeBox.currentText())

        if currentName == "dirLineEdit":
            srcDir = self.dirLineEdit.getDirectory()
            if srcDir is None or not srcDir.exists():
                self.showMsgDialog("提示", "找不到图片的目录路径(ノдヽ)")
                self.setInputStatus(True)
                return
            _thread.start_new_thread(self.findDuplicate, (srcDir, hashType, hashSize, isDeepSeek, threshold, False))

        elif currentName == "bothLineEdit":
            srcDir = self.srcLineEdit.getDirectory()
            tarDir = self.tarLineEdit.getDirectory()
            if srcDir is None or tarDir is None or not srcDir.exists() or not tarDir.exists():
                self.showMsgDialog("提示", "找不到图片的目录路径(°Д°)")
                self.setInputStatus(True)
                return
            _thread.start_new_thread(self.findDuplicates, (srcDir, tarDir, hashType, hashSize, isDeepSeek, threshold))

        else:
            pass

    def findDuplicate(self, srcDir: str | Path, hashType: str, hashSize: int = 8, isDeepSeek: bool = False, threshold: int = 12, fullMatch: bool = False):
        try:
            logger.info(f"开始工作了, 检查[{srcDir}]目录下的图片.")
            srcHashes = self.duplicatesFinder.calcHashes(srcDir, hashType, hashSize, isDeepSeek)
            duplicates = self.duplicatesFinder.findDuplicate(srcHashes, threshold, fullMatch)
            self.signalPostProcess.emit(duplicates)
        except Exception as e:
            logger.exception(e)
            self.showMsgDialog("错误", "找不同时走神了...(-`д-´)")

    def findDuplicates(self, srcDir: str | Path, tarDir: str | Path, hashType: str, hashSize: int = 8, isDeepSeek: bool = False, threshold: int = 12):
        try:
            logger.info(f"开始工作了, 对比[{srcDir}]和[{tarDir}]目录下的图片.")
            srcHashes = self.duplicatesFinder.calcHashes(srcDir, hashType, hashSize, isDeepSeek)
            tarHashes = self.duplicatesFinder.calcHashes(tarDir, hashType, hashSize, isDeepSeek)
            duplicates = self.duplicatesFinder.findDuplicates(srcHashes, tarHashes, threshold)
            self.signalPostProcess.emit(duplicates)
        except Exception as e:
            logger.exception(e)
            self.showMsgDialog("错误", "找不同时走神了...(-`д-´)")

    def postprocess(self, duplicates: dict):
        self.setInputStatus(True)
        if len(duplicates) <= 0:
            self.showMsgDialog("提示", "没找到重复的图片(￣ω￣)")
            return
        else:
            self.showMsgDialog("提示", "检查工作完成啦(￣▽￣)")

        sheet = []
        try:
            for srcPath, tarInfos in duplicates.items():
                for nameInfo in tarInfos:
                    sheet.append([srcPath, str(nameInfo[0]), f"{nameInfo[1] * 100}%"])
            if len(sheet) > 1:
                sheet = sorted(sheet, key=lambda x: float(x[2].rstrip('%')), reverse=True)
        except Exception as e:
            logger.exception(e)
            self.showMsgDialog("错误", "整理重复图片时眼花了...┐(・o・)┌")

        self.tableFrame.setTableData(sheet, ["源图", '重图', '相似度'], [str(i) for i in range(1, len(sheet) + 1)])
        if self.isMaximized():
            self.showNormal()
        self.switchLayout(True)
        self.tableFrame.setCurrentCell(0, 0)
        moveCenter(self)

    def setCompareImage(self, row, col=None):
        rowCount = self.tableFrame.rowCount()
        if 0 <= row < rowCount:
            srcPath = self.tableFrame.item(row, 0).text()
            tarPath = self.tableFrame.item(row, 1).text()
            self.srcImgFrame.setImage(srcPath)
            self.tarImgFrame.setImage(tarPath)

    def onImageRemoved(self, text):
        self.tableFrame.delTableData(text)
        rowCount = self.tableFrame.rowCount()
        if rowCount <= 0:
            self.switchLayout(False)

    def showMsgDialog(self, title, content, isSingle: bool = True):
        msgW = MessageBox(title, content, parent=self)
        msgW.yesButton.setText('确定')
        msgW.cancelButton.setText('取消')
        if isSingle:
            msgW.cancelButton.setVisible(False)
        if msgW.exec():
            return True
        else:
            return False


# ------------------------------------------Common-UI------------------------------------------ #


class CommonFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('CommonFrame')
        self.vBoxLayout = QVBoxLayout()
        self.setLayout(self.vBoxLayout)
        self.setStyleSheet('''#CommonFrame {border: 1px solid rgba(0, 0, 0, 15);border-radius: 4px;background-color: rgba(250, 250, 250, 200);}''')

    def addWidget(self, widget, **kwargs):
        self.vBoxLayout.addWidget(widget, **kwargs)

    def addLayout(self, layout, **kwargs):
        self.vBoxLayout.addLayout(layout, **kwargs)

    def setContentsMargins(self, margins: QMargins):
        self.vBoxLayout.setContentsMargins(margins)

    def addSpacing(self, value: int):
        self.vBoxLayout.addSpacing(value)

    def addStretch(self, value: int):
        self.vBoxLayout.addStretch(value)


class PivotWidget(QFrame):
    signalCurrentChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pivot = TabBar(self)
        self.pivot.setCloseButtonDisplayMode(TabCloseButtonDisplayMode.NEVER)
        self.pivot.setAddButtonVisible(False)
        self.pivot.setTabMaximumWidth(100)
        self.pivot.setScrollable(True)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.addWidget(self.pivot, alignment=Qt.AlignmentFlag.AlignTop)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.currentWidget = None

    def addWidget(self, widget, objectName, text, icon=None):
        widget.setObjectName(objectName)
        self.pivot.addTab(routeKey=objectName, text=text, onClick=lambda: self.stackedWidget.setCurrentWidget(widget), icon=icon)
        self.stackedWidget.addWidget(widget)

    def setCurrentWidget(self, widget):
        self.currentWidget = widget
        self.stackedWidget.setCurrentWidget(widget)
        self.pivot.setCurrentTab(widget.objectName())

    def onCurrentIndexChanged(self, index):
        widget = self.stackedWidget.widget(index)
        self.currentWidget = widget
        self.pivot.setCurrentIndex(index)
        self.signalCurrentChanged.emit(int(index))

    def getCurrentWidget(self):
        return self.currentWidget

    def getCurrentWidgetObjectName(self):
        return self.currentWidget.objectName()


class PathLineEdit(LineEdit):
    def __init__(self):
        super().__init__()
        self.latestDir = None
        self.textChanged.connect(self.textChangedEvent)
        self.setAcceptDrops(True)

    def getDirectory(self) -> Path | None:
        return self.latestDir

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.choiceDirectory('选择目录')

    def choiceDirectory(self, title: str):
        if self.latestDir is None:
            self.latestDir = Path.home()
        fileDir = QFileDialog.getExistingDirectory(self.window(), title, str(self.latestDir), options=QFileDialog.Option.ShowDirsOnly)
        if not fileDir:
            return
        self.latestDir = Path(fileDir)
        self.setText(fileDir)

    def textChangedEvent(self, text):
        path = Path(text)
        if path.exists():
            self.latestDir = Path(text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.setText(str(path))


class ImageFrame(CommonFrame):
    signalFileRemoved = Signal(str)

    def __init__(self, imagePath: str | Path = None, dpiScale: float = 1.0, parent=None):
        super().__init__(parent)
        self.imagePath = imagePath
        self.image = None
        self.__initUI()
        if self.imagePath is not None:
            self.setImage(self.imagePath)
        self.flyoutMenu = None
        self.imageDpiScale = dpiScale

    def __initUI(self):
        self.setObjectName("ImageFrame")
        self.setStyleSheet('''#ImageFrame{border: 1px solid rgba(0, 0, 0, 15);border-radius: 4px;background-color: rgb(245, 245, 245);}''')
        self.imgLabel = QLabel()
        self.imgLabel.setMinimumSize(1, 1)
        self.imgLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.nameLabel = QLabel()
        self.nameLabel.setObjectName('picNameStyle')
        self.nameLabel.setStyleSheet("#picNameStyle{font: 12px 'Microsoft YaHei';padding: 5px;}")

        self.resolutionLabel = QLabel()
        self.resolutionLabel.setObjectName('picResolutionStyle')
        self.resolutionLabel.setStyleSheet("#picResolutionStyle{font: 12px 'Microsoft YaHei';padding: 5px;}")

        self.sizeLabel = QLabel()
        self.sizeLabel.setObjectName('picSizeStyle')
        self.sizeLabel.setStyleSheet("#picSizeStyle{font: 12px 'Microsoft YaHei';padding: 5px;}")

        self.setInfo(self.imagePath.name if isinstance(self.imagePath, Path) else "image name.png", 'xxxx X xxxx', 'xxx KB/MB')

        hbox = QHBoxLayout()
        hbox.addWidget(self.nameLabel, alignment=Qt.AlignmentFlag.AlignCenter, stretch=4)
        hbox.addWidget(self.sizeLabel, alignment=Qt.AlignmentFlag.AlignCenter, stretch=3)
        hbox.addWidget(self.resolutionLabel, alignment=Qt.AlignmentFlag.AlignCenter, stretch=3)

        self.addWidget(self.imgLabel, stretch=90)
        self.addLayout(hbox, stretch=10)

    def setImage(self, imagePath: str | Path):
        """加载原始图片并保存"""
        self.imagePath = imagePath if isinstance(imagePath, Path) else Path(imagePath)
        if self.imagePath.exists():
            imageSize = self.imagePath.stat().st_size
            self.image = QImage(str(self.imagePath))
            self.image.setDevicePixelRatio(self.imageDpiScale)
            self.setInfo(self.imagePath.name,
                         f"{self.image.width()} X {self.image.height()}",
                         f"{round(imageSize / 1024)} KB" if imageSize < 1024 * 1024 else f"{round(imageSize / (1024 * 1024))} MB")
            self.adjustImageSize()
        else:
            self.image = None
            self.imgLabel.clear()
            self.setInfo("文件不存在或已删除(￣ω￣;)", "xxxx X xxxx", "xxx KB/MB")

    def setInfo(self, name: str, resolution: str, size: str):
        self.nameLabel.setText(f"名字: {name}")
        self.resolutionLabel.setText(f"尺寸: {resolution}")
        self.sizeLabel.setText(f"大小: {size}")

    def setImageDpiScale(self, ratio: float):
        self.imageDpiScale = ratio

    def adjustImageSize(self):
        """根据当前label尺寸缩放图片"""
        if self.image is not None:
            scaledPixmap = QPixmap.fromImage(self.image.scaled(int(self.imgLabel.width() * self.imageDpiScale) - 2, int(self.imgLabel.height() * self.imageDpiScale) - 2, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            scaledPixmap.setDevicePixelRatio(self.imageDpiScale)
            self.imgLabel.setPixmap(scaledPixmap)

    def resizeEvent(self, event):
        """重写缩放事件"""
        super().resizeEvent(event)
        if self.image is not None:
            self.adjustImageSize()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor(200, 200, 200), 0.5, Qt.PenStyle.DotLine))

        # 绘制水平网格线
        for y in range(0, self.height(), 10):  # 20为网格间距
            painter.drawLine(0, y, self.width(), y)

        # 绘制垂直网格线
        for x in range(0, self.width(), 10):
            painter.drawLine(x, 0, x, self.height())

        super().paintEvent(event)

    def mousePressEvent(self, event):
        currentButton = event.button()
        if currentButton == Qt.MouseButton.RightButton:
            view = CommandBarView(self)

            deleteAction = Action(FluentIcon.DELETE, self.tr('删除'), triggered=self.deleteImage)
            openAction = Action(FluentIcon.FOLDER, self.tr('打开目录'), triggered=self.showFile)
            showAction = Action(FluentIcon.SEND, self.tr('打开预览'), triggered=self.showImage)
            if self.imagePath is None or not self.imagePath.exists():
                deleteAction.setEnabled(False)
                openAction.setEnabled(False)
                showAction.setEnabled(False)

            view.addAction(deleteAction)
            view.addAction(openAction)
            view.addAction(showAction)

            view.resizeToSuitableWidth()
            self.flyoutMenu = Flyout.make(view, event.globalPosition().toPoint(), self, FlyoutAnimationType.FADE_IN)

    def deleteImage(self):
        if self.imagePath is not None and self.imagePath.exists():
            send2trash.send2trash(self.imagePath)
            self.signalFileRemoved.emit(str(self.imagePath))
            if self.flyoutMenu is not None:
                self.flyoutMenu.close()

    def showFile(self):
        if self.imagePath is not None and self.imagePath.exists():
            showFile(self.imagePath)
            if self.flyoutMenu is not None:
                self.flyoutMenu.close()

    def showImage(self):
        if self.imagePath is not None and self.imagePath.exists():
            showImage(self.imagePath)
            if self.flyoutMenu is not None:
                self.flyoutMenu.close()


class TableFrame(TableWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__initUI()

    def __initUI(self):
        self.setBorderRadius(8)
        self.setBorderVisible(True)

    def setTableData(self, sheet: list | tuple, horHeader: list | tuple = None, verHeader: list | tuple = None):
        self.clear()
        row = len(sheet)
        column = len(sheet[0]) if row > 0 else 0
        self.setColumnCount(column)
        self.setRowCount(row)

        if horHeader is None:
            self.horizontalHeader().hide()
        else:
            self.setHorizontalHeaderLabels(horHeader)
        if verHeader is None:
            self.verticalHeader().hide()
        else:
            self.setVerticalHeaderLabels(verHeader)

        for i, items in enumerate(sheet):
            for j, item in enumerate(items):
                self.setItem(i, j, QTableWidgetItem(item))

    def delTableData(self, text: str):
        row = 0
        while row < self.rowCount():
            matchFound = False
            # 遍历当前行的所有列
            for col in range(self.columnCount()):
                cell = self.item(row, col)
                if cell and (text == cell.text()):
                    matchFound = True
                    break

            if matchFound:
                self.removeRow(row)  # 删除行后索引不递增
            else:
                row += 1  # 只有不删除时才递增行号
        self.setCurrentCell(self.currentRow(), 0)

    def adjustColumnsToContents(self):
        self.resizeColumnsToContents()
        columnsWidth = [self.columnWidth(col) for col in range(self.columnCount())]
        totalWidth = sum(columnsWidth)
        maxWidth = self.viewport().width() - 50
        columnsPercentage = [width / totalWidth for width in columnsWidth]
        for col in range(self.columnCount()):
            self.setColumnWidth(col, max(100, int(columnsPercentage[col] * maxWidth)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjustColumnsToContents()
        event.accept()


def moveCenter(widget: QWidget):
    rect = QApplication.primaryScreen().availableGeometry()
    w, h = rect.width(), rect.height()
    widget.move(w // 2 - widget.width() // 2, h // 2 - widget.height() // 2)


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

import logging

from os import startfile
from pathlib import Path


def showFile(filePath: str | Path):
    filePath = filePath if isinstance(filePath, Path) else Path(filePath)
    if not filePath.exists():
        return
    filePath = str(filePath).replace("/", "\\")
    startfile("explorer.exe", arguments=f'/select,"{filePath}"')


def showImage(imagePath: str | Path):
    imagePath = imagePath if isinstance(imagePath, Path) else Path(imagePath)
    if not imagePath.exists():
        return
    startfile(imagePath)


def initLogger(name: str = "logs", maxBytes: int = 0):
    logsPath = Path.cwd() / f"{name}.log"
    if logsPath.exists() and 0 < maxBytes < logsPath.stat().st_size:
        logsPath.unlink()

    if name in logging.Logger.manager.loggerDict:
        return logging.getLogger(name)

    formatter = logging.Formatter("%(asctime)s [%(threadName)s] %(name)s (%(filename)s:%(lineno)d) %(levelname)s - %(message)s")
    fileHandler = logging.FileHandler(str(logsPath), delay=True, encoding='utf-8')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(streamHandler)
    logger.addHandler(fileHandler)
    return logger


logger = initLogger("duplicatesFinder", 10 * 1048576)

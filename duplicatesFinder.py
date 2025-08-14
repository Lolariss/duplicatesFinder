import logging

import imagehash

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image


class DuplicateFinder:
    def __init__(self):
        self.hashMap = {
            'phash': imagehash.phash,
            'dhash': imagehash.dhash
        }

    def calcHash(self, imagePath: str | Path, hashMethod='phash'):
        try:
            img = Image.open(imagePath)
            hashFunc = self.hashMap[hashMethod]
            return str(imagePath), hashFunc(img)
        except Exception as e:
            logging.error(f"Error processing {imagePath}: {str(e)}")
            return str(imagePath), None

    def calcHashes(self, imageDir: str | Path, hashMethod='phash', isDeepSeek: bool = False):
        """多线程批量生成哈希字典"""
        imageDir = imageDir if isinstance(imageDir, Path) else Path(imageDir)
        hashes = {}
        with ThreadPoolExecutor() as executor:
            pathList = imageDir.rglob("*") if isDeepSeek else imageDir.glob("*")
            futures = [executor.submit(self.calcHash, path, hashMethod) for path in pathList if path.suffix.lower() in {'.jpg', '.png', '.jpeg'}]
            for future in futures:
                path, h = future.result()
                if h is not None:
                    hashes[path] = h
        return hashes

    def findDuplicate(self, hashes, threshold=12, fullMatch=False):
        """多线程安全的结果聚合"""
        duplicates = {}
        hashItems = list(hashes.items())

        def compareHashes(index):
            basePath, baseHash = hashItems[index]
            matches = []
            interval = range(len(hashItems)) if fullMatch else range(index + 1, len(hashItems))
            for num in interval:
                comparePath, compareHash = hashItems[num]
                distance = baseHash - compareHash
                if distance <= threshold:
                    similarity = 1 - distance / (len(baseHash.hash) ** 2)
                    matches.append((comparePath, round(similarity, 2)))
            return basePath, matches

        with ThreadPoolExecutor() as executor:
            results = executor.map(compareHashes, range(len(hashItems)))
            for basePath, matches in results:
                if matches:
                    duplicates[basePath] = matches
        return duplicates

    def findDuplicates(self, baseHashes, compareHash, threshold=12):
        """
        多线程对比两组哈希集合（不进行自身比对）
        :param baseHashes: Dict[str, ImageHash] 基准哈希字典
        :param compareHash: Dict[str, ImageHash] 待对比哈希字典
        :param threshold: int 汉明距离阈值
        :return: Dict[str, List[Tuple[str, float]]] 重复项字典
        """
        duplicates = {}
        baseItems = list(baseHashes.items())
        compareItems = list(compareHash.items())

        def compareHashes(base_item):
            basePath, baseHash = base_item
            matches = []
            for comparePath, compareHash in baseItems:
                distance = baseHash - compareHash
                if distance <= threshold:
                    similarity = 1 - distance / (len(baseHash.hash) ** 2)
                    matches.append((comparePath, round(similarity, 2)))
            return basePath, matches

        with ThreadPoolExecutor() as executor:
            results = executor.map(compareHashes, compareItems)
            for basePath, matches in results:
                if matches:
                    duplicates[basePath] = matches
        return duplicates

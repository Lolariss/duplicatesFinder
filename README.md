<h1 align="center">
  图片查重工具 - duplicates finder
</h1>

核心算法库 imagehash

本项目工具目录主要使用了phash、dhash、whash来进行计算图片汉明距离

使用了线程池来保证对比速度，全内存操作，在对比大量图片时会加剧内存占用

工具提供的图片删除为安全删除操作（回收站），防止误删

使用pyside6 进行了高dpi 缩放兼容，使用 [qfluentwidgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) 进行前端美化

<img width="1046" height="349" alt="图片" src="https://github.com/user-attachments/assets/0b5a469d-588c-4509-96a9-8126f61e69e9" />

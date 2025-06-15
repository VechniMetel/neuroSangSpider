# ![](https://qingchenyou-1301914189.cos.ap-beijing.myqcloud.com/this_32.png)NeuroSongSpider



## 项目简介

这是一个基于 `Python 3.13` 开发的歌回软件，用于从 Bilibili（哔哩哔哩）爬取 **Neuro/Evil** 的歌曲的视频内容。

~~(当然也可以通过自定义 **UP 主列表** 和 **关键词**，灵活调整爬取目标)~~ 

目前 GUI 界面仍在开发中。

---

## 特性概述
### ✅ 已实现功能
- 获取歌回列表，支持按设置的 UP 主和关键词筛选目标视频
- 支持搜索歌曲，下载指定歌回、本地播放歌曲
- 基于 `PyQt6` 的GUI
- 调用bilibili搜索补全歌曲列表
- 升级 GUI 界面，提供可视化交互（设置面板等）

### 🚧 正在计划中
- 支持在线播放，无需下载歌曲
- 支持修改更多设置项
- 添加更多功能

---

## 安装步骤

选择对应的系统版本，下载后解压
打开`NeuroSongSpider.exe`既可

如果你想要更好的效果要点击“获取视频列表”!!!

---

## 构建步骤

**请注意，如果你要拉取仓库，请拉取master仓库！如果你要提交代码，请PR到Other仓库！请确保你的代码没有问题后再提交到master仓库！**

首先你需要将ffmpeg扔到ffmpeg文件夹，因为这个软件需要ffmpeg

路径为 `项目根目录/ffmpeg/bin/ffmpeg.exe`

```bash
# 克隆仓库
git clone https://github.com/qingchenyouforcc/neuroSangSpider

# 进入目录
cd neuroSangSpider

# 安装依赖
uv sync

# 运行
uv run main.py
```

---

## 感谢名单

### 感谢Stazer提供的加载动画授权

- 稳定器stz https://space.bilibili.com/125198191

### 感谢以下up主对Neuro/Evil歌回的贡献，没有你们就不会有这个项目的出现

- _环戊烷多氢菲_ https://space.bilibili.com/351692111
- Neuro21烤肉组 https://space.bilibili.com/1880487363
- 绅士羊OuO https://space.bilibili.com/22535350
- NSC987 https://space.bilibili.com/3546612622166788
- 西街Westreet https://space.bilibili.com/5971855
- BulletFX https://space.bilibili.com/483178955
- ASDFHGV https://space.bilibili.com/690857494
- 意念艾特感叹号 https://space.bilibili.com/390418501

以及感谢所有切Neuro/Evil歌回和做二创的UP主们

还有对本项目做出贡献的所有开发者

![](https://qingchenyou-1301914189.cos.ap-beijing.myqcloud.com/681dcdd42da7fc5484c1dd3a9875b54a_324.png)

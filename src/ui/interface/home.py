from PyQt6.QtCore import Qt, QTimer, QSize, QEvent
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QIcon
from qfluentwidgets import (
    BodyLabel, SubtitleLabel, TitleLabel, CardWidget, IconWidget, 
    TransparentToolButton, FluentIcon as FIF,
    ProgressBar, ScrollArea, isDarkTheme
)

from src.config import VERSION, cfg
from src.app_context import app_context
from src.core.player import nextSong, previousSong
from src.ui.widgets.custom_label import ScrollingLabel


class NowPlayingCard(CardWidget):
    """当前播放音乐卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nowPlayingCard")
        
        # 设置卡片大小
        self.setFixedHeight(200)
        self.setMinimumWidth(400)
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(10)
        
        # 标题栏
        self.headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel("当前播放", self)
        self.titleIcon = IconWidget(FIF.MUSIC, self)
        self.headerLayout.addWidget(self.titleIcon)
        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addStretch(1)
        
        # 歌曲信息
        self.infoLayout = QHBoxLayout()
        
        # 封面图片
        self.coverLabel = QLabel(self)
        self.coverLabel.setFixedSize(100, 100)
        self.coverLabel.setScaledContents(True)
        
        # 使用已有的图标作为默认封面
        self.musicIcon = QIcon(FIF.MUSIC.path())
        self.defaultCover = self.musicIcon.pixmap(QSize(100, 100))
        self.coverLabel.setPixmap(self.defaultCover)
        
        # 歌曲详情
        self.detailLayout = QVBoxLayout()
        self.songNameLabel = ScrollingLabel("未播放", self)
        self.songNameLabel.setFixedHeight(30)
        # 设置滚动参数：速度适中，边缘停留时间较长，每次滚动1像素，边缘留白合适
        self.songNameLabel.setScrollingSettings(speed=40, pause_time=2000, scroll_step=1, margin=25)
        
        # 播放进度条
        self.progressLayout = QHBoxLayout()
        self.currentTimeLabel = QLabel("0:00", self)
        self.progressBar = ProgressBar(self)
        self.progressBar.setValue(0)
        self.totalTimeLabel = QLabel("0:00", self)
        self.progressLayout.addWidget(self.currentTimeLabel)
        self.progressLayout.addWidget(self.progressBar, 1)
        self.progressLayout.addWidget(self.totalTimeLabel)
        
        # 播放控制按钮
        self.controlLayout = QHBoxLayout()
        self.prevButton = TransparentToolButton(FIF.CARE_LEFT_SOLID, self)
        self.playButton = TransparentToolButton(FIF.PLAY_SOLID, self)
        self.nextButton = TransparentToolButton(FIF.CARE_RIGHT_SOLID, self)
        
        self.controlLayout.addStretch(1)
        self.controlLayout.addWidget(self.prevButton)
        self.controlLayout.addWidget(self.playButton)
        self.controlLayout.addWidget(self.nextButton)
        self.controlLayout.addStretch(1)
        
        # 添加详情布局
        self.detailLayout.addWidget(self.songNameLabel)
        self.detailLayout.addLayout(self.progressLayout)
        self.detailLayout.addLayout(self.controlLayout)
        self.detailLayout.addStretch(1)
        
        # 添加到信息布局
        self.infoLayout.addWidget(self.coverLabel)
        self.infoLayout.addSpacing(10)
        self.infoLayout.addLayout(self.detailLayout, 1)
        
        # 添加到主布局
        self.vBoxLayout.addLayout(self.headerLayout)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addLayout(self.infoLayout, 1)
        
        # 连接信号和槽
        self.prevButton.clicked.connect(previousSong)
        self.playButton.clicked.connect(self._togglePlay)
        self.nextButton.clicked.connect(nextSong)
        
        # 创建定时器，用于更新播放进度
        self.updateTimer = QTimer(self)
        self.updateTimer.setInterval(1000)  # 每秒更新一次
        self.updateTimer.timeout.connect(self.updatePlayingInfo)
        self.updateTimer.start()
        
        # 初始化
        self.updatePlayingInfo()
        self._updateStyle()
    
    def _togglePlay(self):
        """切换播放/暂停状态"""
        assert app_context.player is not None, "播放器未初始化"
        app_context.player.togglePlayState()
        self.playButton.setIcon(FIF.PAUSE_BOLD)
    
    def updatePlayingInfo(self):
        """更新当前播放信息"""
        if not app_context.player or not app_context.playing_now:
            self.songNameLabel.setText("未播放")
            self.progressBar.setValue(0)
            self.currentTimeLabel.setText("0:00")
            self.totalTimeLabel.setText("0:00")
            self.playButton.setIcon(FIF.PLAY_SOLID)
            return
        
        # 更新歌曲名称，美化显示
        song_name = app_context.playing_now.rsplit('.', 1)[0]
        # 从文件名中提取更简洁的显示名称
        if "【" in song_name and "】" in song_name:
            # 尝试提取更友好的名称格式
            author = song_name.split("【")[1].split("】")[0]
            parts = song_name.split("】")
            if len(parts) > 1 and "⭐" in parts[1]:
                display_name = parts[1].split("⭐")[1].split("🎵")[0].strip()
                if display_name:  # 如果成功提取到歌名
                    song_name = f"▶ {display_name} - {author}"
        
        # 检查是否需要更新文本，避免不必要的重置
        if self.songNameLabel.text() != song_name:
            self.songNameLabel.setText(song_name)
            # 文本更新后，确保滚动正常工作
            self.songNameLabel._checkIfNeedsScroll()
        # 即使文本没变，也要确保滚动状态正确
        elif hasattr(self.songNameLabel, '_animate') and self.songNameLabel._animate and not self.songNameLabel._timerId:
            self.songNameLabel._startScrolling()
        
        # 更新播放状态图标
        if app_context.player and app_context.player.player:
            if app_context.player.player.isPlaying():
                # 使用其他图标作为暂停图标
                self.playButton.setIcon(FIF.PAUSE_BOLD)
            else:
                self.playButton.setIcon(FIF.PLAY_SOLID)
        
        # 更新进度
        position = app_context.player.player.position()
        duration = app_context.player.player.duration()
        
        if duration > 0:
            # 更新进度条
            self.progressBar.setValue(int(position / duration * 100))
            
            # 更新时间标签
            self.currentTimeLabel.setText(self._formatTime(position))
            self.totalTimeLabel.setText(self._formatTime(duration))
    
    def _formatTime(self, time_ms):
        """格式化时间（毫秒转为分:秒）"""
        time_s = int(time_ms / 1000)
        minutes = time_s // 60
        seconds = time_s % 60
        return f"{minutes}:{seconds:02d}"
        
    def _updateStyle(self):
        """根据当前主题更新样式"""
        dark_mode = isDarkTheme()
        
        # 调整标签颜色
        text_color = "white" if dark_mode else "black"
        self.currentTimeLabel.setStyleSheet(f"color: {text_color};")
        self.totalTimeLabel.setStyleSheet(f"color: {text_color};")
        
        # 更新歌曲名称标签样式
        self.songNameLabel.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {text_color};
            padding: 2px;
        """)
        
        # 如果使用默认封面，根据主题调整图标
        if app_context.player and not app_context.playing_now:
            # 根据主题调整默认音乐图标的颜色
            icon_path = FIF.MUSIC.path()
            self.musicIcon = QIcon(icon_path)
            self.defaultCover = self.musicIcon.pixmap(QSize(100, 100))
            self.coverLabel.setPixmap(self.defaultCover)
        
        # 更新按钮样式
        for btn in [self.prevButton, self.playButton, self.nextButton]:
            btn.update()
            
        # 触发歌名标签重绘
        self.songNameLabel.update()
    
    def changeEvent(self, a0):
        """处理控件状态变化事件"""
        if a0 and a0.type() == QEvent.Type.PaletteChange:
            # 调色板变化（主题变化）时更新样式
            self._updateStyle()
        super().changeEvent(a0)


class WelcomeCard(CardWidget):
    """欢迎卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("welcomeCard")
        
        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(10)
        
        # 标题
        self.titleLabel = SubtitleLabel("欢迎使用 NeuroSangSpider", self)
        
        # 介绍
        self.infoLabel = BodyLabel(
            "这是一个基于 Python 3.13 开发的歌回播放软件。"
            "\n\n主要功能："
            "\n • 智能搜索机制，精准查找歌曲"
            "\n • 可自定义UP主列表和关键词"
            "\n • 音频提取与播放"
            "\n • 本地播放器，支持播放队列管理"
            f"\n\nLicense: AGPL-3.0\nVersion: {VERSION}",
            self
        )
        self.infoLabel.setWordWrap(True)
        
        # 添加到主布局
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.infoLabel, 1)
        
        # 初始化样式
        self._updateStyle()
    
    def _updateStyle(self):
        """根据当前主题更新样式"""
        # WelcomeCard样式已自动适应主题，这里预留方法以便将来扩展
        pass
        
    def changeEvent(self, a0):
        """处理控件状态变化事件"""
        if a0 and a0.type() == QEvent.Type.PaletteChange:
            # 调色板变化（主题变化）时更新样式
            self._updateStyle()
        super().changeEvent(a0)


class HomeInterface(QWidget):
    """主页GUI"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("homeInterface")

        # 创建滚动区域
        self.scrollArea = ScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建容器小部件
        self.container = QWidget(self.scrollArea)
        self.container.setObjectName("homeContainer")
        self.scrollArea.setWidget(self.container)
        
        # 主布局
        self.mainLayout = QVBoxLayout(self)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.mainLayout.addWidget(self.scrollArea)
        
        # 容器布局
        self._layout = QVBoxLayout(self.container)
        self._layout.setContentsMargins(30, 30, 30, 30)
        self._layout.setSpacing(20)
        
        # 页面标题
        self.titleLabel = TitleLabel("NeuroSangSpider", self.container)
        
        # 创建卡片组件
        self.nowPlayingCard = NowPlayingCard(self.container)
        self.welcomeCard = WelcomeCard(self.container)
        
        # 添加版本信息和版权声明
        self.versionLabel = BodyLabel(f"版本: {VERSION} | NeuroSangSpider", self.container)
        self.versionLabel.setObjectName("versionLabel")
        
        # 添加小部件到布局
        self._layout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignTop)
        self._layout.addWidget(self.nowPlayingCard)
        self._layout.addWidget(self.welcomeCard)
        self._layout.addWidget(self.versionLabel, 0, Qt.AlignmentFlag.AlignRight)
        
        self._layout.addStretch(1)
        
        # 初始化样式
        self._updateStyle()
        
        # 连接主题变化信号
        cfg.theme_mode.valueChanged.connect(self._updateStyle)
    
    def _updateStyle(self):
        """根据当前主题更新界面样式"""
        dark_mode = isDarkTheme()
        
        # 更新滚动区域的透明度设置
        self.scrollArea.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # 更新版本标签样式
        text_color = "rgba(255, 255, 255, 150)" if dark_mode else "rgba(0, 0, 0, 150)"
        self.versionLabel.setStyleSheet(f"color: {text_color}")
        
        # 刷新组件
        self.nowPlayingCard._updateStyle()
        self.welcomeCard._updateStyle()
        
    def changeEvent(self, a0):
        """处理控件状态变化事件"""
        if a0 and a0.type() == QEvent.Type.PaletteChange:
            # 调色板变化（主题变化）时更新样式
            self._updateStyle()
        super().changeEvent(a0)

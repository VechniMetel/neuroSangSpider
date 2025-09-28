from PyQt6.QtCore import Qt, QTimer, QEvent
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtGui import QIcon, QPainter, QPainterPath, QColor, QPixmap
from qfluentwidgets import (
    BodyLabel,
    SubtitleLabel,
    TitleLabel,
    CardWidget,
    IconWidget,
    TransparentToolButton,
    FluentIcon as FIF,
    ProgressBar,
    ScrollArea,
    isDarkTheme,
)

try:
    # 优先从公开导出导入
    from qfluentwidgets import AcrylicBrush  # type: ignore
except Exception:  # pragma: no cover - 兼容不同版本的导出位置
    try:
        from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush  # type: ignore
    except Exception:
        AcrylicBrush = None  # type: ignore
from loguru import logger

from src.i18n.i18n import t
from src.config import VERSION, cfg
from src.app_context import app_context
from src.core.player import nextSong, previousSong, getMusicLocalStr
from src.ui.widgets.custom_label import ScrollingLabel
from src.utils.cover import get_cover_pixmap


def _rgba_to_qcolor(rgba, fallback=(255, 255, 255, 255)) -> QColor:
    """将 [r,g,b,a] 转为 QColor，数值自动裁剪到 0-255。"""
    try:
        if not rgba or len(rgba) != 4:
            r, g, b, a = fallback
        else:
            r, g, b, a = [int(max(0, min(255, int(x)))) for x in rgba]
        return QColor(r, g, b, a)
    except Exception:
        r, g, b, a = fallback
        return QColor(r, g, b, a)


class NowPlayingCard(CardWidget):
    """当前播放音乐卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nowPlayingCard")
        # 记录上一次用于封面的歌曲名，避免重复刷新
        self._last_cover_song_name = None
        self._acrylic_ready = (
            bool(AcrylicBrush) and getattr(cfg, "acrylic_enabled", None) and bool(cfg.acrylic_enabled.value)
        )

        # 设置卡片大小
        self.setFixedHeight(200)
        self.setMinimumWidth(400)

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 16, 16, 16)
        self.vBoxLayout.setSpacing(10)

        # 背景：亚克力材质（使用歌曲封面）
        # 使用独立子控件承载亚克力绘制，避免与 CardWidget 的绘制顺序冲突
        class _AcrylicBackground(QWidget):
            def __init__(self, parent_card: "NowPlayingCard"):
                super().__init__(parent_card)
                self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self._has_image = False
                self._radius = 12
                # 依据配置创建亚克力画刷
                self._brush = None
                self.build_brush_from_cfg()

            def build_brush_from_cfg(self):
                """按当前配置重建亚克力画刷。"""
                self._brush = None
                if not AcrylicBrush:
                    return
                if not (getattr(cfg, "acrylic_enabled", None) and bool(cfg.acrylic_enabled.value)):
                    return
                try:
                    tint_list = list(cfg.acrylic_tint_rgba.value)
                except Exception:
                    tint_list = [242, 242, 242, 140]
                try:
                    lum_list = list(cfg.acrylic_luminosity_rgba.value)
                except Exception:
                    lum_list = [255, 255, 255, 12]
                try:
                    blur_r = int(cfg.acrylic_blur_radius.value)
                except Exception:
                    blur_r = 18
                tint = _rgba_to_qcolor(tint_list)
                luminosity = _rgba_to_qcolor(lum_list)
                self._brush = AcrylicBrush(self, blurRadius=blur_r, tintColor=tint, luminosityColor=luminosity)
                # 刷新裁剪路径
                self._updateClipPath()

            def setPixmap(self, pix: QPixmap | None):
                if not self._brush:
                    return
                if isinstance(pix, QPixmap) and not pix.isNull():
                    self._brush.setImage(pix)
                    self._has_image = True
                else:
                    # 传入空图时清空显示
                    self._has_image = False
                self.update()

            def _updateClipPath(self):
                if not self._brush:
                    return
                r = int(getattr(getattr(cfg, "cover_corner_radius", None), "value", 12) or 12)
                r = max(0, r)
                self._radius = r
                path = QPainterPath()
                w, h = self.width(), self.height()
                path.addRoundedRect(0.0, 0.0, float(w), float(h), float(r), float(r))
                self._brush.setClipPath(path)

            def resizeEvent(self, a0):
                super().resizeEvent(a0)
                self._updateClipPath()

            def paintEvent(self, a0):
                super().paintEvent(a0)
                if not self._brush or not self._has_image:
                    return
                try:
                    self._brush.paint()
                except Exception:
                    # 亚克力绘制失败时，不影响其它内容
                    pass

        self._acrylicBg = _AcrylicBackground(self)
        self._acrylicBg.lower()

        # 标题栏
        self.headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(t("home.titlebar.now_playing"), self)
        self.titleIcon = IconWidget(FIF.MUSIC, self)
        self.titleIcon.setFixedSize(28, 28)
        self.headerLayout.addWidget(self.titleIcon)
        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addStretch(1)

        # 歌曲信息
        self.infoLayout = QHBoxLayout()

        # 歌曲详情
        self.detailLayout = QVBoxLayout()
        self.songNameLabel = ScrollingLabel(t("home.now_playing.wait_play"), self)
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
        # 移除左侧封面占位，详情占据整行
        self.infoLayout.addLayout(self.detailLayout, 1)

        # 添加到主布局
        self.vBoxLayout.addLayout(self.headerLayout)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addLayout(self.infoLayout, 1)

        # 连接信号和槽
        self.prevButton.clicked.connect(previousSong)
        self.playButton.clicked.connect(self._togglePlay)
        self.nextButton.clicked.connect(nextSong)

        # 创建定时器，用于更新播放进度（去重后保留一份）
        self.updateTimer = QTimer(self)
        self.updateTimer.setInterval(1000)  # 每秒更新一次
        self.updateTimer.timeout.connect(self.updatePlayingInfo)
        self.updateTimer.start()

        # 初始化
        self.updatePlayingInfo()
        self._updateStyle()

        # 监听配置变化，实时重建亚克力参数
        try:
            cfg.acrylic_enabled.valueChanged.connect(lambda *_: self.rebuildAcrylicFromConfig())
            cfg.acrylic_blur_radius.valueChanged.connect(lambda *_: self.rebuildAcrylicFromConfig())
            cfg.acrylic_tint_rgba.valueChanged.connect(lambda *_: self.rebuildAcrylicFromConfig())
            cfg.acrylic_luminosity_rgba.valueChanged.connect(lambda *_: self.rebuildAcrylicFromConfig())
        except Exception:
            pass

    def _togglePlay(self):
        """切换播放/暂停状态"""
        assert app_context.player is not None, t("home.now_playing.player_not_init")
        app_context.player.togglePlayState()
        self.playButton.setIcon(FIF.PAUSE_BOLD)

    def updatePlayingInfo(self):
        """更新当前播放信息"""
        if not app_context.player or not app_context.playing_now:
            self.songNameLabel.setText(t("home.now_playing.wait_play"))
            self.progressBar.setValue(0)
            self.currentTimeLabel.setText("0:00")
            self.totalTimeLabel.setText("0:00")
            self.playButton.setIcon(FIF.PLAY_SOLID)
            # 清理亚克力背景
            if self._acrylic_ready:
                self._acrylicBg.setPixmap(None)
            # 恢复标题图标为音乐图标
            self.titleIcon.setIcon(FIF.MUSIC)
            self._last_cover_song_name = None
            return

        # 更新歌曲名称，美化显示
        song_name = app_context.playing_now.rsplit(".", 1)[0]
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
        elif (
            hasattr(self.songNameLabel, "_animate") and self.songNameLabel._animate and not self.songNameLabel._timerId
        ):
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

        # 更新亚克力封面背景（仅在歌曲变更时刷新，避免每秒拉取）
        try:
            current_name = app_context.playing_now
            if current_name and current_name != self._last_cover_song_name:
                path = getMusicLocalStr(current_name)
                if path:
                    # 先取较大尺寸以获得更清晰裁切，再中心裁切到目标显示尺寸
                    # 对背景，我们按卡片尺寸生成更大底图
                    target_w, target_h = max(self.width(), 300), max(self.height(), 200)
                    base_size = max(target_w, target_h, 512)
                    pix = get_cover_pixmap(path, size=base_size)
                    # 设置亚克力背景（内部会按控件大小裁切/绘制）
                    if self._acrylic_ready:
                        # 尽量居中裁切以避免拉伸
                        pix2 = self._scale_center_crop(pix, target_w, target_h)
                        self._acrylicBg.setPixmap(pix2)
                    # 同步把标题栏的小图标换成小尺寸圆角封面（可选）
                    try:
                        icon_size = 28
                        small = self._scale_center_crop(pix, icon_size, icon_size)
                        r2 = max(0, int(min(icon_size, icon_size) / 5))
                        if r2 > 0:
                            w2, h2 = small.width(), small.height()
                            rounded2 = small.__class__(w2, h2)
                            rounded2.fill(Qt.GlobalColor.transparent)
                            painter2 = QPainter(rounded2)
                            painter2.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                            path2b = QPainterPath()
                            path2b.addRoundedRect(0.0, 0.0, float(w2), float(h2), float(r2), float(r2))
                            painter2.setClipPath(path2b)
                            painter2.drawPixmap(0, 0, small)
                            painter2.end()
                            small = rounded2
                            # 如果 IconWidget 支持从 QIcon 设置，则应用
                            try:
                                self.titleIcon.setIcon(QIcon(small))
                            except Exception:
                                pass
                    except Exception:
                        pass
                    self._last_cover_song_name = current_name
        except Exception as e:
            logger.exception(f"更新主页封面失败: {e}")

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

        # 背景亚克力不依赖主题切换，仅微调色调（可按需扩展）
        # 这里保留默认逻辑，不做额外处理

        # 更新按钮样式
        for btn in [self.prevButton, self.playButton, self.nextButton]:
            btn.update()

        # 触发歌名标签重绘
        self.songNameLabel.update()

    @staticmethod
    def _rgba_to_qcolor(rgba: list[int] | tuple[int, int, int, int] | None, fallback=(255, 255, 255, 255)) -> QColor:
        try:
            if not rgba or len(rgba) != 4:
                r, g, b, a = fallback
            else:
                r, g, b, a = [int(max(0, min(255, x))) for x in rgba]
            return QColor(r, g, b, a)
        except Exception:
            r, g, b, a = fallback
            return QColor(r, g, b, a)

    def changeEvent(self, a0):
        """处理控件状态变化事件"""
        if a0 and a0.type() == QEvent.Type.PaletteChange:
            # 调色板变化（主题变化）时更新样式
            self._updateStyle()
        super().changeEvent(a0)

    def resizeEvent(self, a0):
        # 同步调整背景铺满卡片
        super().resizeEvent(a0)
        try:
            if hasattr(self, "_acrylicBg"):
                self._acrylicBg.setGeometry(self.rect())
        except Exception:
            pass

    def rebuildAcrylicFromConfig(self):
        """根据配置重建亚克力背景和状态。"""
        self._acrylic_ready = (
            bool(AcrylicBrush) and getattr(cfg, "acrylic_enabled", None) and bool(cfg.acrylic_enabled.value)
        )
        if hasattr(self, "_acrylicBg") and self._acrylicBg:
            self._acrylicBg.build_brush_from_cfg()
        # 根据当前歌曲刷新或清空背景
        if not self._acrylic_ready:
            try:
                self._acrylicBg.setPixmap(None)
            except Exception:
                pass
        else:
            # 重新应用当前封面作为背景
            self.updatePlayingInfo()

    # --- helpers ---
    def _scale_center_crop(self, pix, target_w: int, target_h: int):
        """按原比例缩放以覆盖目标区域后，从中心裁切到目标尺寸。"""
        if pix.isNull() or target_w <= 0 or target_h <= 0:
            return pix
        scaled = pix.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - target_w) // 2)
        y = max(0, (scaled.height() - target_h) // 2)
        return scaled.copy(x, y, target_w, target_h)


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
        self.titleLabel = SubtitleLabel(t("home.welcome.title"), self)

        # 介绍
        self.infoLabel = BodyLabel(t("home.welcome.introduction", version=VERSION), self)
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


class SongStatsCard(CardWidget):
    """歌曲统计信息卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("songStatsCard")

        # 设置卡片大小
        self.setMinimumWidth(400)
        self.setFixedHeight(130)

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(16, 12, 16, 16)
        self.vBoxLayout.setSpacing(12)

        # 标题栏
        self.headerLayout = QHBoxLayout()
        self.titleLabel = SubtitleLabel(t("home.song_stats.title"), self)
        self.titleIcon = IconWidget(FIF.ALBUM, self)
        self.headerLayout.addWidget(self.titleIcon)
        self.headerLayout.addWidget(self.titleLabel)
        self.headerLayout.addStretch(1)

        # 统计信息布局
        self.statsLayout = QHBoxLayout()
        self.statsLayout.setSpacing(20)

        # 歌曲数量统计
        self.songCountLayout = QVBoxLayout()
        self.songCountIcon = IconWidget(FIF.LIBRARY, self)
        self.songCountIcon.setFixedSize(32, 32)
        self.songCountLabel = BodyLabel(t("home.song_stats.song_count_text", song_count="0"), self)
        self.songCountLabel.setObjectName("statsLabel")
        self.songCountLayout.addWidget(self.songCountIcon, 0, Qt.AlignmentFlag.AlignCenter)
        self.songCountLayout.addWidget(self.songCountLabel, 0, Qt.AlignmentFlag.AlignCenter)
        self.songCountLayout.setSpacing(8)

        # 空间占用统计
        self.spaceUsageLayout = QVBoxLayout()
        self.spaceUsageIcon = IconWidget(FIF.FOLDER, self)
        self.spaceUsageIcon.setFixedSize(32, 32)
        self.spaceUsageLabel = BodyLabel(t("home.song_stats.space_usage_text", space_usage="0MB"), self)
        self.spaceUsageLabel.setObjectName("statsLabel")
        self.spaceUsageLayout.addWidget(self.spaceUsageIcon, 0, Qt.AlignmentFlag.AlignCenter)
        self.spaceUsageLayout.addWidget(self.spaceUsageLabel, 0, Qt.AlignmentFlag.AlignCenter)
        self.spaceUsageLayout.setSpacing(8)

        # 总播放次数统计
        self.totalPlayLayout = QVBoxLayout()
        self.totalPlayIcon = IconWidget(FIF.PLAY, self)
        self.totalPlayIcon.setFixedSize(32, 32)
        self.totalPlayLabel = BodyLabel(t("home.song_stats.total_play_text", play_count="0"), self)
        self.totalPlayLabel.setObjectName("statsLabel")
        self.totalPlayLayout.addWidget(self.totalPlayIcon, 0, Qt.AlignmentFlag.AlignCenter)
        self.totalPlayLayout.addWidget(self.totalPlayLabel, 0, Qt.AlignmentFlag.AlignCenter)
        self.totalPlayLayout.setSpacing(8)

        # 添加到统计信息布局
        self.statsLayout.addLayout(self.songCountLayout)
        self.statsLayout.addLayout(self.spaceUsageLayout)
        self.statsLayout.addLayout(self.totalPlayLayout)

        # 添加到主布局
        self.vBoxLayout.addLayout(self.headerLayout)
        self.vBoxLayout.addLayout(self.statsLayout)

        # 创建定时器，定期更新统计信息
        self.updateTimer = QTimer(self)
        self.updateTimer.setInterval(30000)
        self.updateTimer.timeout.connect(self.updateStats)
        self.updateTimer.start()

        # 初始化
        self.updateStats()
        self._updateStyle()

    def updateStats(self):
        """更新歌曲统计信息"""
        from src.config import MUSIC_DIR
        import os

        try:
            song_files = [f for f in os.listdir(MUSIC_DIR) if f.lower().endswith((".mp3", ".ogg", ".wav"))]
            song_count = len(song_files)

            total_size = sum(os.path.getsize(os.path.join(MUSIC_DIR, f)) for f in song_files)

            try:
                plays_dict = getattr(cfg.play_count, "value", {})
                total_plays = sum(int(v) for v in plays_dict.values()) if isinstance(plays_dict, dict) else 0
            except Exception:
                total_plays = 0

            if total_size < 1024 * 1024:
                size_str = f"{total_size / 1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"

            self.songCountLabel.setText(t("home.song_stats.song_count_text", song_count=song_count))
            self.spaceUsageLabel.setText(t("home.song_stats.space_usage_text", space_usage=size_str))
            total_plays_str = f"{total_plays:,}" if isinstance(total_plays, int) else str(total_plays)
            self.totalPlayLabel.setText(t("home.song_stats.total_play_text", play_count=total_plays_str))

            if song_count > 0:
                self.songCountIcon.setIcon(FIF.LIBRARY)
                self.spaceUsageIcon.setIcon(FIF.FOLDER)
                self.totalPlayIcon.setIcon(FIF.PLAY)
            else:
                self.songCountIcon.setIcon(FIF.DOCUMENT)
                self.spaceUsageIcon.setIcon(FIF.REMOVE)
                self.totalPlayIcon.setIcon(FIF.PLAY)

        except Exception as e:
            self.songCountLabel.setText(t("home.song_stats.song_count_text", song_count="0"))
            self.spaceUsageLabel.setText(t("home.song_stats.space_usage_text", space_usage="0KB"))
            self.totalPlayLabel.setText(t("home.song_stats.total_play_text", play_count="0"))
            self.songCountIcon.setIcon(FIF.DOCUMENT)
            self.spaceUsageIcon.setIcon(FIF.REMOVE)
            self.totalPlayIcon.setIcon(FIF.PLAY)
            logger.error(f"更新歌曲统计信息失败: {e}")

    def _updateStyle(self):
        """根据当前主题更新样式"""
        dark_mode = isDarkTheme()
        text_color = "white" if dark_mode else "black"

        stats_style = f"""
            color: {text_color};
            font-weight: bold;
            font-size: 14px;
        """
        self.songCountLabel.setStyleSheet(stats_style)
        self.spaceUsageLabel.setStyleSheet(stats_style)
        self.totalPlayLabel.setStyleSheet(stats_style)

        for icon in [self.songCountIcon, self.spaceUsageIcon, self.totalPlayIcon]:
            icon.setFixedSize(36, 36)

    def changeEvent(self, a0):
        if a0 and a0.type() == QEvent.Type.PaletteChange:
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
        self.songStatsCard = SongStatsCard(self.container)
        self.welcomeCard = WelcomeCard(self.container)

        # 添加版本信息和版权声明
        self.versionLabel = BodyLabel(f"{t('app.version')}: {VERSION} | NeuroSangSpider", self.container)
        self.versionLabel.setObjectName("versionLabel")

        # 添加小部件到布局
        self._layout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignTop)
        self._layout.addWidget(self.nowPlayingCard)
        self._layout.addWidget(self.songStatsCard)
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
        self.songStatsCard._updateStyle()  # 更新歌曲统计卡片样式
        self.welcomeCard._updateStyle()
        self.songStatsCard._updateStyle()

    def changeEvent(self, a0):
        """处理控件状态变化事件"""
        if a0 and a0.type() == QEvent.Type.PaletteChange:
            # 调色板变化（主题变化）时更新样式
            self._updateStyle()
        super().changeEvent(a0)

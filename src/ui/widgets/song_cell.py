from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import BodyLabel, CaptionLabel, isDarkTheme
import re


def build_song_cell(
    display_name: str,
    parent: Optional[QWidget] = None,
    *,
    parse_brackets: bool = True,
    compact: bool = False,
) -> QWidget:
    """构建歌曲单元格控件

    参数:
    - parse_brackets: 是否解析并展示【...】为副标题；False 时不解析，仅显示原文本
    - compact: 紧凑模式（0 内边距、0 间距，仅主标题），适合表格普通文本风格
    """
    if parse_brackets:
        parts = re.findall(r"【(.*?)】", display_name)
        main_text = re.sub(r"【.*?】", "", display_name).strip()
    else:
        parts = []
        main_text = display_name

    w = QWidget(parent)
    lay = QVBoxLayout(w)
    if compact:
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
    else:
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(2)

    main_lbl = BodyLabel(main_text, w)
    main_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    main_lbl.setToolTip(display_name)
    lay.addWidget(main_lbl)

    if parts and not compact:
        sub_lbl = CaptionLabel(" · ".join(parts), w)
        # 深色主题下用较浅灰，浅色主题下稍深的灰
        sub_color = "#C8C8C8" if isDarkTheme() else "#6E6E6E"
        sub_lbl.setStyleSheet(f"color: {sub_color};")
        sub_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lay.addWidget(sub_lbl)

    return w

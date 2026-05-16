from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    def __init__(
        self,
        title: str,
        content: QWidget,
        collapsed: bool,
        on_toggled: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__()
        self._content = content
        self._on_toggled = on_toggled

        self._toggle = QToolButton()
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(not collapsed)
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle.setStyleSheet("QToolButton:checked { color: #000000; }")
        self._toggle.clicked.connect(self._handle_toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._toggle)
        layout.addWidget(self._content)

        self.set_collapsed(collapsed)

    def _handle_toggle(self) -> None:
        collapsed = not self._toggle.isChecked()
        self.set_collapsed(collapsed)
        if self._on_toggled is not None:
            self._on_toggled(collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self._content.setVisible(not collapsed)
        self._toggle.setArrowType(Qt.RightArrow if collapsed else Qt.DownArrow)
        self._toggle.setChecked(not collapsed)

    def is_collapsed(self) -> bool:
        return not self._content.isVisible()

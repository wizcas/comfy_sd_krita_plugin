import re
from typing import List, Tuple

from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel, QRect
from PyQt5.QtGui import QSyntaxHighlighter, QColor, QTextCursor
from PyQt5.QtWidgets import QCompleter

from ..config import Config
from ..utils import (
    auto_complete_LoRA,
    auto_complete_embedding,
    get_simple_lora_list,
    re_embedding,
    re_lora,
    re_lora_start,
)


class QPromptHighLighter(QSyntaxHighlighter):
    def __init__(self, cfg: Config, *args, **kwargs):
        super(QSyntaxHighlighter, self).__init__(*args, **kwargs)

        self.cfg = cfg
        self.highlighters = [
            [re_lora, auto_complete_LoRA],
            [re_embedding, auto_complete_embedding]]

    def highlightBlock(self, line):
        for expression, func in self.highlighters:
            for m in re.finditer(expression, line):
                valid, names = func(self.cfg, m.group(1))
                color: QColor = QColor(Qt.green)
                color = color if valid else QColor(Qt.red)
                color = color if len(names) < 2 else QColor(Qt.yellow)
                self.setFormat(m.start(0), m.end(0)-m.start(0), color)
                color: QColor = QColor(Qt.green)
                color = color if valid else QColor(Qt.red)
                color = color if len(names) < 2 else QColor(Qt.yellow)
                self.setFormat(m.start(0), m.end(0)-m.start(0), color)


class QPromptCompleter(QCompleter):
    insertText = pyqtSignal(str)
    lastSelected: str = None
    model: QStringListModel = None

    def __init__(self, cfg: Config, parent=None):
        super().__init__(parent)
        self.model = QStringListModel()
        self.setModel(self.model)
        self.setCompletionMode(QCompleter.PopupCompletion)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.highlighted.connect(self.setHighlighted)
        self.setMaxVisibleItems(5)
        self.cfg = cfg
        self.rules: List[Tuple[str, List[str]]] = [
            (re_embedding, self.cfg("sd_embedding_list", str)),
            (re_lora_start, get_simple_lora_list(self.cfg))
        ]

    def set_string_list(self, keys: List[str]):
        self.model.setStringList(keys)

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected

    def try_auto_complete(self, tc: QTextCursor, cr: QRect):
        # Get the line
        tc.select(QTextCursor.LineUnderCursor)
        line = tc.selectedText()

        # Match re and completion lists
        rule: Tuple[str, List[str]] = None
        match: re.Match[str] = None

        # match last occurrence of rule on the line
        for r in self.rules:
            match = re.search(r[0] + "$", line)
            if match is not None:
                rule = r
                break

        if match is not None:
            # Select first match group so we can replace it
            tc.movePosition(QTextCursor.StartOfLine, mode=QTextCursor.MoveAnchor)
            tc.movePosition(QTextCursor.Right, mode=QTextCursor.MoveAnchor, n=match.span(1)[0])
            tc.movePosition(QTextCursor.Right, mode=QTextCursor.KeepAnchor, n=match.span(1)[1])
            # update the completer for with the list for this rule
            self.set_string_list(rule[1])
            self.setCompletionPrefix(tc.selectedText())
            popup = self.popup()
            popup.setCurrentIndex(self.completionModel().index(0, 0))
            cr.setWidth(popup.sizeHintForColumn(0)
                        + popup.verticalScrollBar().sizeHint().width())
            self.complete(cr)
        else:
            self.popup().hide()

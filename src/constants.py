# loading gif by Hassan Alkhateeb

const_styles = """
QWidget {
    background: black;
    color: white;
    font-family: "Helvetica";
    font-weight: bold;
}

QLabel {
    background: black;
}

QPushButton {
    background-color: black;
    color: white;
    border: none;
    min-width: 32px;
    min-height: 32px;
    max-width: 32px;
    max-height: 32px;
    border-radius: 0;
}

QToolButton {
    border-radius: 0;
}

QToolButton:hover {
    background-color: rgba(0, 157, 255, 0.5);
}

QToolButton:pressed {
    background-color: rgb(0, 157, 255);
}

QPushButton:hover {
    background-color: rgba(0, 157, 255, 0.5);
}

QPushButton:pressed {
    background-color: rgb(0, 157, 255);
}

QScrollBar:vertical, QScrollBar:horizontal {
    background: black;
    border: none;
}

QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background: rgb(0, 157, 255);
    border: none;
    border-radius: 0px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    background: black;
    border: none;
}

QScrollBar::add-page, QScrollBar::sub-page {
    background: black;
}
"""
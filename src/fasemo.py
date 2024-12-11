import sys
from PyQt6 import sip
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QToolBar,
    QToolButton,
    QScrollArea,
    QHBoxLayout,
    QSizePolicy,
    QLineEdit,
    QPushButton,
    QSpacerItem,
    QLabel,
    QFrame
)
from PyQt6.QtCore import Qt, QUrl, QSize, QMimeData, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QDrag
from PyQt6.QtWebEngineWidgets import QWebEngineView
from os import path

class DragLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.browser_container = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.browser_container:
            # Initiate a drag
            drag = QDrag(self)
            mime_data = QMimeData()
            # We identify the browser container by its memory address or a unique id.
            # Here we can simply store its python id or a custom attribute.
            mime_data.setData("application/x-fasemo-browser", str(id(self.browser_container)).encode('utf-8'))
            drag.setMimeData(mime_data)

            # Use the label pixmap as the drag pixmap
            if not self.pixmap().isNull():
                drag.setPixmap(self.pixmap())
            else:
                # fallback: blank pixmap
                drag.setPixmap(QPixmap(20, 20))

            drag.exec(Qt.DropAction.MoveAction)


class BrowserContainer(QWidget):
    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(url))
        self.browser.setMinimumWidth(320)
        self.browser.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Top bar with Close button and URL edit
        top_bar = QHBoxLayout()

        self.drag_label = DragLabel()
        self.drag_label.setPixmap(QPixmap(path.join("resources", "drag.png")))
        self.drag_label.browser_container = self  # Reference back to this container
        top_bar.addWidget(self.drag_label)

        self.url_edit = QLineEdit(url)
        self.url_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.url_edit.editingFinished.connect(self.on_url_edited)
        top_bar.addWidget(self.url_edit)

        grow_button = QPushButton()
        grow_icon = QIcon(path.join("resources", "btn-grow.png"))
        grow_button.setIcon(grow_icon)
        grow_button.setText("")
        grow_button.clicked.connect(self.request_grow)
        top_bar.addWidget(grow_button)

        close_button = QPushButton()
        close_icon = QIcon(path.join("resources", "btn-exit.png"))
        close_button.setIcon(close_icon)
        close_button.setText("")
        close_button.clicked.connect(self.request_close)
        top_bar.addWidget(close_button)

        layout.addLayout(top_bar)
        layout.addWidget(self.browser)

        self.browser.urlChanged.connect(self.on_browser_url_changed)
        self.close_requested = None

    def request_close(self):
        if self.close_requested:
            self.close_requested(self)

    def request_grow(self):
        main_window = self.window()
        if not main_window:
            return

        if not hasattr(main_window, "scroll_area"):
            return

        scroll_area = main_window.scroll_area
        scroll_area.widget().adjustSize()
        viewport_width = scroll_area.viewport().width()
        self.setFixedWidth(viewport_width)
        scroll_area.widget().adjustSize()

        container_pos_x = self.x()
        container_width = self.width()
        view_width = scroll_area.viewport().width()
        desired_scroll_value = (
            container_pos_x + (container_width / 2) - (view_width / 2)
        )

        h_scrollbar = scroll_area.horizontalScrollBar()
        desired_scroll_value = max(desired_scroll_value, h_scrollbar.minimum())
        desired_scroll_value = min(desired_scroll_value, h_scrollbar.maximum())
        h_scrollbar.setValue(int(desired_scroll_value))

    def on_browser_url_changed(self, qurl: QUrl):
        self.url_edit.setText(qurl.toString())

    def on_url_edited(self):
        text = self.url_edit.text().strip()
        if text:
            if not (text.startswith("http://") or text.startswith("https://")):
                text = "http://" + text
            self.browser.setUrl(QUrl(text))


class SplitterHandle(QWidget):
    def __init__(self, left_widget, container, parent=None):
        super().__init__(parent)
        self.left_widget = left_widget
        self.container = container
        self.setFixedWidth(20)
        self.setCursor(Qt.CursorShape.SplitHCursor)
        self.dragging = False
        self.offset = 0
        self.drag_pixmap = QPixmap(path.join("resources", "drag.png"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.start_global_x = event.globalPosition().x()
            self.start_width = self.left_widget.width()

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().x() - self.start_global_x
            new_width = self.start_width + delta
            if new_width < 320:
                new_width = 320
            self.left_widget.setFixedWidth(int(new_width))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.container.adjustSize()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        x = (self.width() - self.drag_pixmap.width()) // 2
        y = (self.height() - self.drag_pixmap.height()) // 2
        painter.drawPixmap(x, y, self.drag_pixmap)


class Fasemo(QMainWindow):
    def __init__(self):
        super().__init__()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        self.h_layout = QHBoxLayout()
        self.h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.container = QWidget()
        self.container.setLayout(self.h_layout)
        # Accept drops on the container
        self.container.setAcceptDrops(True)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        self.browser_containers = []
        self.handles = []
        self.browser_toolbar_actions = []

        screen = QApplication.primaryScreen()
        self.screen_width = screen.availableGeometry().width()
        self.extra_spacer = None

        self.toolbar = QToolBar("Browser Toolbar")
        self.toolbar.setOrientation(Qt.Orientation.Horizontal)
        new_button = QToolButton()
        new_button.setText("New")
        new_button.clicked.connect(self.on_new_button_clicked)
        self.toolbar.addWidget(new_button)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.toolbar)

        self.setWindowTitle("Fasemo")

        for bc in self.browser_containers:
            self.add_browser_button(bc)

        self.add_spacer()
        self.add_browser("https://www.google.com")
        self.showMaximized()

        # Instead of using the stylesheet to set width, just do:
        self.insertion_line = QFrame(self.container)
        self.insertion_line.setFrameShape(QFrame.Shape.VLine)
        self.insertion_line.setFrameShadow(QFrame.Shadow.Plain)
        self.insertion_line.setFixedWidth(2)
        self.insertion_line.setStyleSheet("QFrame { background-color: white; }")
        self.insertion_line.hide()

        self.dragged_browser_id = None

    def closeEvent(self, event):
        super().closeEvent(event)

    def add_spacer(self):
        self.remove_existing_spacer()
        self.extra_spacer = QSpacerItem(
            self.screen_width, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.h_layout.addItem(self.extra_spacer)

    def remove_existing_spacer(self):
        if self.extra_spacer is None:
            return

        if self.h_layout is not None and not sip.isdeleted(self.h_layout):
            for i in range(self.h_layout.count()):
                item = self.h_layout.itemAt(i)
                if item is self.extra_spacer:
                    self.h_layout.removeItem(item)
                    self.extra_spacer = None
                    break

    def add_browser_button(self, bc):
        btn = QToolButton()
        btn.setText("")
        btn.clicked.connect(
            lambda checked, browser_container=bc: self.center_browser(browser_container)
        )
        action = self.toolbar.addWidget(btn)
        self.browser_toolbar_actions.append((btn, action))
        bc.browser.iconChanged.connect(
            lambda _, b=bc.browser, bt=btn: self.updateButtonIcon(bt, b)
        )
        self.updateButtonIcon(btn, bc.browser)

    def add_browser(self, url: str):
        self.remove_existing_spacer()

        bc = BrowserContainer(url)
        bc.close_requested = self.close_browser

        self.h_layout.addWidget(bc)
        self.browser_containers.append(bc)

        handle = SplitterHandle(bc, self.container)
        self.h_layout.addWidget(handle)
        self.handles.append(handle)

        self.add_spacer()
        self.container.adjustSize()

        if hasattr(self, "toolbar"):
            self.add_browser_button(bc)

    def updateButtonIcon(self, button, browser):
        icon = browser.icon()
        if not icon.isNull():
            button.setIcon(icon)
            button.setIconSize(QSize(64, 64))
            button.setText("")

    def on_new_button_clicked(self):
        self.add_browser("https://www.google.com")

    def close_browser(self, bc: BrowserContainer):
        if bc not in self.browser_containers:
            return
        index = self.browser_containers.index(bc)
        self.remove_existing_spacer()

        item_to_remove = self.find_layout_item(self.h_layout, bc)
        if item_to_remove is not None:
            self.h_layout.removeItem(item_to_remove)
        self.h_layout.removeWidget(bc)
        bc.setParent(None)
        self.browser_containers.remove(bc)

        # Remove corresponding handle
        if index < len(self.handles):
            handle = self.handles[index]
            handle_item = self.find_layout_item(self.h_layout, handle)
            if handle_item is not None:
                self.h_layout.removeItem(handle_item)
            self.h_layout.removeWidget(handle)
            handle.setParent(None)
            self.handles.pop(index)

        # Remove corresponding toolbar button
        if index < len(self.browser_toolbar_actions):
            btn, action = self.browser_toolbar_actions[index]
            self.toolbar.removeAction(action)
            self.browser_toolbar_actions.pop(index)

        self.add_spacer()
        self.container.adjustSize()

    def find_layout_item(self, layout, widget):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() == widget:
                return item
        return None

    def center_browser(self, bc: BrowserContainer):
        scroll_area = self.scroll_area
        scroll_area.widget().adjustSize()
        container_pos_x = bc.x()
        container_width = bc.width()
        view_width = scroll_area.viewport().width()
        desired_scroll_value = (
            container_pos_x + (container_width / 2) - (view_width / 2)
        )

        h_scrollbar = scroll_area.horizontalScrollBar()
        desired_scroll_value = max(desired_scroll_value, h_scrollbar.minimum())
        desired_scroll_value = min(desired_scroll_value, h_scrollbar.maximum())
        h_scrollbar.setValue(int(desired_scroll_value))

    # -------- Drag and Drop Handling --------
    def dragEnterEvent(self, event):
        # Only accept if we have our custom MIME
        if event.mimeData().hasFormat("application/x-fasemo-browser"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasFormat("application/x-fasemo-browser"):
            event.ignore()
            return

        event.acceptProposedAction()

        # Determine the position where we would drop
        pos = event.position().toPoint()
        self.show_insertion_indicator(pos)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-fasemo-browser"):
            event.ignore()
            return

        event.acceptProposedAction()
        dropped_id = event.mimeData().data("application/x-fasemo-browser").data().decode('utf-8')

        # Find the browser container by its id
        dragged_bc = None
        for bc in self.browser_containers:
            if str(id(bc)) == dropped_id:
                dragged_bc = bc
                break

        if not dragged_bc:
            return

        pos = event.position().toPoint()
        insert_index = self.calculate_insert_index(pos)

        # Remove from old position
        old_index = self.browser_containers.index(dragged_bc)
        # Each browser is followed by a handle in layout
        # The relationship: [BC0, Handle0, BC1, Handle1, ...]
        # Remove BC and its handle from layout arrays and UI
        self.remove_existing_spacer()
        self.remove_browser_from_layout(old_index)

        # Adjust insert_index if we removed an item before it
        if old_index < insert_index:
            insert_index -= 1

        # Re-insert at new position
        self.insert_browser_at_index(dragged_bc, insert_index)

        self.add_spacer()
        self.container.adjustSize()

        # Hide insertion line
        self.insertion_line.hide()

    def show_insertion_indicator(self, pos: QPoint):
        insert_index = self.calculate_insert_index(pos)

        # Ensure the container and layout are up-to-date:
        self.container.adjustSize()
        self.container.layout().update()

        if insert_index < len(self.browser_containers):
            # Insert before an existing browser
            reference_browser = self.browser_containers[insert_index]
            x_pos = reference_browser.x() - 17
        else:
            # Insert at the end - after the last browser and handle
            if self.browser_containers:
                last_browser = self.browser_containers[-1]
                last_handle = self.handles[-1]
                x_pos = last_browser.x() + last_browser.width() + last_handle.width() - 5
            else:
                # No browsers at all, start at 0
                x_pos = 0

        # Place the insertion line at the determined position
        self.insertion_line.move(x_pos, 0)
        self.insertion_line.setFixedHeight(self.container.height())
        self.insertion_line.show()


    def calculate_insert_index(self, pos: QPoint):
        """Given a mouse position, determine at which index to insert the dragged browser."""
        # We'll measure each BC+Handle pair to find where pos.x() fits
        x_accum = 0
        for i, bc in enumerate(self.browser_containers):
            bc_width = bc.width() + self.handles[i].width()
            if pos.x() < x_accum + bc.width() / 2:
                return i
            x_accum += bc_width

        return len(self.browser_containers)

    def remove_browser_from_layout(self, index):
        """Remove browser and its handle from layout by index."""
        bc = self.browser_containers.pop(index)
        handle = self.handles.pop(index)

        item_to_remove = self.find_layout_item(self.h_layout, bc)
        if item_to_remove:
            self.h_layout.removeItem(item_to_remove)
        self.h_layout.removeWidget(bc)
        bc.setParent(None)

        handle_item = self.find_layout_item(self.h_layout, handle)
        if handle_item:
            self.h_layout.removeItem(handle_item)
        self.h_layout.removeWidget(handle)
        handle.setParent(None)

        # Also update toolbar:
        btn, action = self.browser_toolbar_actions.pop(index)
        self.toolbar.removeAction(action)

    def insert_browser_at_index(self, bc, index):
        """Insert browser container and handle back at a given index."""
        # Insert the browser container at given index
        # The current layout order is BC0, Handle0, BC1, Handle1, ... + spacer
        # We must consider that each BC is followed by a handle.
        # Insert at index means before the BC currently at that index if any.

        # Insert browser container
        browser_pos = self.calculate_layout_position_for_browser(index)
        self.h_layout.insertWidget(browser_pos, bc)
        self.browser_containers.insert(index, bc)

        # Insert its handle right after it
        handle = SplitterHandle(bc, self.container)
        self.h_layout.insertWidget(browser_pos + 1, handle)
        self.handles.insert(index, handle)

        # Add toolbar button back
        self.add_browser_button(bc)

    def calculate_layout_position_for_browser(self, index):
        """
        Given an index of a browser, return the layout position
        where the browser should be inserted. Each browser has
        one handle after it. The layout structure is:
        [BC0, Handle0, BC1, Handle1, BC2, Handle2, ... , spacer]

        So the nth browser starts at position 2*n in layout.
        """
        return 2 * index

    # Override drag leave if needed
    def dragLeaveEvent(self, event):
        self.insertion_line.hide()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = Fasemo()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

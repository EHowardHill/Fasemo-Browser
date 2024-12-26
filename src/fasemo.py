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
    QLabel,
    QFrame,
)
from PyQt6.QtCore import Qt, QUrl, QSize, QMimeData, QPoint, QEvent
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QDrag, QFontDatabase, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from os import path
from constants import *

styles = stylesheet = const_styles

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
            mime_data.setData(
                "application/x-fasemo-browser",
                str(id(self.browser_container)).encode("utf-8"),
            )
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
        self.setWindowIcon(QIcon(path.join("resources", "helmet.png")))

        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout()
        central_widget.setLayout(self.main_layout)

        self.h_layout = QHBoxLayout()
        self.h_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.container = QFrame()
        self.container.setLayout(self.h_layout)
        self.container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

        self.browser_containers = []
        self.handles = []
        self.browser_toolbar_actions = []

        screen = QApplication.primaryScreen()
        self.screen_width = screen.availableGeometry().width()

        self.wallpaper_label = QLabel()
        self.wallpaper_label.setFixedWidth(
            QApplication.primaryScreen().geometry().width()
        )
        self.wallpaper_label.setScaledContents(False)
        self.wallpaper_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.wallpaper_pixmap = QPixmap(path.join("resources", "wallpaper2.jpg"))

        self.toolbar = QToolBar("Toolbar")
        self.toolbar.setIconSize(QSize(48, 48))
        self.toolbar.setOrientation(Qt.Orientation.Horizontal)
        self.new_button = QToolButton()
        self.new_icon = QIcon(path.join("resources", "btn-add.png"))
        self.new_button.setIcon(self.new_icon)
        self.new_button.clicked.connect(self.on_new_button_clicked)
        self.new_button_action = self.toolbar.addWidget(self.new_button)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.toolbar)

        self.setWindowTitle("Fasemo")

        self.add_browser("https://www.google.com")
        self.showMaximized()

        self.h_layout.addWidget(self.wallpaper_label)

        self.insertion_line = QFrame(self.container)
        self.insertion_line.setFrameShape(QFrame.Shape.VLine)
        self.insertion_line.setFrameShadow(QFrame.Shadow.Plain)
        self.insertion_line.setFixedWidth(2)
        self.insertion_line.setStyleSheet("QFrame { background-color: white; }")
        self.insertion_line.hide()

        self.dragged_browser_id = None

        self.update_container_height()
        self.scroll_area.viewport().installEventFilter(self)

        self.loading_icon = QIcon(path.join("resources", "helmet.png"))

    def eventFilter(self, source, event):
        if source == self.scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self.update_container_height()
        return super().eventFilter(source, event)

    def update_container_height(self):
        # Match the container height to the scroll area viewport height
        viewport_height = self.scroll_area.viewport().height()
        self.container.setFixedHeight(viewport_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.wallpaper_label is not None and self.wallpaper_pixmap is not None:
            scaled_pixmap = self.wallpaper_pixmap.scaled(
                self.wallpaper_label.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.wallpaper_label.setPixmap(scaled_pixmap)

        # Also ensure container matches new viewport height on window resize
        self.update_container_height()

    def reinsert_browser(self, dragged_bc: BrowserContainer, pos: QPoint):
        """
        Given a dragged BrowserContainer and the drop position,
        remove the browser container from the old layout index
        and insert it at the new calculated index.
        """
        old_index = self.browser_containers.index(dragged_bc)
        insert_index = self.calculate_insert_index(pos)

        # Remove it from the layout
        self.remove_browser_from_layout(old_index)

        # If we're moving the container from left to right in the same row,
        # the final insert_index will shift by one.
        if old_index < insert_index:
            insert_index -= 1

        # Insert it at the new location
        self.insert_browser_at_index(dragged_bc, insert_index)

        # Ensure everything is resized properly and the insertion line is hidden
        self.container.adjustSize()
        self.insertion_line.hide()

        # Move the wallpaper_label to the end again
        self.h_layout.removeWidget(self.wallpaper_label)
        self.h_layout.addWidget(self.wallpaper_label)

        # <-- Rebuild toolbar icons
        self.reorder_toolbar()

    def add_browser_button(self, bc):
        btn = QToolButton()
        btn.setText("")
        btn.clicked.connect(
            lambda checked, browser_container=bc: self.center_browser(browser_container)
        )
        action = self.toolbar.addWidget(btn)
        self.browser_toolbar_actions.append((btn, action))
        self.updateButtonIcon(btn, bc.browser)

    def add_browser(self, url: str):
        bc = BrowserContainer(url)
        bc.close_requested = self.close_browser
        
        # Connect signals for showing the loading icon
        bc.browser.loadStarted.connect(lambda: self.on_load_started(bc.browser))
        bc.browser.iconChanged.connect(lambda icon: self.on_browser_icon_changed(bc.browser, icon))
        bc.browser.loadFinished.connect(lambda ok: self.on_load_finished(bc.browser, ok))

        self.h_layout.addWidget(bc)
        self.browser_containers.append(bc)

        handle = SplitterHandle(bc, self.container)
        self.h_layout.addWidget(handle)
        self.handles.append(handle)

        self.container.adjustSize()

        if hasattr(self, "toolbar"):
            self.add_browser_button(bc)

        self.h_layout.removeWidget(self.wallpaper_label)
        self.h_layout.addWidget(self.wallpaper_label)

        self.reorder_toolbar()

    def toolbar_button_for_browser(self, browser):
        """
        Given a QWebEngineView, return the corresponding QToolButton from browser_toolbar_actions.
        """
        # Each entry in self.browser_toolbar_actions is (btn, action),
        # in the same order as self.browser_containers.
        # So if we find the index of the bc that has .browser == browser,
        # we can return the corresponding button.
        for i, bc in enumerate(self.browser_containers):
            if bc.browser == browser:
                return self.browser_toolbar_actions[i][0]  # The button
        return None

    def on_load_started(self, browser):
        """
        Called when a browser begins loading a page.
        Replace toolbar icon with the loading.gif.
        """
        button = self.toolbar_button_for_browser(browser)
        if button:
            button.setIcon(self.loading_icon)

    def on_browser_icon_changed(self, browser, icon):
        """
        Called whenever the browser's favicon changes.
        If the icon is not null, use it immediately (page's real favicon).
        """
        if not icon.isNull():
            button = self.toolbar_button_for_browser(browser)
            if button:
                button.setIcon(icon)

    def on_load_finished(self, browser, ok):
        """
        Called when the browser finishes loading.
        - If ok == True, the page loaded successfully.
        - If the final icon is still null, you may want a fallback icon.
        """
        # In some cases, the site never provides a favicon, or the icon might remain null.
        # If you want to show a fallback (like a default "web" icon), do it here if icon is still null:
        icon = browser.icon()
        if icon.isNull():
            # e.g. use a fallback icon, or keep the loading icon, etc.
            button = self.toolbar_button_for_browser(browser)
            if button:
                fallback_icon = QIcon(path.join("resources", "btn-default-favicon.png"))
                button.setIcon(fallback_icon)

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

        self.container.adjustSize()

        # <-- Call reorder_toolbar here
        self.reorder_toolbar()

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

    def reorder_toolbar(self):
        """
        Rebuild the toolbar so that its icons match the current
        left-to-right order of browser_containers.
        Keeps the 'New' button at the far left.
        """
        # 1) Capture the action for the "New" button so we can re-add it.
        new_button_action = None
        for action in self.toolbar.actions():
            widget = self.toolbar.widgetForAction(action)
            if widget == self.new_button:
                new_button_action = action
                break

        # 2) Remove all actions from the toolbar.
        for action in self.toolbar.actions():
            self.toolbar.removeAction(action)
        self.browser_toolbar_actions.clear()

        # 3) Re-add the "New" button first (keeps it on the left).
        if new_button_action is not None:
            self.toolbar.addAction(new_button_action)

        # 4) Re-add each browser in order:
        for bc in self.browser_containers:
            btn = QToolButton()
            btn.setText("")
            btn.clicked.connect(
                lambda checked=False, container=bc: self.center_browser(container)
            )
            action = self.toolbar.addWidget(btn)
            self.browser_toolbar_actions.append((btn, action))

            # Keep the icon in sync with the browser’s favicon
            bc.browser.iconChanged.connect(
                lambda _, br=bc.browser, bt=btn: self.updateButtonIcon(bt, br)
            )
            self.updateButtonIcon(btn, bc.browser)

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

        # Convert the event’s position (relative to the main window)
        # into coordinates inside self.container
        pos_in_container = self.container.mapFromGlobal(
            self.mapToGlobal(event.position().toPoint())
        )

        self.show_insertion_indicator(pos_in_container)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-fasemo-browser"):
            event.ignore()
            return

        event.acceptProposedAction()

        dropped_id = (
            event.mimeData().data("application/x-fasemo-browser").data().decode("utf-8")
        )

        # Locate the dragged BrowserContainer by id
        dragged_bc = None
        for bc in self.browser_containers:
            if str(id(bc)) == dropped_id:
                dragged_bc = bc
                break
        if not dragged_bc:
            return

        # Convert drop position to container’s coordinates
        pos_in_container = self.container.mapFromGlobal(
            self.mapToGlobal(event.position().toPoint())
        )

        self.reinsert_browser(dragged_bc, pos_in_container)

    def show_insertion_indicator(self, pos: QPoint):
        insert_index = self.calculate_insert_index(pos)

        self.container.adjustSize()
        self.container.layout().update()

        if insert_index < len(self.browser_containers):
            reference_browser = self.browser_containers[insert_index]
            x_pos = reference_browser.x() - 17
        else:
            if self.browser_containers:
                last_browser = self.browser_containers[-1]
                last_handle = self.handles[-1]
                x_pos = (
                    last_browser.x() + last_browser.width() + last_handle.width() - 5
                )
            else:
                x_pos = 0

        self.insertion_line.move(x_pos, 0)
        self.insertion_line.setFixedHeight(self.container.height())
        self.insertion_line.show()

    def calculate_insert_index(self, pos: QPoint):
        x_accum = 0
        for i, bc in enumerate(self.browser_containers):
            bc_width = bc.width() + self.handles[i].width()
            if pos.x() < x_accum + bc.width() / 2:
                return i
            x_accum += bc_width

        return len(self.browser_containers)

    def remove_browser_from_layout(self, index):
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
        browser_pos = self.calculate_layout_position_for_browser(index)
        self.h_layout.insertWidget(browser_pos, bc)
        self.browser_containers.insert(index, bc)

        handle = SplitterHandle(bc, self.container)
        self.h_layout.insertWidget(browser_pos + 1, handle)
        self.handles.insert(index, handle)

        self.add_browser_button(bc)

    def calculate_layout_position_for_browser(self, index):
        return 2 * index

    def dragLeaveEvent(self, event):
        self.insertion_line.hide()
        event.accept()


def main():
    app = QApplication(sys.argv)

    # Load the custom font
    font_id = QFontDatabase.addApplicationFont(
        path.join("resources", "Helvetica-Bold.ttf")
    )
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0], 12))

    app.setStyleSheet(stylesheet)

    window = Fasemo()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

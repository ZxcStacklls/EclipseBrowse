import sys
import os
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QTabWidget,
                             QToolBar, QStatusBar, QMessageBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QKeySequence, QFont, QAction


class BrowserTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("about:blank"))

        # Navigation toolbar
        self.nav_bar = QToolBar("Navigation")
        self.nav_bar.setIconSize(QSize(24, 24))

        # Back button
        self.back_btn = QPushButton()
        self.back_btn.setIcon(QIcon.fromTheme("go-previous"))
        self.back_btn.setToolTip("Back")

        # Forward button
        self.forward_btn = QPushButton()
        self.forward_btn.setIcon(QIcon.fromTheme("go-next"))
        self.forward_btn.setToolTip("Forward")

        # Reload button
        self.reload_btn = QPushButton()
        self.reload_btn.setIcon(QIcon.fromTheme("view-refresh"))
        self.reload_btn.setToolTip("Reload")

        # Home button
        self.home_btn = QPushButton()
        self.home_btn.setIcon(QIcon.fromTheme("go-home"))
        self.home_btn.setToolTip("Home")

        # URL bar
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search terms...")
        self.url_bar.setClearButtonEnabled(True)
        self.url_bar.setMinimumWidth(300)

        # Add widgets to toolbar
        self.nav_bar.addWidget(self.back_btn)
        self.nav_bar.addWidget(self.forward_btn)
        self.nav_bar.addWidget(self.reload_btn)
        self.nav_bar.addWidget(self.home_btn)
        self.nav_bar.addWidget(self.url_bar)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.nav_bar)
        layout.addWidget(self.browser)
        self.setLayout(layout)

        # Connect signals
        self.back_btn.clicked.connect(self.browser.back)
        self.forward_btn.clicked.connect(self.browser.forward)
        self.reload_btn.clicked.connect(self.browser.reload)
        self.home_btn.clicked.connect(self.navigate_home)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.browser.urlChanged.connect(self.update_urlbar)
        self.browser.loadFinished.connect(self.update_title)
        self.browser.loadProgress.connect(self.update_progress)

    def navigate_to_url(self):
        url = self.url_bar.text()
        if not url.startswith(("http://", "https://")):
            if "." in url and " " not in url:
                url = "http://" + url
            else:
                url = "https://www.google.com/search?q=" + url.replace(" ", "+")
        self.browser.setUrl(QUrl(url))

    def navigate_home(self):
        # Получаем путь к HTML файлу
        html_path = os.path.join(os.path.dirname(__file__), "home_page.html")

        # Читаем содержимое файла
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Устанавливаем HTML с базовым URL
        self.browser.setHtml(html_content, QUrl.fromLocalFile(html_path))

    def update_urlbar(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_title(self):
        title = self.browser.page().title()
        if hasattr(self.parent().parent(), "setWindowTitle"):
            self.parent().parent().setWindowTitle(f"{title} - EclipseBrowse")

    def update_progress(self, progress):
        if hasattr(self.parent().parent(), "statusBar"):
            if progress < 100:
                self.parent().parent().statusBar().showMessage(f"Loading... {progress}%")
            else:
                self.parent().parent().statusBar().clearMessage()


class EclipseBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EclipseBrowse")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Create actions
        self.create_actions()

        # Create toolbar
        self.create_toolbar()

        # Create menu bar
        self.create_menus()

        # Add initial tab
        self.add_new_tab()

        # Apply styles
        self.apply_styles()

    def create_actions(self):
        self.new_tab_action = QAction("New Tab", self)
        self.new_tab_action.setShortcut(QKeySequence.StandardKey.AddTab)
        self.new_tab_action.triggered.connect(self.add_new_tab)

        self.close_tab_action = QAction("Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        self.close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))

        self.quit_action = QAction("Exit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about)

    def create_toolbar(self):
        nav_toolbar = QToolBar("Main Navigation")
        nav_toolbar.setMovable(False)
        self.addToolBar(nav_toolbar)

        new_tab_btn = QPushButton("+")
        new_tab_btn.setToolTip("New Tab")
        new_tab_btn.clicked.connect(self.add_new_tab)
        nav_toolbar.addWidget(new_tab_btn)

        nav_toolbar.addSeparator()

        back_btn = QPushButton()
        back_btn.setIcon(QIcon.fromTheme("go-previous"))
        back_btn.setToolTip("Back")
        back_btn.clicked.connect(self.navigate_back)
        nav_toolbar.addWidget(back_btn)

        forward_btn = QPushButton()
        forward_btn.setIcon(QIcon.fromTheme("go-next"))
        forward_btn.setToolTip("Forward")
        forward_btn.clicked.connect(self.navigate_forward)
        nav_toolbar.addWidget(forward_btn)

        reload_btn = QPushButton()
        reload_btn.setIcon(QIcon.fromTheme("view-refresh"))
        reload_btn.setToolTip("Reload")
        reload_btn.clicked.connect(self.reload_page)
        nav_toolbar.addWidget(reload_btn)

        home_btn = QPushButton()
        home_btn.setIcon(QIcon.fromTheme("go-home"))
        home_btn.setToolTip("Home")
        home_btn.clicked.connect(self.navigate_home)
        nav_toolbar.addWidget(home_btn)

    def create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_tab_action)
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.about_action)

    def add_new_tab(self, url=None):
        tab = BrowserTab()
        i = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(i)

        if url:
            tab.browser.setUrl(QUrl(url))
        else:
            tab.navigate_home()

        tab.browser.titleChanged.connect(
            lambda title, tab_index=i: self.update_tab_title(tab_index, title)
        )

    def close_tab(self, index):
        if self.tabs.count() < 2:
            return
        widget = self.tabs.widget(index)
        widget.deleteLater()
        self.tabs.removeTab(index)

    def update_tab_title(self, index, title):
        if title:
            self.tabs.setTabText(index, title[:15] + "..." if len(title) > 15 else title)
        else:
            self.tabs.setTabText(index, "New Tab")

    def current_tab(self):
        return self.tabs.currentWidget()

    def navigate_back(self):
        self.current_tab().browser.back()

    def navigate_forward(self):
        self.current_tab().browser.forward()

    def reload_page(self):
        self.current_tab().browser.reload()

    def navigate_home(self):
        self.current_tab().navigate_home()

    def show_about(self):
        QMessageBox.about(self, "About EclipseBrowse",
                          "EclipseBrowse v1.0\n\n"
                          "A modern web browser built with Python and PyQt6\n"
                          "© 2025 EclipseBrowse Project\n\n"
                          "Features:\n"
                          "- Tabbed browsing\n"
                          "- Custom home page\n"
                          "- Navigation controls\n"
                          "- Google search integration")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d30;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #252526;
                color: #d4d4d4;
                padding: 8px;
                border: 1px solid #3c3c3c;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                border-color: #0078d7;
            }
            QToolBar {
                background: #333337;
                border: none;
                padding: 4px;
            }
            QLineEdit {
                background: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #0078d7;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton {
                background: #333337;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 32px;
            }
            QPushButton:hover {
                background: #3c3c3c;
                border-color: #0078d7;
            }
            QPushButton:pressed {
                background: #0078d7;
            }
            QStatusBar {
                background: #252526;
                color: #d4d4d4;
            }
        """)

        # Set custom font
        font = QFont("Segoe UI", 10)
        QApplication.setFont(font)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("EclipseBrowse")
    app.setApplicationDisplayName("EclipseBrowse")
    app.setWindowIcon(QIcon.fromTheme("web-browser"))

    browser = EclipseBrowser()
    browser.show()

    sys.exit(app.exec())
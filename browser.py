import sys
import os
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from PyQt6.QtCore import QUrl, Qt, QSize, QStandardPaths
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QTabWidget,
                             QToolBar, QStatusBar, QMessageBox, QFileDialog)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtGui import QIcon, QKeySequence, QFont, QAction, QColor
from PyQt6.QtCore import QDir

class LocalHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(paths.app_data), **kwargs)

    def end_headers(self):
        # Разрешаем загрузку ресурсов
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        super().end_headers()

# Добавьте эту функцию
def run_local_server():
    server_address = ('localhost', 8000)
    httpd = HTTPServer(server_address, LocalHTTPRequestHandler)
    logging.info("Starting local server at http://localhost:8000")
    httpd.serve_forever()


class BrowserPaths:
    def __init__(self):
        self.app_data = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation)) / "EclipseBrowse"

        self.cache = self.app_data / "Cache"
        self.logs = self.app_data / "Logs"
        self.profiles = self.app_data / "Profiles"
        self.extensions = self.app_data / "Extensions"
        self.themes = self.app_data / "Themes"

        self.create_dirs()

    def create_dirs(self):
        self.app_data.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(exist_ok=True)
        self.logs.mkdir(exist_ok=True)
        self.profiles.mkdir(exist_ok=True)
        self.extensions.mkdir(exist_ok=True)
        self.themes.mkdir(exist_ok=True)

    @property
    def settings_file(self):
        return self.app_data / "settings.json"

    @property
    def bookmarks_file(self):
        return self.app_data / "bookmarks.json"

    @property
    def history_file(self):
        return self.app_data / "history.log"


class BrowserTab(QWidget):
    def __init__(self, profile, home_path, main_window, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.home_path = home_path
        self.main_window = main_window

        # Создаем кастомную страницу с профилем
        self.page = CustomWebEnginePage(profile, self)
        self.page.set_main_window(main_window)

        self.browser = QWebEngineView()
        self.browser.setPage(self.page)  # Используем нашу кастомную страницу
        self.browser.setUrl(QUrl("about:blank"))

        # Настройки профиля
        self.profile.setCachePath(str(paths.cache))
        self.profile.setPersistentStoragePath(str(paths.profiles / "default"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

        # Панель навигации
        self.setup_navbar()

        # Макет
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.nav_bar)
        layout.addWidget(self.browser)
        self.setLayout(layout)

        # Соединения сигналов
        self.connect_signals()

    def setup_navbar(self):
        self.nav_bar = QToolBar("Navigation")
        self.nav_bar.setIconSize(QSize(24, 24))

        # Кнопки
        self.back_btn = QPushButton(QIcon.fromTheme("go-previous"), "")
        self.forward_btn = QPushButton(QIcon.fromTheme("go-next"), "")
        self.reload_btn = QPushButton(QIcon.fromTheme("view-refresh"), "")
        self.home_btn = QPushButton(QIcon.fromTheme("go-home"), "")

        # URL-бар
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL or search...")
        self.url_bar.setClearButtonEnabled(True)
        self.url_bar.setMinimumWidth(300)

        # Добавление элементов
        for btn in [self.back_btn, self.forward_btn, self.reload_btn, self.home_btn]:
            btn.setFixedSize(32, 32)
            self.nav_bar.addWidget(btn)

        self.nav_bar.addWidget(self.url_bar)

    def connect_signals(self):
        self.back_btn.clicked.connect(self.browser.back)
        self.forward_btn.clicked.connect(self.browser.forward)
        self.reload_btn.clicked.connect(self.browser.reload)
        self.home_btn.clicked.connect(self.navigate_home)
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.browser.urlChanged.connect(self.update_urlbar)
        self.browser.titleChanged.connect(self.update_title)
        self.browser.loadProgress.connect(self.update_progress)

    # В классе BrowserTab метод navigate_to_url:
    def navigate_to_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return

        log_history(url)

        # Обработка специальных URL
        if url.startswith("http://localhost:8000/search.html?q="):
            # Поисковые запросы открываем в текущей вкладке
            self.browser.setUrl(QUrl(url))
        elif not url.startswith(("http://", "https://")):
            if "." in url and " " not in url:
                url = "https://" + url
            else:
                url = f"http://localhost:8000/search.html?q={url.replace(' ', '+')}"

        self.browser.setUrl(QUrl(url))

    def navigate_home(self):
        self.browser.setUrl(QUrl("http://localhost:8000/home_page.html"))

    def update_urlbar(self, q):
        self.url_bar.setText(q.toString())
        self.url_bar.setCursorPosition(0)

    def update_title(self, title):
        if hasattr(self.parent().parent(), "setWindowTitle"):
            self.parent().parent().setWindowTitle(f"{title} - EclipseBrowse")

    def update_progress(self, progress):
        if hasattr(self.parent().parent(), "statusBar"):
            if progress < 100:
                self.parent().parent().statusBar().showMessage(f"Loading... {progress}%")
            else:
                self.parent().parent().statusBar().clearMessage()



class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, profile=None, parent=None):
        super().__init__(profile, parent) if profile else super().__init__(parent)
        self.main_window = None

    def set_main_window(self, main_window):
        self.main_window = main_window

    def createWindow(self, type):
        if self.main_window:
            self.main_window.add_new_tab()
            return self.main_window.current_tab().browser.page()
        return super().createWindow(type)

class EclipseBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.paths = paths
        self.setWindowTitle("EclipseBrowse")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)

        # Инициализация
        self.setup_tabs()
        self.statusBar().showMessage("Ready")
        self.create_actions()
        self.create_toolbar()
        self.create_menus()
        self.load_settings()

        # Первая вкладка
        self.add_new_tab()

        icon_path = str(Path(__file__).parent / "assets" / "EclipseBrowseLogo.png")
        self.setWindowIcon(QIcon(icon_path))

    def setup_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

    def create_actions(self):
        # Файл
        self.new_tab_action = QAction("New Tab", self)
        self.new_tab_action.setShortcut(QKeySequence.StandardKey.AddTab)
        self.new_tab_action.triggered.connect(self.add_new_tab)

        self.close_tab_action = QAction("Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        self.close_tab_action.triggered.connect(
            lambda: self.close_tab(self.tabs.currentIndex()))

        self.quit_action = QAction("Exit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        # Настройки
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.show_settings)

        # Помощь
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about)

    def create_toolbar(self):
        nav_toolbar = QToolBar("Main Navigation")
        nav_toolbar.setMovable(False)
        self.addToolBar(nav_toolbar)

        # New Tab button
        new_tab_btn = QPushButton("+")
        new_tab_btn.setToolTip("New Tab")
        new_tab_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        new_tab_btn.clicked.connect(self.add_new_tab)
        nav_toolbar.addWidget(new_tab_btn)

        # Navigation buttons
        nav_buttons = [
            ("Back", QIcon.fromTheme("go-previous"), self.navigate_back),
            ("Forward", QIcon.fromTheme("go-next"), self.navigate_forward),
            ("Reload", QIcon.fromTheme("view-refresh"), self.reload_page),
            ("Home", QIcon.fromTheme("go-home"), self.navigate_home)
        ]

        for text, icon, handler in nav_buttons:
            btn = QPushButton(icon, "")
            btn.setToolTip(text)
            btn.clicked.connect(handler)
            nav_toolbar.addWidget(btn)

    def create_menus(self):
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.new_tab_action)
        file_menu.addAction(self.close_tab_action)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_action)

        # Меню Настройки
        settings_menu = menubar.addMenu("&Settings")
        settings_menu.addAction(self.settings_action)

        # Меню Помощь
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.about_action)



    def add_new_tab(self, url=None):
        profile = QWebEngineProfile(f"Profile-{self.tabs.count()}", self)

        # Передаем self (главное окно) в BrowserTab
        tab = BrowserTab(profile, str(paths.home_page), self, self.tabs)

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

    def show_settings(self):
        QMessageBox.information(
            self,
            "Settings",
            "Customization settings will be implemented in the next version"
        )

    def show_about(self):
        QMessageBox.about(
            self,
            "About EclipseBrowse",
            f"EclipseBrowse v1.0\n\n"
            f"Data Directory: {paths.app_data}\n"
            f"Cache: {paths.cache}\n"
            f"Logs: {paths.logs}\n\n"
            "© 2025 EclipseBrowse Project"
        )

    def load_settings(self):
        try:
            if paths.settings_file.exists():
                with open(paths.settings_file, "r") as f:
                    settings = json.load(f)
                    # Применение настроек
        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            settings = {
                "theme": "dark",
                "last_session": [],
                "extensions": []
            }
            with open(paths.settings_file, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def closeEvent(self, event):
        self.save_settings()
        event.accept()


def log_history(url):
    try:
        with open(paths.history_file, "a") as f:
            f.write(f"{datetime.now().isoformat()} - {url}\n")
    except Exception as e:
        logging.error(f"History logging failed: {e}")


def setup_home_page():
    # Пути к файлам
    assets_dir = Path(__file__).parent / "assets"
    custom_home_path = Path(__file__).parent / "home_page.html"
    app_data_home_path = paths.app_data / "home_page.html"

    # Создаем папку assets в AppData, если нужно
    (paths.app_data / "assets").mkdir(exist_ok=True)

    try:
        if custom_home_path.exists():
            with open(custom_home_path, "r", encoding="utf-8") as f:
                content = f.read()

            # ИСПРАВЛЯЕМ пути к ресурсам
            content = content.replace(
                'src="assets/EclipseLogo.png"',
                'src="/assets/EclipseLogo.png"'
            )
            content = content.replace(
                'src="edit.png"',
                'src="/assets/edit.png"'
            )
            content = content.replace(
                'src="delete.png"',
                'src="/assets/delete.png"'
            )


            # Копируем ресурсы
            for img in ["EclipseLogo.png", "edit.png", "delete.png"]:
                src = assets_dir / img
                dst = paths.app_data / "assets" / img
                if src.exists():
                    with open(src, "rb") as src_file, open(dst, "wb") as dst_file:
                        dst_file.write(src_file.read())

            with open(app_data_home_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Резервная страница
            with open(app_data_home_path, "w", encoding="utf-8") as f:
                f.write("""<!DOCTYPE html><html><body>EclipseBrowse Default Home</body></html>""")
    except Exception as e:
        logging.error(f"Error setting up home page: {e}")

    return app_data_home_path


def setup_search_page():
    # Пути к файлам
    assets_dir = Path(__file__).parent / "assets"
    custom_search_path = Path(__file__).parent / "search.html"
    app_data_search_path = paths.app_data / "search.html"

    # Создаем папку assets в AppData, если нужно
    (paths.app_data / "assets").mkdir(exist_ok=True)

    try:
        if custom_search_path.exists():
            with open(custom_search_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Убираем file:/// из путей
            content = content.replace(
                'src="assets/EclipseLogo.png"',
                'src="/assets/EclipseLogo.png"'
            )

            # Копируем ресурсы
            for img in ["EclipseLogo.png"]:
                src = assets_dir / img
                dst = paths.app_data / "assets" / img
                if src.exists():
                    with open(src, "rb") as src_file, open(dst, "wb") as dst_file:
                        dst_file.write(src_file.read())

            with open(app_data_search_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            # Резервная страница
            with open(app_data_search_path, "w", encoding="utf-8") as f:
                f.write("""<!DOCTYPE html><html><body>Search page not found</body></html>""")
    except Exception as e:
        logging.error(f"Error setting up search page: {e}")

    return app_data_search_path


if __name__ == "__main__":
    # Инициализация путей
    global paths
    paths = BrowserPaths()

    # Настройка логгирования
    logging.basicConfig(
        filename=paths.logs / "browser.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Запуск сервера в отдельном потоке
    server_thread = threading.Thread(target=run_local_server, daemon=True)
    server_thread.start()

    # Создание домашней страницы
    paths.home_page = setup_home_page()

    # Создание страницы поиска
    paths.search_page = setup_search_page()

    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e2b;
        }
        QStatusBar {
            background-color: #1a1a24;
            color: #8888a0;
            border-top: 1px solid #2a2a3c;
        }
        QMenuBar {
            background-color: #1e1e2b;
            color: #e0e0ff;
        }
        QMenuBar::item:selected {
            background: #3a3a4c;
        }
        QMenu {
            background-color: #2a2a3c;
            color: #e0e0ff;
            border: 1px solid #444;
        }
        QMenu::item:selected {
            background-color: #3a3a4c;
        }
    """)

    # Установка иконки приложения
    app_icon_path = str(Path(__file__).parent / "assets" / "EclipseLogo.png")
    app.setWindowIcon(QIcon(app_icon_path))

    browser = EclipseBrowser()
    browser.show()

    sys.exit(app.exec())
import sys
import webbrowser
import requests
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QDialog, QSpacerItem, QSizePolicy,
    QGraphicsDropShadowEffect, QGraphicsBlurEffect, QDesktopWidget
)
from PyQt5.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QPixmap, QFont, QCursor, QFontDatabase, QColor, QLinearGradient, QBrush, QPalette

# --- Configuración IGDB ---
CLIENT_ID = "aio0y5syf7jlxq20qoy7768korw1me"
ACCESS_TOKEN = "pps4h1dpxrcyiuz04m725vf653obzw"
HEADERS = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {ACCESS_TOKEN}"}

# --- Funciones API ---
def buscar_juego(nombre, limit=8):
    url = "https://api.igdb.com/v4/games"
    query = f'''
    search "{nombre}";
    fields name, cover.image_id, summary, rating, platforms.name, screenshots.image_id, genres.name;
    limit {limit};
    '''
    response = requests.post(url, headers=HEADERS, data=query)
    if response.status_code == 200:
        juegos = response.json()
        juegos.sort(key=lambda x: x.get("rating",0), reverse=True)
        return juegos
    else:
        raise ValueError(f"Error API: {response.status_code}")

def obtener_url_cover(image_id, size="cover_big"):
    if not image_id: return None
    return f"https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg"

def obtener_url_screenshot(image_id, size="original"):
    if not image_id: return None
    return f"https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg"

# --- Worker de imágenes ---
class WorkerSignals(QObject):
    finished = pyqtSignal(QPixmap, object)

class ImagenWorker(QRunnable):
    image_cache = {}

    def __init__(self, url, label):
        super().__init__()
        self.url = url
        self.label = label
        self.signals = WorkerSignals()

    def run(self):
        pixmap = QPixmap()
        try:
            if self.url in ImagenWorker.image_cache:
                pixmap = ImagenWorker.image_cache[self.url]
            elif self.url:
                response = requests.get(self.url)
                if response.status_code == 200 and pixmap.loadFromData(response.content):
                    ImagenWorker.image_cache[self.url] = pixmap
                else:
                    pixmap.load("placeholder.jpg")
            else:
                pixmap.load("placeholder.jpg")
        except Exception as e:
            print(f"Error cargando imagen: {e}")
            pixmap.load("placeholder.jpg")

        self.signals.finished.emit(pixmap, self.label)

# --- Frame con hover y fondo semi-transparente ---
class HoverFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.default_style = """
            background-color: rgba(27,40,56, 180);
            border-radius:10px;
            padding:10px;
            border:1px solid #2A475E;
        """
        self.hover_style = """
            background-color: rgba(42,71,94, 200);
            border-radius:10px;
            padding:10px;
            border:1px solid #3E5C7C;
        """
        self.setStyleSheet(self.default_style)

    def enterEvent(self, event):
        self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.default_style)
        super().leaveEvent(event)

# --- QLabel con zoom ---
class ZoomLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self._zoom_factor = 1.2
        self._original_pixmap = None
        self.zoom_enabled = True

    def setPixmap(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        super().setPixmap(pixmap)

    def enterEvent(self, event):
        if not self.zoom_enabled or self._original_pixmap is None:
            return
        w = int(self._original_pixmap.width() * self._zoom_factor)
        h = int(self._original_pixmap.height() * self._zoom_factor)
        scaled = self._original_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super().setPixmap(scaled)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.zoom_enabled or self._original_pixmap is None:
            return
        super().setPixmap(self._original_pixmap)
        super().leaveEvent(event)

# --- Ventana principal ---
class GameTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Tracker - Gamer Style")
        self.showMaximized()
        self.setStyleSheet("background-color:#0B1D2F; color:white;")
        self.threadpool = QThreadPool()

        QFontDatabase.addApplicationFont("Orbitron-Bold.ttf")
        self.title_font = QFont("Orbitron", 48, QFont.Bold)
        self.game_font = QFont("Orbitron", 20, QFont.Bold)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20,20,20,20)
        self.layout.setSpacing(20)

        self.title_label = QLabel("Biblioteca de Juegos")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(self.title_font)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0,0,0))
        shadow.setOffset(3,3)
        self.title_label.setGraphicsEffect(shadow)
        self.layout.addWidget(self.title_label)

        self.gradient_offset = 0.0
        self.gradient_timer = QTimer()
        self.gradient_timer.timeout.connect(self.update_title_gradient)
        self.gradient_timer.start(50)

        self.explore_btn = QPushButton("Explorar Biblioteca")
        self.explore_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.explore_btn.setStyleSheet("""
            QPushButton {
                padding:10px 20px;
                font-size:18px;
                color:#FFFFFF;
                background-color:#1B2838;
                border:2px solid #2A475E;
                border-radius:8px;
            }
            QPushButton:hover {background-color:#2A475E;}
        """)
        self.explore_btn.clicked.connect(self.mostrar_busqueda)
        self.layout.addWidget(self.explore_btn, alignment=Qt.AlignHCenter)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(20)
        self.results_widget.setLayout(self.results_layout)
        self.scroll.setWidget(self.results_widget)
        self.layout.addWidget(self.scroll)
        self.scroll.setVisible(False)

        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(200,0,200,0)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar juegos...")
        self.search_bar.setStyleSheet("""
            background-color:#1B2838;
            color:white;
            padding:8px;
            border:2px solid #2A475E;
            border-radius:6px;
        """)
        self.search_button = QPushButton("Buscar")
        self.search_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.search_button.setStyleSheet("""
            background-color:#2A475E; 
            color:white; 
            border-radius:6px; 
            padding:8px 14px; 
            border:1px solid #3E5C7C;
        """)
        self.search_button.clicked.connect(self.buscar_juegos)
        self.home_button = QPushButton("Inicio")
        self.home_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.home_button.setStyleSheet("""
            background-color:#1B2838; 
            color:white; 
            border-radius:6px; 
            padding:8px 14px; 
            border:1px solid #2A475E;
        """)
        self.home_button.clicked.connect(self.volver_inicio)
        search_layout.addWidget(self.home_button)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)

        self.search_bar.setVisible(False)
        self.search_button.setVisible(False)
        self.home_button.setVisible(False)
        self.layout.insertLayout(1, search_layout)

    def update_title_gradient(self):
        self.gradient_offset += 0.01
        if self.gradient_offset > 1.0:
            self.gradient_offset = 0.0
        gradient = QLinearGradient(0, 0, self.title_label.width(), 0)
        gradient.setColorAt((0 + self.gradient_offset) % 1.0, QColor("#66C0F4"))
        gradient.setColorAt((0.5 + self.gradient_offset) % 1.0, QColor("#FFFFFF"))
        gradient.setColorAt((1.0 + self.gradient_offset) % 1.0, QColor("#66C0F4"))
        palette = QPalette()
        palette.setBrush(QPalette.WindowText, QBrush(gradient))
        self.title_label.setPalette(palette)

    def mostrar_busqueda(self):
        self.title_label.hide()
        self.explore_btn.hide()
        self.scroll.show()
        self.search_bar.setVisible(True)
        self.search_button.setVisible(True)
        self.home_button.setVisible(True)

    def volver_inicio(self):
        self.title_label.show()
        self.explore_btn.show()
        self.scroll.hide()
        self.search_bar.setVisible(False)
        self.search_button.setVisible(False)
        self.home_button.setVisible(False)

    def buscar_juegos(self):
        texto = self.search_bar.text().strip()
        if not texto: return
        for i in reversed(range(self.results_layout.count())):
            w = self.results_layout.itemAt(i).widget()
            if w: w.setParent(None)
        try:
            results = buscar_juego(texto, limit=12)
            if not results:
                raise ValueError("No se encontraron resultados.")
        except Exception as e:
            label = QLabel(str(e))
            label.setStyleSheet("font-size:18px; color:#FF5555;")
            self.results_layout.addWidget(label)
            return
        for game in results:
            tarjeta = self.crear_tarjeta_horizontal(game)
            self.results_layout.addWidget(tarjeta)

    def crear_tarjeta_horizontal(self, game):
        frame = HoverFrame()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        frame.setLayout(main_layout)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        # Portada
        cover_id = game.get("cover", {}).get("image_id")
        cover_label = QLabel()
        cover_label.setMaximumWidth(250)
        cover_label.setCursor(QCursor(Qt.ArrowCursor))
        left_layout.addWidget(cover_label)
        if cover_id:
            cover_url = obtener_url_cover(cover_id)
            worker = ImagenWorker(cover_url, cover_label)
            worker.signals.finished.connect(partial(self.set_pixmap_con_blur, cover_label, 250))
            self.threadpool.start(worker)

        # Capturas
        screenshots = game.get("screenshots", [])[:3]
        if screenshots:
            h_layout_screens = QHBoxLayout()
            h_layout_screens.setSpacing(10)
            for s in screenshots:
                lbl = ZoomLabel()
                lbl.setFixedSize(400, 225)
                lbl.setStyleSheet("border-radius:5px;")
                lbl.mousePressEvent = self.crear_clickable_popup(lbl)
                h_layout_screens.addWidget(lbl)
                url = obtener_url_screenshot(s.get("image_id"))
                worker = ImagenWorker(url, lbl)
                worker.signals.finished.connect(partial(self.set_pixmap, lbl, 400))
                self.threadpool.start(worker)
            left_layout.addLayout(h_layout_screens)

        main_layout.addLayout(left_layout, stretch=1)

        # Datos
        right_layout = QVBoxLayout()
        right_layout.setSpacing(8)

        name_label = QLabel(game.get('name','N/A'))
        name_label.setFont(self.game_font)
        gradient = QLinearGradient(0,0,150,0)
        gradient.setColorAt(0, QColor("#66C0F4"))
        gradient.setColorAt(1, QColor("#FFFFFF"))
        palette = QPalette()
        palette.setBrush(QPalette.WindowText, QBrush(gradient))
        name_label.setPalette(palette)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0,0,0))
        shadow.setOffset(2,2)
        name_label.setGraphicsEffect(shadow)
        right_layout.addWidget(name_label)

        rating = game.get("rating")
        rating_label = QLabel(f"Rating: {rating:.2f}" if rating else "Rating: N/A")
        rating_label.setStyleSheet("color:#CCCCCC;")
        right_layout.addWidget(rating_label)

        platforms = ", ".join([p['name'] for p in game.get("platforms", [])]) if game.get("platforms") else "N/A"
        platforms_label = QLabel(f"Plataformas: {platforms}")
        platforms_label.setStyleSheet("color:#CCCCCC;")
        right_layout.addWidget(platforms_label)

        genres = ", ".join([g['name'] for g in game.get("genres", [])]) if game.get("genres") else "N/A"
        genres_label = QLabel(f"Géneros: {genres}")
        genres_label.setStyleSheet("color:#66C0F4; font-weight:bold;")
        right_layout.addWidget(genres_label)

        summary = game.get("summary","No hay resumen disponible.")
        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet("color:#AAAAAA;")
        right_layout.addWidget(summary_label)

        trailer_btn = QPushButton("Ver Trailer")
        trailer_btn.setCursor(QCursor(Qt.PointingHandCursor))
        trailer_btn.setStyleSheet("""
            QPushButton {
                padding:10px 20px;
                font-size:16px;
                background-color:#3E5C7C;
                color:white;
                border-radius:8px;
            }
            QPushButton:hover {background-color:#66C0F4;}
        """)
        trailer_btn.clicked.connect(lambda _, n=game.get("name",""): webbrowser.open(f"https://www.youtube.com/results?search_query={n.replace(' ','+')}+trailer"))
        right_layout.addWidget(trailer_btn, alignment=Qt.AlignLeft)

        right_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        main_layout.addLayout(right_layout, stretch=2)
        return frame

    # --- Aplicar blur a la portada ---
    def set_pixmap_con_blur(self, label, width, pixmap):
        if pixmap:
            scaled = pixmap.scaled(width, int(width*pixmap.height()/pixmap.width()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled)
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(12)
            label.setGraphicsEffect(blur)

    def crear_clickable_popup(self, label):
        def handler(event):
            pixmap = label.pixmap()
            if pixmap is not None:
                label.zoom_enabled = False
                self.mostrar_imagen_completa(pixmap)
                label.zoom_enabled = True
        return handler

    def set_pixmap(self, label, width, pixmap):
        if pixmap:
            label.setPixmap(pixmap.scaled(width, int(width*pixmap.height()/pixmap.width()), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def mostrar_imagen_completa(self, pixmap):
        if pixmap is None: return
        dialog = QDialog(self)
        dialog.setWindowTitle("Captura del juego")
        dialog.setModal(True)
        dialog.setWindowOpacity(0.9)
        dialog.setStyleSheet("""
            QDialog {
                background-color:#0B1D2F;
                border-radius:15px;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10,10,10,10)
        dialog.setLayout(layout)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0,0,0,180))
        shadow.setOffset(0,0)
        dialog.setGraphicsEffect(shadow)

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        screen = QDesktopWidget().availableGeometry(self)
        max_width = int(screen.width() * 0.8)
        max_height = int(screen.height() * 0.8)
        w_ratio = max_width / pixmap.width()
        h_ratio = max_height / pixmap.height()
        ratio = min(w_ratio, h_ratio, 1.0)
        new_w = int(pixmap.width() * ratio)
        new_h = int(pixmap.height() * ratio)
        label.setPixmap(pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        dialog.resize(new_w, new_h)
        dialog.adjustSize()
        dialog.exec_()

# --- Ejecutar ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameTrackerApp()
    window.show()
    sys.exit(app.exec_())






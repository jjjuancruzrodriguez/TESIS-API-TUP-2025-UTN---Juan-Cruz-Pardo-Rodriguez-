import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QGraphicsDropShadowEffect, QDialog
)
from PyQt5.QtCore import Qt, QThreadPool, QRunnable, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase, QColor, QLinearGradient, QBrush, QPalette

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
        juegos.sort(key=lambda x: x.get("rating", 0), reverse=True)
        return juegos
    else:
        raise ValueError(f"Error API: {response.status_code}")

def obtener_url_cover(image_id, size="cover_big"):
    if not image_id: return None
    return f"https://images.igdb.com/igdb/image/upload/t_{size}/{image_id}.jpg"

def obtener_url_screenshot(image_id, size="720p"):
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

# --- CoverLabel ---
class CoverLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                border-radius:12px;
                border:2px solid #555555;
                background-color:#111111;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(35)
        shadow.setColor(QColor(0,0,0,200))
        shadow.setOffset(0,0)
        self.setGraphicsEffect(shadow)

# --- ZoomLabel con pop-up al hover ---
class ZoomLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        self._original_pixmap = None
        self._popup = None
        self.setStyleSheet("""
            QLabel {
                border-radius:10px;
                border:2px solid rgba(255,255,255,40);
                background-color: rgba(50, 50, 50, 50);
            }
            QLabel:hover {
                border-color:#FFD700;
            }
        """)

    def setPixmap(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        super().setPixmap(pixmap)

    def enterEvent(self, event):
        if self._original_pixmap:
            self._popup = QDialog()
            self._popup.setWindowFlag(Qt.FramelessWindowHint)
            self._popup.setWindowFlag(Qt.Tool)
            self._popup.setAttribute(Qt.WA_TranslucentBackground)
            layout = QVBoxLayout(self._popup)
            layout.setContentsMargins(5,5,5,5)
            label = QLabel()
            label.setPixmap(self._original_pixmap.scaled(450, 260, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            layout.addWidget(label)
            # Posición del pop-up cerca del cursor
            pos = self.mapToGlobal(self.rect().bottomLeft())
            self._popup.move(pos.x(), pos.y()+5)
            self._popup.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._popup:
            self._popup.close()
            self._popup = None
        super().leaveEvent(event)

# --- CardFrame ---
class CardFrame(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 230);
                border-radius:15px;
                border: 2px solid rgba(255,255,255,40);
            }
        """)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0,0,0,200))
        self.shadow.setOffset(0,0)
        self.setGraphicsEffect(self.shadow)

    def enterEvent(self, event):
        self.shadow.setBlurRadius(40)
        self.shadow.setOffset(0,-5)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0,0)
        super().leaveEvent(event)

# --- Ventana principal ---
class GameTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WIKI JUEGOS UTN")
        self.showMaximized()

        palette = QPalette()
        gradient = QLinearGradient(0,0,0,1080)
        gradient.setColorAt(0.0, QColor("#000000"))
        gradient.setColorAt(1.0, QColor("#2E2E2E"))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)

        self.threadpool = QThreadPool()
        QFontDatabase.addApplicationFont("Orbitron-Bold.ttf")
        self.title_font = QFont("Orbitron",48)
        self.game_font = QFont("Orbitron",16)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20,20,20,20)
        self.layout.setSpacing(20)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.logo_label)

        self.title_label = QLabel("WIKI JUEGOS UTN")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(self.title_font)
        self.title_label.setStyleSheet("color:white;")
        self.layout.addWidget(self.title_label)

        self.explore_btn = QPushButton("Explorar Biblioteca")
        self.explore_btn.setCursor(Qt.PointingHandCursor)
        self.explore_btn.setStyleSheet("""
            QPushButton {
                padding:10px 20px;
                font-size:18px;
                color:#FFFFFF;
                background-color:#222222;
                border:2px solid #555555;
                border-radius:8px;
            }
            QPushButton:hover {background-color:#444444;}
        """)
        self.explore_btn.clicked.connect(self.mostrar_busqueda)
        self.layout.addWidget(self.explore_btn,alignment=Qt.AlignHCenter)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_layout.setSpacing(25)
        self.results_widget.setLayout(self.results_layout)
        self.scroll.setWidget(self.results_widget)
        self.layout.addWidget(self.scroll)
        self.scroll.setVisible(False)

        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar juegos...")
        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.buscar_juegos)
        self.home_button = QPushButton("Inicio")
        self.home_button.clicked.connect(self.volver_inicio)
        search_layout.addWidget(self.home_button)
        search_layout.addWidget(self.search_bar)
        search_layout.addWidget(self.search_button)
        self.layout.insertLayout(3,search_layout)

        self.resizeEvent = self.redibujar_capturas

    def mostrar_busqueda(self):
        self.logo_label.hide()
        self.title_label.hide()
        self.explore_btn.hide()
        self.scroll.show()
        self.search_bar.setVisible(True)
        self.search_button.setVisible(True)
        self.home_button.setVisible(True)

    def volver_inicio(self):
        self.logo_label.show()
        self.title_label.show()
        self.explore_btn.show()
        self.scroll.hide()
        self.search_bar.setVisible(False)
        self.search_button.setVisible(False)
        self.home_button.setVisible(False)

    def buscar_juegos(self):
        nombre = self.search_bar.text().strip()
        if not nombre: return
        for i in reversed(range(self.results_layout.count())):
            widget = self.results_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        try:
            self.juegos = buscar_juego(nombre)
        except Exception as e:
            print(f"Error: {e}")
            return

        for juego in self.juegos:
            frame = CardFrame()
            frame_layout = QVBoxLayout(frame)
            frame_layout.setSpacing(12)

            top_layout = QHBoxLayout()
            top_layout.setSpacing(20)

            cover_label = CoverLabel()
            cover_label.setFixedSize(220, 300)
            cover_url = obtener_url_cover(juego.get("cover", {}).get("image_id"))
            worker = ImagenWorker(cover_url, cover_label)
            worker.signals.finished.connect(lambda pixmap, label=cover_label: label.setPixmap(
                pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.threadpool.start(worker)
            top_layout.addWidget(cover_label)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(6)
            title = QLabel(juego.get("name","Sin nombre"))
            title.setFont(self.game_font)
            title.setStyleSheet("color:white;")
            info_layout.addWidget(title)

            summary = QLabel(juego.get("summary","Sin descripción"))
            summary.setWordWrap(True)
            summary.setStyleSheet("color:#CCCCCC;")
            info_layout.addWidget(summary)

            rating = QLabel(f"Rating: {juego.get('rating',0):.1f}")
            rating.setStyleSheet("color:#FFD700;")
            info_layout.addWidget(rating)

            platforms = ", ".join([p["name"] for p in juego.get("platforms",[])]) if juego.get("platforms") else "N/A"
            genres = ", ".join([g["name"] for g in juego.get("genres",[])]) if juego.get("genres") else "N/A"
            plat_label = QLabel(f"Plataformas: {platforms}")
            plat_label.setStyleSheet("color:#AAAAAA;")
            info_layout.addWidget(plat_label)
            genre_label = QLabel(f"Géneros: {genres}")
            genre_label.setStyleSheet("color:#AAAAAA;")
            info_layout.addWidget(genre_label)

            top_layout.addLayout(info_layout)
            frame_layout.addLayout(top_layout)

            screenshots = juego.get("screenshots", [])[:4]
            ss_container = QScrollArea()
            ss_container.setWidgetResizable(True)
            ss_container.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            ss_container.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            ss_container.setStyleSheet("background: transparent; border: none;")

            ss_widget = QWidget()
            ss_widget.setStyleSheet("background-color: rgba(40, 40, 40, 30); border: none;")
            ss_layout = QHBoxLayout(ss_widget)
            ss_layout.setSpacing(15)

            frame.capturas_labels = []
            for ss in screenshots:
                ss_label = ZoomLabel()
                ss_label.setFixedSize(350, int(350*0.57))
                frame.capturas_labels.append((ss_label, ss.get("image_id")))
                ss_layout.addWidget(ss_label)
            ss_container.setWidget(ss_widget)
            frame_layout.addWidget(ss_container)

            self.results_layout.addWidget(frame)

        self.redibujar_capturas()

    def redibujar_capturas(self, event=None):
        if not hasattr(self, 'juegos'):
            return
        for i in range(self.results_layout.count()):
            frame = self.results_layout.itemAt(i).widget()
            if hasattr(frame, 'capturas_labels'):
                for ss_label, image_id in frame.capturas_labels:
                    ss_url = obtener_url_screenshot(image_id)
                    worker = ImagenWorker(ss_url, ss_label)
                    worker.signals.finished.connect(lambda pixmap,label=ss_label: label.setPixmap(
                        pixmap.scaled(label.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation)))
                    self.threadpool.start(worker)
        if event: super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameTrackerApp()
    window.show()
    sys.exit(app.exec_())























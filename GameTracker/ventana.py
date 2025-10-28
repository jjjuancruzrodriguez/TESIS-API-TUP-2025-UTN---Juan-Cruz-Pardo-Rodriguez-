import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit

class GameTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Game Tracker IGDB")
        self.setGeometry(100, 100, 500, 400)

        # Layout
        layout = QVBoxLayout()

        # Input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Escribe el nombre del juego...")
        layout.addWidget(self.search_input)

        # Botón
        self.search_button = QPushButton("Buscar Juego")
        layout.addWidget(self.search_button)
        self.search_button.clicked.connect(self.search_game)

        # Resultados
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        layout.addWidget(self.result_area)

        self.setLayout(layout)

    def search_game(self):
        game_name = self.search_input.text()
        if game_name:
            self.result_area.setText(f"Buscando información de: {game_name}")
            # Aquí llamaremos a la API
        else:
            self.result_area.setText("Por favor, escribe un nombre de juego.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameTrackerApp()
    window.show()
    sys.exit(app.exec_())

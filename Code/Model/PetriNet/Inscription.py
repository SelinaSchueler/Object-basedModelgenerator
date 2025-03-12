class Inscription:
    def __init__(self):
        self.texts = []

    def add_text(self, text):
        if isinstance(text, str):  # Überprüfen, ob der Text ein String ist
            self.texts.append(text)
        elif isinstance(text, list):  # Überprüfen, ob der Text eine Liste ist
            self.texts.extend(text)
        else:
            print("Ungültiger Texttyp")  # Behandeln Sie andere Typen nach Bedarf
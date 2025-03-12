#Alle erzeugten Elemente werden in einem Wörterbuch gespeichert und können daher durch die ID zurück gegeben werden.
class Instances:
    # Klassenvariable als Wörterbuch
    instances = {}

    def __init__(self, inst_id, name):
        # Konstruktor-Methode: Initialisiert eine Instanz mit inst_id und name
        self.inst_id = inst_id
        self.name = name
        # Füge die Instanz zum Wörterbuch hinzu, mit inst_id als Schlüssel und der Instanz als Wert
        Instances.instances[inst_id] = self

    @staticmethod
    def get_instance_by_id(inst_id):
        # Statische Methode: Gibt die Instanz basierend auf der inst_id zurück
        # Verwendet get-Methode, um None zurückzugeben, wenn inst_id nicht gefunden wird
        return Instances.instances.get(inst_id, None)

    @classmethod
    def get_all_instances(cls):
        # Klassenmethode: Gibt alle Instanzen der Klasse zurück
        return cls.instances.values()
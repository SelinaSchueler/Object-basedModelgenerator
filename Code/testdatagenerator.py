import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class TestDataGenerator:
    def __init__(self, start_date="01.01.2023", end_date="31.12.2023"):
        self.start_date = datetime.strptime(start_date, "%d.%m.%Y")
        self.end_date = datetime.strptime(end_date, "%d.%m.%Y")
        self.kunden = []
        self.produkte = []
        self.bestellungen = []
        self.bestatigungen = []
        self.lieferscheine = []
        self.rechnungen = []
        
    def generate_all_data(self, num_kunden=10, num_produkte=10, num_bestellungen=20):
        self.generate_kunden(num_kunden)
        self.generate_produkte(num_produkte)
        self.generate_bestellungen(num_bestellungen)
        return {
            "kunden": self.kunden,
            "produkte": self.produkte,
            "bestellungen": self.bestellungen,
            "bestatigungen": self.bestatigungen,
            "lieferscheine": self.lieferscheine,
            "rechnungen": self.rechnungen
        }

    def generate_kunden(self, count: int):
        laender = ["Deutschland", "Schweiz", "Österreich"]
        staedte = {
            "Deutschland": ["Berlin", "Hamburg", "München", "Köln"],
            "Schweiz": ["Zürich", "Bern", "Basel", "Genf"],
            "Österreich": ["Wien", "Graz", "Salzburg", "Linz"]
        }
        zahlungsarten = ["Kreditkarte", "PayPal", "Überweisung", "Lastschrift"]
        
        for i in range(count):
            land = random.choice(laender)
            self.kunden.append({
                "Kundennummer": i + 1,
                "Name": f"Kunde_{i + 1}",
                "Adresse": {
                    "Straße": f"Straße_{i + 1}",
                    "Ort": random.choice(staedte[land]),
                    "Land": land
                },
                "Email": f"kunde_{i + 1}@example.com",
                "Zahlungsart": random.choice(zahlungsarten)
            })

    def generate_produkte(self, count: int):
        for i in range(count):
            self.produkte.append({
                "Produktid": i + 100,
                "Name": f"Schraube {random.randint(100, 500)}mm",
                "Preis": round(random.uniform(5.0, 50.0), 2),
                "Lagermenge": random.randint(50, 500),
                "Einzelgewicht": round(random.uniform(0.1, 2.0), 1)
            })

    def generate_random_date(self) -> datetime:
        time_between_dates = self.end_date - self.start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = random.randrange(days_between_dates)
        return self.start_date + timedelta(days=random_number_of_days)

    def format_date(self, date: datetime) -> str:
        return date.strftime("%d.%m.%Y")

    def generate_bestellungen(self, count: int):
        for i in range(count):
            bestellung_datum = self.generate_random_date()
            kunde = random.choice(self.kunden)
            
            # Generate order products
            produkte = []
            gesamtpreis = 0
            gesamtgewicht = 0
            num_products = random.randint(1, 3)
            
            selected_products = random.sample(self.produkte, num_products)
            for produkt in selected_products:
                menge = random.randint(1, 5)
                produkte.append({
                    "Produktid": produkt["Produktid"],
                    "Menge": menge
                })
                gesamtpreis += produkt["Preis"] * menge
                gesamtgewicht += produkt["Einzelgewicht"] * menge

            # Create order
            bestellung = {
                "Case_id": i + 1,
                "Bestellungsnummer": i + 1,
                "Kundennummer": kunde["Kundennummer"],
                "Produkte": produkte,
                "Lieferart": random.randint(1, 3),
                "Gesamtpreis": round(gesamtpreis, 2),
                "Datum": self.format_date(bestellung_datum)
            }
            self.bestellungen.append(bestellung)

            # Generate confirmation
            bestaetigung_datum = bestellung_datum + timedelta(days=random.randint(1, 3))
            lieferdatum = bestaetigung_datum + timedelta(days=random.randint(7, 14))
            
            bestaetigung = {
                "Case_id": i + 1,
                "Bestellungsnummer": bestellung["Bestellungsnummer"],
                "Kundennummer": kunde["Kundennummer"],
                "Bestätigung": random.random() > 0.1,  # 90% success rate
                "Voraussichtliches Lieferdatum": self.format_date(lieferdatum),
                "Datum": self.format_date(bestaetigung_datum)
            }
            self.bestatigungen.append(bestaetigung)

            # Only generate delivery note and invoice if order is confirmed
            if bestaetigung["Bestätigung"]:
                # Generate delivery note
                lieferschein_datum = lieferdatum - timedelta(days=random.randint(1, 2))
                lieferschein = {
                    "Lieferscheinid": 2000 + i,
                    "Case_id": i + 1,
                    "Bestellungsnummer": bestellung["Bestellungsnummer"],
                    "Datum": self.format_date(lieferschein_datum),
                    "Produkte": produkte,
                    "Gesamtgewicht": round(gesamtgewicht, 1)
                }
                self.lieferscheine.append(lieferschein)

                # Generate invoice
                rechnung_datum = lieferschein_datum + timedelta(days=random.randint(1, 3))
                rechnung = {
                    "Case_id": i + 1,
                    "Bestellungsnummer": bestellung["Bestellungsnummer"],
                    "BestätigungID": 1000 + i,
                    "Gesamtbetrag": bestellung["Gesamtpreis"],
                    "Rabatt": round(random.uniform(0, 0.05), 2),
                    "Lieferkosten": 15.0 if bestellung["Gesamtpreis"] < 100 else 0,
                    "Fälligkeitsdatum": self.format_date(rechnung_datum + timedelta(days=30)),
                    "Datum": self.format_date(rechnung_datum)
                }
                self.rechnungen.append(rechnung)

    def save_to_files(self, base_path: str = ""):
        """Save generated data to individual JSON files"""
        files = {
            "Kunden.json": {"Kunden": self.kunden},
            "Produkt.json": {"Produkte": self.produkte},
            "Bestellung.json": {"Bestellung": self.bestellungen},
            "Bestätigung.json": {"Bestätigung": self.bestatigungen},
            "Lieferschein.json": {"Lieferscheine": self.lieferscheine},
            "Rechnung.json": {"Rechnung": self.rechnungen}
        }
        
        for filename, data in files.items():
            with open(f"{base_path}{filename}", 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
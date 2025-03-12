from datetime import datetime
import re

class DateTransformer:
    def __init__(self):
        # Einheitliches Format nach der Konvertierung
        self.unified_date_pattern = re.compile(
            r'\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2}'  # DD.MM.YYYY HH:MM:SS
        )
        
        self.date_formats = [
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%d.%m.%Y",
            "%d.%m.%y",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%y %H:%M:%S"
        ]
        # Ein regulärer Ausdruck, um verschiedene Datumsformate zu finden

        self.date_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?)|'    # YYYY-MM-DDTHH:MM:SS
            r'(\d{2}/\d{2}/\d{4}(?: \d{2}:\d{2}:\d{2})?)|'    # DD/MM/YYYY HH:MM:SS
            r'(\d{4}/\d{2}/\d{2}(?: \d{2}:\d{2}:\d{2})?)|'    # YYYY/MM/DD HH:MM:SS
            r'(\d{4}\.\d{2}\.\d{2}(?: \d{2}:\d{2}:\d{2})?)|'  # YYYY.MM.DD HH:MM:SS
            r'(\d{2}/\d{2}/\d{4})|'                           # DD/MM/YYYY
            r'(\d{4}/\d{2}/\d{2})|'                           # YYYY/MM/DD
            r'(\d{2}\.\d{2}\.\d{4})|'                         # DD.MM.YYYY
            r'(\d{2}\.\d{2}\.\d{2})'                          # DD.MM.YY
        )

    def parse_date(self, date_str):
            # Erst prüfen ob überhaupt ein Datumsmuster
        if not any(match for match in self.date_pattern.findall(date_str)):
            return None
    
        try:
            dt = None
            if len(date_str) < 12:  # Nur Datum
                if '/' in date_str:
                    if len(date_str.split('/')[0]) == 4:# Format: YYYY/MM/DD
                        dt = datetime.strptime(date_str, "%Y/%m/%d")
                    else: # Format: DD/MM/YYYY
                        dt = datetime.strptime(date_str, "%d/%m/%Y")
                elif '.' in date_str:
                    if len(date_str.split('.')[2]) == 4:# Format: DD.MM.YYYY
                        dt = datetime.strptime(date_str, "%d.%m.%Y")
                    else:# Format: DD.MM.YY
                        dt = datetime.strptime(date_str, "%d.%m.%y")
                else:# Format: YYYY-MM-DD
                    dt = datetime.strptime(date_str, "%Y-%m-%d")
                # Bei reinem Datum Zeit auf 00:00:00 setzen
                dt = dt.replace(hour=0, minute=0, second=0)
            # Datum mit Zeit
            elif 'T' in date_str:# ISO Format: YYYY-MM-DDTHH:MM:SS
                dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            elif '/' in date_str:
                if len(date_str.split('/')[0]) == 4: # Format: YYYY/MM/DD HH:MM:SS
                    dt = datetime.strptime(date_str, "%Y/%m/%d %H:%M:%S")
                else:# Format: DD/MM/YYYY HH:MM:SS
                    dt = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
            elif '.' in date_str:
                if len(date_str.split('.')[2]) == 4:# Format: DD.MM.YYYY HH:MM:SS
                    dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M:%S")
                else: # Format: DD.MM.YY HH:MM:SS
                    dt = datetime.strptime(date_str, "%d.%m.%y %H:%M:%S")
            else:# Falls das Datum nur YYYY-MM-DD ist, ergänze automatisch 00:00:00 Uhr
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt.replace(hour=0, minute=0, second=0)
            return dt
        except ValueError:
            return None

    def format_date(self, dt):
        # Überprüfen, ob die Zeit auf 00:00:00 gesetzt werden muss
        if dt is None:
            return None
        elif dt.hour == 0 and dt.minute == 0 and dt.second == 0:
            return dt.strftime("%d.%m.%Y 00:00:00")
        else:
            return dt.strftime("%d.%m.%Y %H:%M:%S")

    def find_and_parse_Date(self, obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str):
                    parsed_date = self.parse_date(value)
                    if parsed_date:
                        # Setze die Uhrzeit auf 00:00:00, wenn sie nicht vorhanden ist
                        if parsed_date.hour == 0 and parsed_date.minute == 0 and parsed_date.second == 0:
                            parsed_date = parsed_date.replace(hour=0, minute=0, second=0)
                        obj[key] = self.format_date(parsed_date)
                elif isinstance(value, (dict, list)):
                    self.find_and_parse_Date(value)
        elif isinstance(obj, list):
            for i in range(len(obj)):
                if isinstance(obj[i], str):
                    parsed_date = self.parse_date(obj[i])
                    if parsed_date:
                        # Setze die Uhrzeit auf 00:00:00, wenn sie nicht vorhanden ist
                        if parsed_date.hour == 0 and parsed_date.minute == 0 and parsed_date.second == 0:
                            parsed_date = parsed_date.replace(hour=0, minute=0, second=0)
                        obj[i] = self.format_date(parsed_date)
                elif isinstance(obj[i], (dict, list)):
                    self.find_and_parse_Date(obj[i])

        return obj
    
    def get_content_timestamps(self, doc_content):
        """Extrahiert alle Zeitstempel aus dem Dokument mit ihren Pfaden"""
        timestamps_dict = {}
        self._find_dates_with_path(doc_content, timestamps_dict)
        return timestamps_dict

    def _find_dates_with_path(self, obj, timestamps_dict, parent_key=''):
        """Findet bereits konvertierte Datumswerte und speichert sie mit ihrem Pfad"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{parent_key}.{key}" if parent_key else key
                self._find_dates_with_path(value, timestamps_dict, full_key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                full_key = f"{parent_key}[{index}]"
                self._find_dates_with_path(item, timestamps_dict, full_key)
        elif isinstance(obj, str):
            if self.unified_date_pattern.match(obj):
                timestamps_dict[parent_key] = obj
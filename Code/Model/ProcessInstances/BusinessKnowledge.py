class BusinessKnowledge:
    @staticmethod
    def define_business_keys():
        """
        Defines the hierarchy of business keys.

        Returns:
            dict: A dictionary with the hierarchy of business keys categorized as:
                - 'direkt': Direct keys, e.g., ['Case_id']
                - 'primär': Primary keys, e.g., ['Bestellungsnummer', 'Auftragsnummer', 'Rechnungsnummer']
                - 'sekundär': Secondary keys, e.g., ['Kundennummer', 'Produktid', 'Artikelnummer']
                - 'tertiär': Tertiary keys, e.g., ['Lieferadresse', 'Email', 'Telefonnummer']
        """
        return {
            'direkt': ['Case_id'],
            'primär': ['Bestellungsnummer', 'Auftragsnummer', 'Rechnungsnummer'],
            'sekundär': ['Kundennummer', 'Produktid', 'Artikelnummer'],
            'tertiär': ['Lieferadresse', 'Email', 'Telefonnummer']
        }

    @staticmethod
    def define_document_patterns():
        """Definiert typische Dokumentflüsse und Regeln"""
        return {
            'Bestellung': {
                'followed_by': ['Auftragsbestätigung', 'Rechnung', 'Lieferschein'],
                'max_time_diff': {'days': 30},
                'required_fields': ['Bestellungsnummer', 'Kundennummer']
            },
            'Auftragsbestätigung': {
                'follows': ['Bestellung'],
                'followed_by': ['Rechnung', 'Lieferschein'],
                'required_fields': ['Auftragsnummer', 'Bestellungsnummer']
            },
            'Rechnung': {
                'follows': ['Auftragsbestätigung', 'Lieferschein'],
                'required_fields': ['Rechnungsnummer', 'Bestellungsnummer']
            },
            'Lieferschein': {
                'follows': ['Auftragsbestätigung'],
                'followed_by': ['Rechnung'],
                'required_fields': ['Lieferadresse', 'Bestellungsnummer']
            }
        }

import io
import json
import os
import threading
from datetime import datetime
import sys
import webbrowser
import PIL
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QProgressBar, QTabWidget, QTextEdit, QScrollArea, QWidget, QListWidget, QListWidgetItem, QAbstractItemView, QDialogButtonBox, QDialog
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QGridLayout
from PyQt5.QtCore import QUrl, pyqtSignal, QObject, Qt
from graphviz import Digraph
from PIL import ImageQt
from PIL import Image
from PyQt5.QtWidgets import (QGroupBox, QScrollArea, QWidget, QVBoxLayout, QGridLayout, 
                            QLabel, QCheckBox, QPushButton, QHBoxLayout)
from PyQt5 import QtCore
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from PyQt5.QtWidgets import QSplitter
from PyQt5.QtWidgets import QFrame
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from Model.ObjectModel.ObjectRelation import RealtationType


#'/home/user/example/parent/child'
current_path = os.path.abspath('.')

#'/home/user/example/parent'
parent_path = os.path.dirname(current_path)

sys.path.append(parent_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'child.settings')

import Controller.Informationextraction.DocToObjectModel.ObjectModelGenerator as omg
from Model.ObjectModel.ObjectModel import ObjectModel
from Controller.Informationextraction.ProcessinstanceClassifier import ProcessInstanceClassifier
from Controller.Informationextraction.ObjecttypeGenerator.ObjectGenerator import ObjectTypeGenerator
from Controller.Informationextraction.ObjectRelationGenerator import ObjectRelationGenerator
from Controller.Informationextraction.ActivityGenerator.ActivityGenerator import ActivityGenerator
from Controller.Transformation.PNGenerator import EventlogPNGenerator
from Controller.PreDataAnalyse.PreInstancegenerator import PreInstanceGenerator
from Controller.Informationextraction.ObjecttypeGenerator.DocumentClassifier import DocumentClassifier
from Controller.Transformation.Ruleextactor import DecisionPointAnalyzer

class SignalEmitter(QObject):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    update_object_types_signal = pyqtSignal(list)
    update_object_relations_signal = pyqtSignal(dict, dict)
    update_activities_signal = pyqtSignal(list, list, object)
    add_figure_signal = pyqtSignal(object, str, bool)
    update_process_instances_signal = pyqtSignal(dict, list)
    update_rule_extractor_signal = pyqtSignal(dict, dict)

class ZoomableLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1, 1)
        self.scale_factor = 1.0
        self.original_pixmap = None
        # Enable high-quality rendering
        self.setRenderHints()
        
    def setRenderHints(self):
        # Set attributes for high quality rendering
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        
    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        super().setPixmap(pixmap)
        
    def wheelEvent(self, event):
        if self.original_pixmap:
            if event.angleDelta().y() > 0:
                self.scale_factor *= 1.1
            else:
                self.scale_factor *= 0.9
            self.scale_factor = max(0.1, self.scale_factor)
            
            # Get the current scroll position
            scrollarea = self.parent().parent()
            if isinstance(scrollarea, QScrollArea):
                old_pos = scrollarea.viewportToContents(event.pos())
            
            # Scale with high quality settings
            new_size = self.original_pixmap.size() * self.scale_factor
            scaled_pixmap = self.original_pixmap.scaled(
                new_size,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)
            
            # Adjust scroll position to keep mouse position fixed
            if isinstance(scrollarea, QScrollArea):
                new_pos = scrollarea.viewportToContents(event.pos())
                delta = new_pos - old_pos
                scrollarea.horizontalScrollBar().setValue(
                    scrollarea.horizontalScrollBar().value() + delta.x())
                scrollarea.verticalScrollBar().setValue(
                    scrollarea.verticalScrollBar().value() + delta.y())
                
class ZoomableFigureCanvas(FigureCanvas):
    def __init__(self, figure):
        super().__init__(figure)
        self.figure = figure
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFocus()
        self.mpl_connect('scroll_event', self.zoom)

    def zoom(self, event):
        ax = event.inaxes
        if ax is None:
            return

        scale_factor = 1.1 if event.button == 'up' else 0.9

        xdata, ydata = event.xdata, ydata
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor

        relx = (xlim[1] - xdata) / (xlim[1] - xlim[0])
        rely = (ylim[1] - ydata) / (ylim[1] - ydata)

        ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
        ax.set_ylim([ydata - new_height * (1 - rely)])
        self.draw_idle()
        
class ParameterAdjustmentDialog(QtWidgets.QDialog):
    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parameter einstellen")
        self.layout = QVBoxLayout(self)
        
        self.param_widgets = {}
        tooltips = {
            'same_value_threshold': 'Minimale Ähnlichkeit zwischen Werten',
            'significant_instance_threshold': 'Erforderlicher Prozentsatz für Mustersignifikanz',
            'same_common_value_threshold': 'Minimale Ähnlichkeit zwischen häufigen Werten',
            'rule_significance_threshold': 'Vertrauensschwelle für Regeln',
            'early_position_bonus': 'Bonus für frühe Dokumente',
            'late_position_penalty': 'Strafe für späte Dokumente',
            'reference_weight': 'Wichtigkeit von Querverweisen',
            'reference_position_factor': 'Einfluss der Positionen',
            'sequence_weight': 'Einfluss von Prozessmustern',
            'attribute_weight': 'Wichtigkeit von Attributen',
            'temporal_weight': 'Einfluss zeitlicher Beziehungen',
            'variant_weight': 'Einfluss von Varianten',
            'parallel_object_penalty': 'Strafe für gleichzeitige Verarbeitung',
            'each_attribute_by_object': 'Jedes Attribut einzeln verarbeiten',
            'database_visualization': 'Datenbankvisualisierung aktivieren',
            'loop_weight': 'Gewichtung für Schleifen in Aktivitäten',
            'max_features': 'Maximale Anzahl von Merkmalen für Klassifikatoren',
            'threshold': 'Schwellenwert für Klassifikatoren'
        }
        
        for param, value in params.items():
            label = QLabel(param)
            label.setToolTip(tooltips.get(param, ''))
            if isinstance(value, bool):
                checkbox = QCheckBox()
                checkbox.setChecked(value)
                self.param_widgets[param] = checkbox
                row_layout = QHBoxLayout()
                row_layout.addWidget(label)
                row_layout.addWidget(checkbox)
                self.layout.addLayout(row_layout)
            else:
                line_edit = QLineEdit(str(value))
                line_edit.setMinimumWidth(200)  # Increase the width of the input box
                self.param_widgets[param] = line_edit
                row_layout = QHBoxLayout()
                row_layout.addWidget(label)
                row_layout.addWidget(line_edit)
                self.layout.addLayout(row_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
    
    def get_params(self):
        params = {}
        for param, widget in self.param_widgets.items():
            if isinstance(widget, QCheckBox):
                params[param] = widget.isChecked()
            else:
                params[param] = float(widget.text())
        return params

class ObjectTypeNameDialog(QtWidgets.QDialog):
    def __init__(self, object_types, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Objekttypnamen ändern")
        self.layout = QVBoxLayout(self)
        
        self.name_widgets = {}
        for obj_type in object_types:
            label = QLabel(obj_type)
            line_edit = QLineEdit(obj_type)
            self.name_widgets[obj_type] = line_edit
            row_layout = QHBoxLayout()
            row_layout.addWidget(label)
            row_layout.addWidget(line_edit)
            self.layout.addLayout(row_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
    
    def get_new_names(self):
        return {obj_type: widget.text() for obj_type, widget in self.name_widgets.items()}

class ObjectRelationScoreDialog(QtWidgets.QDialog):
    def __init__(self, object_relations, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Objektbeziehungen bewerten")
        
        self.layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        self.score_widgets = {}
        for obj_relation in object_relations:
            label = QLabel(obj_relation)
            checkbox = QCheckBox()
            self.score_widgets[obj_relation] = checkbox
            row_layout = QHBoxLayout()
            row_layout.addWidget(label)
            row_layout.addWidget(checkbox)
            scroll_layout.addLayout(row_layout)
        
        scroll_area.setWidget(scroll_content)
        self.layout.addWidget(scroll_area)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
    
    def get_scores(self):
        return {obj_relation: widget.isChecked() for obj_relation, widget in self.score_widgets.items()}

class ActivityTypeNameDialog(QtWidgets.QDialog):
    def __init__(self, activity_types, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Aktivitätstypnamen ändern")
        self.layout = QVBoxLayout(self)
        
        self.name_widgets = {}
        for activity_type in activity_types:
            label = QLabel(activity_type)
            line_edit = QLineEdit(activity_type)
            self.name_widgets[activity_type] = line_edit
            row_layout = QHBoxLayout()
            row_layout.addWidget(label)
            row_layout.addWidget(line_edit)
            self.layout.addLayout(row_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
    
    def get_new_names(self):
        return {activity_type: widget.text() for activity_type, widget in self.name_widgets.items()}

class ProcessAnalyzerGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.signals = SignalEmitter()
        self.setWindowTitle("Prozessmodellgenerator")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)
        
        self.default_params = {
            'same_value_threshold': 0.8,
            'significant_instance_threshold': 0.9,
            'same_common_value_threshold': 1,
            'rule_significance_threshold': 0.9,
            'early_position_bonus': 1.5,
            'late_position_penalty': 0.5,
            'reference_weight': 2.0,
            'reference_position_factor': 2.0,
            'sequence_weight': 1.5,
            'attribute_weight': 1.2,
            'temporal_weight': 4.0,
            'variant_weight': 0.5,
            'parallel_object_penalty': 6.0,
            'each_attribute_by_object': False,
            'database_visualization': False
        }

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # Settings section with expandable advanced settings
        settings_frame = QtWidgets.QGroupBox("Einstellungen")
        settings_layout = QVBoxLayout(settings_frame)
        self.layout.addWidget(settings_frame)

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Eingabeordner:"))
        self.input_path = QLineEdit("C:\\ProcessModelGenerator\\Testfiles")
        file_layout.addWidget(self.input_path)
        browse_button = QPushButton("Durchsuchen")
        browse_button.clicked.connect(self.select_input_folder)
        file_layout.addWidget(browse_button)
        settings_layout.addLayout(file_layout)

       

        # Advanced Settings Panel
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.settings_widget.hide()
        self.setup_advanced_settings()
        settings_layout.addWidget(self.settings_widget)

        # Control buttons
        control_layout = QHBoxLayout()
       

        # Add mode selection for debug
        self.mode_selection = QComboBox()
        self.mode_selection.addItems(["Automatisierte Generierung", "Iterative Generierung"])
        #control_layout.addWidget(QLabel("Vorgehensweise:"))
        control_layout.addWidget(self.mode_selection)

        self.debug_mode = QCheckBox("Detail-Modus")
        control_layout.addWidget(self.debug_mode)

        control_layout.addSpacing(10)

        self.start_button = QPushButton("Generierung starten")
        self.start_button.setMinimumWidth(150)
        self.start_button.setStyleSheet("background-color: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 4px;")
        self.start_button.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.start_button)
        settings_layout.addLayout(control_layout)

         # Advanced Settings Button
        self.settings_button = QPushButton("▼ Erweiterte Einstellungen")
        self.settings_button.setStyleSheet("text-align: left; padding: 5px;")
        self.settings_button.clicked.connect(self.toggle_settings)

        
        settings_layout.addWidget(self.settings_button)# Progress bar

        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)

        self.status_text = QLabel("Bereit")
        self.layout.addWidget(self.status_text)

        # Rest of the UI setup
        self.setup_notebook()
        self.setup_export_button()
        self.setup_signals()
        self.documents_df = None  # Initialize documents_df
        self.current_step = 0  # Track the current step in iterative mode
        self.steps = [
            self.run_pre_instance_generator,
            self.run_document_classifier,
            self.run_process_instance_classifier,
            self.run_object_type_generator,
            self.run_object_relation_generator,
            self.run_activity_generator,
            self.run_petri_net_generator,
            self.run_rule_extractor
        ]
        self.mode_selection.currentTextChanged.connect(self.toggle_buttons_visibility)
        self.setup_continue_button()  # Ensure the continue button is set up
        self.toggle_buttons_visibility(self.mode_selection.currentText())  # Initial toggle

    def handle_setting_change(self, param, value, label=None):
        self.default_params[param] = value
        if label:
            label.setText(f"{value:.1f}")
        self.signals.log_signal.emit(f"Updated {param} to {value}")  # Debug output

    def setup_advanced_settings(self):
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        # Main widget for scroll area
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setSpacing(10)
        
        # Create collapsible groups
        groups = [
            ("Schwellenwerteinstellungen", {
                'same_value_threshold': ('Ähnlicher Wert', 'Minimale Ähnlichkeit zwischen Werten', 0.8),
                'significant_instance_threshold': ('Instanzbedeutung', 'Erforderlicher Prozentsatz für Mustersignifikanz', 0.9),
                'rule_significance_threshold': ('Regelbedeutung', 'Vertrauensschwelle für Regeln', 0.9)
            }),
            ("Gewichtungseinstellungen", {
                'temporal_weight': ('Zeitgewichtung', 'Einfluss zeitlicher Beziehungen', 4.0),
                'reference_weight': ('Referenzgewicht', 'Wichtigkeit von Querverweisen', 2.0),
                'sequence_weight': ('Sequenzgewicht', 'Einfluss von Prozessmustern', 1.5),
                'attribute_weight': ('Attributgewicht', 'Wichtigkeit von Attributen', 1.2)
            }),
            ("Position & Strafe", {
                'early_position_bonus': ('Frühe Position', 'Bonus für frühe Dokumente', 1.5),
                'late_position_penalty': ('Späte Position', 'Strafe für späte Dokumente', 0.5),
                'reference_position_factor': ('Positionsfaktor', 'Einfluss der Positionen', 2.0),
                'parallel_object_penalty': ('Parallele Strafe', 'Strafe für gleichzeitige Verarbeitung', 6.0)
            })
        ]

        self.sliders = {}
        
        for group_name, params in groups:
            group = QGroupBox(group_name)
            group.setCheckable(False)
            group.setChecked(True)
            layout = QGridLayout()
            layout.setVerticalSpacing(8)
            
            for row, (param, (label, tooltip, value)) in enumerate(params.items()):
                label_widget = QLabel(label)
                label_widget.setToolTip(tooltip)
                
                slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
                slider.setFixedWidth(150)  # Control slider width
                value_label = QLabel(f"{value:.1f}")
                
                slider.setMinimum(0)
                slider.setMaximum(100 if value <= 1 else int(value * 100))
                slider.setValue(int(value * 100))
                slider.valueChanged.connect(
                lambda v, p=param, l=value_label: self.handle_setting_change(p, v/100, l)
                )

                self.sliders[param] = slider         
                
                layout.addWidget(label_widget, row, 0)
                layout.addWidget(slider, row, 1)
                layout.addWidget(value_label, row, 2)
                
            group.setLayout(layout)
            main_layout.addWidget(group)
        
        # Checkbox at bottom
        self.attribute_switch = QCheckBox("Jedes Attribut pro Objekt analysieren")
        self.attribute_switch.setToolTip("Jedes Attribut einzeln verarbeiten")
        main_layout.addWidget(self.attribute_switch)

        # Checkbox for database visualization
        self.database_visualization_switch = QCheckBox("Datenbankvisualisierung")
        self.database_visualization_switch.setToolTip("Datenbankvisualisierung aktivieren")
        main_layout.addWidget(self.database_visualization_switch)
        
        self.attribute_switch.stateChanged.connect(
                    lambda state: self.handle_setting_change('each_attribute_by_object', bool(state))
                )

        self.database_visualization_switch.stateChanged.connect(
                    lambda state: self.handle_setting_change('database_visualization', bool(state))
                )
        # Add some stretch at the bottom
        main_layout.addStretch()
        
        scroll.setWidget(main_widget)
        self.settings_layout.addWidget(scroll)

        # Style
        self.apply_styles()

    def apply_styles(self):
        group_style = """
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 1em;
                padding-top: 0.5em;
            }
            QGroupBox::title {
                color: #2563eb;
                padding: 0 3px;
            }
        """
        
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #ddd;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3b82f6;
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """

        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(group_style)
            
        for slider in self.sliders.values():
            slider.setStyleSheet(slider_style)

    def toggle_settings(self):
        is_visible = self.settings_widget.isVisible()
        self.settings_widget.setVisible(not is_visible)
        self.settings_button.setText("▲ Erweiterte Einstellungen" if not is_visible else "▼ Erweiterte Einstellungen")

    def setup_log_tab(self):
        log_frame = QWidget()
        log_layout = QVBoxLayout(log_frame)
        self.notebook.addTab(log_frame, "Protokoll")

        # # Create WebView for the Protokoll page
        # self.protokoll_web_view = QWebEngineView()
        # log_layout.addWidget(self.progress)
        
        # self.status_text = QLabel("Bereit")
        # log_layout.addWidget(self.status_text)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

    def setup_start_page(self):
        start_page_frame = QWidget()
        start_page_layout = QVBoxLayout(start_page_frame)
        self.notebook.addTab(start_page_frame, "Startseite")

        # Create WebView for the start page
        self.start_page_web_view = QWebEngineView()
        start_page_layout.addWidget(self.start_page_web_view)
        
        # Load the processoverview HTML file
        html_path = os.path.join(os.path.dirname(__file__), 'View', 'processoverview.html')
        self.start_page_web_view.setUrl(QUrl.fromLocalFile(html_path))
        
        return start_page_frame
    
    def setup_notebook(self):
        self.notebook = QTabWidget()
        self.layout.addWidget(self.notebook)
        
        # Add all tabs
        self.setup_start_page()
        self.setup_log_tab()
        self.setup_clustering_view()
        self.setup_cluster_files_view()  # Add new tab for cluster files
        self.setup_process_instances_view()
        self.setup_object_types_view()
        self.setup_object_relations_view()
        self.setup_enhanced_activities_view()
        self.setup_image_viewer()
        self.setup_rule_extractor_view()

    def setup_export_button(self):
        export_layout = QHBoxLayout()
        self.layout.addLayout(export_layout)
        export_layout.addStretch()
        
        export_button = QPushButton("Exportieren")
        export_button.clicked.connect(self.export_results)
        export_layout.addWidget(export_button)

    def setup_signals(self):
        self.signals = SignalEmitter()
        self.signals.log_signal.connect(self.log)
        self.signals.progress_signal.connect(self.update_progress)
        self.signals.update_object_types_signal.connect(self.update_object_types_view)
        self.signals.update_object_relations_signal.connect(self.update_object_relations_view)
        self.signals.update_activities_signal.connect(self.update_activities_view)
        self.signals.add_figure_signal.connect(self.add_figure_to_viewer)
        self.signals.update_process_instances_signal.connect(self.update_process_instances_view)
        self.signals.update_rule_extractor_signal.connect(self.update_rule_extractor_view)

    def sync_settings_values(self, key, value):
        """Sync settings between panel and tab view"""
        if key in self.sliders:
            self.sliders[key].setValue(int(value * 100))
        if hasattr(self, 'settings_web_view'):
            self.settings_web_view.page().runJavaScript(
                f'window.updateSettings({json.dumps({key: value})});'
            )

    def save_settings(self):
        """Saves the settings from the settings view"""
        for param, widget in self.param_widgets.items():
            value = widget.text()
            if value.isdigit():
                self.default_params[param] = int(value)
            elif value.replace('.', '', 1).isdigit():
                self.default_params[param] = float(value)
            elif value.lower() in ['true', 'false']:
                self.default_params[param] = value.lower() == 'true'
            else:
                self.default_params[param] = value
        self.default_params['database_visualization'] = self.database_visualization_switch.isChecked()
        self.signals.log_signal.emit("Einstellungen gespeichert.")

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Eingabeordner auswählen")
        if folder:
            self.input_path.setText(folder)
            
    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Add log entry to the Protokoll page if debug mode is enabled
        if self.debug_mode.isChecked():
            escaped_message = message.replace("'", "\\'")
            self.log_text.append(f"[{timestamp}] {escaped_message}")
        else:
            self.log_text.append(f"[{timestamp}] {message}")

            # script = f"handleLogEntry('{escaped_message}');"
            # self.protokoll_web_view.page().runJavaScript(script)

    def update_progress(self, value, status):
        self.progress.setValue(value)
        self.status_text.setText(status)
        #self.log_text.append(status)  # Print the status text in the log tab

    def setup_object_relations_view(self):
        """Erstellt die Ansicht für Objektbeziehungen mit React"""
        self.object_relations_frame = QWidget()
        self.object_relations_layout = QVBoxLayout(self.object_relations_frame)
        self.notebook.addTab(self.object_relations_frame, "Objektbeziehungstypen")
        
        # Erstelle WebView für React-Komponente
        self.object_relations_web_view = QWebEngineView()
        self.object_relations_layout.addWidget(self.object_relations_web_view)
        
        # Lade HTML-Datei
        html_path = os.path.join(os.path.dirname(__file__), 'View/object_relationship_display.html')
        self.object_relations_web_view.setUrl(QUrl.fromLocalFile(html_path))

        # Add button to score object relations
        self.score_relations_button = QPushButton("Objektbeziehungen bewerten")
        self.score_relations_button.clicked.connect(self.show_object_relation_score_dialog)
        self.object_relations_layout.addWidget(self.score_relations_button)

    def update_object_relations_view(self, content_relations, time_relations):
        """Aktualisiert die Ansicht für Objektbeziehungen mit neuen Daten"""
        # Konvertiere Beziehungen in ein serialisierbares Format
        serializable_content = {}
        for key, relations in content_relations.items():
            key_str = str(key)  # Konvertiere Tuple-Schlüssel in String
            serializable_content[key_str] = [
                (str(relation[0]), {
                    'name': relation[1].name,
                    'objects': {str(k): v for k, v in relation[1].objects.items()}, # Konvertiere Tuple-Schlüssel in Strings
                    'rules': [(str(rule[0].value), rule[1]) for rule in relation[1].rules],
                    'processinstances': {
                        str(pid): [
                            self.convert_to_serializable(instance) 
                            for instance in instances
                        ] for pid, instances in relation[1].processinstances.items()
                    }
                }) for relation in relations
            ]

        serializable_time = {}
        for key, (relation_type, relation) in time_relations.items():
            key_str = str(key)  # Konvertiere Tuple-Schlüssel in String
            serializable_time[key_str] = (str(relation_type.value), {
                'name': relation.name,
                'objects': {str(k): v for k, v in relation.objects.items()},  # Konvertiere Tuple-Schlüssel in Strings
                'processinstances': {
                    str(key[0]): self.convert_to_serializable(instances)
                    for key, instances in relation.processinstances.items()
                } if hasattr(relation, 'processinstances') else {}
            })

        # Aktualisiere die React-Komponente über JavaScript
        update_script = f"""
            window.updateObjectRelations(
                {json.dumps(serializable_content)},
                {json.dumps(serializable_time)}
            );
        """
        self.object_relations_web_view.page().runJavaScript(update_script)

    def setup_object_types_view(self):
        """Erstellt die verbesserte Objekttypen-Ansicht mit React"""
        self.object_types_frame = QWidget()
        self.object_types_layout = QVBoxLayout(self.object_types_frame)
        self.notebook.addTab(self.object_types_frame, "Objekttypen")

        # Erstelle WebView für React-Komponente
        self.object_types_web_view = QWebEngineView()
        self.object_types_layout.addWidget(self.object_types_web_view)
        
        # Lade HTML-Datei direkt
        html_path = os.path.join(os.path.dirname(__file__), 'View//object_types_display.html')
        self.object_types_web_view.setUrl(QUrl.fromLocalFile(html_path))

        # Add button to change object type names
        self.change_names_button = QPushButton("Objekttypnamen ändern")
        self.change_names_button.clicked.connect(self.show_object_type_name_dialog)
        self.object_types_layout.addWidget(self.change_names_button)

    def convert_to_serializable(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, 'isoformat'):  # Für Datumstypen
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self.convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_serializable(item) for item in obj]
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return obj

    def update_object_types_view(self, object_type_list):
        """Aktualisiert die Objekttypen-Ansicht mit neuen Daten"""
        # Hilfsfunktion zum Konvertieren von numpy Typen
        
        def process_schema_properties(schema):
            if not isinstance(schema, dict):
                return schema

            result = {}
            for key, value in schema.items():
                if key == 'properties':
                    result[key] = {
                        prop_key: process_schema_properties(prop_value)
                        for prop_key, prop_value in value.items()
                    }
                elif key == 'items' and isinstance(value, dict):
                    # Verarbeite Array-Items rekursiv
                    result[key] = process_schema_properties(value)
                else:
                    result[key] = self.convert_to_serializable(value)
            return result
        
        # Konvertiere die Objekttypen in ein React-freundliches Format
        object_types_data = []
        for obj_type in object_type_list:
            type_data = {
                'id': str(obj_type.inst_id),  # Konvertiere zu string
                'name': str(obj_type.name),
                'category': str(obj_type.category),
                'schema': process_schema_properties(obj_type.jsonSchema),
                'fileCount': int(len(obj_type.df_refs)),  # Explizite Konvertierung zu int
                'instances': int(obj_type.instances) if hasattr(obj_type, 'instances') else 0
            }
            object_types_data.append(type_data)
        
        # Aktualisiere die React-Komponente über JavaScript
        update_script = f"window.updateObjectTypes({json.dumps(object_types_data)});"
        self.object_types_web_view.page().runJavaScript(update_script)
    
    def add_figure_to_viewer(self, figure, title, is_process_mining=True):
        """Fügt eine Matplotlib-Figur oder ein PIL-Bild dem entsprechenden Viewer mit horizontalem Scrollen hinzu."""
        target_notebook = self.pm_images_notebook if is_process_mining else self.at_images_notebook
        
        # Erstelle Scrollbereich mit beiden Scrollleisten aktiviert
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)  # Wichtig: Auf False setzen, um richtiges Scrollen zu ermöglichen
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        
        if isinstance(figure, PIL.Image.Image):
            # PIL-Bildverarbeitungscode...
            buffer = io.BytesIO()
            figure.save(buffer, format='PNG', quality=100, optimize=False)
            buffer.seek(0)
            image_data = buffer.getvalue()
            
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(image_data)
            
            # Erstelle Container-Widget und layout
            container = QWidget()
            layout = QVBoxLayout(container)
            
            label = ZoomableLabel()
            label.setPixmap(pixmap)
            layout.addWidget(label)
            
            scroll_area.setWidget(container)
            
        elif isinstance(figure, plt.Figure):
            # Verwende vorhandenen ZoomableFigureCanvas mit fester Größe
            canvas = ZoomableFigureCanvas(figure)
            
            # Setze eine größere feste Größe für die Leinwand, um Scrollen zu ermöglichen
            canvas.setFixedSize(1200, 800)  # Passen Sie diese Werte nach Bedarf an
            
            # Erstelle ein Container-Widget, um die Leinwand zu halten
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.addWidget(canvas)
            layout.setContentsMargins(0, 0, 0, 0)  # Entferne Ränder
            
            scroll_area.setWidget(container)
            
            # Setze eine vernünftige Mindestgröße für den Scrollbereich
            scroll_area.setMinimumSize(800, 600)
        
        else:
            raise ValueError(f"Unsupported figure type: {type(figure)}")
        
        target_notebook.addTab(scroll_area, title)

    def setup_process_instances_view(self):
        """Erstellt die Ansicht für Prozessinstanzen mit React"""
        self.process_instances_frame = QWidget()
        self.process_instances_layout = QVBoxLayout(self.process_instances_frame)
        self.notebook.addTab(self.process_instances_frame, "Prozessinstanzen")
        
        # Erstelle WebView für React-Komponente
        self.process_instances_web_view = QWebEngineView()
        self.process_instances_layout.addWidget(self.process_instances_web_view)
        
        # Lade HTML-Datei
        html_path = os.path.join(os.path.dirname(__file__), 'View//process_instances_display.html')
        self.process_instances_web_view.setUrl(QUrl.fromLocalFile(html_path))

    def update_process_instances_view(self, process_instances, notused):
        """Aktualisiert die Ansicht für Prozessinstanzen mit neuen Daten"""
        instances_data = {}
        for instance_id, instance in process_instances.items():
            instance_id_converted = self.convert_to_serializable(instance_id)
            instances_data[instance_id_converted] = {
                'instanceId': instance_id_converted,  # Add instanceId here
                'process_docs': [{
                    'filename': doc['filename'],
                    'dec_type': self.convert_to_serializable(doc['doc_type']),  # Split objType into dec_type
                    #'version': self.convert_to_serializable(doc['cluster']),  # Split objType into version
                    'final_timestamp': self.convert_to_serializable(doc['final_timestamp']) if doc['final_timestamp'] else None,
                    'is_partial': self.convert_to_serializable(doc['is_partial']),
                    'is_shared': self.convert_to_serializable(doc['is_shared']),
                    'partial_content': self.convert_to_serializable(doc['partial_content']) if doc.get('partial_content') else None
                } for doc in instance.process_docs],
                'variant': instance.variant,
                'variant_count': instance.variant_count,
                'files_per_cluster': {self.convert_to_serializable(cluster): count
                                      for cluster, count in instance.cluster_counts_without_shared.items()}
            }
        
        notused_data = [{
            'filename': doc['filename'],
            'dec_type': self.convert_to_serializable(doc['doc_type']),  # Split objType into dec_type
            'final_timestamp': self.convert_to_serializable(doc['final_timestamp']) if doc['final_timestamp'] else None,
            'is_partial': self.convert_to_serializable(doc['is_partial']),
            'is_shared': self.convert_to_serializable(doc['is_shared']),
            'partial_content': self.convert_to_serializable(doc['partial_content']) if doc.get('partial_content') else None
        } for doc in notused]

        # Aktualisiere die React-Komponente über JavaScript
        update_script = f"window.updateProcessInstances({json.dumps(instances_data)}, {json.dumps(notused_data)});"
        self.process_instances_web_view.page().runJavaScript(update_script)

    def setup_image_viewer(self):
        """Erstellt die Registerkarten für die Petri-Netz-Visualisierungen"""
        # Registerkarte für Process Mining Visualisierungen
        self.pm_visualization_frame = QWidget()
        self.pm_visualization_layout = QVBoxLayout(self.pm_visualization_frame)
        self.notebook.addTab(self.pm_visualization_frame, "Process Discovery Algorithmen")
        
        self.pm_images_notebook = QTabWidget()
        self.pm_visualization_layout.addWidget(self.pm_images_notebook)
        
        # Registerkarte für Aktivitätstyp-Visualisierungen
        self.at_visualization_frame = QWidget()
        self.at_visualization_layout = QVBoxLayout(self.at_visualization_frame)
        self.notebook.addTab(self.at_visualization_frame, "Zusammengesetzte Aktivitätstypen")
        
        self.at_images_notebook = QTabWidget()
        self.at_visualization_layout.addWidget(self.at_images_notebook)
        
        # Schaltflächenrahmen für Export
        button_layout = QHBoxLayout()
        self.at_visualization_layout.addLayout(button_layout)
        
        save_button = QPushButton("Aktuelle Visualisierung speichern")
        save_button.clicked.connect(self.save_current_visualization)
        button_layout.addWidget(save_button)

    def setup_enhanced_activities_view(self):
        """Erstellt die verbesserte Aktivitätsansicht mit React"""
        self.activities_frame = QWidget()
        self.activities_layout = QVBoxLayout(self.activities_frame)
        self.notebook.addTab(self.activities_frame, "Aktivitätstypen")
        
        # Erstelle WebView für React-Komponente
        self.web_view = QWebEngineView()
        self.activities_layout.addWidget(self.web_view)
        
        # Lade HTML-Datei direkt
        html_path = os.path.join(os.path.dirname(__file__), 'View//activity_display.html')
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))

        # Add button to change activity type names
        self.change_activity_names_button = QPushButton("Aktivitätstypnamen ändern")
        self.change_activity_names_button.clicked.connect(self.show_activity_type_name_dialog)
        self.activities_layout.addWidget(self.change_activity_names_button)

    def toggle_buttons_visibility(self, mode):
        is_iterative = mode == "Iterative Generierung"
        self.change_names_button.setVisible(is_iterative)
        self.score_relations_button.setVisible(is_iterative)
        self.change_activity_names_button.setVisible(is_iterative)

    def update_activities_view(self, content_based_AT, time_based_AT, figures):
        """Aktualisiert die Aktivitätsansicht mit neuen Daten"""
        for title, fig in figures.items():
            self.add_figure_to_viewer(fig, title, False)
        
        # Konvertiere die Aktivitätsdaten in ein React-freundliches Format
        content_based_data = []
        for activity in content_based_AT:
            activity_data = {
                'id': activity.inst_id,
                'name': activity.name,
                'inputTypes': list(activity.input_object_types_names),
                'outputTypes': list(activity.output_object_types_names),
                'rules': [{'type': rule[0].value, 'keys': rule[1]} for rule in activity.rules],
                'instanceCount': max(len(entries) for entries in activity.instanceList.values()) if hasattr(activity, 'instanceList') else 0

            }
            content_based_data.append(activity_data)
            
        time_based_data = []
        for activity in time_based_AT:
            name = (tuple(set(x[0] for x in activity.input_object_types_names)), tuple(set(x[0] for x in activity.output_object_types_names)))
            name = str(name).replace(",)", ")")
            activity_data = {
                'id': activity.inst_id,
                'name': name,
                'inputTypes': list(activity.input_object_types_names),
                'outputTypes': list(activity.output_object_types_names),
                'instanceCount': len(activity.instanceList) if hasattr(activity, 'instanceList') else 0
            }
            time_based_data.append(activity_data)
            
        # Aktualisiere die React-Komponente über JavaScript
        update_script = f"""
            window.updateActivities(
                {json.dumps(content_based_data)},
                {json.dumps(time_based_data)}
            );
        """
        self.web_view.page().runJavaScript(update_script)
    
    def get_files(self, folder_path):
        json_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith(('.json', '.xml', '.txt')):
                    json_files.append(os.path.join(root, file))
        return json_files         

    def export_results(self):
        if not self.input_path.text():
            QMessageBox.critical(self, "Fehler", "Bitte wählen Sie zuerst einen Ausgabeordner aus.")
            return
        
        format_type, ok = QtWidgets.QInputDialog.getItem(
            self, "Exportformat auswählen", "Exportformat:", ["html", "json"], 0, False
        )
        
        if not ok:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == "html":
            filename = os.path.join(self.input_path.text(), f"analyse_ergebnisse_{timestamp}.html")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("""
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        .section { margin-bottom: 30px; }
                        .header { background-color: #f0f0f0; padding: 10px; }
                        .content { margin-left: 20px; }
                        pre { background-color: #f8f8f8; padding: 10px; }
                    </style>
                </head>
                <body>
                """)
                
                f.write("<h2>Objekttypen</h2>")
                f.write(f"<pre>{self.object_types_text.toPlainText()}</pre>")
                
                f.write("<h2>Aktivitäten</h2>")
                f.write(f"<pre>{self.activities_text.toPlainText()}</pre>")
                
                f.write("</body></html>")
                
            webbrowser.open(filename)
            
        elif format_type == "json":
            filename = os.path.join(self.input_path.text(), f"analyse_ergebnisse_{timestamp}.json")
            data = {
                "object_types": self.object_types_text.toPlainText(),
                "activities": self.activities_text.toPlainText()
            }
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
        QMessageBox.information(self, "Export erfolgreich", 
                          f"Die Ergebnisse wurden erfolgreich als {format_type.upper()} exportiert:\n{filename}")
    
    def setup_clustering_view(self):
        """Erstellt die Registerkarte für die Cluster-Visualisierung"""
        # Erstelle Rahmen für Cluster-Visualisierung
        self.clustering_frame = QWidget()
        self.clustering_layout = QVBoxLayout(self.clustering_frame)
        self.notebook.addTab(self.clustering_frame, "Cluster-Analyse")
        
        # Erstelle Figur mit Unterplots
        self.fig = plt.Figure(figsize=(12, 6), dpi=100)
        self.fig.subplots_adjust(wspace=0.3)
        
        # Erstelle Leinwand
        self.canvas = FigureCanvas(self.fig)
        self.clustering_layout.addWidget(self.canvas)

    def update_clustering_plots(self, X, iters, sse, silhouette_scores, optimal_k, cluster_sizes):
        """Aktualisiert die Cluster-Visualisierung mit neuen Daten"""
        # Lösche die Figur
        self.fig.clear()
        
        # Erstelle Unterplots
        ax1 = self.fig.add_subplot(131)
        ax2 = self.fig.add_subplot(132)
        ax3 = self.fig.add_subplot(133)
        
        # Elbow-Methode-Plot
        ax1.plot(iters, sse, marker='o', linewidth=2, markersize=8)
        ax1.set_xlabel('Anzahl der Cluster')
        ax1.set_ylabel('SSE')
        ax1.set_title('Elbow-Methode')
        ax1.grid(True)
        
        # Silhouette-Score-Plot
        ax2.plot(iters, silhouette_scores, marker='o', linewidth=2, markersize=8)
        ax2.axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal (k={optimal_k})')
        ax2.set_xlabel('Anzahl der Cluster')
        ax2.set_ylabel('Silhouette-Score')
        ax2.set_title('Silhouette-Analyse')
        ax2.grid(True)
        ax2.legend()
        
        # Cluster-Größenverteilung
        cluster_labels = [f'C.{i}' for i in range(len(cluster_sizes))]
        bars = ax3.bar(cluster_labels, cluster_sizes)
        ax3.set_xlabel('Cluster')
        ax3.set_ylabel('Anzahl der Dateien')
        ax3.set_title('Cluster-Größenverteilung')
        
        # Füge Wertbeschriftungen oben auf den Balken hinzu
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
        
        # Passe das Layout an und aktualisiere die Leinwand
        self.fig.tight_layout()
        self.canvas.draw()

    def save_figure(self, figure, path):
        """Speichert eine Matplotlib-Figur"""
        figure.savefig(path, bbox_inches='tight', dpi=300)

    def save_current_visualization(self):
        """Speichert die aktuell angezeigte Visualisierung"""
        current_tab = self.pm_images_notebook.currentWidget() or self.at_images_notebook.currentWidget()
        if not current_tab:
            QMessageBox.warning(self, "Warnung", "Keine Registerkarte ausgewählt.")
            return
            
        # Bestimme, welches Notizbuch aktiv ist
        is_pm = current_tab in [self.pm_images_notebook.widget(i) for i in range(self.pm_images_notebook.count())]
        notebook = self.pm_images_notebook if is_pm else self.at_images_notebook
        
        tab_text = notebook.tabText(notebook.indexOf(current_tab))
        output_path, _ = QFileDialog.getSaveFileName(
            self, "Visualisierung speichern", f"{tab_text}.png", "PNG-Dateien (*.png)"
        )
        
        if output_path:
            # Hole die Leinwand aus der ausgewählten Registerkarte
            canvas = current_tab.findChild(FigureCanvas)
            canvas.figure.savefig(output_path, bbox_inches='tight', dpi=300)
            QMessageBox.information(self, "Erfolg", f"Visualisierung gespeichert als:\n{output_path}")

    def run_analysis(self):
        try:
            if not self.input_path.text():
                QMessageBox.critical(self, "Fehler", "Bitte wählen Sie einen Eingabeordner!")
                return

            # Deaktiviere die Start-Schaltfläche, um mehrere Threads zu verhindern
            self.start_button.setEnabled(False)
                
            debug_mode = self.debug_mode.isChecked()
            mode = self.mode_selection.currentText()
            
            json_files = self.get_files(self.input_path.text())
            if not json_files:
                QMessageBox.critical(self, "Fehler", "Keine JSON-Dateien im ausgewählten Ordner gefunden!")
                return
                
            self.signals.log_signal.emit(f"Analyse mit {len(json_files)} JSON-Dateien gestartet")
            
            # PreInstanceGenerator
            self.signals.progress_signal.emit(10, "Instanzen werden generiert...")
            generator = PreInstanceGenerator(debug=debug_mode, log_signal=self.signals.log_signal)
            instances = generator.generateinstances(json_files)
            self.signals.log_signal.emit("Instanzen generiert")
            
            # Dokumentenklassifizierung
            self.signals.progress_signal.emit(25, "Objektinstanzen werden klassifiziert...")
            clusterer = DocumentClassifier(1000, debug=debug_mode, log_signal=self.signals.log_signal)
            clusterer.gui = self
            updated_df = clusterer.classify_documents(instances)
            self.documents_df = updated_df  # Speichere das DataFrame zur späteren Verwendung
            self.signals.log_signal.emit("Objektinstanzen klassifiziert")
            
            # Aktualisiere die Cluster-Dateiansicht
            self.update_cluster_files_view(updated_df)

            if mode == "Iterativ":
                self.start_button.setText("Weiter")
                self.start_button.clicked.disconnect()
                self.start_button.clicked.connect(self.continue_analysis)
                return

            # Fahren Sie mit dem Rest der Analyse fort
            self.continue_analysis()

        except Exception as e:
            self.signals.log_signal.emit(f"Fehler: {str(e)}")
            QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {str(e)}")
            
        finally:
            self.signals.progress_signal.emit(0, "Bereit")
            self.start_button.setEnabled(True)

    def continue_analysis(self):
        try:
            self.start_button.setEnabled(False)
            self.start_button.setText("Generierung starten")
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.start_analysis)

            updated_df = self.documents_df

            # Prozessinstanzklassifizierung
            self.signals.progress_signal.emit(40, "Prozessinstanzen werden klassifiziert...")
            classifier = ProcessInstanceClassifier(updated_df, debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
            process_instances, process_pairs, notused = classifier.classify_documents()
            self.signals.log_signal.emit("Prozessinstanzen klassifiziert")
            
            # Aktualisiere die Ansicht für Prozessinstanzen
            self.signals.update_process_instances_signal.emit(process_instances, notused)
            
            # Objekttyp-Generierung
            self.signals.progress_signal.emit(55, "Objekttypen werden generiert...")
            objecttypegenerator = ObjectTypeGenerator(debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
            object_type_list = objecttypegenerator.generateObjectTypes(updated_df)
            self.signals.log_signal.emit("Objekttypen generiert")
            
            # Aktualisiere die Ansicht für Objekttypen
            self.signals.update_object_types_signal.emit(object_type_list)
            
            # Objektbeziehungstyp-Generierung
            self.signals.progress_signal.emit(70, "Objektbeziehungstypen werden generiert...")
            objectrelationgenerator = ObjectRelationGenerator(
                debug=self.debug_mode.isChecked(),
                same_value_threshold=self.default_params['same_value_threshold'],
                significant_instance_threshold=self.default_params['significant_instance_threshold'],
                same_common_value_threshold=self.default_params['same_common_value_threshold'],
                rule_significance_threshold=self.default_params['rule_significance_threshold'],
                log_signal=self.signals.log_signal
            )
            content_relations, time_relations = objectrelationgenerator.generateObjectRelations(
                updated_df, process_instances, process_pairs)
            self.signals.log_signal.emit("Objektbeziehungstypen generiert")

            # Nach der Generierung von Beziehungen
            self.signals.update_object_relations_signal.emit(content_relations, time_relations) 
            
            # Aktivitätstyp-Generierung
            self.signals.progress_signal.emit(85, "Aktivitäten werden generiert...")
            activitygenerator = ActivityGenerator(
                updated_df, 
                debug=self.debug_mode.isChecked(),
                early_position_bonus=self.default_params['early_position_bonus'],
                late_position_penalty=self.default_params['late_position_penalty'],
                reference_weight=self.default_params['reference_weight'],
                reference_position_factor=self.default_params['reference_position_factor'],
                sequence_weight=self.default_params['sequence_weight'],
                attribute_weight=self.default_params['attribute_weight'],
                temporal_weight=self.default_params['temporal_weight'],
                variant_weight=self.default_params['variant_weight'],
                parallel_object_penalty=self.default_params['parallel_object_penalty'],
                each_attribute_by_object=self.default_params['each_attribute_by_object'],
                min_score=self.default_params.get('min_score', 2.0),
                loop_weight=self.default_params.get('loop_weight', -1.0),
                log_signal=self.signals.log_signal
            )
            time_based_AT, figures = activitygenerator.generate_activities(time_relations, process_instances)
            content_based_AT = activitygenerator.generate_content_activities(content_relations, process_instances)
            # Aktualisiere die Ansicht für Aktivitäten
            self.signals.update_activities_signal.emit(content_based_AT, time_based_AT, figures)
            self.signals.log_signal.emit("Aktivitäten generiert")
            
            # Petri-Netz-Generierung
            self.signals.progress_signal.emit(95, "Petri-Netze werden generiert...")
            petri_net_generator = EventlogPNGenerator(
                debug=self.debug_mode.isChecked(), 
                database_visualization=self.default_params['database_visualization'],
                log_signal=self.signals.log_signal
            )
            process_mining_figures, activity_based_figures, net = petri_net_generator.generate_eventlog_petri_net(
                updated_df, time_based_AT, content_based_AT)

            # Füge Process Mining Visualisierungen hinzu
            for title, fig in process_mining_figures.items():
                self.signals.add_figure_signal.emit(fig, title, True)

            # Füge Aktivitätstyp-Visualisierungen hinzu
            for title, fig in activity_based_figures.items():
                self.signals.add_figure_signal.emit(fig, title, False)
            self.signals.log_signal.emit("Petri-Netze generiert")
            
            # Regel-Extraktion
            self.signals.progress_signal.emit(90, "Regeln werden extrahiert...")
            rule_extractor = DecisionPointAnalyzer(debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
            rules, figures = rule_extractor.analyze_decision_points(
                net, updated_df, content_based_AT)
            self.signals.update_rule_extractor_signal.emit(rules, figures)

            self.signals.log_signal.emit("Regeln extrahiert")  

            self.signals.progress_signal.emit(100, "Generierung abgeschlossen")
            self.signals.log_signal.emit("Generierung erfolgreich abgeschlossen")
            
        except Exception as e:
            self.signals.log_signal.emit(f"Fehler: {str(e)}")
            QMessageBox.critical(self, "Fehler", f"Ein Fehler ist aufgetreten: {str(e)}")
            
        finally:
            self.signals.progress_signal.emit(0, "Bereit")
            self.start_button.setEnabled(True)

    def start_analysis(self):
        self.current_step = 0
        self.start_button.setEnabled(False)
        self.continue_button.setEnabled(False)
        if self.mode_selection.currentText() == "Iterative Generierung":
            self.continue_button.setEnabled(True)
            self.next_step()
        else:
            thread = threading.Thread(target=self.run_analysis)
            thread.daemon = True
            thread.start()

    def next_step(self):
        if self.current_step < len(self.steps):
            if self.show_parameter_adjustment_dialog():
                self.steps[self.current_step]()
                self.current_step += 1
                if self.current_step < len(self.steps):
                    self.notebook.setCurrentIndex(self.current_step)
                if self.current_step >= len(self.steps):
                    self.continue_button.setEnabled(False)
                    self.start_button.setEnabled(True)

    def show_parameter_adjustment_dialog(self):
        step_params = self.get_step_params()
        if step_params:
            dialog = ParameterAdjustmentDialog(step_params, self)
            if dialog.exec_() == QDialog.Accepted:
                self.default_params.update(dialog.get_params())
                return True
            return False
        return True

    def get_step_params(self):
        translations = {
            'max_features': 'Maximale Anzahl von Merkmalen',
            'threshold': 'Korrelations-Schwellwert',
            'same_value_threshold': 'Prozessinstanz-Relevanz',
            'significant_instance_threshold': 'Objektinstanz-Relevanz',
            'same_common_value_threshold': 'Prozessinstanz-Relevanz (häufig gleiche Werte)',
            'rule_significance_threshold': 'Attributs-Relevanz',
            'early_position_bonus': 'Frühe Position',
            'late_position_penalty': 'Späte Position',
            'reference_weight': 'Prozessinstanzunabhängige Objekte',
            'reference_position_factor': 'Positionsfaktor',
            'sequence_weight': 'Häufigkeit',
            'attribute_weight': 'Attributsrelevanz',
            'temporal_weight': 'Zeitgewichtung',
            'variant_weight': 'Variantengewicht',
            'parallel_object_penalty': 'Parallele Strafe',
            'each_attribute_by_object': 'Jedes Attribut pro Objekt',
            'database_visualization': 'Datenbankvisualisierung',
            'min_score': 'Mindestscore',
            'loop_weight': 'Schleifengewicht',
            'relevant_attributes': 'Relevante Attribute'
        }

        if self.current_step == 1:  # DocumentClassifier
            return {
                translations['max_features']: self.default_params.get('max_features', 1000),
                translations['threshold']: self.default_params.get('threshold', 0.8)
            }
        elif self.current_step == 2:  # ProcessInstanceClassifier
            return {
                translations['threshold']: self.default_params.get('threshold', 0.8)
            }
        elif self.current_step == 4:  # ObjectRelationGenerator
            return {
                translations['same_value_threshold']: self.default_params['same_value_threshold'],
                translations['significant_instance_threshold']: self.default_params['significant_instance_threshold'],
                translations['same_common_value_threshold']: self.default_params['same_common_value_threshold'],
                translations['rule_significance_threshold']: self.default_params['rule_significance_threshold']
            }
        elif self.current_step == 5:  # ActivityGenerator
            return {
                translations['early_position_bonus']: self.default_params['early_position_bonus'],
                translations['late_position_penalty']: self.default_params['late_position_penalty'],
                translations['reference_weight']: self.default_params['reference_weight'],
                translations['reference_position_factor']: self.default_params['reference_position_factor'],
                translations['sequence_weight']: self.default_params['sequence_weight'],
                translations['attribute_weight']: self.default_params['attribute_weight'],
                translations['temporal_weight']: self.default_params['temporal_weight'],
                translations['variant_weight']: self.default_params['variant_weight'],
                translations['parallel_object_penalty']: self.default_params['parallel_object_penalty'],
                translations['each_attribute_by_object']: self.default_params['each_attribute_by_object'],
                translations['min_score']: self.default_params.get('min_score', 2.0),
                translations['loop_weight']: self.default_params.get('loop_weight', -1.0)
            }
        elif self.current_step == 6:  # EventlogPNGenerator
            return {
                translations['database_visualization']: self.default_params['database_visualization']
            }
        elif self.current_step == 7:  # DecisionPointAnalyzer
            return {
                translations['relevant_attributes']: self.default_params.get('relevant_attributes', [])
            }
        return {}

    def run_pre_instance_generator(self):
        # ...existing code for PreInstanceGenerator...
        self.signals.progress_signal.emit(10, "Instanzen werden generiert...")
        generator = PreInstanceGenerator(debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
        json_files = self.get_files(self.input_path.text())
        if not json_files:
            QMessageBox.critical(self, "Fehler", "Keine JSON-Dateien im ausgewählten Ordner gefunden!")
            return
        self.instances = generator.generateinstances(json_files)
        self.signals.log_signal.emit("Instanzen generiert")
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(20, "Bereit für den nächsten Schritt")

    def run_document_classifier(self):
        # ...existing code for DocumentClassifier...
        self.signals.progress_signal.emit(25, "Objektinstanzen werden klassifiziert...")
        clusterer = DocumentClassifier(
            debug=self.debug_mode.isChecked(),
            max_features=int(self.default_params.get('max_features', 1000)),
            similarity_threshold=self.default_params.get('threshold', 0.8),
            log_signal=self.signals.log_signal
        )
        clusterer.gui = self
        self.updated_df = clusterer.classify_documents(self.instances)
        self.documents_df = self.updated_df  # Speichere das DataFrame zur späteren Verwendung
        self.signals.log_signal.emit("Objektinstanzen klassifiziert")
        self.update_cluster_files_view(self.updated_df)
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(35, "Bereit für den nächsten Schritt")

    def run_process_instance_classifier(self):
        # ...existing code for ProcessInstanceClassifier...
        self.signals.progress_signal.emit(40, "Prozessinstanzen werden klassifiziert...")
        classifier = ProcessInstanceClassifier(
            self.updated_df, 
            key_frequency=self.default_params.get('threshold', 0.8), 
            debug=self.debug_mode.isChecked(),
            log_signal=self.signals.log_signal
        )
        self.process_instances, self.process_pairs, self.notused = classifier.classify_documents()
        self.signals.log_signal.emit("Prozessinstanzen klassifiziert")
        self.signals.update_process_instances_signal.emit(self.process_instances, self.notused)
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(50, "Bereit für den nächsten Schritt")

    def run_object_type_generator(self):
        # ...existing code for ObjectTypeGenerator...
        self.signals.progress_signal.emit(55, "Objekttypen werden generiert...")
        objecttypegenerator = ObjectTypeGenerator(debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
        self.object_type_list = objecttypegenerator.generateObjectTypes(self.updated_df)
        self.signals.log_signal.emit("Objekttypen generiert")
        self.signals.update_object_types_signal.emit(self.object_type_list)
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(65, "Bereit für den nächsten Schritt")

    def run_object_relation_generator(self):
        # ...existing code for ObjectRelationGenerator...
        self.signals.progress_signal.emit(70, "Objektbeziehungstypen werden generiert...")
        objectrelationgenerator = ObjectRelationGenerator(
            debug=self.debug_mode.isChecked(),
            same_value_threshold=self.default_params['same_value_threshold'],
            significant_instance_threshold=self.default_params['significant_instance_threshold'],
            same_common_value_threshold=self.default_params['same_common_value_threshold'],
            rule_significance_threshold=self.default_params['rule_significance_threshold'],
            log_signal=self.signals.log_signal
        )
        self.content_relations, self.time_relations = objectrelationgenerator.generateObjectRelations(
            self.updated_df, self.process_instances, self.process_pairs)
        self.signals.log_signal.emit("Objektbeziehungstypen generiert")
        self.signals.update_object_relations_signal.emit(self.content_relations, self.time_relations)
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(75, "Bereit für den nächsten Schritt")

    def run_activity_generator(self):
        # ...existing code for ActivityGenerator...
        self.signals.progress_signal.emit(85, "Aktivitäten werden generiert...")
        activitygenerator = ActivityGenerator(
            self.updated_df, 
            debug=self.debug_mode.isChecked(),
            early_position_bonus=self.default_params['early_position_bonus'],
            late_position_penalty=self.default_params['late_position_penalty'],
            reference_weight=self.default_params['reference_weight'],
            reference_position_factor=self.default_params['reference_position_factor'],
            sequence_weight=self.default_params['sequence_weight'],
            attribute_weight=self.default_params['attribute_weight'],
            temporal_weight=self.default_params['temporal_weight'],
            variant_weight=self.default_params['variant_weight'],
            parallel_object_penalty=self.default_params['parallel_object_penalty'],
            each_attribute_by_object=self.default_params['each_attribute_by_object'],
            min_score=self.default_params.get('min_score', 2.0),
            loop_weight=self.default_params.get('loop_weight', -1.0),
            log_signal=self.signals.log_signal
        )
        self.time_based_AT, self.figures = activitygenerator.generate_activities(self.time_relations, self.process_instances)
        self.content_based_AT = activitygenerator.generate_content_activities(self.content_relations, self.process_instances)
        self.signals.update_activities_signal.emit(self.content_based_AT, self.time_based_AT, self.figures)
        self.signals.log_signal.emit("Aktivitäten generiert")
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(90, "Bereit für den nächsten Schritt")

    def run_petri_net_generator(self):
        # ...existing code for EventlogPNGenerator...
        self.signals.progress_signal.emit(95, "Petri-Netze werden generiert...")
        petri_net_generator = EventlogPNGenerator(
            debug=self.debug_mode.isChecked(), 
            database_visualization=self.default_params['database_visualization'],
            log_signal=self.signals.log_signal
        )
        self.process_mining_figures, self.activity_based_figures, self.net = petri_net_generator.generate_eventlog_petri_net(
            self.updated_df, self.time_based_AT, self.content_based_AT)
        for title, fig in self.process_mining_figures.items():
            self.signals.add_figure_signal.emit(fig, title, True)
        for title, fig in self.activity_based_figures.items():
            self.signals.add_figure_signal.emit(fig, title, False)
        self.signals.log_signal.emit("Petri-Netze generiert")
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(95, "Bereit für den nächsten Schritt")

    def run_rule_extractor(self):
        # ...existing code for DecisionPointAnalyzer...
        self.signals.progress_signal.emit(90, "Regeln werden extrahiert...")
        rule_extractor = DecisionPointAnalyzer(debug=self.debug_mode.isChecked(), log_signal=self.signals.log_signal)
        self.rules, self.figures = rule_extractor.analyze_decision_points(
            self.net, self.updated_df, self.content_based_AT)
        self.signals.update_rule_extractor_signal.emit(self.rules, self.figures)
        self.signals.log_signal.emit("Regeln extrahiert")
        if self.mode_selection.currentText() == "Iterativ":
            self.signals.progress_signal.emit(100, "Generierung abgeschlossen")
            self.signals.log_signal.emit("Generierung erfolgreich abgeschlossen")
            self.continue_button.setEnabled(False)
            self.start_button.setEnabled(True)

    def setup_continue_button(self):
        """Setup the continue button for iterative mode"""
        self.continue_button = QPushButton("Weiter")
        self.continue_button.clicked.connect(self.next_step)
        self.continue_button.setEnabled(False)
        self.layout.addWidget(self.continue_button)

    def run(self):
        self.show()

    def setup_rule_extractor_view(self):
        """Erstellt die Registerkarte für die Regel-Extraktor-Ansicht mit Text und Figuren"""
        self.rule_extractor_frame = QWidget()
        self.rule_extractor_layout = QVBoxLayout(self.rule_extractor_frame)
        self.notebook.addTab(self.rule_extractor_frame, "Regel-Extraktor")

        # Erstelle geteiltes Layout für Text und Figuren
        splitter = QSplitter(QtCore.Qt.Vertical)
        self.rule_extractor_layout.addWidget(splitter)

        # Textbereich für Regeln
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        self.rule_extractor_text = QTextEdit()
        self.rule_extractor_text.setReadOnly(True)
        text_layout.addWidget(self.rule_extractor_text)
        splitter.addWidget(text_widget)

        # Scrollbereich für Figuren
        scroll_widget = QWidget()
        self.figures_layout = QVBoxLayout(scroll_widget)
        scroll = QScrollArea()
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        splitter.addWidget(scroll)

        # Setze anfängliche Splittergrößen
        splitter.setSizes([300, 400])

    def update_rule_extractor_view(self, rules, figures):
        """Aktualisiert die Regel-Extraktor-Ansicht mit Regeln und Visualisierungen"""
        # Lösche vorhandenen Inhalt
        self.rule_extractor_text.clear()
        
        # Lösche vorhandene Figuren
        for i in reversed(range(self.figures_layout.count())): 
            widget = self.figures_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        # Aktualisiere den Textinhalt
        for dp_name, rule_info in rules.items():
            self.rule_extractor_text.append(f"\n{'='*80}\n")
            self.rule_extractor_text.append(f"Entscheidungspunkt: {dp_name}\n")
            self.rule_extractor_text.append(f"{'='*80}\n\n")
            
            if 'class_distribution' in rule_info:
                self.rule_extractor_text.append("Pfadverteilung:\n")
                for path, count in rule_info['class_distribution'].items():
                    self.rule_extractor_text.append(f"  {path}: {count} Instanzen\n")
                self.rule_extractor_text.append("\n")
            
            if 'sample_size' in rule_info:
                self.rule_extractor_text.append(f"Gesamtproben: {rule_info['sample_size']}\n\n")
            
            self.rule_extractor_text.append("Merkmalsbedeutung:\n")
            for rule, importance in rule_info['importance'].items():
                self.rule_extractor_text.append(f"  └─ {rule}: {importance:.4f}\n")
            self.rule_extractor_text.append("\n")

        # Füge Figuren hinzu
        for name, fig in figures.items():
            # Erstelle Rahmen für Figur
            frame = QFrame()
            frame.setFrameStyle(QFrame.Panel | QFrame.Raised)
            frame.setLineWidth(2)
            layout = QVBoxLayout(frame)
            
            # Füge Titel hinzu
            title = QLabel(name)
            title.setAlignment(QtCore.Qt.AlignCenter)
            title.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px;")
            layout.addWidget(title)
            
            # Konvertiere Matplotlib-Figur in Qt-Widget
            canvas = FigureCanvas(fig)
            canvas.setMinimumHeight(400)  # Setze Mindesthöhe für Sichtbarkeit
            layout.addWidget(canvas)
            
            # Füge Navigationsleiste hinzu
            toolbar = NavigationToolbar(canvas, frame)
            layout.addWidget(toolbar)
            
            self.figures_layout.addWidget(frame)

        # Füge am Ende Stretch hinzu, um unerwünschte Erweiterung zu verhindern
        self.figures_layout.addStretch()

    def setup_cluster_files_view(self):
        """Erstellt die Registerkarte zum Anzeigen von Clustern und ihren zugewiesenen Dateien"""
        self.cluster_files_frame = QWidget()
        self.cluster_files_layout = QVBoxLayout(self.cluster_files_frame)
        self.notebook.addTab(self.cluster_files_frame, "Cluster-Dateien")

        self.cluster_files_list = QListWidget()
        self.cluster_files_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cluster_files_layout.addWidget(self.cluster_files_list)

        self.reassign_button = QPushButton("Ausgewählte Dateien neu zuweisen")
        self.reassign_button.clicked.connect(self.reassign_files_to_cluster)
        self.cluster_files_layout.addWidget(self.reassign_button)

        self.cluster_input = QLineEdit()
        self.cluster_input.setPlaceholderText("Neue Cluster-Nummer eingeben")
        self.cluster_files_layout.addWidget(self.cluster_input)

        self.independent_checkbox = QCheckBox("Als prozessunabhängig markieren")
        self.cluster_files_layout.addWidget(self.independent_checkbox)

        self.mark_independent_button = QPushButton("Ausgewählte Cluster als unabhängig markieren")
        self.mark_independent_button.clicked.connect(self.mark_clusters_as_independent)
        self.cluster_files_layout.addWidget(self.mark_independent_button)

    def update_cluster_files_view(self, documents_df):
        """Aktualisiert die Cluster-Dateiansicht mit neuen Daten"""
        self.cluster_files_list.clear()
        grouped = documents_df.groupby('cluster')
        for cluster, group in grouped:
            cluster_item = QListWidgetItem(f"Cluster {cluster} (Bezeichnung: {group['doc_type'].iloc[0]})")
            cluster_item.setFlags(cluster_item.flags() | Qt.ItemIsUserCheckable)
            cluster_item.setCheckState(Qt.Unchecked)
            # Überprüfen, ob der Cluster unabhängig ist
            if group['process_instance_independent'].any():
                cluster_item.setText(f"Cluster {cluster} (Prozessinstanznabhängig, Bezeichnung: {group['doc_type'].iloc[0]})")
            self.cluster_files_list.addItem(cluster_item)
            for index, row in group.iterrows():
                item = QListWidgetItem(f"  {row['filename']}")
                item.setData(Qt.UserRole, index)
                self.cluster_files_list.addItem(item)

    def reassign_files_to_cluster(self):
        """Weist ausgewählte Dateien einem neuen Cluster zu"""
        selected_items = self.cluster_files_list.selectedItems()
        new_cluster = self.cluster_input.text()
        if not new_cluster.isdigit():
            QMessageBox.warning(self, "Ungültige Eingabe", "Bitte geben Sie eine gültige Cluster-Nummer ein.")
            return

        new_cluster = int(new_cluster)
        mark_independent = self.independent_checkbox.isChecked()

        for item in selected_items:
            index = item.data(Qt.UserRole)
            if index is not None:  # Überspringe Cluster-Header
                self.documents_df.at[index, 'cluster'] = new_cluster
                self.documents_df.at[index, 'process_instance_independent'] = mark_independent
                item.setText(f"  {self.documents_df.at[index, 'filename']}")

        # Aktualisiere alle anderen Cluster, um nicht prozessunabhängig zu sein
        if mark_independent:
            other_indices = self.documents_df.index.difference([item.data(Qt.UserRole) for item in selected_items if item.data(Qt.UserRole) is not None])
            self.documents_df.loc[other_indices, 'process_instance_independent'] = False

        # Aktualisiere die Cluster-Ansicht
        self.update_cluster_files_view(self.documents_df)

        QMessageBox.information(self, "Erfolg", "Ausgewählte Dateien wurden dem neuen Cluster zugewiesen.")

    def mark_clusters_as_independent(self):
        """Markiert ausgewählte Cluster als prozessunabhängig"""
        for i in range(self.cluster_files_list.count()):
            item = self.cluster_files_list.item(i)
            if item.checkState() == Qt.Checked and item.text().startswith("Cluster"):
                cluster_number = int(item.text().split()[1])
                self.documents_df.loc[self.documents_df['cluster'] == cluster_number, 'process_instance_independent'] = True
            elif item.text().startswith("Cluster"):
                cluster_number = int(item.text().split()[1])
                self.documents_df.loc[self.documents_df['cluster'] == cluster_number, 'process_instance_independent'] = False
        
        # Aktualisiere die Cluster-Ansicht
        self.update_cluster_files_view(self.documents_df)

        QMessageBox.information(self, "Erfolg", "Ausgewählte Cluster wurden als unabhängig markiert.")

    def show_object_type_name_dialog(self):
        object_types = self.documents_df['doc_type'].unique()
        dialog = ObjectTypeNameDialog(object_types, self)
        dialog.setFixedSize(400, 300)  # Set fixed size for the dialog
        if dialog.exec_() == QDialog.Accepted:
            new_names = dialog.get_new_names()
            self.update_object_type_names(new_names)

    def update_object_type_names(self, new_names):
        self.documents_df['doc_type'] = self.documents_df['doc_type'].map(new_names)
        self.update_object_types_view(self.object_type_list)

    def show_object_relation_score_dialog(self):
        object_relations = [str(relation.name) for relations in self.content_relations.values() for key, relation in relations if key == RealtationType.CONTENT_BASED_RELATION]
        dialog = ObjectRelationScoreDialog(object_relations, self)
        dialog.setFixedSize(400, 300)  # Set fixed size for the dialog
        if dialog.exec_() == QDialog.Accepted:
            scores = dialog.get_scores()
            self.update_object_relation_scores(scores)

    def update_object_relation_scores(self, scores):
        for relations in self.content_relations.values():
            for relation_type, relation in relations:
                if relation.name in scores and relation_type == RealtationType.CONTENT_BASED_RELATION:
                    relation.score = 5.0 if scores[relation.name] else 0.0
        self.update_object_relations_view(self.content_relations, self.time_relations)

    def show_activity_type_name_dialog(self):
        activity_types = [activity.name for activity in self.content_based_AT]
        dialog = ActivityTypeNameDialog(activity_types, self)
        dialog.setFixedSize(400, 300)  # Set fixed size for the dialog
        if dialog.exec_() == QDialog.Accepted:
            new_names = dialog.get_new_names()
            self.update_activity_type_names(new_names)

    def update_activity_type_names(self, new_names):
        for activity in self.content_based_AT:
            if activity.name in new_names:
                activity.name = new_names[activity.name]
        self.update_activities_view(self.content_based_AT, self.time_based_AT, self.figures)

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = ProcessAnalyzerGUI()
    window.run()
    sys.exit(app.exec_())
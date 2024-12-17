import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QSlider, QComboBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer
import numpy as np

class SynthGUI(QMainWindow):
    def __init__(self, synth_core):
        super().__init__()
        self.synth_core = synth_core
        self.setWindowTitle('MIDI Synthesizer')
        self.setGeometry(100, 100, 800, 600)
        
        # Register callback for parameter updates
        self.synth_core.param_callbacks.append(self.update_gui)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Create parameter sections
        self.create_oscillator_section(layout)
        self.create_filter_section(layout)
        self.create_envelope_section(layout)
        self.create_effects_section(layout)
        
        # Create voice activity display
        self.create_voice_display(layout)
        
        # Update timer for voice activity
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_voice_display)
        self.update_timer.start(50)  # Update every 50ms
        
    def create_oscillator_section(self, parent_layout):
        group = QGroupBox("Oscillator")
        layout = QVBoxLayout()
        
        # Waveform selector
        wave_layout = QHBoxLayout()
        wave_layout.addWidget(QLabel("Waveform:"))
        self.waveform_combo = QComboBox()
        self.waveform_combo.addItems(['sine', 'square', 'saw', 'triangle'])
        self.waveform_combo.currentTextChanged.connect(
            lambda x: self.param_changed('waveform', x))
        wave_layout.addWidget(self.waveform_combo)
        layout.addLayout(wave_layout)
        
        # Detune slider
        self.add_slider(layout, "Detune", -100, 100, 0,
                       lambda x: self.param_changed('detune', x/100))
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_filter_section(self, parent_layout):
        group = QGroupBox("Filter")
        layout = QVBoxLayout()
        
        # Cutoff and resonance
        self.add_slider(layout, "Cutoff", 0, 100, 100,
                       lambda x: self.param_changed('filter_cutoff', x/100))
        self.add_slider(layout, "Resonance", 0, 100, 0,
                       lambda x: self.param_changed('filter_resonance', x/100))
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_envelope_section(self, parent_layout):
        group = QGroupBox("Envelope")
        layout = QVBoxLayout()
        
        # ADSR controls
        self.add_slider(layout, "Attack", 0, 100, 1,
                       lambda x: self.param_changed('amp_attack', x/100))
        self.add_slider(layout, "Decay", 0, 100, 10,
                       lambda x: self.param_changed('amp_decay', x/100))
        self.add_slider(layout, "Sustain", 0, 100, 70,
                       lambda x: self.param_changed('amp_sustain', x/100))
        self.add_slider(layout, "Release", 0, 100, 20,
                       lambda x: self.param_changed('amp_release', x/100))
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_effects_section(self, parent_layout):
        group = QGroupBox("Effects")
        layout = QVBoxLayout()
        
        # LFO controls
        self.add_slider(layout, "LFO Rate", 0, 100, 0,
                       lambda x: self.param_changed('lfo_rate', x/100))
        self.add_slider(layout, "LFO Amount", 0, 100, 0,
                       lambda x: self.param_changed('lfo_amount', x/100))
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def create_voice_display(self, parent_layout):
        self.voice_display = QWidget()
        self.voice_display.setMinimumHeight(100)
        self.voice_display.setStyleSheet("background-color: black;")
        parent_layout.addWidget(self.voice_display)
        
    def add_slider(self, layout, name, min_val, max_val, default, callback):
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel(f"{name}:"))
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.valueChanged.connect(callback)
        slider_layout.addWidget(slider)
        layout.addLayout(slider_layout)
        
    def param_changed(self, param, value):
        self.synth_core.voice_params[param] = value
        
    def update_gui(self, param, value):
        # Update GUI elements when parameters change via MIDI
        pass
        
    def update_voice_display(self):
        # Update voice activity visualization
        active_voices = len(self.synth_core.voices)
        # TODO: Add visualization of active voices
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = SynthGUI(None)  # For testing
    gui.show()
    sys.exit(app.exec_())

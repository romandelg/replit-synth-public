import sys
import numpy as np
from synth_core import SAMPLE_RATE
import pyqtgraph as pg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QSlider, QComboBox, QGroupBox,
                           QGridLayout)
from PyQt5.QtCore import Qt, QTimer
import numpy as np

class SynthGUI(QMainWindow):
    def __init__(self, synth_core):
        super().__init__()
        self.synth_core = synth_core
        self.setWindowTitle('MIDI Synthesizer')
        self.setGeometry(100, 100, 1200, 800)
        
        # Configure for headless/offscreen rendering
        self.setAttribute(Qt.WA_DontShowOnScreen, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create horizontal layout for left panel and visualization
        main_layout = QHBoxLayout(main_widget)
        
        # Register callback for parameter updates
        if hasattr(self.synth_core, 'param_callbacks'):
            self.synth_core.param_callbacks.append(self.update_gui)
        
        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create parameter sections
        self.create_oscillator_section(left_layout)
        self.create_filter_section(left_layout)
        self.create_envelope_section(left_layout)
        self.create_effects_section(left_layout)
        
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel for visualizations
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create waveform and spectrum displays
        self.create_visualization_section(right_layout)
        
        # Create voice activity display
        self.create_voice_display(right_layout)
        
        main_layout.addWidget(right_panel, stretch=2)
        
        # Update timer for visualizations
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_displays)
        self.update_timer.start(30)  # ~30fps updates
        
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
        
    def create_visualization_section(self, parent_layout):
        from pyqtgraph import PlotWidget, mkPen
        
        # Waveform display
        group = QGroupBox("Waveform")
        layout = QVBoxLayout()
        
        self.waveform_plot = PlotWidget()
        self.waveform_plot.setBackground('black')
        self.waveform_plot.showGrid(True, True)
        self.waveform_curve = self.waveform_plot.plot(pen=mkPen('g', width=2))
        layout.addWidget(self.waveform_plot)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
        # Spectrum analyzer
        group = QGroupBox("Spectrum")
        layout = QVBoxLayout()
        
        self.spectrum_plot = PlotWidget()
        self.spectrum_plot.setBackground('black')
        self.spectrum_plot.showGrid(True, True)
        self.spectrum_curve = self.spectrum_plot.plot(pen=mkPen('y', width=2))
        layout.addWidget(self.spectrum_plot)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_voice_display(self, parent_layout):
        group = QGroupBox("Active Voices")
        layout = QVBoxLayout()
        
        self.voice_grid = QWidget()
        self.voice_grid_layout = QGridLayout(self.voice_grid)
        
        # Create voice indicators (16 maximum voices)
        self.voice_indicators = []
        for i in range(16):
            indicator = QLabel()
            indicator.setFixedSize(30, 30)
            indicator.setStyleSheet("background-color: #333; border-radius: 15px;")
            self.voice_indicators.append(indicator)
            self.voice_grid_layout.addWidget(indicator, i // 8, i % 8)
            
        layout.addWidget(self.voice_grid)
        group.setLayout(layout)
        parent_layout.addWidget(group)
        
    def add_slider(self, layout, name, min_val, max_val, default, callback):
        slider_layout = QHBoxLayout()
        
        # Add label with current value
        label = QLabel(f"{name}:")
        slider_layout.addWidget(label)
        
        # Create slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        
        # Add value label
        value_label = QLabel(str(default))
        value_label.setMinimumWidth(40)
        
        # Update value label when slider changes
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        slider.valueChanged.connect(callback)
        
        slider_layout.addWidget(slider)
        slider_layout.addWidget(value_label)
        layout.addLayout(slider_layout)
        
    def param_changed(self, param, value):
        self.synth_core.voice_params[param] = value
        
    def update_gui(self, param, value):
        # Update GUI elements when parameters change via MIDI
        pass
        
    def update_displays(self):
        try:
            # Update waveform display
            if hasattr(self.synth_core, 'audio_buffer'):
                # Get the latest audio data safely
                try:
                    buffer_data = list(self.synth_core.audio_buffer)[-1024:] if len(self.synth_core.audio_buffer) > 0 else []
                    if buffer_data:
                        data = np.array(buffer_data)
                        self.waveform_curve.setData(y=data)
                        
                        # Calculate and update spectrum
                        if len(data) >= 1024:
                            window = np.hanning(len(data))
                            windowed_data = data * window
                            spectrum = np.abs(np.fft.rfft(windowed_data))
                            freqs = np.fft.rfftfreq(len(data), 1.0 / SAMPLE_RATE)
                            # Convert to dB with proper limiting
                            db_spectrum = 20 * np.log10(np.maximum(spectrum[1:], 1e-10))
                            self.spectrum_curve.setData(x=freqs[1:], y=db_spectrum)
                    else:
                        # Clear plots if no data
                        self.waveform_curve.setData(y=np.zeros(1024))
                        self.spectrum_curve.setData(x=np.zeros(512), y=np.zeros(512))
                except Exception as e:
                    print(f"Error updating waveform/spectrum: {e}")
            
            # Update voice indicators
            try:
                if hasattr(self.synth_core, 'voices'):
                    active_voices = list(self.synth_core.voices.keys())
                else:
                    active_voices = list(self.synth_core.active_notes.keys())
                    
                for i, indicator in enumerate(self.voice_indicators):
                    if i < len(active_voices):
                        note = active_voices[i]
                        # Use either velocity from voices or default to 1.0
                        if hasattr(self.synth_core, 'voices'):
                            velocity = getattr(self.synth_core.voices[note], 'velocity', 1.0)
                        else:
                            velocity = 1.0
                        color = int(velocity * 255)
                        indicator.setStyleSheet(
                            f"background-color: rgb(0, {color}, 0); border-radius: 15px;"
                        )
                    else:
                        indicator.setStyleSheet(
                            "background-color: #333; border-radius: 15px;"
                        )
            except Exception as e:
                print(f"Error updating voice indicators: {e}")
                
        except Exception as e:
            print(f"Error in update_displays: {e}")
            # Ensure plots are cleared in case of error
            self.waveform_curve.setData(y=np.zeros(1024))
            self.spectrum_curve.setData(x=np.zeros(512), y=np.zeros(512))
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = SynthGUI(None)  # For testing
    gui.show()
    sys.exit(app.exec_())

import pyaudio
import threading
import atexit
import numpy as np
import matplotlib.pyplot as plt
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QLabel, QVBoxLayout, QDial, QSizePolicy)
import PyQt5
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar

###### Live Mic Recording Class
class MicRec(object):
    def __init__(self, rate=4000, chunksize=1024):
        self.rate = rate
        self.chunksize = chunksize
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunksize,
                                  stream_callback=self.new_frame)
        self.lock = threading.Lock()
        self.stop = False
        self.frames = []
        atexit.register(self.close)

    def new_frame(self, data, frame_count, time_info, status):
        data = np.fromstring(data, 'int16')
        with self.lock:
            self.frames.append(data)
            if self.stop:
                return None, pyaudio.paComplete
        return None, pyaudio.paContinue

    def get_frames(self):
        with self.lock:
            frames = self.frames
            self.frames = []
            return frames

    def start(self):
        self.stream.start_stream()

    def close(self):
        with self.lock:
            self.stop = True
        self.stream.close()
        self.p.terminate()


class MplFigure(object):
    def __init__(self, parent):
        self.figure = plt.figure(facecolor='grey')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, parent)
        self.canvas.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        self.canvas.updateGeometry()



class LiveSpectrum(QWidget):

    def __init__(self):
        super().__init__()
        self.title = 'Live Spectrum Analyser'
        # customize the UI
        self.initUI()
        # init class data
        self.initData()

        # connect slots
        self.connectSlots()

        # init MPL widget
        self.initMplWidget()

    def initUI(self):

        # Frequency Domain Gain Dial
        Freq_Gain = QHBoxLayout()
        dial_FreqLabel = QLabel('Spectrum Gain')
        dial_Freq = QDial()
        dial_Freq.setMinimum(0)
        dial_Freq.setMaximum(100)
        dial_Freq.setValue(40)
        dial_Freq.setNotchesVisible(True)
        dial_Freq.notchSize = 5
        dial_Freq.valueChanged.connect(dial_Freq.sliderMoved)
        Freq_Gain.addWidget(dial_FreqLabel)
        Freq_Gain.addWidget(dial_Freq)
        # reference to dial
        self.dial_Freq = dial_Freq

        # Time Domain Gain Dial
        Time_Gain = QHBoxLayout()
        dial_TimeLabel = QLabel('Time Gain')
        dial_Time = QDial()
        dial_Time.setMinimum(0)
        dial_Time.setMaximum(100)
        dial_Time.setValue(40)
        dial_Time.setNotchesVisible(True)
        dial_Time.notchSize = 5
        dial_Time.valueChanged.connect(dial_Time.sliderMoved)
        Time_Gain.addWidget(dial_TimeLabel)
        Time_Gain.addWidget(dial_Time)
        # reference to dial
        self.dial_Time = dial_Time

        vbox = QVBoxLayout()

        vbox.addLayout(Freq_Gain)
        vbox.addLayout(Time_Gain)


        # mpl figure
        self.main_figure = MplFigure(self)
        vbox.addWidget(self.main_figure.toolbar)
        vbox.addWidget(self.main_figure.canvas)

        self.setLayout(vbox)

        self.setGeometry(300, 300, 1000, 500)
        self.setWindowTitle('Live Spectrum')
        self.show()
        timer = PyQt5.QtCore.QTimer()
        timer.timeout.connect(self.Datasync)
        timer.start(100)
        # keep reference to timer
        self.timer = timer

    def initData(self):
        mic = MicRec()
        mic.start()

        # keeps reference to mic
        self.mic = mic

        # computes the parameters that will be used during plotting
        self.freq_vect = np.fft.rfftfreq(mic.chunksize,
                                         1. / mic.rate)
        self.time_vect = np.arange(mic.chunksize, dtype=np.float32) / mic.rate * 1000

    def connectSlots(self):
        pass

    def initMplWidget(self):

        # top plot
        self.ax_top = self.main_figure.figure.add_subplot(211)
        self.ax_top.set_ylim(-32768, 32768)
        self.ax_top.set_xlim(0, self.time_vect.max())
        self.ax_top.set_xlabel(u'time (ms)', fontsize=10)

        # bottom plot
        self.ax_bottom = self.main_figure.figure.add_subplot(212)
        self.ax_bottom.set_ylim(0, 1)
        self.ax_bottom.set_xlim(0, self.freq_vect.max())
        self.ax_bottom.set_xlabel(u'frequency (Hz)', fontsize=10)
        # line objects
        self.line_top, = self.ax_top.plot(self.time_vect,
                                          np.ones_like(self.time_vect))

        self.line_bottom, = self.ax_bottom.plot(self.freq_vect,
                                                np.ones_like(self.freq_vect))

    def Datasync(self):
        # gets the latest frames
        frames = self.mic.get_frames()

        if len(frames) > 0:
            # keeps only the last frame
            current_frame = frames[-1]
            # plots the time signal
            self.line_top.set_data(self.time_vect, self.dial_Time.value()*current_frame)
            # computes and plots the fft signal
            fft_frame = np.fft.rfft(current_frame)

            fft_frame *= self.dial_Freq.value()/2000000.
            # print(np.abs(fft_frame).max())
            self.line_bottom.set_data(self.freq_vect, np.abs(fft_frame))

            # refreshes the plots
            self.main_figure.canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LiveSpectrum()
    sys.exit(app.exec_())
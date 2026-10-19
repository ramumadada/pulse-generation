import numpy as np

from scipy.fft import fft, fftfreq

# ==========================================================
# WINDOW
# ==========================================================

def apply_window(y, window_type="hanning"):

    N = len(y)

    if window_type == "hanning":

        window = np.hanning(N)

    elif window_type == "hamming":

        window = np.hamming(N)

    elif window_type == "blackman":

        window = np.blackman(N)

    else:

        window = np.ones(N)

    return y * window

# ==========================================================
# SMOOTH FFT
# ==========================================================

def smooth_fft(yf, window_size=5):

    return np.convolve(
        yf,
        np.ones(window_size) / window_size,
        mode='same'
    )

# ==========================================================
# FFT
# ==========================================================

def calculate_fft(

    y,

    time_gap,

    window_type="hanning",

    smooth=True

):

    try:

        if y is None:
            return None, None

        if len(y) == 0:
            return None, None

        y = apply_window(
            y,
            window_type
        )

        N = len(y)

        yf = fft(y)

        xf = fftfreq(
            N,
            time_gap * 1e-6
        )

        positive = xf >= 0

        xf = xf[positive]

        yf = np.abs(
            yf[positive]
        )

        if smooth:

            yf = smooth_fft(yf)

        return xf, yf

    except Exception as e:

        print(e)

        return None, None

# ==========================================================
# PEAK FREQUENCY
# ==========================================================

def detect_peak_frequency(xf, yf):

    peak_index = np.argmax(
        yf[1:]
    ) + 1

    return xf[peak_index]

# ==========================================================
# PEAK MARKER
# ==========================================================

def detect_peak_marker(xf, yf):

    peak_index = np.argmax(
        yf[1:]
    ) + 1

    return xf[peak_index], yf[peak_index]

# ==========================================================
# HARMONICS
# ==========================================================

def detect_harmonics(

    xf,

    yf,

    fundamental_freq,

    harmonics=5

):

    harmonic_data = []

    for n in range(1, harmonics + 1):

        target_freq = fundamental_freq * n

        index = np.argmin(
            np.abs(xf - target_freq)
        )

        harmonic_data.append(
            (
                xf[index],
                yf[index]
            )
        )

    return harmonic_data

# ==========================================================
# THD
# ==========================================================

def calculate_thd(

    xf,

    yf,

    fundamental_freq,

    harmonics=5

):

    harmonic_data = detect_harmonics(
        xf,
        yf,
        fundamental_freq,
        harmonics
    )

    if len(harmonic_data) == 0:
        return 0

    fundamental_mag = harmonic_data[0][1]

    harmonic_power = 0

    for freq, mag in harmonic_data[1:]:

        harmonic_power += mag ** 2

    thd = np.sqrt(
        harmonic_power
    ) / fundamental_mag

    return thd * 100
# ==========================================================
# save_module.py
# ==========================================================

import os
import csv
import datetime

import pyqtgraph.exporters

# ==========================================================
# CREATE FOLDERS
# ==========================================================

def create_folders():

    folders = [

        "screenshots",

        "waveform_data",

        "fft_data",

        "experiment_logs"

    ]

    for folder in folders:

        os.makedirs(

            folder,

            exist_ok=True

        )

# ==========================================================
# SAVE CRO SCREENSHOT
# ==========================================================

def save_cro_image(cro_plot):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"screenshots/CRO_{timestamp}.png"

        )

        exporter = pyqtgraph.exporters.ImageExporter(

            cro_plot.plotItem

        )

        exporter.export(

            filename

        )

        return filename

    except Exception as e:

        print("Save CRO Error")

        print(e)

        return None

# ==========================================================
# SAVE FFT SCREENSHOT
# ==========================================================

def save_fft_image(fft_plot):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"screenshots/FFT_{timestamp}.png"

        )

        exporter = pyqtgraph.exporters.ImageExporter(

            fft_plot.plotItem

        )

        exporter.export(

            filename

        )

        return filename

    except Exception as e:

        print("Save FFT Error")

        print(e)

        return None

# ==========================================================
# SAVE WAVEFORM CSV
# ==========================================================

def save_waveform_csv(x, y):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"waveform_data/WAVEFORM_{timestamp}.csv"

        )

        with open(

            filename,

            "w",

            newline=""

        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                "Time(us)",

                "Voltage(V)"

            ])

            for time_value, voltage_value in zip(x, y):

                writer.writerow([

                    time_value,

                    voltage_value

                ])

        return filename

    except Exception as e:

        print("Waveform CSV Error")

        print(e)

        return None

# ==========================================================
# SAVE FFT CSV
# ==========================================================

def save_fft_csv(xf, yf):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"fft_data/FFT_{timestamp}.csv"

        )

        with open(

            filename,

            "w",

            newline=""

        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                "Frequency(Hz)",

                "Magnitude"

            ])

            for freq, mag in zip(xf, yf):

                writer.writerow([

                    freq,

                    mag

                ])

        return filename

    except Exception as e:

        print("FFT CSV Error")

        print(e)

        return None

# ==========================================================
# SAVE EXPERIMENT LOG
# ==========================================================

def save_experiment_log(

    pin,

    frequency,

    duty,

    amplitude,

    thd

):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"experiment_logs/LOG_{timestamp}.txt"

        )

        with open(

            filename,

            "w"

        ) as file:

            file.write(

                "EXPERIMENT LOG\n"

            )

            file.write(

                "=====================\n"

            )

            file.write(

                f"Timestamp : {timestamp}\n"

            )

            file.write(

                f"Pin : {pin}\n"

            )

            file.write(

                f"Frequency : {frequency} Hz\n"

            )

            file.write(

                f"Duty : {duty} %\n"

            )

            file.write(

                f"Amplitude : {amplitude} V\n"

            )

            file.write(

                f"THD : {thd:.2f} %\n"

            )

        return filename

    except Exception as e:

        print("Experiment Log Error")

        print(e)

        return None

# ==========================================================
# SAVE DUAL-CHANNEL WAVEFORM CSV
# ==========================================================

def save_dual_waveform_csv(x, a1, a2=None, differential=None):

    try:

        create_folders()

        timestamp = datetime.datetime.now().strftime(

            "%Y%m%d_%H%M%S"

        )

        filename = (

            f"waveform_data/DUAL_WAVEFORM_{timestamp}.csv"

        )

        with open(

            filename,

            "w",

            newline=""

        ) as file:

            writer = csv.writer(file)

            writer.writerow([

                "Time(ms)",

                "A1(V)",

                "A2(V)",

                "A1_minus_A2(V)"

            ])

            if a2 is None:

                a2 = []

            if differential is None:

                differential = []

            max_length = len(x)

            for index in range(max_length):

                writer.writerow([

                    x[index],

                    a1[index] if index < len(a1) else "",

                    a2[index] if index < len(a2) else "",

                    differential[index] if index < len(differential) else ""

                ])

        return filename

    except Exception as e:

        print("Dual Waveform CSV Error")

        print(e)

        return None

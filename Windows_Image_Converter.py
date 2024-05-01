import os
import sys
from PIL import Image
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtCore as QtCore

try:
    import wand.image
except ImportError:
    wand = None
    print(
        "ImportError - HEIC conversion requires the 'wand' library, which is not installed."
    )


class ImageConverter(QtWidgets.QWidget):
    def __init__(self):
        self.image_formats = ["HEIC", "PNG", "JPG", "BMP"]
        super().__init__()
        self.initUI()

    def initUI(self):
        # Set window properties
        self.setWindowTitle("Image Converter")
        self.setGeometry(100, 100, 400, 300)

        # Create widgets
        self.folderLabel = QtWidgets.QLabel("Folder Path:")
        self.folderLineEdit = QtWidgets.QLineEdit()
        self.folderButton = QtWidgets.QPushButton("Browse")
        self.folderButton.clicked.connect(self.browseFolder)

        self.inputFormatLabel = QtWidgets.QLabel("Input Format:")
        self.inputFormatComboBox = QtWidgets.QComboBox()
        self.inputFormatComboBox.addItems(self.image_formats)

        self.outputFormatLabel = QtWidgets.QLabel("Output Format:")
        self.outputFormatComboBox = QtWidgets.QComboBox()
        self.outputFormatComboBox.addItems(self.image_formats)

        self.replaceCheckBox = QtWidgets.QCheckBox("Replace Original Images")

        self.convertButton = QtWidgets.QPushButton("Convert")
        self.convertButton.clicked.connect(self.convertImages)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setValue(0)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.folderLabel)
        layout.addWidget(self.folderLineEdit)
        layout.addWidget(self.folderButton)
        layout.addWidget(self.inputFormatLabel)
        layout.addWidget(self.inputFormatComboBox)
        layout.addWidget(self.outputFormatLabel)
        layout.addWidget(self.outputFormatComboBox)
        layout.addWidget(self.replaceCheckBox)
        layout.addWidget(self.convertButton)
        layout.addWidget(self.progressBar)

        self.setLayout(layout)

    def browseFolder(self):
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder")
        self.folderLineEdit.setText(folder_path)

    def convertImages(self):
        folder_path = self.folderLineEdit.text()
        input_format = self.inputFormatComboBox.currentText().lower()
        output_format = self.outputFormatComboBox.currentText().lower()
        replace_images = self.replaceCheckBox.isChecked()

        if input_format == output_format:
            QtWidgets.QMessageBox.warning(
                self, "Error", "Input and output formats cannot be the same."
            )
            return

        if not os.path.isdir(folder_path):
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid folder path.")
            return

        try:
            images = [
                f
                for f in os.listdir(folder_path)
                if f.lower().endswith(f".{input_format}")
            ]
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))
            return

        if not images:
            QtWidgets.QMessageBox.warning(
                self, "Warning", "No images found in the selected folder."
            )
            return

        if not wand and (input_format == "heic" or output_format == "heic"):
            QtWidgets.QMessageBox.warning(
                self,
                "Error",
                "HEIC conversion requires the 'wand' library, which is not installed.",
            )
            return

        self.progressBar.setMaximum(len(images))

        # Create a worker thread for image conversion
        self.worker = ImageConversionWorker(
            folder_path, images, input_format, output_format, replace_images
        )
        self.worker.progress.connect(self.updateProgressBar)
        self.worker.finished.connect(self.conversionFinished)
        self.worker.start()

    def updateProgressBar(self, value, filename):
        self.progressBar.setValue(value)
        self.progressBar.setFormat(f"{filename} ({value}/{self.progressBar.maximum()})")

    def conversionFinished(self, errors):
        if errors:
            error_message = "\n".join(errors)
            QtWidgets.QMessageBox.warning(
                self,
                "Errors",
                f"The following errors occurred during conversion:\n{error_message}",
            )
        else:
            QtWidgets.QMessageBox.information(
                self, "Success", "Image conversion completed successfully."
            )

        self.progressBar.setValue(0)


class ImageConversionWorker(QtCore.QThread):
    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(list)

    def __init__(
        self, folder_path, images, input_format, output_format, replace_images
    ):
        super().__init__()
        self.folder_path = folder_path
        self.images = images
        self.input_format = input_format
        self.output_format = output_format
        self.replace_images = replace_images
        self.errors = []

    def run(self):
        for i, image_name in enumerate(self.images):
            try:
                self.convertImage(image_name)
            except Exception as e:
                self.errors.append(f"Error converting {image_name}: {str(e)}")

            self.progress.emit(i + 1, image_name)

        self.finished.emit(self.errors)

    def convertImage(self, image_name):
        input_path = os.path.join(self.folder_path, image_name)

        output_extension = (
            ".HEIC"
            if self.output_format == "heic"
            else f".{self.output_format.upper()}"
        )
        output_path = os.path.join(
            self.folder_path, f"{os.path.splitext(image_name)[0]}{output_extension}"
        )

        if self.input_format == self.output_format:
            raise Exception("Input and output formats cannot be the same.")

        if self.input_format == "heic" or self.output_format == "heic":
            if wand:
                with wand.image.Image(filename=input_path) as img:
                    if self.output_format == "heic":
                        img.save(filename=output_path)
                    else:
                        img.format = self.output_format.upper()
                        img.save(filename=output_path)
            else:
                raise Exception(
                    "HEIC conversion requires the 'wand' library, which is not installed."
                )
        else:
            with Image.open(input_path) as img:
                if self.output_format == "jpg":
                    output_format = "JPEG"
                    # Convert image mode to RGB if it's not already
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                else:
                    output_format = self.output_format.upper()
                img.save(output_path, output_format)

        if self.replace_images:
            os.remove(input_path)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    converter = ImageConverter()
    converter.show()
    sys.exit(app.exec())

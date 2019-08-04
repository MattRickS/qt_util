from PySide2 import QtCore, QtGui, QtWidgets


class LoginWidget(QtWidgets.QDialog):
    loginEntered = QtCore.Signal(str, str)

    def __init__(self, parent=None):
        # type: (QtWidgets.QWidget) -> None
        super(LoginWidget, self).__init__(parent)

        # ----- Widgets -----

        self._username = QtWidgets.QLineEdit()
        self._username.setPlaceholderText("Username")
        self._username.setObjectName("loginUsername")

        self._password = QtWidgets.QLineEdit()
        self._password.setPlaceholderText("Password")
        self._password.setEchoMode(QtWidgets.QLineEdit.Password)
        self._password.setObjectName("loginPassword")

        self._error_label = QtWidgets.QLabel()
        self._error_label.setAlignment(QtCore.Qt.AlignCenter)
        self._error_label.setStyleSheet("QLabel {background-color: red};")
        self._error_label.hide()

        self._login_btn = QtWidgets.QPushButton("Login")
        self._login_btn.setDefault(True)
        self._login_btn.setEnabled(False)

        self._cancel_btn = QtWidgets.QPushButton("Cancel")

        # ----- Layout -----

        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._login_btn)

        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("User", self._username)
        form_layout.addRow("Password", self._password)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self._error_label)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # ----- Connections -----

        self._username.textEdited.connect(self.on_text_edited)
        self._password.textEdited.connect(self.on_text_edited)
        self._login_btn.clicked.connect(self.on_login_btn_clicked)
        self._cancel_btn.clicked.connect(self.close)

    def clear_error_message(self):
        self._error_label.setText("")
        self._error_label.hide()

    def set_error_message(self, message):
        """
        Args:
            message (str): Message to display
        """
        self._error_label.setText(message)
        self._error_label.show()

    def on_login_btn_clicked(self):
        self.loginEntered.emit(self._username.text(), self._password.text())

    def on_text_edited(self):
        username = self._username.text()
        password = self._password.text()
        self._login_btn.setEnabled(bool(username) and bool(password))


if __name__ == '__main__':
    import sys
    app = QtWidgets.QApplication(sys.argv)

    w = LoginWidget()
    w.show()

    def prnt(user, pw):
        print(user, pw)
        w.set_error_message("Invalid login")

    w.loginEntered.connect(prnt)

    app.exec_()
    sys.exit()

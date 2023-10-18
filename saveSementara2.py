import sys
import datetime
from dateutil.relativedelta import relativedelta
import pymysql
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QComboBox, QFormLayout, QGroupBox,QMessageBox,
                            QDialogButtonBox, QDialog, QDateEdit, QScrollArea, QSpacerItem, QSizePolicy, QMenu, QAbstractItemView, )
from PyQt5.QtCore import QTimer, Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5 import sip
import psycopg2

import pymysql

class Worker(QThread):
    dataLoaded = pyqtSignal()

    def run(self):
        # Anda bisa menggantinya dengan operasi loading data sebenarnya
        import time
        time.sleep(2)
        self.dataLoaded.emit()

class CustomTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super(CustomTableWidget, self).__init__(*args, **kwargs)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)

    def contextMenuEvent(self, event):
        print("Context menu opened.")  
        context_menu = QMenu(self)

        copy_action = context_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy_selection_to_clipboard)

        # Tampilkan menu konteks di posisi kursor
        context_menu.popup(QCursor.pos())

    def copy_selection_to_clipboard(self):
        selection = self.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[''] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                col = index.column() - columns[0]
                table[row][col] = index.data() if index.data() is not None else ''  # periksa jika data adalah None
            stream = '\n'.join(['\t'.join(row) for row in table])
            QApplication.clipboard().setText(stream)


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            print("CTRL+C pressed")  # ini hanya untuk debugging
            self.copy_selection_to_clipboard()
        else:
            super().keyPressEvent(event)


class DatabaseManager:
    def __init__(self):
        self.host = 'localhost'
        self.user = 'root'
        self.password = ''
        self.database = 'conwood'
        self.connection = self.connect_to_db()
        self.cursor = self.connection.cursor()  # Menambahkan cursor di sini

    def connect_to_db(self):
        return pymysql.connect(host=self.host, user=self.user, password=self.password, database=self.database)

    def execute_query(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:  # Menjamin cursor ditutup setelah selesai
                cursor.execute(query, params)

                if query.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
                    self.connection.commit()
                return True

        except Exception as e:
            print(f"Database error: {e}")
            return False
        
    def get_all_machines_with_ids(self):
        try:
            self.cursor.execute("SELECT id, name FROM machinepm")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving machines: {e}")
            return False
        
    def get_all_parts_with_ids(self):
        try:
            self.cursor.execute("SELECT id, bagian_mesin FROM machinepm")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving parts: {e}")
            return False
        
    def get_all_labor_with_ids(self):
        try:
            self.cursor.execute("SELECT id, labor FROM machinepm")
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error retrieving parts: {e}")
            return False

    def fetch_data(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"Database error: {e}")
            return None

    def close_connection(self):
        if self.cursor:  # Menutup cursor
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def fetch_one(self, query, params=None):
        try:
            with self.connection.cursor() as cursor:  # Menggunakan with statement untuk menjamin cursor ditutup setelah digunakan
                cursor.execute(query, params)
                return cursor.fetchone()
        except Exception as e:
            print(f"Database error: {e}")
            return None

class MaintenanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()

        self.setWindowTitle("Preventive Maintenance Logger")
        self.setGeometry(100, 100, 1200, 800)

        self.details_inputs = []
        self.standard_inputs = []
        self.frequency_pemeriksaan_combos = []
        self.spare_part_inputs = []
        self.part_number_inputs = []
        self.maintenance_date_inputs = []
        self.entries = []

        self.current_page = 1
        self.rows_per_page = 100  # Menampilkan 100 baris per halaman

        self.central_widget = QTabWidget()
        self.setCentralWidget(self.central_widget)

        # Machine tab
        self.machine_tab = QWidget()
        self.central_widget.addTab(self.machine_tab, "Mechanical")
        self.setup_machine_tab()

        # Electric tab
        self.electric_tab = QWidget()
        self.central_widget.addTab(self.electric_tab, "Electric")
        self.setup_electric_tab()

        # Output tab
        self.output_tab = QWidget()
        self.central_widget.addTab(self.output_tab, "Schedule")
        self.setup_output_tab()

        # Output Electric tab
        self.output_electric_tab = QWidget()
        self.central_widget.addTab(self.output_electric_tab, "Output Electric")
        self.setup_output_electric_tab()
        self.central_widget.tabBar().setTabVisible(self.central_widget.indexOf(self.output_electric_tab), False)

        # Next Maintenance tab
        self.next_maintenance_tab = QWidget()
        self.central_widget.addTab(self.next_maintenance_tab, "In progress")
        self.setup_next_maintenance_tab()

        # Next Maintenance Electric tab
        self.next_maintenance_electric_tab = QWidget()
        self.central_widget.addTab(self.next_maintenance_electric_tab, "ElectricPM")
        self.setup_next_maintenance_electric_tab()
        self.central_widget.tabBar().setTabVisible(self.central_widget.indexOf(self.next_maintenance_electric_tab), False)

        # History tab
        self.history_tab = QWidget()  # New History tab
        self.central_widget.addTab(self.history_tab, "History")
        self.setup_history_tab()  # Anda harus membuat fungsi ini untuk mengatur tab History

        self.central_widget.currentChanged.connect(self.on_tab_changed)

        self.outputWorker = Worker()
        self.outputWorker.dataLoaded.connect(self.populate_output_tab)
        self.outputElectricWorker = Worker()
        self.outputElectricWorker.dataLoaded.connect(self.populate_output_electric_tab)
        self.nextMaintenanceWorker = Worker()
        self.nextMaintenanceWorker.dataLoaded.connect(self.populate_next_maintenance_tab)
        self.nextMaintenanceElectricWorker = Worker()
        self.nextMaintenanceElectricWorker.dataLoaded.connect(self.populate_next_maintenance_electric_tab)

        # Set up a QTimer for real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_maintenance_entries)
        self.timer.start(1000)  # Update every 1000 ms (1 second)

        self.active_filters = None


    def next_page(self):
        self.current_page += 1
        self.populate_output_tab(self.active_filters)  # gunakan filter yang aktif
        self.update_page_label()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.populate_output_tab(self.active_filters)  # gunakan filter yang aktif
            self.update_page_label()
       


    def update_page_label(self):
        self.page_label.setText(f"Page {self.current_page}")

    def update_pagination(self):
        total_rows = sum(1 for i in range(self.table.rowCount()) if not self.table.isRowHidden(i))  # Hitung jumlah baris yang tidak disembunyikan
        start = (self.current_page - 1) * self.rows_per_page
        end = start + self.rows_per_page
        displayed_rows = 0  # Hitung jumlah baris yang ditampilkan

        for i in range(self.table.rowCount()):
            if not self.table.isRowHidden(i):
                should_display = displayed_rows >= start and displayed_rows < end
                self.table.setRowHidden(i, not should_display)
                displayed_rows += 1

    def show_edit_dialog(self, item_id):
        # Fetch the current data for this item_id
        query = "SELECT * FROM machinePM WHERE id = %s"
        data = self.db_manager.fetch_one(query, (item_id,))

        # Create the dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Entry")
        layout = QFormLayout(dialog)

        # Set a fixed width for the dialog
        dialog.setFixedWidth(500)  # Set the width as per your requirement

        # Create widgets for each field with a special case for frequency
        fields = ['Name', 'Bagian Mesin', 'Frequency Pemeriksaan', 'Deskripsi', 'Spare Part', 'Part Number', 'Standard', 'Date', 'Next Maintenance Date']
        widgets = []
        for i in range(1, 10):
            if i != 3:  # If not frequency
                widget = QLineEdit(str(data[i])) if i != 8 and i != 9 else QDateEdit(QDate.fromString(str(data[i]), 'yyyy-MM-dd'))
            else:  # Special case for frequency
                widget = QComboBox()
                widget.addItems(['1 Minggu', '2 Minggu', '1 Bulan', '3 Bulan', '6 Bulan', '1 Tahun'])
                widget.setCurrentText(str(data[i]))
            widgets.append(widget)

        # Populate the form with current data
        for i, field in enumerate(fields):
            layout.addRow(field, widgets[i])

        # Buttons to save or cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, dialog)
        layout.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        # Show the dialog
        result = dialog.exec_()

        # If the user pressed OK, then update the database
        if result == QDialog.Accepted:
            new_values = [widget.text() if not isinstance(widget, QDateEdit) and not isinstance(widget, QComboBox) else widget.date().toString('yyyy-MM-dd') if isinstance(widget, QDateEdit) else widget.currentText() for widget in widgets]
            update_query = """
            UPDATE machinePM SET
                name = %s, bagian_mesin = %s, frequency_pemeriksaan = %s, deskripsi = %s,
                spare_part = %s, part_number = %s, standard = %s, date = %s, next_maintenance_date = %s
            WHERE id = %s
            """
            self.db_manager.execute_query(update_query, (*new_values, item_id))

            # Refresh the output tab
            self.populate_output_tab()

    def on_delete_button_clicked(self, item_id):
        # Tampilkan dialog konfirmasi
        reply = QMessageBox.question(self, 'Delete Confirmation',
                                     'Are you sure you want to delete this entry?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            query = "DELETE FROM machinePM WHERE id = %s"
            self.db_manager.execute_query(query, (item_id,))
            self.populate_output_tab()  # Perbarui tabel output


    def on_tab_changed(self, index):
        current_tab = self.central_widget.widget(index)
        if current_tab == self.output_tab and not self.outputWorker.isRunning():
            self.outputWorker.start()
        elif current_tab == self.output_electric_tab and not self.outputElectricWorker.isRunning():
            self.outputElectricWorker.start()
        elif current_tab == self.next_maintenance_tab and not self.nextMaintenanceWorker.isRunning():
            self.nextMaintenanceWorker.start()
        elif current_tab == self.next_maintenance_electric_tab and not self.nextMaintenanceElectricWorker.isRunning():
            self.nextMaintenanceElectricWorker.start()

    def fetch_one(self, query, params):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def on_cancel_button_clicked(self, item_id):
        # Update status in the database
        query = """
        UPDATE machinePM
        SET status = %s
        WHERE id = %s
        """
        self.db_manager.execute_query(query, ("Start", item_id))
        
        # Refresh the output tab to display the cancelled entry
        self.populate_output_tab()
        
        # Remove the entry from the next maintenance table
        for i in range(self.next_maintenance_table.rowCount()):
            if self.next_maintenance_table.item(i, 9).data(Qt.UserRole) == item_id:  # adjust the column index according to your table
                self.next_maintenance_table.removeRow(i)
                break
        
        # Refresh the next maintenance tab
        self.populate_next_maintenance_tab()

    def on_status_button_clicked(self, item_id):
        query = "SELECT * FROM machinePM WHERE id=%s"
        data = self.db_manager.fetch_one(query, (item_id,))
        if not data:
            print("Data not found")
            return

        current_status = data[11]  # Index diperbarui karena menambahkan kolom "Labor"

        if current_status == "Start":
            query = """
            UPDATE machinePM
            SET status = %s
            WHERE id = %s
            """
            self.db_manager.execute_query(query, ("In Progress", item_id))

            row_position = self.next_maintenance_table.rowCount()
            self.next_maintenance_table.insertRow(row_position)
            for i in range(10):  # Index diperbarui karena menambahkan kolom "Labor"
                self.next_maintenance_table.setItem(row_position, i, QTableWidgetItem(str(data[i+1])))
            self.next_maintenance_table.setItem(row_position, 10, QTableWidgetItem("In Progress"))  # Index diperbarui karena menambahkan kolom "Labor"

            self.populate_output_tab()

        elif current_status == "In Progress":
            query = """
            UPDATE machinePM
            SET status = %s
            WHERE id = %s
            """
            self.db_manager.execute_query(query, ("Completed", item_id))

            # Calculate the next maintenance date by adding one year to the current date
            next_maintenance_date = datetime.datetime.strptime(str(data[10]), "%Y-%m-%d").date() + relativedelta(years=1)

            query = """
            INSERT INTO machinePM (labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, date, next_maintenance_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], next_maintenance_date, "Start")    # Added 'Start' status
            self.db_manager.execute_query(query, values)  # There was an error here; not enough values were being passed

            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)
            for i in range(10):  # Index updated because of the addition of "Labor" column
                self.history_table.setItem(row_position, i, QTableWidgetItem(str(data[i+1])))
            self.history_table.setItem(row_position, 10, QTableWidgetItem("Completed"))  # Index updated because of the addition of "Labor" column

            self.populate_next_maintenance_tab()
            self.populate_output_tab()  # Ensure this method is updated to handle the new "labor" column and also re-populate the Output tab

        else:
            print("Unknown status:", current_status)


    def populate_output_tab(self, filters=None):
        # Clear the table first
        self.table.setRowCount(0)

        query = """
        SELECT id, labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, date, next_maintenance_date, status 
        FROM machinePM
        WHERE status = 'Start'
        """
        
        # If filters are provided, apply them to the query
        if filters:
            additional_queries = [f"{key} = '{value}'" for key, value in filters.items()]
            query += " AND " + " AND ".join(additional_queries)

        query += " ORDER BY date ASC, id ASC"
        
        data = self.db_manager.fetch_data(query)

        if data is None:
            print("No data returned or an error occurred.")
            return

        for row_data in data:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)

            for col, item in enumerate(row_data[1:], start=0):  
                self.table.setItem(row_position, col, QTableWidgetItem(str(item)))

            self.table.setItem(row_position, 10, QTableWidgetItem("Start"))  

            status_button = QPushButton("Process", self)
            edit_button = QPushButton("Edit", self)
            delete_button = QPushButton("Delete", self)

            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.addWidget(status_button)
            button_layout.addWidget(edit_button)
            button_layout.addWidget(delete_button)
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(5)
                
            self.table.setCellWidget(row_position, 11, button_widget)  

        self.update_pagination() 


    def populate_output_electric_tab(self):

        pass
    
    def populate_next_maintenance_tab(self):
        # Clear the table first
        self.next_maintenance_table.setRowCount(0)

        query = """
        SELECT id, labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, date, next_maintenance_date, status 
        FROM machinePM
        WHERE status='In Progress'
        ORDER BY labor ASC, name ASC, FIELD(frequency_pemeriksaan, '1 Minggu', '2 Minggu', '1 Bulan', '3 Bulan', '6 Bulan', '1 Tahun')
        """
        data = self.db_manager.fetch_data(query)

        for row_data in data:
            row_position = self.next_maintenance_table.rowCount()
            self.next_maintenance_table.insertRow(row_position)

            # Here, row_data[0] is the id from the database.
            item_id = row_data[0]

            # Memasukkan data ke dalam tabel
            for col, item in enumerate(row_data[1:], start=0):
                self.next_maintenance_table.setItem(row_position, col, QTableWidgetItem(str(item)))

            # Tambahkan tombol Complete
            complete_button = QPushButton("Complete", self)
            complete_button.clicked.connect(lambda checked, item_id=item_id: self.on_status_button_clicked(item_id))

            # Tambahkan tombol Cancel
            cancel_button = QPushButton("Cancel", self)
            cancel_button.clicked.connect(lambda checked, item_id=item_id: self.on_cancel_button_clicked(item_id))

            # Membuat widget yang mengandung kedua tombol
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.addWidget(complete_button)
            layout.addWidget(cancel_button)
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)

            self.next_maintenance_table.setCellWidget(row_position, 11, widget) # Adjust column index accordingly


    def populate_next_maintenance_electric_tab(self):
        # Clear the table first
        self.next_maintenance_electric_table.setRowCount(0)

        # Fetch data from the database
        query = "SELECT kode, name, frequency_pemeriksaan, date, next_maintenance_date FROM ElectricPM"
        data = self.db_manager.fetch_data(query)

        for row_data in data:
            row_position = self.next_maintenance_electric_table.rowCount()
            self.next_maintenance_electric_table.insertRow(row_position)
            for col, item in enumerate(row_data):
                self.next_maintenance_electric_table.setItem(row_position, col, QTableWidgetItem(str(item)))

    def populate_history_tab(self):
        self.history_table.setRowCount(0)
        query = """
        SELECT id, labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, date, next_maintenance_date, status 
        FROM machinePM
        WHERE status != 'Start'  # Anda mungkin perlu memperbarui kondisi ini sesuai kebutuhan Anda
        ORDER BY date ASC, id ASC
        """
        data = self.db_manager.fetch_data(query)
        for row_data in data:
            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)

            for col, item in enumerate(row_data[1:], start=0):
                self.history_table.setItem(row_position, col, QTableWidgetItem(str(item)))

            status_item = QTableWidgetItem("Completed")
            self.history_table.setItem(row_position, 10, status_item)

    def populate_combo_output(self, combo, data_type):
        try:
            combo.clear()
            combo.addItem("All")

            items_with_ids = []

            if data_type == 'labor':
                items_with_ids = self.db_manager.get_all_labor_with_ids()
            elif data_type == 'machine':
                items_with_ids = self.db_manager.get_all_machines_with_ids()
            elif data_type == 'part':
                items_with_ids = self.db_manager.get_all_parts_with_ids()
            else:
                print(f"Unsupported data type: {data_type}")
                return

            item_names = {item[1] for item in items_with_ids}  # Mengambil nama item saja dan menghapus duplikat dengan mengubahnya menjadi set

            sorted_item_names = sorted(item_names)  # Sort set items to display

            combo.addItems(sorted_item_names)  # Convert set to list and sort it for better presentation

        except Exception as e:
            print(f"Error populating combo ({data_type}): {e}")


    def populate_combo_next_maintenance(self, combo, data_type):
        try:
            combo.clear()
            combo.addItem("All")

            items_with_ids = []
            if data_type == 'labor':
                items_with_ids = self.db_manager.get_all_labor_with_ids()
            elif data_type == 'machine':
                items_with_ids = self.db_manager.get_all_machines_with_ids()
            elif data_type == 'part':
                items_with_ids = self.db_manager.get_all_parts_with_ids()
            else:
                print(f"Unsupported data type: {data_type}")
                return

            item_names = {item[1] for item in items_with_ids}  # Mengambil nama item saja dan menghapus duplikat dengan mengubahnya menjadi set

            sorted_item_names = sorted(item_names)  # Sort set items to display

            combo.addItems(sorted_item_names)  # Convert set to list and sort it for better presentation

        except Exception as e:
            print(f"Error populating combo ({data_type}): {e}")

    def populate_combo_history(self, combo, data_type):
        try:
            combo.clear()
            combo.addItem("All")

            items_with_ids = []

            if data_type == 'labor':
                items_with_ids = self.db_manager.get_all_labor_with_ids()
            elif data_type == 'machine':
                items_with_ids = self.db_manager.get_all_machines_with_ids()
            elif data_type == 'part':
                items_with_ids = self.db_manager.get_all_parts_with_ids()
            else:
                print(f"Unsupported data type: {data_type}")
                return

            item_names = {item[1] for item in items_with_ids}  # Mengambil nama item saja dan menghapus duplikat dengan mengubahnya menjadi set

            sorted_item_names = sorted(item_names)  # Sort set items to display

            combo.addItems(sorted_item_names)  # Convert set to list and sort it for better presentation

        except Exception as e:
            print(f"Error populating combo ({data_type}): {e}")

    def setup_machine_tab(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(4)
        self.machine_tab.setLayout(self.layout)

        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(4)

        # Menambahkan ComboBox untuk Labor
        self.labor_label = QLabel("Labor")
        self.labor_combo = QComboBox()
        self.labor_combo.addItem("Pilih Area / Labor")  # Menambahkan item default
        self.labor_combo.addItems(["Fiber Preparation", "Utility", "Final Mix", "Laminating", "Dryer", "Finishing"])  # Menambahkan opsi lain
        self.form_layout.addRow(self.labor_label, self.labor_combo)
        self.labor_combo.setMaximumWidth(400)

        self.name_input = QLineEdit()
        self.name_input.setMaximumWidth(400)
        self.form_layout.addRow("Nama Mesin", self.name_input)

        self.bagian_mesin_input = QLineEdit()
        self.bagian_mesin_input.setMaximumWidth(400)
        self.form_layout.addRow("Bagian Mesin", self.bagian_mesin_input)

        self.frequency_pemeriksaan_label = QLabel("Job Frequency")
        self.frequency_pemeriksaan_combo = QComboBox()
        self.frequency_pemeriksaan_combo.addItems(["Pilih Frequency", "1 Minggu", "2 Minggu", "1 Bulan", "3 Bulan", "6 Bulan", "1 Tahun"])
        self.form_layout.addRow(self.frequency_pemeriksaan_label, self.frequency_pemeriksaan_combo)
        self.frequency_pemeriksaan_combo.setMaximumWidth(400)

        self.outer_group_box = QGroupBox("Deskripsi")
        self.outer_group_layout = QVBoxLayout()
        self.outer_group_box.setLayout(self.outer_group_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.outer_group_layout.addWidget(self.scroll_area)

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_widget.setLayout(self.container_layout)
        self.scroll_area.setWidget(self.container_widget)

        self.add_input_fields()

        self.add_entry_button = QPushButton("Add Entry")
        self.add_entry_button.clicked.connect(self.add_entry)

        self.add_details_button = QPushButton("Add Deskripsi")
        self.add_details_button.clicked.connect(self.add_input_fields)

        self.form_layout.addRow(self.outer_group_box)
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.add_details_button)
        self.layout.addWidget(self.add_entry_button)


    def setup_electric_tab(self):
        self.layout = QVBoxLayout()
        self.layout.setSpacing(4)
        self.electric_tab.setLayout(self.layout)

        # Menggunakan QFormLayout untuk mengatur pasangan label dan input
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(4)

        self.kode_input_electric = QLineEdit()
        self.kode_input_electric.setMaximumWidth(400)
        self.form_layout.addRow("Kode:", self.kode_input_electric)

        self.name_input_electric = QLineEdit()
        self.name_input_electric.setMaximumWidth(400)
        self.form_layout.addRow("Nama Mesin:", self.name_input_electric)

        self.frequency_pemeriksaan_combo_electric = QComboBox()
        self.frequency_pemeriksaan_combo_electric.setMaximumWidth(400)
        self.frequency_pemeriksaan_combo_electric.addItems(["1 Minggu", "2 Minggu", "1 Bulan", "3 Bulan", "6 Bulan", "1 Tahun"])
        self.form_layout.addRow("Frequency Pemeriksaan:", self.frequency_pemeriksaan_combo_electric)

        self.add_entry_button_electric = QPushButton("Add Entry (Electric)")
        self.add_entry_button_electric.clicked.connect(self.add_entry_electric)

        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.add_entry_button_electric)

    def add_input_fields(self):
        try:
            
            inner_group_box = QGroupBox("Inner Frame")
            main_layout = QVBoxLayout()

            # Membuat layout horizontal untuk Deskripsi Pemeriksaan dan tombol delete
            top_layout = QHBoxLayout()

            details_label = QLabel("Job Activity          ")
            details_input = QLineEdit()
            details_input.setFixedWidth(400)  # Mengatur lebar tetap

            # Menambahkan spacer untuk memberikan jarak antara input dan tombol delete
            spacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

            delete_button = QPushButton("Delete")
            delete_button.setFixedSize(60, 25)
            delete_button.clicked.connect(lambda: self.delete_inner_frame(inner_group_box))

            top_layout.addWidget(details_label)
            top_layout.addWidget(details_input)
            top_layout.addItem(spacer)  # Menambahkan spacer ke dalam layout
            top_layout.addWidget(delete_button)

            main_layout.addLayout(top_layout)

            # Membuat layout form untuk input fields lainnya
            form_layout = QFormLayout()

            spare_part_input = QLineEdit()
            spare_part_input.setFixedWidth(400)  # Mengatur lebar tetap
            form_layout.addRow("Spare Part", spare_part_input)

            standard_input = QLineEdit()
            standard_input.setFixedWidth(400)  # Mengatur lebar tetap
            form_layout.addRow("Standard", standard_input)

            part_number_input = QLineEdit()
            part_number_input.setFixedWidth(400)  # Mengatur lebar tetap
            form_layout.addRow("Part Number", part_number_input)

            # Menambahkan input field untuk Maintenance Date
            maintenance_date_input = QDateEdit()
            maintenance_date_input.setFixedWidth(400)  # Mengatur lebar tetap
            maintenance_date_input.setCalendarPopup(True)  # Menampilkan popup kalender
            maintenance_date_input.setDate(QDate.currentDate())  # Set tanggal ke hari ini
            form_layout.addRow("Maintenance Date", maintenance_date_input)

            main_layout.addLayout(form_layout)
            inner_group_box.setLayout(main_layout)

            self.container_layout.addWidget(inner_group_box)

            # Menyimpan referensi input fields jika diperlukan
            self.details_inputs.append(details_input)
            self.standard_inputs.append(standard_input)
            self.spare_part_inputs.append(spare_part_input)
            self.part_number_inputs.append(part_number_input)
            self.maintenance_date_inputs.append(maintenance_date_input)  # Menyimpan referensi input tanggal

            # Menambahkan pernyataan cetak untuk debugging
            print("Details Inputs:", [input.text() for input in self.details_inputs])
            print("Standard Inputs:", [input.text() for input in self.standard_inputs])
            print("Spare Part Inputs:", [input.text() for input in self.spare_part_inputs])
            print("Part Number Inputs:", [input.text() for input in self.part_number_inputs])
            print("Maintenance Date Inputs:", [
                input.date().toString()
                for input in self.maintenance_date_inputs
                if not sip.isdeleted(input)  # Tambahkan pemeriksaan ini
            ])  # Menampilkan tanggal

            # Ini adalah baris kode baru untuk mencetak nilai saat ini dari self.maintenance_date_inputs
            for i, date_input in enumerate(self.maintenance_date_inputs):
                if not sip.isdeleted(date_input):
                    print(f"Maintenance Date Input {i}: {date_input.date().toString()}")
                else:
                    print(f"Maintenance Date Input {i} has been deleted")

        except Exception as e:
            print("Error in add_input_fields:", e)
            import traceback
            print(traceback.format_exc())  # Ini akan mencetak stack trace untuk memberikan konteks error


    def add_input_fields_electric(self):
        # Membuat QGroupBox (frame) untuk mengelompokkan Deskripsi Pemeriksaan dan Frequency
        inner_group_box = QGroupBox("Inner Frame (Electric)")
        main_inner_layout = QVBoxLayout()

        # Create a horizontal layout for the label and delete button
        top_layout = QHBoxLayout()
        details_label = QLabel("Deskripsi Pemeriksaan (Electric):")
        delete_button = QPushButton("Delete")
        delete_button.setFixedSize(50, 20)
        delete_button.clicked.connect(lambda: self.delete_inner_frame(inner_group_box))

        top_layout.addWidget(details_label)
        top_layout.addStretch()  # This will push the button to the right
        top_layout.addWidget(delete_button)
        main_inner_layout.addLayout(top_layout)

        details_input = QLineEdit()
        details_input.setMaximumWidth(400)
        main_inner_layout.addWidget(details_input)

        frequency_pemeriksaan_label = QLabel("Frequency (Electric):")
        frequency_pemeriksaan_combo = QComboBox()
        frequency_pemeriksaan_combo.setMaximumWidth(400)
        frequency_pemeriksaan_combo.addItems(["1 Minggu", "2 Minggu", "1 Bulan", "3 Bulan", "6 Bulan", "1 Tahun"])
        main_inner_layout.addWidget(frequency_pemeriksaan_label)
        main_inner_layout.addWidget(frequency_pemeriksaan_combo)

        inner_group_box.setLayout(main_inner_layout)
        self.outer_group_layout_electric.addWidget(inner_group_box)

        self.details_inputs_electric.append(details_input)
        self.frequency_pemeriksaan_combos_electric.append(frequency_pemeriksaan_combo)

    def setup_output_tab(self):
        # Setup layout
        self.layout = QVBoxLayout()
        self.output_tab.setLayout(self.layout)

        # Create combo boxes for filtering
        filter_layout = QHBoxLayout()

        self.search_by_labor_combo_output = QComboBox()
        self.search_by_labor_combo_output.addItem("All")
        self.search_by_labor_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Labor:"))
        filter_layout.addWidget(self.search_by_labor_combo_output)

        self.search_by_name_combo_output = QComboBox()
        self.search_by_name_combo_output.addItem("All")
        self.search_by_name_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Nama Mesin:"))
        filter_layout.addWidget(self.search_by_name_combo_output)

        self.search_by_part_combo_output = QComboBox()
        self.search_by_part_combo_output.addItem("All")
        self.search_by_part_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Bagian Mesin:"))
        filter_layout.addWidget(self.search_by_part_combo_output)

        # Menambahkan combo box untuk filter job deskripsi
        self.search_by_job_activity_combo_output = QComboBox()
        self.search_by_job_activity_combo_output.addItem("All")
        self.search_by_job_activity_combo_output.addItems(["Periksa", "Ganti", "Bersihkan", "Kencangkan", "Sejajarkan", "Lubrikasi"])
        self.search_by_job_activity_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Job Activity:"))
        filter_layout.addWidget(self.search_by_job_activity_combo_output)

        # Adding combo box for part number filter
        self.search_by_part_number_combo_output = QComboBox()
        self.search_by_part_number_combo_output.addItem("All")
        self.search_by_part_number_combo_output.addItems(["With Part Number", "Only N/A"])
        self.search_by_part_number_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Part Number:"))
        filter_layout.addWidget(self.search_by_part_number_combo_output)

        self.search_by_month_combo_output = QComboBox()
        self.search_by_month_combo_output.addItem("All")
        self.search_by_month_combo_output.addItems(["January", "February", "March", "April", "May", "June",
                                                "July", "August", "September", "October", "November", "December"])
        self.search_by_month_combo_output.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(QLabel("Search by Month:"))
        filter_layout.addWidget(self.search_by_month_combo_output)


        self.layout.addLayout(filter_layout)

        # Button untuk membuka tab "Output Electric"
        self.new_tab_button = QPushButton("Open Output Electric Tab")
        self.new_tab_button.clicked.connect(self.add_output_electric_tab)
        self.layout.addWidget(self.new_tab_button)

        # Tabel output
        self.table = CustomTableWidget()
        self.table.setColumnCount(12)  # Menambahkan satu kolom lagi untuk "Labor"
        self.table.setHorizontalHeaderLabels(["Labor", "Nama Mesin", "Bagian Mesin", "Job Frequency", "Job Activity", "Spare Part",
                                            "Part Number", "Standard", "Date", "Next PM", "Status", "Action"])  # Menambahkan label "Labor"
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        self.navigationLayout = QHBoxLayout()

        self.prev_button = QPushButton('Previous')
        self.prev_button.clicked.connect(self.prev_page)
        self.navigationLayout.addWidget(self.prev_button)

        self.page_label = QLabel('Page 1')
        self.navigationLayout.addWidget(self.page_label)

        self.next_button = QPushButton('Next')
        self.next_button.clicked.connect(self.next_page)
        self.navigationLayout.addWidget(self.next_button)

        self.layout.addLayout(self.navigationLayout)

        # Hubungkan sinyal itemClicked dengan metode on_status_clicked
        self.table.itemClicked.connect(self.on_status_button_clicked)

        # Update the filter combos with distinct values from the database (if needed)
        self.populate_combo_output(self.search_by_labor_combo_output, 'labor')
        self.populate_combo_output(self.search_by_name_combo_output, 'machine')
        self.populate_combo_output(self.search_by_part_combo_output, 'part')

    def setup_output_electric_tab(self):
        layout = QVBoxLayout()
        self.output_electric_tab.setLayout(layout)

        # Tambahkan tombol untuk kembali ke tab "Output"
        back_button = QPushButton("Back to Output")
        back_button.clicked.connect(lambda: self.central_widget.setCurrentWidget(self.output_tab))
        layout.addWidget(back_button)

        self.output_electric_table = QTableWidget()
        self.output_electric_table.setColumnCount(4)
        self.output_electric_table.setHorizontalHeaderLabels(["Kode", "Nama Mesin", "Frequency Pemeriksaan", "Next Maintenance Date"])
        self.output_electric_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        layout.addWidget(self.output_electric_table)

    def add_output_electric_tab(self):
        # Pindah ke tab "Output Electric"
        self.central_widget.setCurrentWidget(self.output_electric_tab)

    def go_to_output_tab(self):
        self.central_widget.setCurrentWidget(self.output_tab)

    def setup_next_maintenance_tab(self):
        self.layout = QVBoxLayout()
        self.next_maintenance_tab.setLayout(self.layout)

        # Membuat layout horizontal untuk filter
        self.filter_layout = QHBoxLayout()

        # Membuat QComboBox untuk labor
        self.search_by_labor_combo = QComboBox()
        self.filter_layout.addWidget(QLabel("Search by Labor:"))
        self.filter_layout.addWidget(self.search_by_labor_combo)

        # Membuat QComboBox untuk nama mesin
        self.search_by_name_combo = QComboBox()
        self.filter_layout.addWidget(QLabel("Search by Nama Mesin:"))
        self.filter_layout.addWidget(self.search_by_name_combo)

        # Membuat QComboBox untuk bagian mesin
        self.search_by_part_combo = QComboBox()
        self.filter_layout.addWidget(QLabel("Search by Bagian Mesin:"))
        self.filter_layout.addWidget(self.search_by_part_combo)

        # Membuat QComboBox untuk bulan
        self.month_filter_combo = QComboBox()
        self.month_filter_combo.addItem("All")
        self.month_filter_combo.addItems(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        self.filter_layout.addWidget(QLabel("Search by Month:"))
        self.filter_layout.addWidget(self.month_filter_combo)

        # Menambahkan layout filter ke layout utama
        self.layout.addLayout(self.filter_layout)

        # Membuat QTableWidget
        self.next_maintenance_table = CustomTableWidget()
        self.next_maintenance_table.itemClicked.connect(self.on_status_button_clicked)
        self.next_maintenance_table.setColumnCount(12)  # Menambahkan satu kolom lagi untuk "Labor"
        self.next_maintenance_table.setHorizontalHeaderLabels(["Labor", "Nama Mesin", "Bagian Mesin", "Job Frequency", "Job Activity", "Spare Part", "Part Number", "Standard", "Date", "Next PM", "Status", "Action"])  # Menambahkan label "Labor"
        self.next_maintenance_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.next_maintenance_table)

        # Hubungkan QComboBox dengan metode filter yang sesuai
        self.search_by_labor_combo.currentIndexChanged.connect(self.apply_filters_next_maintenance)
        self.search_by_name_combo.currentIndexChanged.connect(self.apply_filters_next_maintenance)
        self.search_by_part_combo.currentIndexChanged.connect(self.apply_filters_next_maintenance)
        self.month_filter_combo.currentIndexChanged.connect(self.apply_filters_next_maintenance)

        # Mengisi QComboBox dengan data
        self.populate_combo_next_maintenance(self.search_by_labor_combo, 'labor')
        self.populate_combo_next_maintenance(self.search_by_name_combo, 'machine')
        self.populate_combo_next_maintenance(self.search_by_part_combo, 'part')

        # Menambahkan tombol ke layout
        self.open_next_maintenance_electric_button = QPushButton("Open Next Maintenance Electric Tab")
        self.open_next_maintenance_electric_button.clicked.connect(self.open_next_maintenance_electric)
        self.layout.addWidget(self.open_next_maintenance_electric_button)


    def setup_next_maintenance_electric_tab(self):
        layout = QVBoxLayout()
        self.next_maintenance_electric_tab.setLayout(layout)

        # Tambahkan fitur pencarian berdasarkan nama
        search_layout = QFormLayout()
        self.search_input_electric = QLineEdit()
        self.search_input_electric.setMaximumWidth(400)
        self.search_input_electric.textChanged.connect(self.filter_by_name_next_maintenance_electric)
        search_layout.addRow("Search by Name:", self.search_input_electric)
        layout.addLayout(search_layout)

        # Dropdown untuk memilih bulan yang diinginkan
        month_filter_label = QLabel("Filter by Month:")
        month_filter_combo = QComboBox()
        month_filter_combo.addItem("All")
        month_filter_combo.addItems(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        month_filter_combo.currentIndexChanged.connect(self.filter_by_month_next_maintenance_electric)  # Anda perlu mendefinisikan metode ini

        layout.addWidget(month_filter_label)
        layout.addWidget(month_filter_combo)

        # Tambahkan tombol untuk kembali ke tab "Next Maintenance"
        back_button = QPushButton("Back to Next Maintenance")
        back_button.clicked.connect(lambda: self.central_widget.setCurrentWidget(self.next_maintenance_tab))
        layout.addWidget(back_button)

        self.next_maintenance_electric_table = QTableWidget()
        self.next_maintenance_electric_table.setColumnCount(5)
        self.next_maintenance_electric_table.setHorizontalHeaderLabels(["Kode", "Nama Mesin", "Frequency Pemeriksaan", "Date", "Next Maintenance Date"])
        self.next_maintenance_electric_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.next_maintenance_electric_table)

    def setup_history_tab(self):
        self.history_layout = QVBoxLayout()
        self.history_tab.setLayout(self.history_layout)

        # Create combo boxes for filtering
        filter_layout = QHBoxLayout()

        # Membuat QComboBox untuk labor
        self.search_by_labor_combo_history = QComboBox()
        self.search_by_labor_combo_history.addItem("All")
        self.search_by_labor_combo_history.currentIndexChanged.connect(self.apply_filters_history)
        filter_layout.addWidget(QLabel("Search by Labor:"))
        filter_layout.addWidget(self.search_by_labor_combo_history)

        self.search_by_name_combo_history = QComboBox()
        self.search_by_name_combo_history.addItem("All")
        self.search_by_name_combo_history.currentIndexChanged.connect(self.apply_filters_history)
        filter_layout.addWidget(QLabel("Search by Nama Mesin:"))
        filter_layout.addWidget(self.search_by_name_combo_history)

        self.search_by_part_combo_history = QComboBox()
        self.search_by_part_combo_history.addItem("All")
        self.search_by_part_combo_history.currentIndexChanged.connect(self.apply_filters_history)
        filter_layout.addWidget(QLabel("Search by Bagian Mesin:"))
        filter_layout.addWidget(self.search_by_part_combo_history)

        self.search_by_month_combo_history = QComboBox()
        self.search_by_month_combo_history.addItem("All")
        self.search_by_month_combo_history.addItems(["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"])
        self.search_by_month_combo_history.currentIndexChanged.connect(self.apply_filters_history)
        filter_layout.addWidget(QLabel("Search by Month:"))
        filter_layout.addWidget(self.search_by_month_combo_history)

        self.history_layout.addLayout(filter_layout)

        # History Table
        self.history_table = CustomTableWidget()
        self.history_table.setColumnCount(11)
        self.history_table.setHorizontalHeaderLabels(["Labor", "Nama Mesin", "Bagian Mesin", "Frequency Pemeriksaan", "Deskripsi Pemeriksaan", "Spare Part", "Part Number", "Standard", "Date", "Next Maintenance Date", "Status"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.itemClicked.connect(self.on_status_button_clicked)  # Assuming you have or will have this method
        self.history_layout.addWidget(self.history_table)

        # Initially populate the combo boxes with data
        self.populate_combo_history(self.search_by_labor_combo_history, 'labor')
        self.populate_combo_history(self.search_by_name_combo_history, 'machine')
        self.populate_combo_history(self.search_by_part_combo_history, 'part')

        # Populate the history table with data (you can add this function)
        self.populate_history_tab()

    def open_next_maintenance_electric(self):
      self.central_widget.setCurrentWidget(self.next_maintenance_electric_tab)

    def apply_filters(self):
        # Use a dictionary to store active filters
        self.active_filters = {}

        # Check if a specific labor is selected
        selected_labor = self.search_by_labor_combo_output.currentText()
        if selected_labor != "All":
            self.active_filters["labor"] = selected_labor

        # Check if a specific machine name is selected
        selected_name = self.search_by_name_combo_output.currentText()
        if selected_name != "All":
            self.active_filters["name"] = selected_name

        # Check if a specific machine part is selected
        selected_part = self.search_by_part_combo_output.currentText()
        if selected_part != "All":
            self.active_filters["bagian_mesin"] = selected_part

        # Apply the filters and update the table
        self.populate_output_tab(self.active_filters)



    def apply_filters_next_maintenance(self):
        # Ambil nilai dari setiap QComboBox
        selected_labor = self.search_by_labor_combo.currentText()
        selected_name = self.search_by_name_combo.currentText()
        selected_part = self.search_by_part_combo.currentText()
        selected_month = self.month_filter_combo.currentText()

        for row in range(self.next_maintenance_table.rowCount()):
            machine_labor_item = self.next_maintenance_table.item(row, 0)
            machine_name_item = self.next_maintenance_table.item(row, 0)
            part_name_item = self.next_maintenance_table.item(row, 1)
            date_item = self.next_maintenance_table.item(row, 8)  # Anda mungkin perlu menyesuaikan indeks kolom

            should_display = True
            if selected_labor != "All" and machine_labor_item.text() != selected_labor:
                should_display = False
            elif selected_name != "All" and machine_name_item.text() != selected_name:
                should_display = False
            elif selected_part != "All" and part_name_item.text() != selected_part:
                should_display = False
            elif selected_month != "All":
                try:
                    date = datetime.datetime.strptime(date_item.text(), "%Y-%m-%d")
                    if date.strftime("%B") != selected_month:
                        should_display = False
                except ValueError:
                    should_display = False

            self.next_maintenance_table.setRowHidden(row, not should_display)

    def apply_filters_history(self):
        try:
            selected_labor_history = self.search_by_labor_combo_history .currentText()
            selected_name_history = self.search_by_name_combo_history.currentText()
            selected_part_history = self.search_by_part_combo_history.currentText()
            selected_month_history = self.search_by_month_combo_history.currentText()

            for row in range(self.history_table.rowCount()):
                labor_item = self.history_table.item(row, 0)
                machine_name_item = self.history_table.item(row, 1)
                machine_part_item = self.history_table.item(row, 2)
                date_item = self.history_table.item(row, 9)  # Sesuaikan indeks kolom dengan kebutuhan

                should_display = True

                if selected_labor_history != "All" and labor_item and labor_item.text() != selected_labor_history:
                    should_display = False

                if selected_name_history != "All" and machine_name_item and machine_name_item.text() != selected_name_history:
                    should_display = False

                if should_display and selected_part_history != "All" and machine_part_item and machine_part_item.text() != selected_part_history:
                    should_display = False

                if should_display and selected_month_history != "All" and date_item:
                    date = datetime.datetime.strptime(date_item.text(), "%Y-%m-%d")
                    month_name = date.strftime("%B")
                    if month_name != selected_month_history:
                        should_display = False

                self.history_table.setRowHidden(row, not should_display)

        except Exception as e:
            print("Error in apply_filters_history:", e)
            import traceback
            print(traceback.format_exc())

    


    def filter_by_name_next_maintenance_electric(self):
        search_text = self.search_input_electric.text().lower()

        for row in range(self.next_maintenance_electric_table.rowCount()):
            machine_name_item = self.next_maintenance_electric_table.item(row, 1)

            if machine_name_item:
                machine_name = machine_name_item.text().lower()

                if search_text in machine_name:
                    self.next_maintenance_electric_table.setRowHidden(row, False)
                else:
                    self.next_maintenance_electric_table.setRowHidden(row, True)    

    def sort_next_maintenance_table(self):
        self.next_maintenance_table.sortItems(5)  # Urutkan berdasarkan kolom "Next Maintenance Date"

    def sort_next_maintenance_electric_table(self):
        self.next_maintenance_electric_table.sortItems(5)  # Urutkan berdasarkan kolom "Next Maintenance Date"


    def delete_inner_frame(self, frame):
        try:
            # Temukan index dari frame yang ingin dihapus dalam layout
            index_to_remove = -1
            for i in range(self.container_layout.count()):
                if self.container_layout.itemAt(i).widget() == frame:
                    index_to_remove = i
                    break

            print("Index to remove:", index_to_remove)  # Menambahkan print statement

            if index_to_remove == -1:  # Jika frame tidak ditemukan
                return

            # Hapus input fields yang berhubungan dengan frame yang dihapus
            del self.details_inputs[index_to_remove]
            del self.standard_inputs[index_to_remove]
            del self.spare_part_inputs[index_to_remove]
            del self.part_number_inputs[index_to_remove]
            if not sip.isdeleted(self.maintenance_date_inputs[index_to_remove]):
                del self.maintenance_date_inputs[index_to_remove]
            else:
                print(f"Maintenance Date Input {index_to_remove} is already deleted")

            # Anda mungkin juga memiliki list lain yang perlu Anda hapus itemnya di sini

            # Hapus frame dari layout
            widget_to_remove = self.container_layout.takeAt(index_to_remove).widget()
            if widget_to_remove:
                widget_to_remove.deleteLater()

        except Exception as e:
            print("Error in delete_inner_frame:", e)
            import traceback
            print(traceback.format_exc())  # Ini akan mencetak stack trace untuk memberikan konteks error


    def add_entry(self):
        if not self.validate_inputs():
            return

        labor = self.labor_combo.currentText()  # Menambahkan baris ini untuk mengambil teks dari combo box labor
        name = self.name_input.text()
        bagian_mesin = self.bagian_mesin_input.text()
        frequency_pemeriksaan = self.frequency_pemeriksaan_combo.currentText()

        if name and bagian_mesin:
            try:
                initial_maintenance_date = None 

                for i in range(len(self.details_inputs)):
                    deskripsi = self.details_inputs[i].text()
                    standard = self.standard_inputs[i].text() if i < len(self.standard_inputs) else ""
                    spare_part = self.spare_part_inputs[i].text() if i < len(self.spare_part_inputs) else ""
                    part_number = self.part_number_inputs[i].text() if i < len(self.part_number_inputs) else ""

                    if i < len(self.maintenance_date_inputs) and not sip.isdeleted(self.maintenance_date_inputs[i]):
                        maintenance_date = datetime.datetime.strptime(self.maintenance_date_inputs[i].date().toString("yyyy-MM-dd"), "%Y-%m-%d")
                        print(f"Maintenance date from input {i}: {maintenance_date}")
                        if i == 0:
                            initial_maintenance_date = maintenance_date  
                    else:
                        if initial_maintenance_date:
                            maintenance_date = initial_maintenance_date 
                            print(f"Using initial maintenance date: {maintenance_date}")
                        else:
                            print("Error: No initial maintenance date found.")
                            return

                    if deskripsi:
                        frequency_pemeriksaan_days = self.frequency_pemeriksaan_to_days(frequency_pemeriksaan)
                        total_iterations = 365 // frequency_pemeriksaan_days

                        for j in range(total_iterations):
                            next_maintenance_date = maintenance_date + datetime.timedelta(days=frequency_pemeriksaan_days * (j+1))
                            next_maintenance_date_str = next_maintenance_date.strftime("%Y-%m-%d")

                            if not part_number:
                                part_number = "N/A"

                            query = """
                            INSERT INTO machinePM (labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, date, next_maintenance_date, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            # Menambahkan 'labor' ke tuple parameter query
                            self.db_manager.execute_query(query, (labor, name, bagian_mesin, frequency_pemeriksaan, deskripsi, spare_part, part_number, standard, maintenance_date.strftime("%Y-%m-%d"), next_maintenance_date_str, "Start"))

                            row_position = self.table.rowCount()
                            self.table.insertRow(row_position)
                            self.table.setItem(row_position, 0, QTableWidgetItem(labor))  # Menambahkan baris ini untuk menampilkan labor di tabel
                            self.table.setItem(row_position, 1, QTableWidgetItem(name))
                            self.table.setItem(row_position, 8, QTableWidgetItem(maintenance_date.strftime("%Y-%m-%d")))
                            self.table.setItem(row_position, 9, QTableWidgetItem(next_maintenance_date_str))
                            self.table.setItem(row_position, 10, QTableWidgetItem("Start"))

                self.populate_combo_output(self.search_by_labor_combo_output, 'labor')
                self.populate_combo_output(self.search_by_name_combo_output, 'machine')
                self.populate_combo_output(self.search_by_part_combo_output, 'part')

                self.populate_combo_next_maintenance(self.search_by_labor_combo, 'labor')
                self.populate_combo_next_maintenance(self.search_by_name_combo, 'machine')
                self.populate_combo_next_maintenance(self.search_by_part_combo, 'part')
                
                self.populate_combo_history(self.search_by_labor_combo_history, 'labor')
                self.populate_combo_history(self.search_by_name_combo_history, 'machine')
                self.populate_combo_history(self.search_by_part_combo_history, 'part')
                self.sort_next_maintenance_table()
                self.reset_input_fields()
                self.remove_additional_inner_frames()

            except ValueError:
                print("Error: Unable to add entry due to ValueError")
                return
            except Exception as e:
                print(f"Error: {e}")
                return


    def add_entry_electric(self):
        kode = self.kode_input_electric.text()
        name_electric = self.name_input_electric.text()
        frequency_pemeriksaan = self.frequency_pemeriksaan_combo_electric.currentText()

        if kode and name_electric:
            try:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                
                # Tambahkan loop untuk memasukkan 5 jadwal pemeliharaan
                for _ in range(5):
                    next_date = datetime.datetime.strptime(date, "%Y-%m-%d")

                    # Convert the Frequency choice to the number of days
                    frequency_pemeriksaan_days = self.frequency_pemeriksaan_to_days(frequency_pemeriksaan)
                    next_date += datetime.timedelta(days=frequency_pemeriksaan_days)
                    next_maintenance_date = next_date.strftime("%Y-%m-%d")

                    # Prepare the SQL query to insert data into the ElectricPM table
                    query = """
                    INSERT INTO ElectricPM (kode, name, frequency_pemeriksaan, date, next_maintenance_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    # Execute the query using the DatabaseManager
                    self.db_manager.execute_query(query, (kode, name_electric, frequency_pemeriksaan, date, next_maintenance_date))

                    # Update the GUI table for Output Electric
                    row_position = self.output_electric_table.rowCount()
                    self.output_electric_table.insertRow(row_position)
                    self.output_electric_table.setItem(row_position, 0, QTableWidgetItem(kode))
                    self.output_electric_table.setItem(row_position, 1, QTableWidgetItem(name_electric))
                    self.output_electric_table.setItem(row_position, 2, QTableWidgetItem(frequency_pemeriksaan))
                    self.output_electric_table.setItem(row_position, 3, QTableWidgetItem(date))
                    self.output_electric_table.setItem(row_position, 4, QTableWidgetItem(next_maintenance_date))
                    
                    # Update the date for the next iteration
                    date = next_maintenance_date

            except ValueError:
                return

        # Reset the input fields
        self.reset_input_fields_electric()


    # Metode untuk menghapus inner frames tambahan
    def remove_additional_inner_frames(self):
        # Ambil jumlah total inner frames
        total_inner_frames = self.container_layout.count()

        # Mulai dari yang terakhir, hapus hingga satu yang tersisa
        for i in range(total_inner_frames - 1, 0, -1):
            widget_to_remove = self.container_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.deleteLater()
                self.container_layout.removeItem(self.container_layout.itemAt(i))

        # Reset input field yang tersisa
        if self.details_inputs:
            self.details_inputs[0].clear()
        if self.standard_inputs:
            self.standard_inputs[0].clear()
        if self.spare_part_inputs:
            self.spare_part_inputs[0].clear()
        if self.part_number_inputs:
            self.part_number_inputs[0].clear()

        # Menghapus dari list juga
        while len(self.details_inputs) > 1:
            self.details_inputs.pop().deleteLater()
            self.standard_inputs.pop().deleteLater()
            self.spare_part_inputs.pop().deleteLater()
            self.part_number_inputs.pop().deleteLater()

        # Reset input field pertama
        self.details_inputs[0].clear()
        self.standard_inputs[0].clear()
        self.spare_part_inputs[0].clear()
        self.part_number_inputs[0].clear()
        
    def reset_input_fields(self):
        # Mengatur ulang input fields ke nilai default
        self.name_input.clear()
        self.bagian_mesin_input.clear()
        
        # Mengatur ulang self.frequency_pemeriksaan_combo
        self.frequency_pemeriksaan_combo.setCurrentIndex(0)  # Pilih opsi "Pilih Frequency"


    def reset_input_fields_electric(self):
        # Reset the input fields for the "Electric" tab
        self.kode_input_electric.clear()
        self.name_input_electric.clear()
        self.frequency_pemeriksaan_combo_electric.setCurrentIndex(0) 

    def update_maintenance_entries(self):
                    pass


    def filter_by_month_next_maintenance_electric(self):
        selected_month_text = self.month_filter_combo.currentText()
        selected_month_index = self.month_filter_combo.currentIndex()

        for row in range(self.next_maintenance_electric_table.rowCount()):
            next_maintenance_date_item = self.next_maintenance_electric_table.item(row, 3)  # Kolom "Next Maintenance Date"

            if next_maintenance_date_item:
                next_maintenance_date = next_maintenance_date_item.text()
                month = datetime.datetime.strptime(next_maintenance_date, "%Y-%m-%d").strftime("%B")

                if selected_month_index == 0 or month == selected_month_text:
                    self.next_maintenance_electric_table.setRowHidden(row, False)
                else:
                    self.next_maintenance_electric_table.setRowHidden(row, True)
    
    def frequency_pemeriksaan_to_days(self, frequency_pemeriksaan):
        # Fungsi ini mengonversi pilihan Frequency menjadi jumlah hari
        if frequency_pemeriksaan == "1 Minggu":
            return 7
        elif frequency_pemeriksaan == "2 Minggu":
            return 14
        elif frequency_pemeriksaan == "1 Bulan":
            return 30
        elif frequency_pemeriksaan == "3 Bulan":
            return 90
        elif frequency_pemeriksaan == "6 Bulan":
            return 180
        elif frequency_pemeriksaan == "1 Tahun":
            return 365
        else:
            return 30  # Default jika tidak ada yang cocok
           
    def validate_inputs(self):
        # Validasi untuk Labor
        selected_labor = self.labor_combo.currentText()
        if selected_labor == "Pilih Area / Labor":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Area / Labor!")
            return False
        # Validasi untuk Name
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required!")
            return False

        # Validasi untuk Bagian Mesin
        bagian_mesin = self.bagian_mesin_input.text().strip()
        if not bagian_mesin:
            QMessageBox.warning(self, "Validation Error", "Bagian Mesin is required!")
            return False

        # Validasi untuk Frequency Pemeriksaan
        selected_frequency = self.frequency_pemeriksaan_combo.currentText()
        if selected_frequency == "Pilih Frequency":
            QMessageBox.warning(self, "Validation Error", "Please select a valid Frequency Pemeriksaan!")
            return False

        # Loop through each spare part input to validate
        for spare_part_input in self.spare_part_inputs:
            if isinstance(spare_part_input, QLineEdit):
                spare_part = spare_part_input.text().strip()
                if not spare_part:
                    QMessageBox.warning(self, "Validation Error", "Spare Part is required for every entry!")
                    return False

        for detail_input in self.details_inputs:
            deskripsi = detail_input.text().strip() if isinstance(detail_input, QLineEdit) else ""
            if not deskripsi:
                QMessageBox.warning(self, "Validation Error", "Deskripsi is required!")
                return False

        for standard in self.standard_inputs:
            std_value = standard.text().strip() if isinstance(standard, QLineEdit) else ""
            if not std_value:
                QMessageBox.warning(self, "Validation Error", "Standard is required!")
                return False

        return True

        
def main():
    app = QApplication(sys.argv)
    window = MaintenanceApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
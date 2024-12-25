import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import serial
import threading
import time
import re

class SerialApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle ESP32")

        # Variáveis para exibir os dados
        self.var_x = tk.StringVar(value="X: --")
        self.var_y = tk.StringVar(value="Y: --")
        self.var_z = tk.StringVar(value="Z: --")
        self.var_rps = tk.StringVar(value="RPS: --")
        self.var_encsin = tk.StringVar(value="ENCSIN: --")

        # Variáveis para controle
        self.running = False
        self.esp = None

        # Variável de status da conexão
        self.connection_status = tk.StringVar(value="Desconectado")
        self.connection_color = "red"

        # Layout da interface
        self.create_widgets()

    def create_widgets(self):
        # Configurações da porta serial
        config_frame = tk.Frame(self.root)
        config_frame.pack(pady=10)

        tk.Label(config_frame, text="Porta COM:").grid(row=0, column=0, padx=5)
        self.com_port = ttk.Combobox(config_frame, values=self.get_serial_ports(), width=10)
        self.com_port.grid(row=0, column=1, padx=5)
        self.com_port.set("COM3")  # Valor padrão

        tk.Label(config_frame, text="Baud Rate:").grid(row=0, column=2, padx=5)
        self.baud_rate = ttk.Combobox(config_frame, values=["9600", "115200"], width=10)
        self.baud_rate.grid(row=0, column=3, padx=5)
        self.baud_rate.set("9600")  # Valor padrão

        # Status da conexão
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10)
        tk.Label(status_frame, text="Status da Conexão:").grid(row=0, column=0, padx=5)
        self.status_label = tk.Label(status_frame, textvariable=self.connection_status, bg=self.connection_color, width=10, font=("Arial", 12))
        self.status_label.grid(row=0, column=1, padx=5)

        # Painel de informações
        data_frame = tk.Frame(self.root)
        data_frame.pack(pady=10)
        tk.Label(data_frame, textvariable=self.var_x, font=("Arial", 14)).pack(pady=5)
        tk.Label(data_frame, textvariable=self.var_y, font=("Arial", 14)).pack(pady=5)
        tk.Label(data_frame, textvariable=self.var_z, font=("Arial", 14)).pack(pady=5)
        tk.Label(data_frame, textvariable=self.var_rps, font=("Arial", 14)).pack(pady=5)
        tk.Label(data_frame, textvariable=self.var_encsin, font=("Arial", 14)).pack(pady=5)

        # Botões de controle
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Estabelecer Conexão", command=self.establish_connection, font=("Arial", 12)).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="START", command=lambda: self.send_command("START"), font=("Arial", 12)).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="STOP", command=lambda: self.send_command("STOP"), font=("Arial", 12)).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Fechar Conexão", command=self.close_connection, font=("Arial", 12)).grid(row=0, column=3, padx=5)

    def get_serial_ports(self):
        """Retorna uma lista de portas COM disponíveis (Windows)."""
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def update_status(self, status, color):
        """Atualiza o LED de status."""
        self.connection_status.set(status)
        self.status_label.config(bg=color)

    def establish_connection(self):
        """Estabelece a conexão com a porta serial."""
        try:
            port = self.com_port.get()
            baud = int(self.baud_rate.get())
            self.esp = serial.Serial(port, baud, timeout=1)
            self.running = True
            self.update_status("Conectado", "green")
            threading.Thread(target=self.read_serial, daemon=True).start()
        except serial.SerialException as e:
            messagebox.showerror("Erro", f"Erro ao estabelecer conexão: {e}")
            self.update_status("Desconectado", "red")

    def calculate_crc(self, data):
        """Calcula o CRC (checksum) da string recebida."""
        crc = 0
        for char in data:
            crc ^= ord(char)  # XOR simples
        return crc

    def read_serial(self):
        """Lê os dados da serial continuamente."""
        while self.running:
            if self.esp and self.esp.inWaiting() > 0:
                message = self.esp.readline().decode().strip()
                self.process_message(message)
            time.sleep(0.1)

    def process_message(self, message):
        """Processa as mensagens recebidas e verifica o CRC."""
        # Padrão esperado: [TAG] DADO[CRC]
        pattern = r"\[(\w+)\] ([^\[]+)\[(\d+)\]"
        match = re.match(pattern, message)

        if match:
            tag = match.group(1)  # TAG
            data = match.group(2)  # DADO
            crc_received = int(match.group(3))  # CRC recebido

            # Calcula o CRC esperado
            crc_calculated = self.calculate_crc(data)

            if crc_calculated == crc_received:
                # Atualiza os valores com base na TAG
                if tag == "MPU":
                    parts = data.split()
                    for part in parts:
                        key, value = part.split('=')
                        if key == "X":
                            self.var_x.set(f"X: {value}")
                        elif key == "Y":
                            self.var_y.set(f"Y: {value}")
                        elif key == "Z":
                            self.var_z.set(f"Z: {value}")
                elif tag == "RPS":
                    self.var_rps.set(f"RPS: {data}")
                elif tag == "ENCSIN":
                    self.var_encsin.set(f"ENCSIN: {data}")
            else:
                print(f"[{tag}] Dado inválido! CRC calculado ({crc_calculated}) não corresponde ao CRC recebido ({crc_received}).")
        else:
            print("Formato de mensagem inválido.")

    def send_command(self, command):
        """Envia comandos ao ESP32."""
        if self.esp and self.esp.is_open:
            self.esp.write((command + '\n').encode())
        else:
            messagebox.showerror("Erro", "Conexão não estabelecida.")

    def close_connection(self):
        """Fecha a conexão serial."""
        if self.esp and self.esp.is_open:
            self.running = False
            self.esp.close()
            self.update_status("Desconectado", "red")
        else:
            messagebox.showerror("Erro", "Conexão já está encerrada.")

# Inicializa a interface gráfica
root = tk.Tk()
app = SerialApp(root)
root.mainloop()

import re
from socket import *
class LEEDDevice:
    def __init__(self, leed_host='129.217.168.64', leed_port=4004):
        if not self.is_valid_ip(leed_host):
            raise ValueError("Invalid IP address")
        self.leed_server_host = leed_host
        self.leed_server_port = leed_port
        self.device_socket = socket(AF_INET, SOCK_STREAM)
        self.connection_established=self.connect_to_device()
        self.valid_ip=self.validate_leed_ip(ip_address=self.leed_server_host)

    def validate_leed_ip(self, ip_address):
        if self.is_valid_ip(ip_address):
            self.valid_ip=True
            return True
        else:
            self.valid_ip=False
            return False

    def is_valid_ip(self, ip):
        ip_regex = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return bool(re.match(ip_regex, ip))

    def connect_to_device(self):
        try:
            self.device_socket.connect((self.leed_server_host, self.leed_server_port))
            return True
        except ConnectionRefusedError:
            raise ConnectionError("Could not connect to the LEED device")
            return False
    def send_energy(self, energy):
        try:
            command = f'VEN{float(energy)}\r'
            result=self.send_command(command)
            return result
        except OSError:
            return f"Error sending command. The device returned {result}"
    def read_energy(self):
        try:
            command = f'REN\r'
            result = self.send_command(command)
            return result
        except OSError:
            return f"Error sending command. The device returned {result}"
    def send_command(self, command):
        try:
            self.device_socket.send(command.encode())
            data_set = self.device_socket.recv(256)
            return data_set.decode('utf-8')
        except OSError:
            return f"Error sending command. The device returned {data_set}"

    def change_ip_address(self, new_ip):
        if self.is_valid_ip(new_ip):
            if not self.connection_established:  # Check if connection is not yet established
                try:
                    self.device_socket.connect((new_ip, self.leed_server_port))
                    self.leed_server_host = new_ip
                    self.valid_ip = True
                    self.connection_established = True  # Update connection status
                except ConnectionRefusedError:
                    self.valid_ip = False
                    raise ConnectionError("Could not connect to the LEED device with the new IP")
            else:
                # If connection is already established, update IP and close the current connection
                self.leed_server_host = new_ip
                self.valid_ip = True
                self.close_connection()
                self.device_socket = socket(AF_INET, SOCK_STREAM)
        else:
            self.valid_ip = False
            raise ValueError("Invalid IP address. IP change was not possible.")
    def close_connection(self):
        self.device_socket.close()
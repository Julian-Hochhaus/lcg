import re
import select
import time
from socket import *
class LEEDDevice:
    def __init__(self, leed_host='129.217.168.64', leed_port=4004):
        if not self.is_valid_ip(leed_host):
            raise ValueError("Invalid IP address")
        self.leed_host = leed_host
        self.leed_port = leed_port
        self.device_socket = socket(AF_INET, SOCK_STREAM)
        #self.device_socket.setblocking(0)
        self.connection_established=self.connect_to_device()
        self.valid_ip=self.validate_leed_ip(ip_address=self.leed_host)

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
            self.device_socket.connect((self.leed_host, self.leed_port))
            return True
        except ConnectionRefusedError:
            raise ConnectionError("Could not connect to the LEED device")
            return False
    def send_energy(self, energy):
        max_attempts = 20
        attempts = 0
        while attempts < max_attempts:
            try:
                command = f'VEN{float(energy)}\r'
                state= self.send_command(command)
                if state:
                    return state
                else:
                    raise ValueError(
                        f"Setting the energy was not sucessful!")

            except OSError:
                attempts += 1
                return f"Error setting energy."
            except ValueError as ve:
                attempts += 1
                print(f"ValueError: {ve}. Retrying... (Attempt {attempts}/{max_attempts})")
    def send_ramp(self, ramp):
        try:
            command = f'VRA{float(ramp)}\r'
            result=self.send_command(command)
            return result
        except OSError:
            return f"Error setting ramp."
    def read_screen(self):
        try:
            command = f'RSC'
            state, value=self.read_device_property(command)
            return state, value[2]
        except OSError as e:
            return f"Error reading Screen state: {str(e)}"
    def read_ramp(self):
        try:
            command = f'RRA'
            state, value=self.read_device_property(command)
            return state, value
        except OSError as e:
            return f"Error reading Ramp: {str(e)}"
    def read_cathode(self):
        try:
            command = f'RCA'
            state, value = self.read_device_property(command)
            return state, value[2]
        except OSError as e:
            return f"Error reading Cathode state: {str(e)}"

    def read_device_property(self, command_type):
        max_attempts = 5
        attempts = 0
        while attempts < max_attempts:
            try:
                command = f'{command_type}\r'
                result=self.send_and_read_msg(command=command.encode())
                if result is not None:
                    result = result.decode('utf-8')
                    if command in result:
                        if self.regex_prop_off(result):
                            return False, result
                        else:
                            numbers = self.regex_prop_actual_values(result)
                            if len(numbers) == 5:
                                return True, numbers
                            else:
                                raise ValueError(f"The LEED did not return the expected result reading the {command_type} voltage. Pattern matching failed.")
                    else:
                        raise ValueError(f"The LEED did not return the expected result reading the {command_type} voltage. Pattern matching failed.")
            except OSError as e:
                attempts += 1
                print(f"Error reading {command_type} state: {str(e)}. Retrying... (Attempt {attempts}/{max_attempts})")
            except ValueError as ve:
                attempts += 1
                print(f"ValueError: {ve}. Retrying... (Attempt {attempts}/{max_attempts})")

    def read_energy(self):
        try:
            command = f'REN'
            state, value = self.read_device_property(command)
            return state, value[3]
        except OSError as e:
            return f"Error reading Energy: {str(e)}"
    def read_beam_current(self):
        try:
            command = f'RI0'
            state, value = self.read_device_property(command)
            return state, value[-1]
        except OSError as e:
            return f"Error reading beam current: {str(e)}"
    def read_collector(self):
        try:
            command = f'RCO'
            state, value = self.read_device_property(command)
            return state, value
        except OSError as e:
            return f"Error reading Collector: {str(e)}"
    def regex_prop_off(self, input_text):
        pattern = re.compile(
            r"[A-Za-z]+\s+[A-Za-z]+\s+off",
            re.IGNORECASE)
        return pattern.match(input_text)

    def regex_prop_actual_values(self, input_text):
        pattern = re.compile(r'[\+\-](?:[^\d]*([\d]*[\.\d]*[eE+-]*[\d]+|[\d]*)){5}')
        match = pattern.search(input_text)
        if match:
            matched_sequence = match.group(0)
            #print(matched_sequence)
            numbers = re.findall(r'[\+\-](?:[^\d]*([\d]*[\.\d]*[eE+-]*[\d]+|[\d]*))', matched_sequence)
            return numbers
        else:
            raise ValueError("No matching sequence found in the input text.")


    def get_value_command(self, command):
        max_attempts = 5
        attempts = 0
        while attempts < max_attempts:
            try:
                state=self.send_msg(command.encode())
                if state:
                    return state
                else:
                    raise ValueError( f"Sending command was not successful.")
            except OSError:
                return f"Error sending command."
            except ValueError as ve:
                attempts += 1
                print(f"ValueError: {ve}. Retrying... (Attempt {attempts}/{max_attempts})")
    def send_command(self, command):
        try:
            state=self.send_msg(command.encode())
            return state
        except OSError:
                return f"Error sending command."
    def change_ip_address(self, new_ip):
        if self.is_valid_ip(new_ip):
            if not self.connection_established:  # Check if connection is not yet established
                try:
                    self.device_socket.connect((new_ip, self.leed_port))
                    self.leed_host = new_ip
                    self.valid_ip = True
                    self.connection_established = True  # Update connection status
                except ConnectionRefusedError:
                    self.valid_ip = False
                    raise ConnectionError("Could not connect to the LEED device with the new IP")
            else:
                # If connection is already established, update IP and close the current connection
                self.leed_host = new_ip
                self.valid_ip = True
                self.close_connection()
                self.device_socket = socket(AF_INET, SOCK_STREAM)
        else:
            self.valid_ip = False
            raise ValueError("Invalid IP address. IP change was not possible.")

    def send_msg(self, msg):
        bytes=len(msg)
        send_bytes,state=self.send_all(msg)
        if bytes== send_bytes and state==None:
            return True
        else:
            return False

    def send_and_read_msg(self, command):
        bytes_len = len(command)
        send_bytes, state = self.send_all(command)

        if bytes_len == send_bytes and state is None:
            while True:
                # Check if the socket is ready to be read
                ready_to_read, _, _ = select.select([self.device_socket], [], [], 0.5)  # 0.5-second timeout
                if self.device_socket in ready_to_read:
                    msg = self.recv_msg()
                    if msg:
                        # Wait for the expected end sign
                        if b'\r\n>' in msg:
                            if command in msg:
                                return msg

                # If timeout occurred or unexpected data, continue waiting or raise an exception
                else:
                    print("Timeout occurred while waiting for data")
                    return None

        else:
            return None


    def send_all(self, data):
        ret = self.device_socket.send(data)
        if ret > 0:
            return ret, self.send_all(data[ret:])
        else:
            return None

    def recv_msg(self):
        msg = self.recvall()
        return msg

    def recvall(self, end_sign=b'\r\n>'):
        data = bytearray()
        while not end_sign in data:
            ready_to_read, _, _ = select.select([self.device_socket], [], [], 0.5)  # 0.5-second timeout
            if self.device_socket in ready_to_read:
                packet = self.device_socket.recv(1)
                if not packet:
                    return None
                data += packet
            else:
                print("Timeout occurred while waiting for data")
                return None
        return data

    def close_connection(self):
        self.device_socket.close()
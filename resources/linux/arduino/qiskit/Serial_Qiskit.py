import json
import time
import glob
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import QiskitRuntimeService, Sampler
from qiskit_aer import Aer
from serial import Serial


def find_arduino_port() -> str:
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    if not ports:
        print("No Arduino found.")
        return ""
    print(ports[0])
    return ports[0]


def configure_ibm_token(token: str) -> bytes:
    QiskitRuntimeService.save_account(token, overwrite=True)
    print("IBM Quantum token configured.")
    return json.dumps({"status": "IBM token configured"}).encode('utf-8')


def generate_superposition_qubits_simulated(num_qubits: int) -> list[int]:
    circuit = QuantumCircuit(num_qubits, num_qubits)
    circuit.h(range(num_qubits))
    circuit.measure(range(num_qubits), range(num_qubits))

    simulator = Aer.get_backend('qasm_simulator')
    #sampler = Sampler(simulator)
    job = simulator.run([circuit])
    result = job.result()
    counts = result.get_counts()

    return list(map(int, list(counts.keys())[0]))


def start_serial_connection(baudrate: int = 9600) -> None | Serial | Serial:
    port = find_arduino_port()
    if not port:
        print("No Arduino found. retrying...")
        start_serial_connection(baudrate)
        return None

    arduino = Serial(port, baudrate, timeout=1)
    time.sleep(2)  # Allow time for connection establishment
    print(f"Connected to {port}")
    return arduino


def execute_command(data: str) -> bytes | None:
    command = json.loads(data)
    if command["action"] == "start_job":
        return start_job_command(command.get("num_qubits", 1))
    elif command["action"] == "configure_ibm":
        return configure_ibm_token(command["token"])


def start_job_command(num_qubits: int) -> bytes:
    result = generate_superposition_qubits_simulated(num_qubits)
    response = json.dumps({"job_result": result})
    return response.encode('utf-8')


def send_response(arduino: Serial, data: bytes) -> None:
    print("Response: ", data)
    arduino.reset_input_buffer()
    arduino.write(data)


def process_serial_commands(arduino: Serial) -> None:
    while True:
        if arduino.in_waiting > 0:
            data = arduino.readline().decode('utf-8').strip()

            try:
                response = execute_command(data)
                if response:
                    send_response(arduino, response)

            except json.JSONDecodeError:
                arduino.write(json.dumps({"error": "Invalid JSON format"}).encode('utf-8'))


if __name__ == "__main__":
    serial_connection = start_serial_connection()
    process_serial_commands(serial_connection)

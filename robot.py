import socket
import threading
import time
import argparse
import threading
import json

client_threads = []
server_threads = []

def handle_server(server_host, server_port, robot_id, host, port):

    # Artificial delay
    time.sleep(3)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))
        print(f"Robot {robot_id}: Connected to server {server_host}:{server_port}")
        
        message = {
            'sender_id': robot_id,
            'sender_host': host,
            'sender_port': port,
            'message': f"Hello from robot {robot_id}!"
        }

        client_socket.sendall(json.dumps(message).encode('utf-8'))
        print(f"Robot {robot_id}: Sent message: '{message['message']}' to robot on {server_host}:{server_port}.")
        client_socket.close()

def handle_client(client_socket, robot_id):
    with client_socket:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = json.loads(data.decode('utf-8'))
            print(f"Robot {robot_id}: Received message '{message['message']}' from robot {message['sender_id']}.")
        print(f"Robot {robot_id}: Connection closed.")

def main():
    parser = argparse.ArgumentParser(description="Individual Robot Control")
    parser.add_argument(
        "id",
        help="ID of the robot",
        type=int
    )
    parser.add_argument(
        "host",
        help="Host address of the robot (default: localhost)",
        type=str,
        default="localhost",
        nargs="?"
    )
    parser.add_argument(
        "port",
        help="Port number of the robot (default: 8000)",
        type=int,
        default=8000,
        nargs="?"
    )
    parser.add_argument(
        '--automate',
        help="Automate robot setup (overrides host, port, and test_send)",
        action='store_true'
    )
    parser.add_argument(
        '--test_send',
        help="Test sending data by the robot",
        action='store_true'
    )
    parser.add_argument(
        '--server_host',
        help="Host address of the server (default: localhost)",
        type=str,
        default="localhost",
    )
    parser.add_argument(
        '--server_port',
        help="Port number of the server",
        type=int,
    )

    args = parser.parse_args()
    robot_id = args.id
    host = args.host
    port = args.port
    test_send = args.test_send

    if args.automate:
        with open("setup.json", "r") as f:
            data = json.load(f)
            host = data[str(robot_id)]["host"]
            port = data[str(robot_id)]["port"]
            test_send = data[str(robot_id)]["test_send"]
    
    if test_send:
        server_host = args.server_host
        server_port = args.server_port

    try:    
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            print(f"Robot {robot_id}: Listening on {host}:{port}...")
            if test_send:
                server_thread = threading.Thread(
                    target=handle_server,
                    args=(server_host, server_port, robot_id, host, port)
                )
                server_threads.append(server_thread)
                server_thread.start()
                server_thread.join()
            else:
                pass
            
            while True:
                conn, addr = s.accept()
                print(f"Robot {robot_id}: Accepted connection from {addr}")
                t = threading.Thread(target=handle_client, args=(conn, robot_id))
                client_threads.append(t)
                t.start()
                t.join()
    except KeyboardInterrupt:
        print(f"Robot {robot_id}: Shutting down...")
        for t in client_threads:
            t.join()


if __name__ == "__main__":
    main()
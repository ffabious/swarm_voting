import socket
import threading
import time
from datetime import datetime
import argparse
import threading
import json
from pprint import pprint
from enum import Enum
import random

LOG_FILE = "robot_logs.log"

client_threads = []
server_threads = []
robots = {}
topics = {
    1: "Move Up",
    2: "Move Down",
    3: "Move Left",
    4: "Move Right",
    5: "Look Cute",
}

class Topics(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    LOOK_CUTE = 5

def server_loop(socket, robot_id):
    try:
        with socket:
            while True:
                client_socket, addr = socket.accept()
                log_message(f"Robot{robot_id} : Accepted connection from {':'.join(map(str, addr))}.")
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_socket, robot_id)
                )
                client_threads.append(client_thread)
                client_thread.start()
                client_thread.join()
    except KeyboardInterrupt:
        return
    except Exception as e:
        log_message(f"Robot{robot_id} : Error in server loop: {e}")
        exit(1)


def log_message(message):
    log_line = f"[{datetime.now().isoformat()}] {message}\n"
    print(log_line, end="")

    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_line)

def perform_action(action, robot_id):

    # Simulate delay for action
    time.sleep(1)

    if action == Topics.MOVE_UP:
        log_message(f"Robot{robot_id} : Moving Up.")
    elif action == Topics.MOVE_DOWN:
        log_message(f"Robot{robot_id} : Moving Down.")
    elif action == Topics.MOVE_LEFT:
        log_message(f"Robot{robot_id} : Moving Left.")
    elif action == Topics.MOVE_RIGHT:
        log_message(f"Robot{robot_id} : Moving Right.")
    elif action == Topics.LOOK_CUTE:
        log_message(f"Robot{robot_id} : Looking Cute.")
    else:
        log_message(f"Robot{robot_id} : Unknown action '{action}'.")

def handle_action_message(message, robot_id):
    new_message = message.copy()
    host, port = robots[robot_id]["host"], robots[robot_id]["port"]
    new_message['sender_id'] = robot_id
    new_message['sender_host'] = host
    new_message['sender_port'] = port
    return new_message

def handle_vote_message(message, robot_id):
    new_message = message.copy()
    host, port = robots[robot_id]["host"], robots[robot_id]["port"]
    new_message['sender_id'] = robot_id
    new_message['sender_host'] = host
    new_message['sender_port'] = port

    die = random.randint(1, 10)

    topic = Topics(message['poll']['topic']).name

    if die <= 10:
        new_message['poll']['count_for'] += 1
        log_message(f"Robot{robot_id} : Vote for '{topic}' from robot {message['sender_id']}.")
    else:
        new_message['poll']['count_against'] += 1
        log_message(f"Robot{robot_id} : Vote against '{topic}' from robot {message['sender_id']}.")

    return new_message

def handle_server(server_host, server_port, robot_id, message):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))
        log_message(f"Robot{robot_id} : Connected to server {server_host}:{server_port}.")

        client_socket.sendall(json.dumps(message).encode('utf-8'))
        if message['type'] == 'regular':
            log_message(f"Robot{robot_id} : Sent message: '{message['message']}' to robot on {server_host}:{server_port}.")
        else:
            msg_type = message['type']
            topic = Topics(message[msg_type]['topic']).name
            log_message(f"Robot{robot_id} : Sent {msg_type} message on topic '{topic}' to "\
                        f"robot on {server_host}:{server_port}.")
        log_message(f"Robot{robot_id} : Closed connection to server {server_host}:{server_port}.")
        client_socket.close()
    return

def handle_client(client_socket, robot_id):
    with client_socket:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = json.loads(data.decode('utf-8'))
            new_message = None

            # Check message type
            if message['type'] == 'regular':
                # Log the message
                log_message(f"Robot{robot_id} : Received regular message '{message['message']}' " \
                            f"from robot {message['sender_id']}.")

            elif message['type'] == 'poll':
                # Log the poll message
                topic = Topics(message['poll']['topic']).name
                log_message(f"Robot{robot_id} : Received poll message on action '{topic}' " \
                            f"from robot {message['sender_id']}.")
                
                # Handle the poll message
                new_message = handle_vote_message(message, robot_id)

                if new_message['poll']['count_against'] > len(robots) // 2 or \
                    new_message['poll']['count_for'] + new_message['poll']['count_against'] == len(robots):
                    # If yes, log the rejection
                    log_message(f"Robot{robot_id} : Proposal to '{topics(message['poll']['topic'])}' by " \
                                f"robot {message['poll']['initiator_id']} was rejected.")
                    
                elif new_message['poll']['count_for'] > len(robots) // 2:
                    # If yes, perform the action
                    perform_action(Topics(message['poll']['topic']), robot_id)

                    # Propagate the action message
                    new_message = {
                        'sender_id': robot_id,
                        'sender_host': robots[robot_id]['host'],
                        'sender_port': robots[robot_id]['port'],
                        'type': 'action',
                        'action': {
                            'initiator_id': robot_id,
                            'topic': message['poll']['topic']
                        },
                        'message': f"Action '{Topics(message['poll']['topic']).name}' initiated by robot {message['sender_id']}."
                    }
                    
                else:
                    # Continue the poll
                    pass

            elif message['type'] == 'action':
                topic = Topics(message['action']['topic']).name

                # Log the action message
                log_message(f"Robot{robot_id} : Received action message on topic '{topic}' " \
                            f"from robot {message['sender_id']}.")
                
                # If robot is not the initiator, perform the action and propagate the message
                if message['action']['initiator_id'] != robot_id:
                    perform_action(Topics(message['action']['topic']), robot_id)
                    new_message = handle_action_message(message, robot_id)
                # If robot is the initiator, stop propagation
                else:
                    topic = Topics(message['action']['topic']).name
                    log_message(f"Robot{robot_id} : Action '{topic}' " \
                                f"returned to initiator.")
                    new_message = None
            
            else:
                log_message(f"Robot{robot_id} : Unknown message type '{message['type']}' from robot {message['sender_id']}.")
                new_message = None

            if new_message:
                successor_id = robots[robot_id]["successor"]
                successor_host = robots[successor_id]["host"]
                successor_port = robots[successor_id]["port"]
                server_thread = threading.Thread(
                    target=handle_server,
                    args=(successor_host,
                          successor_port,
                          robot_id,
                          new_message)
                )
                server_threads.append(server_thread)
                server_thread.start()
                server_thread.join()
        
            break
    return

def main():
    global client_threads
    global server_threads
    global robots

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
        '-a', '--automate',
        help="Automate robot setup (overrides host, port, and test_send)",
        action='store_true'
    )
    parser.add_argument(
        '-f', '--file',
        help="File containing robot setup data (default: setup3.json)",
        type=str,
        default="setup3.json",
        nargs="?"
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
        with open(args.file, "r") as f:
            data = json.load(f)
            host = data[str(robot_id)]["host"]
            port = data[str(robot_id)]["port"]
            test_send = data[str(robot_id)]["test_send"]
            for id in data.keys():
                robots[int(id)] = {
                    "host": data[id]["host"],
                    "port": data[id]["port"],
                    "successor": data[id]["successor"],
                }

    print(f"Robot{robot_id}: List of comrades:")
    pprint(robots)
    
    if test_send and robots[robot_id]["successor"] != -1:
        successor_id = int(robots[robot_id]["successor"])
        server_host = robots[successor_id]["host"]
        server_port = robots[successor_id]["port"]
    elif test_send:
        server_host = args.server_host
        server_port = args.server_port
    else:
        pass

    try:    
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            log_message(f"Robot{robot_id} : Listening on {host}:{port}...")
            if test_send:
                topic = Topics.LOOK_CUTE

                message = {
                    'sender_id': robot_id,
                    'sender_host': host,
                    'sender_port': port,
                    'type': 'poll',
                    'poll': {
                        'topic': topic.value,
                        'initiator_id': robot_id,
                        'count_for': 1,
                        'count_against': 0
                    },
                    'message': f"Vote for '{topic.name}' from robot {robot_id}."
                }
                server_thread = threading.Thread(
                    target=handle_server,
                    args=(server_host, server_port, robot_id, message)
                )
                server_threads.append(server_thread)
                server_thread.start()
                server_thread.join()
            else:
                pass

            server_thread = threading.Thread(
                target=server_loop,
                args=(s, robot_id)
            )
            server_thread.start()
            server_thread.join()
            
            
    except KeyboardInterrupt:
        log_message(f"Robot{robot_id} : Shutting down...")
        for t in client_threads:
            t.join()


if __name__ == "__main__":
    main()
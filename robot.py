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

from metrics import get_common_log_file, get_log_file, get_metrics_file, RobotMetrics

# Will be defined in main, according to the robot_id
COMMON_LOG_FILE: str
LOG_FILE: str
METRICS_FILE: str
metrics: RobotMetrics

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
                start_time = time.time()

                client_socket, addr = socket.accept()

                end_time = time.time()
                metrics.record_wait_time(end_time - start_time)

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
    with open(COMMON_LOG_FILE, "a") as log_file:
        log_file.write(log_line)

def log_metrics():
    metrics_data = metrics.get_metrics()
    with open(METRICS_FILE, "a") as metrics_file:
        metrics_file.write(f"\n==== Metrics at {datetime.now().isoformat()} ====\n")
        pprint(metrics_data, metrics_file)
        metrics_file.write("\n")

def perform_action(action, robot_id):
    start_time = time.time()

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

    action_time = time.time() - start_time
    metrics.record_action_time(action_time)
    metrics.increment_action_count(action.name)
    log_message(f"Robot{robot_id} : Action '{action.name}' completed in {action_time:.2f} seconds.")

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

    topic = Topics(message['poll']['topic'])
    start_time = time.time()

    die = random.randint(1, 10)

    is_vote_for = die >= 5

    if is_vote_for:
        new_message['poll']['count_for'] += 1
        log_message(f"Robot{robot_id} : Vote for '{topic.name}' from robot {message['sender_id']}.")
    else:
        new_message['poll']['count_against'] += 1
        log_message(f"Robot{robot_id} : Vote against '{topic.name}' from robot {message['sender_id']}.")

    end_time = time.time()
    metrics.record_voting_time(topic.name, end_time - start_time)
    metrics.record_vote(is_vote_for)

    return new_message

def handle_server(server_host, server_port, robot_id, message):
    start_time = time.time()

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

        propog_time = time.time() - start_time
        metrics.record_propagation_time(message['type'], propog_time)
        log_message(f"Robot{robot_id} : Message propagation to the next peer took {propog_time:.2f} seconds.")

        log_message(f"Robot{robot_id} : Closed connection to server {server_host}:{server_port}.")
        client_socket.close()
    return

def handle_client(client_socket, robot_id):
    with client_socket:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break

            receive_time = time.time()
            message = json.loads(data.decode('utf-8'))
            new_message = None

            metrics.increment_message_count(message['type'])
            log_message(f"Robot{robot_id} : Started processing {message['type']} message from robot {message['sender_id']}...")

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
                    log_message(f"Robot{robot_id} : Proposal to '{topics[message['poll']['topic']]}' by " \
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
                    log_message(f"Robot{robot_id} : Poll for {topic} still in progress.")

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
        
            processed_time = time.time() - receive_time
            log_message(f"Robot{robot_id} : Message processed in {processed_time:.2f} seconds.")
            break
    return

def main():
    global client_threads
    global server_threads
    global robots
    global COMMON_LOG_FILE
    global LOG_FILE
    global METRICS_FILE
    global metrics

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

    COMMON_LOG_FILE = get_common_log_file()
    LOG_FILE = get_log_file(robot_id)
    METRICS_FILE = get_metrics_file(robot_id)
    metrics = RobotMetrics(robot_id)

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
        server_host = -1
        server_port = -1

    try:    
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            s.listen()
            log_message(f"Robot{robot_id} : Listening on {host}:{port}...")
            if test_send:
                topic = Topics(random.randint(1, 5))

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
        log_metrics()
        for t in client_threads:
            t.join()


if __name__ == "__main__":
    main()

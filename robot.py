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

# Import custom metrics tracking module
from metrics import get_common_log_file, get_log_file, get_metrics_file, RobotMetrics

# Global variables that will be initialized in main():
COMMON_LOG_FILE: str  # Path to shared log file for all robots
LOG_FILE: str         # Path to individual log file for this robot
METRICS_FILE: str     # Path to file storing this robot's performance metrics
metrics: RobotMetrics # Metrics tracker instance

CONSENSUS_TIMEOUT = 30.0
start_time_shutdown = None
timeout_flag = False

all_vote_against = False


# Lists to keep track of active threads:
client_threads = []  # Threads handling incoming client connections
server_threads = []  # Threads making outgoing server connections

# Dictionary storing information about all robots in the network:
# Format: {robot_id: {"host": str, "port": int, "successor": int}}
robots = {}

# Predefined topics/actions that robots can vote on:
topics = {
    1: "Move Up",
    2: "Move Down",
    3: "Move Left",
    4: "Move Right",
    5: "Look Cute",
}

# Enum version of topics for cleaner code:
class Topics(Enum):
    MOVE_UP = 1
    MOVE_DOWN = 2
    MOVE_LEFT = 3
    MOVE_RIGHT = 4
    LOOK_CUTE = 5

def server_loop(socket, robot_id):
    """
    Main server loop that continuously accepts incoming connections.
    Each connection is handled in a separate thread.
    """
    global timeout_flag, time_start_shutdown
    try:
        with socket:
            while not timeout_flag:
                if start_time_shutdown and (time.time() - start_time_shutdown) > CONSENSUS_TIMEOUT:
                    log_message(f"Robot{robot_id} : Timeout reached in server loop")
                    perform_graceful_shutdown(robot_id)
                # Measure wait time for metrics
                start_time = time.time()
                
                # Accept incoming connection
                client_socket, addr = socket.accept()
                
                # Record connection wait time
                end_time = time.time()
                metrics.record_wait_time(end_time - start_time)
                
                # Log the new connection
                log_message(f"Robot{robot_id} : Accepted connection from {':'.join(map(str, addr))}.")
                
                # Create and start a thread to handle the client
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
    """
    Log a message to both console and log files.
    Writes to:
    - Individual robot log file
    - Common log file shared by all robots
    - Console output
    """
    log_line = f"[{datetime.now().isoformat()}] {message}\n"
    print(log_line, end="")

    # Append to individual log file
    with open(LOG_FILE, "a") as log_file:
        log_file.write(log_line)
    
    # Append to common log file
    with open(COMMON_LOG_FILE, "a") as log_file:
        log_file.write(log_line)

def log_metrics():
    """Record current metrics to the metrics file with a timestamp."""
    metrics_data = metrics.get_metrics()
    with open(METRICS_FILE, "a") as metrics_file:
        metrics_file.write(f"\n==== Metrics at {datetime.now().isoformat()} ====\n")
        pprint(metrics_data, metrics_file)
        metrics_file.write("\n")

def perform_action(action, robot_id):
    """
    Simulate performing a physical robot action.
    Includes:
    - Action execution delay
    - Action-specific logging
    - Metrics recording
    """
    start_time = time.time()

    # Simulate action taking time
    time.sleep(2)

    # Log specific action being performed
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

    # Record metrics about this action
    action_time = time.time() - start_time
    metrics.record_action_time(action_time)
    metrics.increment_action_count(action.name)
    log_message(f"Robot{robot_id} : Action '{action.name}' completed in {action_time:.2f} seconds.")

def perform_graceful_shutdown(robot_id, send_shutdown_to_others=True):
    log_message(f"Robot{robot_id} : Shutting down initiated due to timeout...")

    if send_shutdown_to_others:
        shutdown_msg = {
            "type": "shutdown",
            "sender_id": robot_id
        }
        for rid, info in robots.items():
            if rid != robot_id:
                try:
                    sock = socket.create_connection((info["host"], info["port"]), timeout=2)
                    msg_str = json.dumps(shutdown_msg)
                    sock.sendall(msg_str.encode('utf-8'))
                    sock.close()
                    log_message(f"Robot{robot_id} : Sent shutdown message to robot {rid}")
                except Exception as e:
                    log_message(f"Robot{robot_id} : Failed to send shutdown to robot {rid}: {e}")

    '''current_thread = threading.current_thread()
    for thread in client_threads + server_threads:
        if thread.is_alive() and thread != current_thread:
            thread.join(timeout=1.0)'''

    log_metrics()
    log_message(f"Robot{robot_id} : Gracefully shutted down.")
    exit(0)

def handle_action_message(message, robot_id):
    """
    Prepare an action message for propagation.
    Adds sender information to the message.
    """
    new_message = message.copy()
    host, port = robots[robot_id]["host"], robots[robot_id]["port"]
    new_message['sender_id'] = robot_id
    new_message['sender_host'] = host
    new_message['sender_port'] = port
    return new_message

def handle_vote_message(message, robot_id):
    """
    Process a voting message:
    1. Adds sender information
    2. Simulates random voting (50/50 chance)
    3. Updates vote counts
    4. Records voting metrics
    """
    new_message = message.copy()
    host, port = robots[robot_id]["host"], robots[robot_id]["port"]
    new_message['sender_id'] = robot_id
    new_message['sender_host'] = host
    new_message['sender_port'] = port

    topic = Topics(message['poll']['topic'])
    start_time = time.time()

    # if it is initiator - no voting
    if robot_id == message['poll']['initiator_id']:
        log_message(f"Robot{robot_id} : Initiator already voted for '{topic.name}'.")
    else:
        global all_vote_against
        # tie votes
        if all_vote_against:
            new_message['poll']['count_against'] += 1
            is_vote_for = False
            log_message(f"Robot{robot_id} : Vote against '{topic.name}' (forced by all_vote_against).")
        else:
            # Simulate random voting (50% chance for/against)
            die = random.randint(1, 10)
            is_vote_for = die >= 5

            if is_vote_for:
                new_message['poll']['count_for'] += 1
                log_message(f"Robot{robot_id} : Vote for '{topic.name}' from robot {message['sender_id']}.")
            else:
                new_message['poll']['count_against'] += 1
                log_message(f"Robot{robot_id} : Vote against '{topic.name}' from robot {message['sender_id']}.")

        # Record voting metrics
        end_time = time.time()
        metrics.record_voting_time(topic.name, end_time - start_time)
        metrics.record_vote(is_vote_for)

    return new_message

def handle_server(server_host, server_port, robot_id, message):
    """
    Connect to another robot's server to send a message.
    Handles:
    - Connection establishment
    - Message serialization and sending
    - Propagation time measurement
    """
    global timeout_flag
    start_time = time.time()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        time.sleep(0.5)
        # Connect to target robot
        client_socket.connect((server_host, server_port))
        log_message(f"Robot{robot_id} : Connected to server {server_host}:{server_port}.")

        # Send the JSON message
        client_socket.sendall(json.dumps(message).encode('utf-8'))
        
        # Log based on message type
        if message['type'] == 'regular':
            log_message(f"Robot{robot_id} : Sent message: '{message['message']}' to robot on {server_host}:{server_port}.")
        else:
            msg_type = message['type']
            topic = Topics(message[msg_type]['topic']).name
            log_message(f"Robot{robot_id} : Sent {msg_type} message on topic '{topic}' to "\
                        f"robot on {server_host}:{server_port}.")

        # Record propagation metrics
        propog_time = time.time() - start_time
        metrics.record_propagation_time(message['type'], propog_time)
        log_message(f"Robot{robot_id} : Message propagation to the next peer took {propog_time:.2f} seconds.")

        log_message(f"Robot{robot_id} : Closed connection to server {server_host}:{server_port}.")
        client_socket.close()
    return

def handle_client(client_socket, robot_id):
    """
    Handle incoming messages from connected robots.
    Processes different message types:
    - Regular messages (simple logging)
    - Poll messages (voting)
    - Action messages (command execution)
    """
    global timeout_flag, start_time_shutdown
    with client_socket:
        while not timeout_flag:
            # Receive data from connected robot
            data = client_socket.recv(1024)
            if not data:
                break
            if start_time_shutdown and (time.time() - start_time_shutdown) > CONSENSUS_TIMEOUT:
                log_message(f"Robot{robot_id} : Consensus timeout reached. Shutting down...")
                timeout_flag = True
                perform_graceful_shutdown(robot_id)
                break

            receive_time = time.time()
            message = json.loads(data.decode('utf-8'))
            new_message = None

            # Record message receipt in metrics
            metrics.increment_message_count(message['type'])
            log_message(f"Robot{robot_id} : Started processing {message['type']} message from robot {message['sender_id']}...")

            # Process message based on type
            if message['type'] == 'regular':
                # Simple message - just log it
                log_message(f"Robot{robot_id} : Received regular message '{message['message']}' " \
                            f"from robot {message['sender_id']}.")

            elif message['type'] == 'poll':
                if start_time_shutdown is None and 'start_time' in message['poll']:
                    start_time_shutdown = message['poll']['start_time']
                    log_message(f"Robot{robot_id} : start_time_shutdown set to {start_time_shutdown}")
                    
                # Voting message
                topic = Topics(message['poll']['topic']).name
                log_message(f"Robot{robot_id} : Received poll message on action '{topic}' " \
                            f"from robot {message['sender_id']}.")
                
                # Process the vote
                new_message = handle_vote_message(message, robot_id)

                global consensus_count, CONSENSUS_LIMIT

                # Check voting results
                if new_message['poll']['count_against'] > len(robots) // 2 or \
                    new_message['poll']['count_for'] + new_message['poll']['count_against'] == len(robots):
                    # Majority against or all votes counted - reject proposal
                    log_message(f"Robot{robot_id} : Proposal to '{topics[message['poll']['topic']]}' by " \
                                f"robot {message['poll']['initiator_id']} was rejected.")
                    
                elif new_message['poll']['count_for'] > len(robots) // 2:
                    # Majority for - perform the action
                    perform_action(Topics(message['poll']['topic']), robot_id)


                    # Convert to action message and propagate
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
                    # No majority yet - continue voting
                    log_message(f"Robot{robot_id} : Poll for {topic} still in progress.")

            elif message['type'] == 'action':
                # Action execution message
                topic = Topics(message['action']['topic']).name

                log_message(f"Robot{robot_id} : Received action message on topic '{topic}' " \
                            f"from robot {message['sender_id']}.")
                
                # Only perform action if we're not the original initiator
                if message['action']['initiator_id'] != robot_id:
                    perform_action(Topics(message['action']['topic']), robot_id)
                    new_message = handle_action_message(message, robot_id)
                else:
                    # Message has returned to initiator - stop propagation
                    log_message(f"Robot{robot_id} : Action '{topic}' " \
                                f"returned to initiator.")
                    new_message = None
                    
            elif message['type'] == 'shutdown':             
                perform_graceful_shutdown(robot_id, send_shutdown_to_others=False)
            else:
                # Unknown message type
                log_message(f"Robot{robot_id} : Unknown message type '{message['type']}' from robot {message['sender_id']}.")
                new_message = None

            # Propagate message to next robot if needed
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
        
            # Record message processing time
            processed_time = time.time() - receive_time
            log_message(f"Robot{robot_id} : Message processed in {processed_time:.2f} seconds.")
            if start_time_shutdown and (time.time() - start_time_shutdown) > CONSENSUS_TIMEOUT:
                log_message(f"Robot{robot_id} : Timeout reached after processing in handle_client")
                perform_graceful_shutdown(robot_id)
                return
            break
    return

def main():
    """
    Main execution function:
    1. Parses command line arguments
    2. Initializes logging and metrics
    3. Sets up robot network configuration
    4. Starts server and client threads
    """
    global client_threads
    global server_threads
    global robots
    global COMMON_LOG_FILE
    global LOG_FILE
    global METRICS_FILE
    global metrics

    # Set up command line argument parsing
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
    parser.add_argument(
        '--timeout',
        help="Consensus timeout in seconds (default: 30)",
        type=float,
        default=30.0
    )
    parser.add_argument(
        '--all_vote_against',
        help="Force all robots to always vote against any proposal",
        action='store_true'
    )


    args = parser.parse_args()
    robot_id = args.id
    host = args.host
    port = args.port
    test_send = args.test_send
    global CONSENSUS_TIMEOUT
    CONSENSUS_TIMEOUT = args.timeout
    global start_time_shutdown
    global all_vote_against
    all_vote_against = args.all_vote_against


    # Initialize logging and metrics files
    COMMON_LOG_FILE = get_common_log_file()
    LOG_FILE = get_log_file(robot_id)
    METRICS_FILE = get_metrics_file(robot_id)
    metrics = RobotMetrics(robot_id)

    if start_time_shutdown is None:
        start_time_shutdown = time.time()
        log_message(f"Robot{robot_id} : Consensus timer started (timeout: {CONSENSUS_TIMEOUT}s)")


    # Load robot network configuration if in automated mode
    if args.automate:
        with open(args.file, "r") as f:
            data = json.load(f)
            host = data[str(robot_id)]["host"]
            port = data[str(robot_id)]["port"]
            test_send = data[str(robot_id)]["test_send"]
            for id_str in data.keys():
                info = data[id_str]
                robots[int(id_str)] = {
                    "host": info["host"],
                    "port": info["port"],
                    "successor": info["successor"],
                    "all_vote_against": info.get("all_vote_against", False)
                }
            if not all_vote_against:  # if not stated in CLI
                all_vote_against = robots[robot_id].get("all_vote_against", False)
    print(f"Robot{robot_id}: List of comrades:")
    pprint(robots)
    
    # Determine where to send initial test message
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
            # Bind to specified host and port
            s.bind((host, port))
            s.listen()
            log_message(f"Robot{robot_id} : Listening on {host}:{port}...")
            # If in test mode, send initial message
            if test_send:
                # Randomly select a topic to vote on
                topic = Topics(random.randint(1, 5))

                # Create poll message
                message = {
                    'sender_id': robot_id,
                    'sender_host': host,
                    'sender_port': port,
                    'type': 'poll',
                    'poll': {
                        'topic': topic.value,
                        'initiator_id': robot_id,
                        'count_for': 1,  # Start with 1 vote for (our own vote)
                        'count_against': 0,
                        'start_time':start_time_shutdown
                    },
                    'message': f"Vote for '{topic.name}' from robot {robot_id}."
                }
                
                # Start thread to send the message
                server_thread = threading.Thread(
                    target=handle_server,
                    args=(server_host, server_port, robot_id, message)
                )
                server_threads.append(server_thread)
                server_thread.start()
                server_thread.join()

            # Start main server loop in a thread
            server_thread = threading.Thread(
                target=server_loop,
                args=(s, robot_id)
            )
            server_thread.start()
            server_thread.join()
            
    except KeyboardInterrupt:
        # Handle graceful shutdown
        log_message(f"Robot{robot_id} : Shutting down...")
        log_metrics()
        for t in client_threads:
            t.join()

if __name__ == "__main__":
    main()

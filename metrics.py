from collections import defaultdict
from datetime import datetime
import os
import statistics

# One file for all robots
def get_common_log_file():
    log_dir = "robot_logs"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"all_robots.log")

# Logs file per each robot
def get_log_file(robot_id):
    log_dir = "robot_logs"
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, f"robot_{robot_id}.log")

# Metrics file per each robot
def get_metrics_file(robot_id):
    metrics_dir = "robot_metrics"
    os.makedirs(metrics_dir, exist_ok=True)
    return os.path.join(metrics_dir, f"robot_{robot_id}_metrics.log")

class RobotMetrics:
    """Stores runtime metrics of each robot"""

    def __init__(self, robot_id):
        self.robot_id = robot_id
        # Time to send a message to the next peer. Stored per each msg type.
        self.message_propagation_times = defaultdict(list)
        # Time to vote(make a decision). Stored per each topic
        self.voting_times = defaultdict(list)
        # Time to perform an action
        self.action_execution_times = []
        # Time for waiting a client connection
        self.message_wait_times = []
        # How many times each message type was received. Stored per each msg type
        self.message_counts = defaultdict(int)
        # How many actions were performed. Stored per each action type
        self.action_counts = defaultdict(int)

        self.vote_distribution = {'for': 0, 'against': 0}
        
    def record_propagation_time(self, message_type, time_taken):
        self.message_propagation_times[message_type].append(time_taken)
            
    def record_voting_time(self, topic, time_taken):
        self.voting_times[topic].append(time_taken)
            
    def record_action_time(self, time_taken):
        self.action_execution_times.append(time_taken)
            
    def record_wait_time(self, time_taken):
        self.message_wait_times.append(time_taken)
            
    def increment_message_count(self, message_type):
        self.message_counts[message_type] += 1
            
    def increment_action_count(self, action_type):
        self.action_counts[action_type] += 1
            
    def record_vote(self, is_vote_for):
        if is_vote_for:
            self.vote_distribution['for'] += 1
        else:
            self.vote_distribution['against'] += 1
                
    def get_metrics(self):
        metrics = {
            'robot_id': self.robot_id,
            'timestamp': datetime.now().isoformat(),
            'message_propagation': {
                'average': {k: statistics.mean(v) for k, v in self.message_propagation_times.items() if v},
                'counts': dict(self.message_counts)
            },
            'voting': {
                'average_time': {k: statistics.mean(v) for k, v in self.voting_times.items() if v},
                'distribution': dict(self.vote_distribution)
            },
            'actions': {
                'average_time': statistics.mean(self.action_execution_times) if self.action_execution_times else 0,
                'counts': dict(self.action_counts)
            },
            'client_wait_times': {
                'average': statistics.mean(self.message_wait_times) if self.message_wait_times else 0
            },
        }
        return metrics

# Decision Making in Robot Swarm via Majority Voting

This project implements a decentralized decision-making system for robot swarms using majority voting. Each robot acts as an independent agent that can propose, share, and vote on movement directions. The system enables the swarm to reach collective decisions without any central controller through peer-to-peer communication and consensus algorithms.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Tests](#tests)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Installation

Clone the repository:
   ```bash
   git clone https://github.com/ffabious/swarm_voting.git
   cd swarm-voting
   ```

## Usage
The robot can be configured using command-line arguments:

| Argument             | Type     | Description                                                                 |
|----------------------|----------|-----------------------------------------------------------------------------|
| `id`                 | int      | **(Required)** Unique ID of the robot.                                      |
| `host`               | str      | Host address of the robot. Default: `localhost`.                            |
| `port`               | int      | Port number of the robot. Default: `8000`.                                  |
| `-a`, `--automate`   | flag     | Enable automatic configuration from a JSON file. Overrides host/port/test.  |
| `-f`, `--file`       | str      | Path to the robot setup JSON file. Default: `setup3.json`.                  |
| `--test_send`        | flag     | Enables sending a test message to a peer.                                   |
| `--server_host`      | str      | Host of the peer server (used with `--test_send`). Default: `localhost`.    |
| `--server_port`      | int      | Port of the peer server (used with `--test_send`).                          |
| `--timeout`          | float    | Consensus timeout in seconds. Default: `30.0`.                              |
| `--all_vote_against` | flag     | Forces robot to vote against any proposal (for testing purposes).           |

1. Configure robot network in ```setupN.json```:
    ```json
    {
        "1": {
            "host": "127.0.0.1",
            "port": 8001,
            "successor": 2,
            "all_vote_against": false
        },
        "2": {
            "host": "127.0.0.1",
            "port": 8002,
            "successor": 3,
            "all_vote_against": false
        },
        "...": { 
            /* add as many robots as needed */ 
        }
    }
    ```
2. Run the swarm. For eachrobot ID in ```setupN.json```, launch a process in the background:
    ```bash
    python robot.py -f setupN.json -a 1 &
    python robot.py -f setupN.json -a 2 &
    ...
    ```

## Project Structure

```bash
swarm-voting/
├── robot.py           # Core robot logic and communication
├── metrics.py         # Metrics recording (action times, vote counts, etc.)
├── setup3.json               # Sample setup config (3 robots)
├── setup3_tie.json           # Config causing voting tie
├── setup5.json               # Config for 5 robots
├── robot_logs/              # Generated logs per robot
├── robot_metrics/           # Collected metrics per robot
├── tests/             # Bash scrripts to run swarm with timeout + log/metric validation
└── README.md
```
## Contributing

Feel free to fork the repo, make changes, and submit a pull request. Ensure code is formatted and commented clearly.

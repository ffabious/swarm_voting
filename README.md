# Decision Making in Robot Swarm via Majority Voting

This project implements a decentralized decision-making system for robot swarms using majority voting. Each robot acts as an independent agent that can propose, share, and vote on movement directions. The system enables the swarm to reach collective decisions without any central controller through peer-to-peer communication and consensus algorithms.

## Table of Contents

- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
- [Tests](#tests)
- [Logs & Metrics](#logs--metrics)
- [Metrics Description](#metrics-description)
- [Project Structure](#project-structure)

## Description

## Installation

Clone the repository:
   ```bash
   git clone https://github.com/ffabious/swarm_voting.git
   cd swarm-voting
   ```

## Usage

1. Configure robot network in ```setupN.json```:
    ```json
    {
        "1": {
            "host": "127.0.0.1",
            "port": 8001,
            "successor": 2,
            "all_vote_against": false /* set true if you want to reach tie situation */
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

## Tests

A suite of shell scripts under ```tests/``` automates end-to-end scenarios:

1. Clean up logs: Prepares the environment by removing previous test artifacts

2. Launch robots: Starts the robot swarm with a specific configuration

3. Wait for shutdown

4. Verify the existence metric files and logs

5. Assert correct consensus behavior: Failure or Success in reaching a majority votes

To run tests locally:

    ```bash
    bash tests/test1.sh # setup3.json - 3 robots in the swarm with normal voting behavior
    bash tests/test2.sh # setup3_tie - 3 robots, configured to always vote against
    bash tests/test3.sh # setup5.sh - 5 robots in the swarm with normal voting behavior
    ```
CI integration via GitHub Actions ensures tests are executed on every push/PR.

## Logs & Metrics

1. **robot_logs/**
    * ```robot_<id>.log```: indiviual robor activity.
    * ```all_robots.log```: merged trace.

2. **robot_metrics/**
    * ```robot_<id>_metrics.log```: recorded metrics over time in case of ```CONSENSUS_TIMEOUT``` or ```KeyboardInterrupt```. 

    Example metrics snapshot:

      ```text
      ==== Metrics at 2025-04-29T23:05:03.153870 ==== 
      {
        'actions': {'average_time': 0, 'counts': {}},
        'client_wait_times': {'average': 1.024892857200221},
        'message_propagation': {'average': {'poll': 0.5369115405612521},
                                'counts': {'poll': 18}},
        'robot_id': 1,
        'timestamp': '2025-04-29T23:05:03.149638',
        'voting': {'average_time': {'MOVE_RIGHT': 0.008251163694593642},
                   'distribution': {'against': 5, 'for': 13}}
      }
      ```

## Metrics description

* **robot_ID**: ID of the robot this metric log belongs to.
* **timestamp**: Time when this metrics snapshot was recorded.
* **message_propagation**: average propagation time and number of messages sent per type.\
* **voting**: average time per voting topic and vote distribution summary.
* **actions**: average execution time and counts of specific robot actions.
* **client_wait_times**: average waiting time for a response from a peer robot during client connection attempts.

## Project Structure

```bash
swarm_voting/
├─ robot.py               # Main robot implementation
├─ metrics.py             # Metrics tracking module
├─ setup3.json            # Example 3-robot config
├─ setup5.json            # Example 5-robot config
├─ setup3_tie.json        # Example 3-robot config with tie situation
├─ tests/
│  ├─ test1.sh
│  ├─ test2.sh
│  └─ test3.sh
├─ robot_logs/            # Generated logs
└─ robot_metrics/         # Generated metrics
```
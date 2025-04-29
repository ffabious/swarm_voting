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
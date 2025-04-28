#!/bin/bash

TOTAL_ROBOTS=3

function remove_logs() {
    rm robot_metrics/*.log
    rm robot_logs/*.log
}

function run_robots() {
    python robot.py --file setup3_tie.json --automate 1 &
    python robot.py --file setup3_tie.json --automate 2 &
    python robot.py --file setup3_tie.json --automate 3
}

function analyze_logs() {
    failed_shutdowns=$(grep "Failed to send shutdown" robot_logs/all_robots.log | wc -l)

    if [[ $(grep "Timeout reached in server loop") != "" ]]
    then
        echo "Timeout for swarm voting was exceeded"
        exit 1

    elif [[ $failed_shutdowns != 0 ]]
    then
        echo "$failed_shutdowns robot(s) in the swarm failed to recieve a shutdown message."
        exit 1
    fi
    exit 0
}

function robot_logs_exist() {
    num_robots=$1
    log_directory="robot_logs"

    if [ ! -d $log_directory ]
    then
        echo "Directory '$log_directory' does not exist"
        exit 1
    
    elif [ ! -f "$log_directory/all_robots.log" ]
    then
        echo "File '$log_directory/all_robots.log' does not exist."
        exit 1
    fi

    for ((i=1;i<=n_robots;i++))
    do
        if [ ! -f "$log_directory/robot_$i.log" ]
        then
            echo "Log '$log_directory/robot_$i.log' does not exist"
            exit 1
        fi
    done

    exit 0
}

function metric_logs_exist() {
    num_robots=$1
    metric_directory="robot_metrics"

    if [ ! -d $metric_directory ]
    then
        echo "Directory '$metric_directory' does not exist"
        exit 1
    fi

    for ((i=1;i<=n_robots;i++))
    do
        if [ ! -f "$metric_directory/robot_$i.log" ]
        then
            echo "Log '$metric_directory/robot_$i.log' does not exist"
            exit 1
        fi
    done

    exit 0
}

pkill -9 python
remove_logs
run_robots

metric_logs_exist $TOTAL_ROBOTS
if [[ $? != 0 ]]
then
    echo "Failure: Robot metric logs don't exist"
    exit 1
fi

robot_logs_exist $TOTAL_ROBOTS
if [[ $? != 0 ]]
then
    echo "Failure: Robot logs don't exist"
    exit 1
fi

analyze_logs
if [[ $? != 0 ]]
then
    echo "Failure: Robot swarm failed to reach a majority vote in time"
    exit 1
fi

exit 0
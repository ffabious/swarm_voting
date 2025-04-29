#!/bin/bash

TOTAL_ROBOTS=3
TEST_TIMEOUT=40

function remove_logs() {
    echo "Removing old logs..."
    rm -f robot_metrics/*.log 2>/dev/null || true
    rm -f robot_logs/*.log 2>/dev/null || true

    echo "Logs cleaned up."
}

function run_robots() {
    python3 robot.py -f setup3.json -a 1 &
    python3 robot.py -f setup3.json -a 2 & 
    python3 robot.py -f setup3.json -a 3 &
    
    sleep $TEST_TIMEOUT
}

function analyze_logs() {
    failed_shutdowns=$(grep "Failed to send shutdown" robot_logs/all_robots.log | wc -l)

    if grep -q "Timeout reached in server loop" robot_logs/all_robots.log
    then
        echo "Timeout for swarm voting was exceeded"
        return 1

    elif [[ $failed_shutdowns != 0 ]]
    then
        echo "$failed_shutdowns robot(s) in the swarm failed to recieve a shutdown message."
        return 1
    fi
    return 0
}

function robot_logs_exist() {
    num_robots=$1
    log_directory="robot_logs"

    if [ ! -d $log_directory ]
    then
        echo "Directory '$log_directory' does not exist"
        return 1
    
    elif [ ! -f "$log_directory/all_robots.log" ]
    then
        echo "File '$log_directory/all_robots.log' does not exist."
        return 1
    fi

    for ((i=1;i<=n_robots;i++))
    do
        if [ ! -f "$log_directory/robot_$i.log" ]
        then
            echo "Log '$log_directory/robot_$i.log' does not exist"
            return 1
        fi
    done

    return 0
}

function metric_logs_exist() {
    num_robots=$1
    metric_directory="robot_metrics"

    if [ ! -d $metric_directory ]
    then
        echo "Directory '$metric_directory' does not exist"
        return 1
    fi

    for ((i=1;i<=n_robots;i++))
    do
        if [ ! -f "$metric_directory/robot_$i.log" ]
        then
            echo "Log '$metric_directory/robot_$i.log' does not exist"
            return 1
        fi
    done

    return 0
}

pkill -9 python3
remove_logs

echo "Starting robots (timeout: ${TEST_TIMEOUT}s)..."
run_robots

pkill -9 python3 2>/dev/null || true
echo "Robots stopped, checking logs..."

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

echo "Success: Robots reached majority vote"
exit 0
# Main Control and depot

Main Control coordinates depot use through the ROS 2 Depot Service. Station controllers report physical parking and charging status.

Carry the station and vehicle identifiers on each assignment and result. Define timestamps and failure handling for occupancy changes, arrival, charging start, and charging completion.

Confirm which component owns slot assignment, how conflicting assignments are prevented, and how a stale or unavailable station is represented.

[Software Architecture](https://drive.google.com/file/d/1RhWCWb6gsMU9gWiC0s1vAgbAXr6wrRPA/view) · [System Requirements SR-025 and SR-033–034](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330/System+Requirements+SR)

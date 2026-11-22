# Service and vehicle state

Main Control owns service progression. The vehicle reports movement, arrival, and safety stops. The depot reports station occupancy and charging events. A command result, a stop cause, and the current service state are separate observations.

The taxi flow covers dispatch, pickup travel, boarding wait, destination travel, arrival wait, and return to the depot. Record pickup arrival and destination arrival separately. Confirm the first integration test's departure condition with the team.

Rental adds parked waiting, return, and time expiry. Confirm when the rental timer starts and how a moving vehicle proceeds after expiry.

Cargo adds travel to the cargo depot and confirmed cart attachment and detachment. Main Control owns these service transitions. The coupling device reports physical completion, and the driving package applies the approved loaded-vehicle configuration.

Review the charging-to-idle guard with the team before using it as a dispatch rule.

[State Architecture](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/8192050/State+Architecture) · [System Requirements](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330/System+Requirements+SR)

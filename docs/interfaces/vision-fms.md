# Vision and Main Control

The vehicle Camera Streamer sends images to the AI Interface over UDP. The AI Interface reports perception results to Main Control over HTTP.

Define how vehicle and camera IDs, frame references, capture timestamps, confidence, and the coordinate frame are represented. Agree on how to detect stale or missing results and how to report disagreement between the map and perception.

Confirm how valid perception results reach the driving package and who owns the freshness checks at each boundary.

[Software Architecture](https://drive.google.com/file/d/1RhWCWb6gsMU9gWiC0s1vAgbAXr6wrRPA/view) · [System Requirements SR-013 and SR-026–029](https://k8c1.atlassian.net/wiki/spaces/K8C1sesac/pages/557330/System+Requirements+SR)

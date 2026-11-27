FROM osrf/ros:jazzy-desktop-full@sha256:ae7ad3ac243da1dfd8bd402a2fa08e149ffbf7a385013bd8ef798d0800accdc8

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ROS_LOG_DIR=/tmp/amo-vision-ros
COPY amo_ai_interface/ amo_ai_interface/
USER 10001:10001
ENTRYPOINT ["/ros_entrypoint.sh", "python3", "-m", "amo_ai_interface.ros_ingress"]

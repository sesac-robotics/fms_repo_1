#include "ros_link.h"

#include <micro_ros_arduino.h>
#include <rcl/rcl.h>
#include <rclc/executor.h>
#include <rclc/rclc.h>
#include <rmw_microros/rmw_microros.h>
#include <std_msgs/msg/string.h>

#include "config.h"
#include "secrets.h"

namespace {

// WAITING_WIFI lets loop() keep running the lamps while the access point is joined.
enum class Link : uint8_t { WAITING_WIFI, WAITING_AGENT, AGENT_AVAILABLE, CONNECTED, DISCONNECTED };

char ssid[] = AMO_WIFI_SSID;
char password[] = AMO_WIFI_PASSWORD;
char agentIp[] = AMO_AGENT_IP;

rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;
rcl_publisher_t statePub;
rcl_subscription_t commandSub;
rclc_executor_t executor;
std_msgs__msg__String stateMsg;
std_msgs__msg__String commandMsg;
char commandBuf[64];

Link linkState = Link::WAITING_WIFI;
micro_ros_agent_locator locator;
uint32_t lastPingMs = 0;
CommandHandler onCommand = nullptr;

void commandCallback(const void *msgin) {
  const auto *msg = static_cast<const std_msgs__msg__String *>(msgin);
  size_t n = msg->data.size < sizeof(commandBuf) - 1 ? msg->data.size : sizeof(commandBuf) - 1;
  char text[sizeof(commandBuf)];
  memcpy(text, msg->data.data, n);
  text[n] = '\0';
  if (onCommand) onCommand(text);
}

// Cleanup results are not actionable; consuming them silences warn_unused_result.
void ignore(rcl_ret_t) {}

bool createEntities() {
  allocator = rcl_get_default_allocator();
  rcl_init_options_t initOptions = rcl_get_zero_initialized_init_options();
  if (rcl_init_options_init(&initOptions, allocator) != RCL_RET_OK) return false;
  bool ready = rcl_init_options_set_domain_id(&initOptions, AMO_ROS_DOMAIN_ID) == RCL_RET_OK &&
               rclc_support_init_with_options(&support, 0, nullptr, &initOptions, &allocator) ==
                   RCL_RET_OK;
  ignore(rcl_init_options_fini(&initOptions));
  if (!ready) return false;
  if (rclc_node_init_default(&node, AMO_NODE_NAME, AMO_NODE_NAMESPACE, &support) != RCL_RET_OK) return false;
  // State is resent every period, so best effort keeps a lost Wi-Fi ack from
  // stalling the loop. Commands stay reliable.
  if (rclc_publisher_init_best_effort(&statePub, &node,
                                  ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
                                  AMO_TOPIC_STATE) != RCL_RET_OK) {
    return false;
  }
  if (rclc_subscription_init_default(&commandSub, &node,
                                     ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, String),
                                     AMO_TOPIC_COMMAND) != RCL_RET_OK) {
    return false;
  }
  commandMsg.data.data = commandBuf;
  commandMsg.data.size = 0;
  commandMsg.data.capacity = sizeof(commandBuf);
  executor = rclc_executor_get_zero_initialized_executor();
  if (rclc_executor_init(&executor, &support.context, 1, &allocator) != RCL_RET_OK) return false;
  return rclc_executor_add_subscription(&executor, &commandSub, &commandMsg, &commandCallback,
                                        ON_NEW_DATA) == RCL_RET_OK;
}

void destroyEntities() {
  rmw_context_t *rmwContext = rcl_context_get_rmw_context(&support.context);
  (void)rmw_uros_set_context_entity_destroy_session_timeout(rmwContext, 0);
  ignore(rcl_subscription_fini(&commandSub, &node));
  ignore(rcl_publisher_fini(&statePub, &node));
  ignore(rclc_executor_fini(&executor));
  ignore(rcl_node_fini(&node));
  ignore(rclc_support_fini(&support));
}

bool pingDue(uint32_t now) {
  if (now - lastPingMs < AGENT_PING_PERIOD_MS) return false;
  lastPingMs = now;
  return true;
}

}  // namespace

void rosLinkBegin(CommandHandler handler) {
  onCommand = handler;
  // set_microros_wifi_transports() would block until Wi-Fi joins; start the
  // connection here and register the transport from rosLinkService() instead.
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // Modem sleep adds 100 ms+ latency to every packet.
  WiFi.begin(ssid, password);
  locator.address.fromString(agentIp);
  locator.port = AMO_AGENT_PORT;
  linkState = Link::WAITING_WIFI;
}

bool rosLinkService() {
  uint32_t now = millis();
  switch (linkState) {
    case Link::WAITING_WIFI:
      if (WiFi.status() == WL_CONNECTED) {
        rmw_uros_set_custom_transport(false, &locator, arduino_wifi_transport_open,
                                      arduino_wifi_transport_close, arduino_wifi_transport_write,
                                      arduino_wifi_transport_read);
        linkState = Link::WAITING_AGENT;
      }
      break;
    case Link::WAITING_AGENT:
      if (pingDue(now) && rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, 1) == RMW_RET_OK) {
        linkState = Link::AGENT_AVAILABLE;
      }
      break;
    case Link::AGENT_AVAILABLE:
      if (createEntities()) {
        linkState = Link::CONNECTED;
      } else {
        destroyEntities();
        linkState = Link::WAITING_AGENT;
      }
      break;
    case Link::CONNECTED:
      if (pingDue(now) && rmw_uros_ping_agent(AGENT_PING_TIMEOUT_MS, 3) != RMW_RET_OK) {
        linkState = Link::DISCONNECTED;
        break;
      }
      rclc_executor_spin_some(&executor, RCL_MS_TO_NS(5));
      break;
    case Link::DISCONNECTED:
      destroyEntities();
      linkState = Link::WAITING_AGENT;
      break;
  }
  return linkState == Link::CONNECTED;
}

bool rosLinkPublish(const char *json) {
  if (linkState != Link::CONNECTED) return false;
  stateMsg.data.data = const_cast<char *>(json);
  stateMsg.data.size = strlen(json);
  stateMsg.data.capacity = stateMsg.data.size + 1;
  return rcl_publish(&statePub, &stateMsg, nullptr) == RCL_RET_OK;
}

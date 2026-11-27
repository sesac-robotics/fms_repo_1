"""Present a vehicle's reported values without deriving dispatch authority."""

from .i18n import Text, display_time
from .models import Vehicle
from .vision_readings import VisionReading, vehicle_vision_summary


def vehicle_details(
    vehicle: Vehicle, vision: tuple[VisionReading, ...], tr: Text
) -> dict[str, str]:
    """Format SI telemetry, Seoul receipt time and the separate dispatch setting."""
    unknown = tr('unknown')
    setting = vehicle.dispatch_enabled
    battery = vehicle.battery_percent
    position = vehicle.position_m
    return {
        'vehicle_no': vehicle.number,
        'status': tr.status(vehicle.status),
        'battery': f'{battery:g}%' if battery is not None else unknown,
        'connection': tr.status(vehicle.connection),
        'stop_reason': tr.status(vehicle.stop_reason),
        'vision_reading': vehicle_vision_summary(vision, vehicle.number, tr),
        'dispatch_setting': (
            tr('dispatch_allowed' if setting else 'dispatch_blocked')
            if setting is not None
            else unknown
        ),
        # The snapshot carries no authoritative route-specific assessment.
        'dispatch_eligibility': unknown,
        'observation_received_at': (
            display_time(vehicle.sample[2]) if vehicle.sample else unknown
        ),
        'position': (
            f'{position[0]:.3f}, {position[1]:.3f} m'
            if position is not None
            else unknown
        ),
        'reported_yaw': (
            f'{vehicle.yaw_rad:.3f} rad' if vehicle.yaw_rad is not None else unknown
        ),
        'reported_speed': (
            f'{vehicle.speed_mps:.3f} m/s' if vehicle.speed_mps is not None else unknown
        ),
    }

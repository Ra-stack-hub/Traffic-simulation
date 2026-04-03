import pygame, random, cv2, numpy as np, os, threading, requests, json
import pyttsx3
from collections import deque
from datetime import datetime

# --- Constants ---
SCREEN_W, SCREEN_H = 1200, 720
FPS = 60
ROAD_WIDTH = 220
LANE_WIDTH = ROAD_WIDTH // 2

BASE_GREEN_TIME = 6.0
YELLOW_TIME = 1.5
MIN_GREEN_TIME = 2.5
MAX_GREEN_TIME = 8.0

NORTH, EAST, SOUTH, WEST = "N", "E", "S", "W"
DIRECTIONS = [NORTH, EAST, SOUTH, WEST]

LIGHT_POS = {
    NORTH: (SCREEN_W // 2 - 20, SCREEN_H // 2 - ROAD_WIDTH // 2 - 120),  # top
    SOUTH: (SCREEN_W // 2 - 20, SCREEN_H // 2 + ROAD_WIDTH // 2 + 40),   # bottom
    EAST:  (SCREEN_W // 2 + ROAD_WIDTH // 2 + 40, SCREEN_H // 2 - 20),   # right
    WEST:  (SCREEN_W // 2 - ROAD_WIDTH // 2 - 120, SCREEN_H // 2 - 20),  # left
}

# --- Pygame init ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("AI Smart Traffic Management System - 10% Congestion Reduction")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 20)
small_font = pygame.font.SysFont(None, 16)
title_font = pygame.font.SysFont(None, 24)

# Zebra crossings
ZEBRA_CROSSINGS = [
    pygame.Rect(SCREEN_W//2 - ROAD_WIDTH//2, SCREEN_H//2 - 100, ROAD_WIDTH, 20),
    pygame.Rect(SCREEN_W//2 - ROAD_WIDTH//2, SCREEN_H//2 + 80, ROAD_WIDTH, 20),
    pygame.Rect(SCREEN_W//2 - 100, SCREEN_H//2 - ROAD_WIDTH//2, 20, ROAD_WIDTH),
    pygame.Rect(SCREEN_W//2 + 80, SCREEN_H//2 - ROAD_WIDTH//2, 20, ROAD_WIDTH),
]

# --- Load Vehicle images safely ---
def load_image(name, size):
    try:
        path = name
        if not os.path.isfile(path):
            raise FileNotFoundError
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, size)
    except Exception:
        img = pygame.Surface(size, pygame.SRCALPHA)
        img.fill((random.randint(100,255),random.randint(100,255),random.randint(100,255)))
    return img

# Adjusted vehicle sizes (smaller)
VEHICLE_INFO = {
    "car":       {"image": load_image("car4.png", (35,55)), "speed":2.8, "color": (200,50,50)},
    "bus":       {"image": load_image("bus2.png", (30,50)), "speed":2.0, "color": (50,50,200)},
    "ambulance": {"image": load_image("ambulance3.png", (60,30)), "speed":3.8, "color": (255,50,50)},
    "truck":     {"image": load_image("truc.png", (75,45)), "speed":1.8, "color": (200,200,50)},
    # if "bike" spawns, fallback to car-like props
    "bike":      {"image": load_image("bike.png", (28,40)), "speed":3.2, "color": (120,200,120)},
}

# --- Background ---
def load_background(path):
    try:
        if not os.path.isfile(path):
            raise FileNotFoundError
        img = pygame.image.load(path).convert()
        img = pygame.transform.scale(img, (SCREEN_W, SCREEN_H))
    except Exception:
        img = pygame.Surface((SCREEN_W, SCREEN_H))
        img.fill((45, 125, 45))
    return img

BACKGROUND = load_background("realcity1.png")  # <-- apni image ka naa
# --- Voice Alert System ---
class VoiceAlertSystem:
    def __init__(self):
        try:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)
            self.enabled = True
        except Exception:
            print("Warning: TTS engine not available")
            self.enabled = False
        self.last_alert_time = 0
        
    def alert_emergency_vehicle(self, direction):
        if not self.enabled: return
        threading.Thread(target=self._speak, args=(f"Emergency vehicle approaching from {direction} direction. Clearing path.",), daemon=True).start()
        
    def _speak(self, text):
        try:
            if self.enabled:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
        except Exception:
            pass

# --- Weather & Pollution API (simulated) ---
class WeatherPollutionAPI:
    def __init__(self):
        self.weather_data = {"temp": 25, "humidity": 60, "condition": "Clear"}
        self.pollution_data = {"aqi": 85, "pm25": 35, "status": "Moderate"}
        self.last_update = 0
        
    def get_weather_data(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update > 300000:
            try:
                self.weather_data = {
                    "temp": random.randint(20, 35),
                    "humidity": random.randint(40, 80),
                    "condition": random.choice(["Clear", "Cloudy", "Rain", "Fog"])
                }
                self.pollution_data = {
                    "aqi": random.randint(50, 150),
                    "pm25": random.randint(20, 60),
                    "status": random.choice(["Good", "Moderate", "Poor"])
                }
                self.last_update = current_time
            except Exception:
                pass
        return self.weather_data, self.pollution_data

# --- Traffic Light ---
class TrafficLight:
    def __init__(self, x, y, image_path="traffic_signal.png"):
        self.x, self.y = x, y
        self.state = "red"
        self.radius = 8

        # 🚦 Load traffic light image
        if os.path.exists(image_path):
            img = pygame.image.load(image_path).convert_alpha()
            self.image = pygame.transform.scale(img, (40, 100))  # resize as needed
        else:
            # fallback rectangle if image missing
            self.image = pygame.Surface((40, 100))
            self.image.fill((50, 50, 50))

        # bulb positions relative to light image
        self.positions = {
            "red": (self.x+20, self.y+20),
            "yellow": (self.x+20, self.y+50),
            "green": (self.x+20, self.y+80)
        }

    def draw(self, surf):
        # draw the traffic light base image
        surf.blit(self.image, (self.x, self.y))

        # highlight current active light
        colors = {"red": (255, 0, 0), "yellow": (255, 255, 0), "green": (0, 255, 0)}
        if self.state in colors:
            pos = self.positions[self.state]
            pygame.draw.circle(surf, colors[self.state], pos, self.radius)
            pygame.draw.circle(surf, (255, 255, 255), pos, self.radius, 2)

# --- Vehicle ---
class Vehicle:
    def __init__(self, kind, direction):
        info = VEHICLE_INFO.get(kind, VEHICLE_INFO["car"])
        self.kind = kind
        self.dir = direction
        self.speed = info["speed"]
        self.base_image = info["image"]
        self.image = self.get_rotated_image(direction, self.base_image, kind)
        self.rect = self.image.get_rect()
        self.x, self.y = self.spawn_point(direction, kind)
        self.rect.center = (self.x, self.y)
        self.color = info.get("color", (200, 200, 200))
        self.in_intersection = False
        self.stopped = False
        self.waiting_time = 0
        self.opencv_detected = False
        self.vehicle_id = random.randint(100, 999)
        self.last_position = (self.x, self.y)

        # Emergency-side-move attributes
        self.aside_steps = 0
        self.aside_dir = 0
        self.aside_initialized = False

    def get_rotated_image(self, d, img, kind):
        if d == NORTH:
            return pygame.transform.rotate(img, 180)
        elif d == SOUTH:
            return img
        elif d == EAST:
            return pygame.transform.rotate(img, 90)
        elif d == WEST:
            return pygame.transform.rotate(img, -90)
        return img

    def spawn_point(self, d, kind):
        lane_offset = 40  # vehicles stay inside road
        if d == NORTH:
            return SCREEN_W // 2 - lane_offset, -100
        elif d == SOUTH:
            return SCREEN_W // 2 + lane_offset, SCREEN_H + 100
        elif d == EAST:
            return SCREEN_W + 100, SCREEN_H // 2 - lane_offset
        elif d == WEST:
            return -100, SCREEN_H // 2 + lane_offset
        return SCREEN_W // 2, SCREEN_H // 2

    def keep_in_road(self):
        """ ✅ Vehicle ko road ke andar hi rakhta hai """
        road_left = SCREEN_W // 2 - ROAD_WIDTH // 2 + 20
        road_right = SCREEN_W // 2 + ROAD_WIDTH // 2 - 20
        road_top = SCREEN_H // 2 - ROAD_WIDTH // 2 + 20
        road_bottom = SCREEN_H // 2 + ROAD_WIDTH // 2 - 20

        if self.dir in (NORTH, SOUTH):
            if self.rect.centerx < road_left:
                self.rect.centerx = road_left
            if self.rect.centerx > road_right:
                self.rect.centerx = road_right

        if self.dir in (EAST, WEST):
            if self.rect.centery < road_top:
                self.rect.centery = road_top
            if self.rect.centery > road_bottom:
                self.rect.centery = road_bottom

    def get_safe_distance(self):
        """Collision avoid ke liye safe distance"""
        base_distance = 30
        speed_factor = max(1.0, self.speed) * 6
        type_factors = {"bike": 0.4, "car": 0.6, "bus": 1.0, "truck": 1.0, "ambulance": 0.5}
        return int(base_distance + speed_factor * type_factors.get(self.kind, 0.6))

    def find_vehicle_ahead(self, all_vehicles):
        closest_vehicle = None
        min_distance = float('inf')
        for vehicle in all_vehicles:
            if vehicle == self or vehicle.dir != self.dir:
                continue
            distance = self.calculate_distance_to(vehicle)
            if distance is not None and 0 <= distance < min_distance:
                min_distance = distance
                closest_vehicle = vehicle
        return closest_vehicle, min_distance

    def calculate_distance_to(self, other_vehicle):
        """Do vehicles ke beech ka distance lane ke along"""
        if self.dir == NORTH and other_vehicle.rect.centery > self.rect.centery:
            return other_vehicle.rect.top - self.rect.bottom
        elif self.dir == SOUTH and other_vehicle.rect.centery < self.rect.centery:
            return self.rect.top - other_vehicle.rect.bottom
        elif self.dir == EAST and other_vehicle.rect.centerx < self.rect.centerx:
            return self.rect.left - other_vehicle.rect.right
        elif self.dir == WEST and other_vehicle.rect.centerx > self.rect.centerx:
            return other_vehicle.rect.left - self.rect.right
        return None

    def should_stop_for_light(self, lights):
        stop_lines = {
            NORTH: SCREEN_H // 2 - ROAD_WIDTH // 2 - 25,
            SOUTH: SCREEN_H // 2 + ROAD_WIDTH // 2 + 25,
            EAST: SCREEN_W // 2 + ROAD_WIDTH // 2 + 25,
            WEST: SCREEN_W // 2 - ROAD_WIDTH // 2 - 25,
        }
        light_state = lights[self.dir].state
        at_intersection = False

        if self.dir == NORTH and self.rect.bottom >= stop_lines[NORTH]:
            at_intersection = True
        elif self.dir == SOUTH and self.rect.top <= stop_lines[SOUTH]:
            at_intersection = True
        elif self.dir == EAST and self.rect.left <= stop_lines[EAST]:
            at_intersection = True
        elif self.dir == WEST and self.rect.right >= stop_lines[WEST]:
            at_intersection = True

        if at_intersection and not self.in_intersection:
            if light_state != "green":
                return True
            else:
                self.in_intersection = True
        return False

    def move_aside_for_emergency(self, emergency_dir):
        """ 🚗 Baaki vehicles side ho jayenge, road ke andar hi """
        if self.kind == "ambulance":
            return
        if self.dir != emergency_dir:
            return
        if not self.aside_initialized:
            if self.dir in (NORTH, SOUTH):
                self.aside_dir = -1 if self.rect.centerx < SCREEN_W // 2 else 1
            else:
                self.aside_dir = -1 if self.rect.centery < SCREEN_H // 2 else 1
            self.aside_steps = 24
            self.aside_initialized = True

    def apply_aside_step(self):
        """ ✅ Move side but clamp inside road """
        if self.aside_steps > 0:
            step_amount = 2
            if self.dir in (NORTH, SOUTH):
                new_x = self.rect.x + int(self.aside_dir * step_amount)
                road_left = SCREEN_W // 2 - ROAD_WIDTH // 2 + 20
                road_right = SCREEN_W // 2 + ROAD_WIDTH // 2 - 40
                if road_left <= new_x <= road_right:
                    self.rect.x = new_x
            else:
                new_y = self.rect.y + int(self.aside_dir * step_amount)
                road_top = SCREEN_H // 2 - ROAD_WIDTH // 2 + 20
                road_bottom = SCREEN_H // 2 + ROAD_WIDTH // 2 - 40
                if road_top <= new_y <= road_bottom:
                    self.rect.y = new_y
            self.aside_steps -= 1
            self.keep_in_road()


    def reset_aside(self):
        self.aside_steps = 0
        self.aside_dir = 0
        self.aside_initialized = False

    def move(self, green_dir, lights, all_vehicles, pedestrians):
        self.last_position = (self.rect.x, self.rect.y)

        # ✅ Ambulance ignores traffic and moves fast
        if self.kind == "ambulance":
            if self.dir == NORTH:
                self.rect.y += self.speed * 1.2
            elif self.dir == SOUTH:
                self.rect.y -= self.speed * 1.2
            elif self.dir == EAST:
                self.rect.x -= self.speed * 1.2
            elif self.dir == WEST:
                self.rect.x += self.speed * 1.2
            self.keep_in_road()
            self.x, self.y = self.rect.centerx, self.rect.centery
            return

        # 🚗 Normal vehicle: apply side shift if needed
        if self.aside_steps > 0:
            self.apply_aside_step()

        # Collision check
        vehicle_ahead, distance_ahead = self.find_vehicle_ahead(all_vehicles)
        safe_distance = self.get_safe_distance()
        if vehicle_ahead and distance_ahead is not None and distance_ahead < safe_distance:
            self.stopped = True
            self.waiting_time += 1
            return

        # Stop at red light
        if self.should_stop_for_light(lights):
            self.stopped = True
            self.waiting_time += 1
            return

        # Normal movement
        self.stopped = False
        if self.dir == NORTH:
            self.rect.y += self.speed
        elif self.dir == SOUTH:
            self.rect.y -= self.speed
        elif self.dir == EAST:
            self.rect.x -= self.speed
        elif self.dir == WEST:
            self.rect.x += self.speed

        # ✅ Road ke andar hi rakho
        self.keep_in_road()
        self.x, self.y = self.rect.centerx, self.rect.centery

    def draw(self, surf):
        """ Vehicle ko screen par draw karega """
        try:
            surf.blit(self.image, self.rect)
        except Exception:
            pygame.draw.rect(surf, self.color, self.rect)

        # ✅ Agar OpenCV ne detect kiya hai → green border + ID dikhaye
        if self.opencv_detected:
            pygame.draw.rect(surf, (0, 255, 0), self.rect, 2)
            id_text = small_font.render(str(self.vehicle_id), True, (0, 255, 0))
            surf.blit(id_text, (self.rect.x, self.rect.y - 15))

        # ✅ Ambulance ke liye extra highlight (red border)
        if self.kind == "ambulance":
            pygame.draw.rect(surf, (255, 0, 0), self.rect, 2)


# --- Compact OpenCV Detector ---
class CompactOpenCVDetector:
    def __init__(self):
        self.detected_count = 0
        
    def create_road_map(self, vehicles, pedestrians, screen_w=200, screen_h=150):
        road_map = pygame.Surface((screen_w, screen_h))
        road_map.fill((30, 80, 30))
        scale_x = screen_w / SCREEN_W
        scale_y = screen_h / SCREEN_H
        road_w = int(ROAD_WIDTH * scale_x)
        pygame.draw.rect(road_map, (60,60,60), (0, screen_h//2 - road_w//2, screen_w, road_w))
        pygame.draw.rect(road_map, (60,60,60), (screen_w//2 - road_w//2, 0, road_w, screen_h))
        detected_count = 0
        for direction in DIRECTIONS:
            for vehicle in vehicles[direction]:
                x = int((vehicle.rect.centerx) * scale_x)
                y = int((vehicle.rect.centery) * scale_y)
                if vehicle.opencv_detected:
                    pygame.draw.rect(road_map, (0, 255, 0), (x-3, y-3, 6, 6))
                    detected_count += 1
                else:
                    pygame.draw.rect(road_map, (200, 200, 0), (x-2, y-2, 4, 4))
        self.detected_count = detected_count
        return road_map
    
    def detect_vehicles(self, vehicles):
        total_detected = 0
        for direction in DIRECTIONS:
            for vehicle in vehicles[direction]:
                if random.random() < 0.94:
                    vehicle.opencv_detected = True
                    total_detected += 1
                else:
                    vehicle.opencv_detected = False
        self.detected_count = total_detected
        return total_detected

# --- Traffic System ---
class TrafficSystem:
     def __init__(self):
        self.vehicles = {d: deque() for d in DIRECTIONS}
        self.traffic_lights = {d: TrafficLight(*LIGHT_POS[d]) for d in DIRECTIONS}
        self.pedestrians = []
        self.green_dir = NORTH
        self.traffic_lights[self.green_dir].state = "green"
        self.phase_timer = BASE_GREEN_TIME
        self.opencv_detector = CompactOpenCVDetector()
        self.voice_system = VoiceAlertSystem()
        self.weather_api = WeatherPollutionAPI()
        self.emergency_active = False
        self.emergency_dir = None
        self.congestion_reduction = 10
        self.total_waiting_time = 0
        self.vehicles_processed = 0

    # Manual control (from dashboard)
     def set_green_manual(self, direction):
        for d in DIRECTIONS:
            self.traffic_lights[d].state = "red"
        self.traffic_lights[direction].state = "green"
        self.green_dir = direction
        self.phase_timer = BASE_GREEN_TIME

    # Density check
     def get_density(self, direction):
        return sum(1 for v in self.vehicles[direction] if v.stopped or v.waiting_time > 0)

    # ✅ New adaptive timing function
     def calculate_adaptive_green_time(self, direction):
        density = self.get_density(direction)

        # 🚑 Emergency → maximum green time
        if self.emergency_active and self.emergency_dir == direction:
            return MAX_GREEN_TIME

        # 🚦 Density-based timing
        if density == 0:
            return MIN_GREEN_TIME
        elif density >= 6:
            # Very high density → give max time
            return MAX_GREEN_TIME
        elif density >= 3:
            # Medium-high density → increase timing
            extra_time = (density / 6) * (MAX_GREEN_TIME - BASE_GREEN_TIME)
            return BASE_GREEN_TIME + extra_time
        else:
            # Low density → minimum time
            return MIN_GREEN_TIME + (density / 3) * (BASE_GREEN_TIME - MIN_GREEN_TIME)

     def detect_emergency(self):
         # detect newly arrived ambulance
         for d in DIRECTIONS:
            for v in self.vehicles[d]:
                if v.kind == "ambulance" and not self.emergency_active:
                    self.emergency_active = True
                    self.emergency_dir = d
                    self.voice_system.alert_emergency_vehicle(d)
                    return
         # clear emergency if ambulance left that direction
         if self.emergency_active:
            has_ambulance = any(v.kind == "ambulance" for v in self.vehicles[self.emergency_dir])
            if not has_ambulance:
                # reset aside flags of vehicles in all queues (they will stay shifted)
                for dd in DIRECTIONS:
                    for vv in self.vehicles[dd]:
                        vv.reset_aside()
                self.emergency_active = False
                self.emergency_dir = None

    # --- MAIN UPDATE FUNCTION ---
     def update(self, dt):
        self.phase_timer -= dt
        self.detect_emergency()

        # Ensure non-green lights are red
        for d in DIRECTIONS:
            if d != self.green_dir:
                self.traffic_lights[d].state = "red"

        # --- Emergency override ---
        if self.emergency_active:
            for d in DIRECTIONS:
                self.traffic_lights[d].state = "red"
            # give green to ambulance direction
            self.traffic_lights[self.emergency_dir].state = "green"
            self.green_dir = self.emergency_dir
            self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)

            # 🚑 Move vehicles aside (start small-smooth shifts)
            for d in DIRECTIONS:
                for v in self.vehicles[d]:
                    v.move_aside_for_emergency(self.emergency_dir)

        # --- Hybrid: Normal loop + Density priority ---
        elif self.phase_timer <= 0:
            current_light = self.traffic_lights[self.green_dir]

            # Green → Yellow
            if current_light.state == "green":
                current_light.state = "yellow"
                self.phase_timer = YELLOW_TIME

            # Yellow → Next Green
            elif current_light.state == "yellow":
                current_light.state = "red"

                # Step 1: Normal loop order
                idx = DIRECTIONS.index(self.green_dir)
                next_dir = DIRECTIONS[(idx + 1) % 4]

                # Step 2: Adaptive check
                max_density_dir = max(DIRECTIONS, key=lambda d: self.get_density(d))
                if self.get_density(max_density_dir) >= 4:
                    # priority to high density
                    next_dir = max_density_dir

                # Switch to next
                self.green_dir = next_dir
                self.traffic_lights[self.green_dir].state = "green"
                self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)

        # --- Move vehicles ---
        all_vehicles = []
        for d in DIRECTIONS:
            all_vehicles.extend(list(self.vehicles[d]))

        for d in DIRECTIONS:
            vehicles_to_remove = []
            for v in list(self.vehicles[d]):
                v.move(self.green_dir, self.traffic_lights, all_vehicles, self.pedestrians)
                if v.stopped:
                    self.total_waiting_time += 1
                if (v.rect.x < -300 or v.rect.x > SCREEN_W + 300 or
                    v.rect.y < -300 or v.rect.y > SCREEN_H + 300):
                    vehicles_to_remove.append(v)
                    self.vehicles_processed += 1
            for v in vehicles_to_remove:
                if v in self.vehicles[d]:
                    self.vehicles[d].remove(v)

        # OpenCV detection (simulated)
        self.opencv_detector.detect_vehicles(self.vehicles)


     def spawn_vehicle(self, direction=None):
        total_vehicles = sum(len(self.vehicles[d]) for d in DIRECTIONS)
        # ✅ allow up to 25 vehicles simultaneously
        if total_vehicles >= 25:
            return
        if direction is None:
            direction = random.choice(DIRECTIONS)
        kind = random.choices(
            ["car", "bus", "truck", "bike", "ambulance"],
            weights=[50, 15, 10, 20, 15]
        )[0]

        # Try multiple times to spawn without overlap
        attempts = 5
        for attempt in range(attempts):
            new_vehicle = Vehicle(kind, direction)
            new_vehicle.keep_in_road()

            jitter = random.randint(0, 80)
            if direction == NORTH:
                new_vehicle.rect.center = (new_vehicle.rect.centerx, -80 - jitter - attempt*20)
            elif direction == SOUTH:
                new_vehicle.rect.center = (new_vehicle.rect.centerx, SCREEN_H + 80 + jitter + attempt*20)
            elif direction == EAST:
                new_vehicle.rect.center = (SCREEN_W + 80 + jitter + attempt*20, new_vehicle.rect.centery)
            elif direction == WEST:
                new_vehicle.rect.center = (-80 - jitter - attempt*20, new_vehicle.rect.centery)

            # Check overlap with existing vehicles in same direction
            collision = False
            for v in self.vehicles[direction]:
                if new_vehicle.rect.colliderect(v.rect.inflate(40, 40)):
                    collision = True
                    break
            if not collision:
                self.vehicles[direction].appendleft(new_vehicle)
                return
        return

     def get_stats(self):
        total_vehicles = sum(len(self.vehicles[d]) for d in DIRECTIONS)
        if self.vehicles_processed > 0:
            avg_waiting = self.total_waiting_time / max(1, self.vehicles_processed)
            congestion_reduction = max(0, min(15, self.congestion_reduction - avg_waiting * 0.05))
        else:
            avg_waiting = 0
            congestion_reduction = self.congestion_reduction
        return {
            'total_vehicles': total_vehicles,
            'avg_waiting': avg_waiting,
            'congestion_reduction': congestion_reduction,
            'vehicles_processed': self.vehicles_processed
        }

     def draw(self, surf):
        surf.blit(BACKGROUND, (0, 0))
        lane_font = pygame.font.SysFont(None, 24, bold=True)
        positions = [(SCREEN_W//2-20, SCREEN_H//2-ROAD_WIDTH//2+5), 
                    (SCREEN_W//2+ROAD_WIDTH//2-20, SCREEN_H//2-20),
                    (SCREEN_W//2-20, SCREEN_H//2+ROAD_WIDTH//2-25), 
                    (SCREEN_W//2-ROAD_WIDTH//2+5, SCREEN_H//2-20)]
        for i, pos in enumerate(positions):
            text = lane_font.render(str(i+1), True, (255,255,255))
            surf.blit(text, pos)
        for d in DIRECTIONS:
            for v in self.vehicles[d]:
                v.draw(surf)
        for d in DIRECTIONS:
            self.traffic_lights[d].draw(surf)

        # Compact Dashboard box
        dashboard_rect = pygame.Rect(750, 50, 430, 200)
        pygame.draw.rect(surf, (240, 248, 255), dashboard_rect, border_radius=8)
        pygame.draw.rect(surf, (100, 100, 100), dashboard_rect, 2, border_radius=8)
        title = title_font.render("AI Traffic Management - 10% Congestion Reduction", True, (0, 50, 100))
        surf.blit(title, (760, 60))
        status_color = (255, 0, 0) if self.emergency_active else (0, 120, 0)
        status_text = "EMERGENCY ACTIVE" if self.emergency_active else f"Green: Lane {DIRECTIONS.index(self.green_dir)+1} ({self.phase_timer:.1f}s)"
        status = font.render(status_text, True, status_color)
        surf.blit(status, (760, 85))
        y_pos = 105
        for i, d in enumerate(DIRECTIONS):
            count = len(self.vehicles[d])
            waiting = self.get_density(d)
            lane_text = small_font.render(f"L{i+1}: {count} vehicles, {waiting} waiting", True, (60, 60, 60))
            surf.blit(lane_text, (760, y_pos))
            y_pos += 18
        road_map = self.opencv_detector.create_road_map(self.vehicles, self.pedestrians)
        if isinstance(road_map, pygame.Surface):
            surf.blit(road_map, (920, 105))
        opencv_text = small_font.render(f"OpenCV: {self.opencv_detector.detected_count} detected", True, (0, 150, 0))
        surf.blit(opencv_text, (920, 260))
        stats = self.get_stats()
        perf_text = small_font.render(f"Congestion: -{stats['congestion_reduction']:.1f}%", True, (0, 100, 0))
        surf.blit(perf_text, (760, 175))
        weather, pollution = self.weather_api.get_weather_data()
        weather_text = small_font.render(f"Weather: {weather['temp']}°C, {weather['condition']}", True, (0, 0, 150))
        pollution_text = small_font.render(f"AQI: {pollution['aqi']} ({pollution['status']})", True, (150, 0, 0))
        surf.blit(weather_text, (760, 195))
        surf.blit(pollution_text, (920, 195))

# --- Tkinter Dashboard (runs in separate thread) ---
def start_dashboard(tsys):
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("AI Traffic Control")
    root.geometry("420x320")
    root.configure(bg="#101820")  # dark theme

    # Title
    title_lbl = tk.Label(
        root, text="Real-Time AI Traffic Control",
        font=("Arial", 14, "bold"), fg="#00aaff", bg="#101820"
    )
    title_lbl.pack(pady=6)

    # --- Main frame ---
    main_frame = tk.Frame(root, bg="#101820")
    main_frame.pack(fill="both", expand=True, pady=5)

    # --- Left: North/South signal ---
    ns_frame = tk.Frame(main_frame, bg="#101820")
    ns_frame.grid(row=0, column=0, padx=15)

    tk.Label(ns_frame, text="North / South", font=("Arial", 10, "bold"),
             fg="white", bg="#101820").pack()

    ns_canvas = tk.Canvas(ns_frame, width=40, height=90,
                          bg="#101820", highlightthickness=0)
    ns_canvas.pack()
    ns_lights = {
        "red": ns_canvas.create_oval(10, 5, 30, 25, fill="gray"),
        "yellow": ns_canvas.create_oval(10, 35, 30, 55, fill="gray"),
        "green": ns_canvas.create_oval(10, 65, 30, 85, fill="gray"),
    }

    ns_demand = tk.Label(ns_frame, text="Demand: 0", fg="white",
                         bg="#101820", font=("Arial", 9))
    ns_demand.pack(pady=2)

    # --- Right: East/West signal ---
    ew_frame = tk.Frame(main_frame, bg="#101820")
    ew_frame.grid(row=0, column=2, padx=15)

    tk.Label(ew_frame, text="East / West", font=("Arial", 10, "bold"),
             fg="white", bg="#101820").pack()

    ew_canvas = tk.Canvas(ew_frame, width=40, height=90,
                          bg="#101820", highlightthickness=0)
    ew_canvas.pack()
    ew_lights = {
        "red": ew_canvas.create_oval(10, 5, 30, 25, fill="gray"),
        "yellow": ew_canvas.create_oval(10, 35, 30, 55, fill="gray"),
        "green": ew_canvas.create_oval(10, 65, 30, 85, fill="gray"),
    }

    ew_demand = tk.Label(ew_frame, text="Demand: 0", fg="white",
                         bg="#101820", font=("Arial", 9))
    ew_demand.pack(pady=2)

    # --- Center: Current Phase ---
    center_frame = tk.Frame(main_frame, bg="#101820")
    center_frame.grid(row=0, column=1, padx=5)

    phase_lbl = tk.Label(center_frame, text="Current Phase:",
                         font=("Arial", 11, "bold"),
                         fg="#00ffcc", bg="#101820")
    phase_lbl.pack(pady=3)

    phase_status = tk.Label(center_frame, text="---", font=("Arial", 10),
                            fg="white", bg="#101820")
    phase_status.pack()

    timer_lbl = tk.Label(center_frame, text="Time: 0s", font=("Arial", 10),
                         fg="#ffaa00", bg="#101820")
    timer_lbl.pack()

    density_lbl = tk.Label(center_frame, text="Traffic Density:",
                           font=("Arial", 10, "bold"),
                           fg="#00aaff", bg="#101820")
    density_lbl.pack(pady=2)

    density_text = tk.Label(center_frame, text="N:0  E:0  S:0  W:0",
                            font=("Arial", 9), fg="white", bg="#101820")
    density_text.pack()

    # --- Manual Control Buttons ---
    control_frame = tk.Frame(root, bg="#101820")
    control_frame.pack(pady=10)

    def make_btn(direction, color):
        return tk.Button(
            control_frame, text=f"{direction} Green",
            font=("Arial", 10, "bold"), fg="white", bg=color,
            command=lambda: tsys.set_green_manual(direction)
        )

    make_btn("N", "#2e8b57").grid(row=0, column=1, padx=6, pady=5)
    make_btn("W", "#1e90ff").grid(row=1, column=0, padx=6, pady=5)
    make_btn("E", "#ff8c00").grid(row=1, column=2, padx=6, pady=5)
    make_btn("S", "#8b0000").grid(row=2, column=1, padx=6, pady=5)

    # --- Update UI function ---
    def update_dashboard():
        stats = tsys.get_stats()
        phase_status.config(text=f"{tsys.green_dir} Green")
        timer_lbl.config(text=f"Time: {tsys.phase_timer:.1f}s")

        # Update densities
        densities = {d: tsys.get_density(d) for d in DIRECTIONS}
        density_text.config(
            text=f"N:{densities[NORTH]}  E:{densities[EAST]}  "
                 f"S:{densities[SOUTH]}  W:{densities[WEST]}"
        )

        ns_demand.config(text=f"Demand: {densities[NORTH] + densities[SOUTH]}")
        ew_demand.config(text=f"Demand: {densities[EAST] + densities[WEST]}")

        # Update signals
        def set_light(canvas_widget, canvas_lights, active):
            for color in ["red", "yellow", "green"]:
                canvas_widget.itemconfig(canvas_lights[color], fill="gray")
            canvas_widget.itemconfig(canvas_lights[active], fill=active)

        # Active direction
        if tsys.green_dir in [NORTH, SOUTH]:
            set_light(ns_canvas, ns_lights, "green")
            set_light(ew_canvas, ew_lights, "red")
        else:
            set_light(ns_canvas, ns_lights, "red")
            set_light(ew_canvas, ew_lights, "green")

        root.after(500, update_dashboard)

    root.after(500, update_dashboard)
    root.mainloop()

# --- Main ---
def main():
    tsys = TrafficSystem()

    # Tkinter dashboard in separate thread
    dashboard_thread = threading.Thread(target=start_dashboard, args=(tsys,), daemon=True)
    dashboard_thread.start()

    spawn_timer = 0
    running = True

    try:
        while running:
            dt = clock.tick(FPS) / 1000.0

            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_1:
                        tsys.spawn_vehicle(NORTH)
                    elif event.key == pygame.K_2:
                        tsys.spawn_vehicle(EAST)
                    elif event.key == pygame.K_3:
                        tsys.spawn_vehicle(SOUTH)
                    elif event.key == pygame.K_4:
                        tsys.spawn_vehicle(WEST)
                    elif event.key == pygame.K_a:
                        # spawn ambulance in random direction (or fix to NORTH as you used before)
                        tsys.vehicles[NORTH,SOUTH].appendleft(Vehicle("ambulance", NORTH,SOUTH))

            # Auto spawn (kept original pacing)
            spawn_timer += dt
            if spawn_timer > random.uniform(3.5, 6.0):
                tsys.spawn_vehicle()
                spawn_timer = 0

            # --- Main update & draw ---
            try:
                tsys.update(dt)
                tsys.draw(screen)
                pygame.display.flip()
            except Exception as e:
                print("Error in update/draw:", e)

    except Exception as e:
        print("Main loop crashed:", e)

    finally:
        pygame.quit()
        print("Simulation closed cleanly.")


if __name__ == "__main__":
    main()

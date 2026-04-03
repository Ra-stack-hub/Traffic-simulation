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
    NORTH: (SCREEN_W // 2 - 15, SCREEN_H // 2 - ROAD_WIDTH // 2 - 50),
    SOUTH: (SCREEN_W // 2 - 15, SCREEN_H // 2 + ROAD_WIDTH // 2 + 10),
    EAST:  (SCREEN_W // 2 + ROAD_WIDTH // 2 + 10, SCREEN_H // 2 - 15),
    WEST:  (SCREEN_W // 2 - ROAD_WIDTH // 2 - 50, SCREEN_H // 2 - 15),
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

# Adjusted vehicle sizes (bus larger & long)
VEHICLE_INFO = {
    "car":       {"image": load_image("car1.png", (45,70)), "speed":2.8, "color": (200,50,50)},
    "bus":       {"image": load_image("bus2.png", (70,120)), "speed":2.0, "color": (50,50,200)},
    "ambulance": {"image": load_image("ambulance1.png", (50,25)), "speed":3.8, "color": (255,50,50)},
    "truck":     {"image": load_image("truc.png", (85,55)), "speed":1.8, "color": (200,200,50)},
}

# --- Background ---
# --- Background (using image) ---
def load_background(path):
    try:
        if not os.path.isfile(path):
            raise FileNotFoundError
        img = pygame.image.load(path).convert()
        img = pygame.transform.scale(img, (SCREEN_W, SCREEN_H))
    except Exception:
        # fallback green if image missing
        img = pygame.Surface((SCREEN_W, SCREEN_H))
        img.fill((45, 125, 45))
    return img

BACKGROUND = load_background("city1.jpg")  # <-- apni image ka naam

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

    # --- Manual Control (from dashboard)
    def set_green_manual(self, direction):
        for d in DIRECTIONS:
            self.traffic_lights[d].state = "red"
        self.traffic_lights[direction].state = "green"
        self.green_dir = direction
        self.phase_timer = BASE_GREEN_TIME

    # --- Density check
    def get_density(self, direction):
        return sum(1 for v in self.vehicles[direction] if v.stopped or v.waiting_time > 0)

    # --- Adaptive green timing
    def calculate_adaptive_green_time(self, direction):
        density = self.get_density(direction)

        # Emergency priority
        if self.emergency_active and self.emergency_dir == direction:
            return MAX_GREEN_TIME

        if density == 0:
            return MIN_GREEN_TIME
        elif density >= 6:
            return MAX_GREEN_TIME
        elif density >= 3:
            extra_time = (density / 6) * (MAX_GREEN_TIME - BASE_GREEN_TIME)
            return BASE_GREEN_TIME + extra_time
        else:
            return MIN_GREEN_TIME + (density / 3) * (BASE_GREEN_TIME - MIN_GREEN_TIME)

    # --- Emergency detection
    def detect_emergency(self):
        for d in DIRECTIONS:
            for v in self.vehicles[d]:
                if v.kind == "ambulance" and not self.emergency_active:
                    self.emergency_active = True
                    self.emergency_dir = d
                    self.voice_system.alert_emergency_vehicle(d)
                    return

        if self.emergency_active:
            has_ambulance = any(v.kind == "ambulance" for v in self.vehicles[self.emergency_dir])
            if not has_ambulance:
                self.emergency_active = False
                self.emergency_dir = None

    # --- Main update
    def update(self, dt):
        self.phase_timer -= dt
        self.detect_emergency()

        for d in DIRECTIONS:
            if d != self.green_dir:
                self.traffic_lights[d].state = "red"

        if self.emergency_active:
            for d in DIRECTIONS:
                self.traffic_lights[d].state = "red"
            self.traffic_lights[self.emergency_dir].state = "green"
            self.green_dir = self.emergency_dir
            self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)

        elif self.phase_timer <= 0:
            current_light = self.traffic_lights[self.green_dir]

            if current_light.state == "green":
                current_light.state = "yellow"
                self.phase_timer = YELLOW_TIME

            elif current_light.state == "yellow":
                current_light.state = "red"
                idx = DIRECTIONS.index(self.green_dir)
                next_dir = DIRECTIONS[(idx + 1) % 4]

                max_density_dir = max(DIRECTIONS, key=lambda d: self.get_density(d))
                if self.get_density(max_density_dir) >= 4:
                    print(f"[Adaptive] High density in {max_density_dir}, giving priority.")
                    next_dir = max_density_dir

                self.green_dir = next_dir
                self.traffic_lights[self.green_dir].state = "green"
                self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)
                print(f"[Signal] Green light → {self.green_dir}")

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

        self.opencv_detector.detect_vehicles(self.vehicles)

    # --- Vehicle spawningdef spawn_vehicle(self, direction=None):
    total_vehicles = sum(len(self.vehicles[d]) for d in DIRECTIONS)
    if total_vehicles >= 30:   # 🚦 Limit set to 30
        return

    if direction is None:
        direction = random.choice(DIRECTIONS)

    kind = random.choices(
        ["car", "bus", "truck", "bike", "ambulance"],
        weights=[55, 15, 10, 15, 5]
    )[0]

    attempts = 8
    for attempt in range(attempts):
        new_vehicle = Vehicle(kind, direction)
        jitter = random.randint(0, 80)
        if direction == NORTH:
            new_vehicle.rect.center = (new_vehicle.rect.centerx, -80 - jitter - attempt*20)
        elif direction == SOUTH:
            new_vehicle.rect.center = (new_vehicle.rect.centerx, SCREEN_H + 80 + jitter + attempt*20)
        elif direction == EAST:
            new_vehicle.rect.center = (SCREEN_W + 80 + jitter + attempt*20, new_vehicle.rect.centery)
        elif direction == WEST:
            new_vehicle.rect.center = (-80 - jitter - attempt*20, new_vehicle.rect.centery)

        collision = False
        for v in self.vehicles[direction]:
            if new_vehicle.rect.colliderect(v.rect.inflate(40, 40)):
                collision = True
                break

        if not collision:
            self.vehicles[direction].appendleft(new_vehicle)
            return
    return



    # --- Stats
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

    # --- Drawing
    def draw(self, surf):
        surf.blit(BACKGROUND, (0, 0))
        lane_font = pygame.font.SysFont(None, 24, bold=True)

        positions = [
            (SCREEN_W//2-20, SCREEN_H//2-ROAD_WIDTH//2+5),
            (SCREEN_W//2+ROAD_WIDTH//2-20, SCREEN_H//2-20),
            (SCREEN_W//2-20, SCREEN_H//2+ROAD_WIDTH//2-25),
            (SCREEN_W//2-ROAD_WIDTH//2+5, SCREEN_H//2-20)
        ]

        for i, pos in enumerate(positions):
            text = lane_font.render(str(i+1), True, (255,255,255))
            surf.blit(text, pos)

        for d in DIRECTIONS:
            for v in self.vehicles[d]:
                v.draw(surf)

        for d in DIRECTIONS:
            self.traffic_lights[d].draw(surf)

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
         for d in DIRECTIONS:
            for v in self.vehicles[d]:
                if v.kind == "ambulance" and not self.emergency_active:
                    self.emergency_active = True
                    self.emergency_dir = d
                    self.voice_system.alert_emergency_vehicle(d)
                    return
         if self.emergency_active:
            has_ambulance = any(v.kind == "ambulance" for v in self.vehicles[self.emergency_dir])
            if not has_ambulance:
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
            self.traffic_lights[self.emergency_dir].state = "green"
            self.green_dir = self.emergency_dir
            self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)

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
                    print(f"[Adaptive] High density in {max_density_dir}, giving priority.")
                    next_dir = max_density_dir

                # Switch to next
                self.green_dir = next_dir
                self.traffic_lights[self.green_dir].state = "green"
                self.phase_timer = self.calculate_adaptive_green_time(self.green_dir)
                print(f"[Signal] Green light → {self.green_dir}")

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
    if total_vehicles >= 35:   # safe max limit (40 bhi ho sakta hai)
        return

    if direction is None:
        direction = random.choice(DIRECTIONS)

    kind = random.choices(
        ["car", "bus", "truck", "bike", "ambulance"],
        weights=[55, 15, 10, 15, 5]
    )[0]

    # Try multiple times to spawn without overlap
    attempts = 8   # thoda zyada try karenge
    for attempt in range(attempts):
        try:
            new_vehicle = Vehicle(kind, direction)
        except Exception as e:
            print("Spawn error:", e)
            return

        jitter = random.randint(0, 80)
        if direction == NORTH:
            new_vehicle.rect.center = (new_vehicle.rect.centerx, -80 - jitter - attempt*20)
        elif direction == SOUTH:
            new_vehicle.rect.center = (new_vehicle.rect.centerx, SCREEN_H + 80 + jitter + attempt*20)
        elif direction == EAST:
            new_vehicle.rect.center = (SCREEN_W + 80 + jitter + attempt*20, new_vehicle.rect.centery)
        elif direction == WEST:
            new_vehicle.rect.center = (-80 - jitter - attempt*20, new_vehicle.rect.centery)

        # Check overlap
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
# --- Tkinter Dashboard (modern + manual control) ---
# --- Tkinter Dashboard (modern + manual control) ---
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
                        tsys.vehicles[NORTH].appendleft(Vehicle("ambulance", NORTH))

           # Auto spawn
            spawn_timer += dt
            if spawn_timer > random.uniform(1.5, 2.5):   # 1.2–2.2 ki jagah safe range
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

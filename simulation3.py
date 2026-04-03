import pygame, random, os
from collections import deque

# ---------------- Configuration -----------------------
SCREEN_W, SCREEN_H = 1200, 720
FPS = 60

BASE_GREEN_TIME = 6.0  # Base green time
YELLOW_TIME = 2.0
MIN_GREEN_TIME = 3.0   # Minimum green time
MAX_GREEN_TIME = 10.0  # Maximum green time

ROAD_WIDTH = 220
LANE_WIDTH = ROAD_WIDTH // 2

# ---------------- Init pygame ------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Smart City – Adaptive Traffic Management")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
title_font = pygame.font.SysFont(None, 36)

# ---------------- Image Loader ----------------------
def load_image(filename, size=None):
    try:
        path = os.path.join(os.path.dirname(__file__), filename)
        img = pygame.image.load(path).convert_alpha()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except:
        # Create placeholder if image not found
        print(f"Image {filename} not found. Using placeholder.")
        surf = pygame.Surface(size if size else (50, 50), pygame.SRCALPHA)
        color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        pygame.draw.rect(surf, color, (0, 0, size[0] if size else 50, size[1] if size else 50))
        return surf

# ---------------- Load Assets -----------------------
# Try to load background image, create one if not available
try:
    BACKGROUND = load_image("city1.jpg", (SCREEN_W, SCREEN_H))
except:
    # Create a programmatic background
    BACKGROUND = pygame.Surface((SCREEN_W, SCREEN_H))
    BACKGROUND.fill((50, 120, 50))  # Green background
    
    # Draw roads
    pygame.draw.rect(BACKGROUND, (80, 80, 80), (0, SCREEN_H//2 - ROAD_WIDTH//2, SCREEN_W, ROAD_WIDTH))
    pygame.draw.rect(BACKGROUND, (80, 80, 80), (SCREEN_W//2 - ROAD_WIDTH//2, 0, ROAD_WIDTH, SCREEN_H))
    
    # Draw road markings
    for i in range(0, SCREEN_W, 40):
        pygame.draw.rect(BACKGROUND, (240, 240, 240), (i, SCREEN_H//2 - 2, 20, 4))
    for i in range(0, SCREEN_H, 40):
        pygame.draw.rect(BACKGROUND, (240, 240, 240), (SCREEN_W//2 - 2, i, 4, 20))
    
    # Draw intersection
    pygame.draw.rect(BACKGROUND, (60, 60, 60), 
                    (SCREEN_W//2 - ROAD_WIDTH//2, SCREEN_H//2 - ROAD_WIDTH//2, 
                     ROAD_WIDTH, ROAD_WIDTH))

# Colors
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
DARK = (50, 50, 50)
GRAY = (100, 100, 100)

# ---------------- Directions ------------------------
NORTH, SOUTH, EAST, WEST = "N", "S", "E", "W"
DIRECTIONS = [NORTH, SOUTH, EAST, WEST]

# Traffic light positions
LIGHT_POS = {
    NORTH: (SCREEN_W // 2 - 15, SCREEN_H // 2 - ROAD_WIDTH // 2 - 50),
    SOUTH: (SCREEN_W // 2 - 15, SCREEN_H // 2 + ROAD_WIDTH // 2 + 10),
    EAST:  (SCREEN_W // 2 + ROAD_WIDTH // 2 + 10, SCREEN_H // 2 - 15),
    WEST:  (SCREEN_W // 2 - ROAD_WIDTH // 2 - 50, SCREEN_H // 2 - 15),
}

# ---------------- Vehicle Types with Images ---------------------
# Try to load vehicle images, use placeholders if not available
VEHICLE_TYPES = {}

# Try to load car image
try:
    VEHICLE_TYPES["car"] = {
        "image": load_image("car1.png", (50, 100)), 
        "length": 50, 
        "width": 100, 
        "speed": 3
    }
except:
    VEHICLE_TYPES["car"] = {
        "color": (200, 50, 50), 
        "length": 50, 
        "width": 30, 
        "speed": 3
    }

# Try to load bus image
try:
    VEHICLE_TYPES["bus"] = {
        "image": load_image("bus2.png", (60, 140)), 
        "length": 60, 
        "width": 140, 
        "speed": 2.5
    }
except:
    VEHICLE_TYPES["bus"] = {
        "color": (50, 50, 200), 
        "length": 70, 
        "width": 35, 
        "speed": 2.5
    }

# Try to load truck image
try:
    VEHICLE_TYPES["truck"] = {
        "image": load_image("truc.png", (70, 150)), 
        "length": 70, 
        "width": 150, 
        "speed": 2
    }
except:
    VEHICLE_TYPES["truck"] = {
        "color": (200, 200, 50), 
        "length": 80, 
        "width": 40, 
        "speed": 2
    }

# Try to load ambulance image
try:
    VEHICLE_TYPES["ambulance"] = {
        "image": load_image("ambulance3.png", (50, 110)), 
        "length": 50, 
        "width": 110, 
        "speed": 3.5
    }
except:
    VEHICLE_TYPES["ambulance"] = {
        "color": (255, 50, 50), 
        "length": 60, 
        "width": 30, 
        "speed": 3.5
    }

# Add Indian vehicles (auto-rickshaw and bike)


# ---------------- Traffic Light Class ----------------
class TrafficLight:
    def __init__(self, x, y, direction):
        self.x = x
        self.y = y
        self.direction = direction
        self.state = "red"
        self.light_radius = 6  # Smaller radius for the light circles

        # Load traffic light image as background
        self.image = load_image("traffic_signal.png")  # Using the traffic light image
        # Scale the image to be more visible
        self.width, self.height = 40, 100  # Smaller overall size
        self.image = pygame.transform.scale(self.image, (self.width, self.height))

        # Colors
        self.colors = {
            "red": (255, 0, 0),     # Bright red
            "yellow": (255, 255, 0), # Bright yellow
            "green": (0, 255, 0),    # Bright green
            "dark": (30, 30, 30)     # Darker when off
        }

        # Calculate light positions relative to image
        spacing = self.height // 4
        self.light_positions = {
            "red": (self.width // 2, spacing),
            "yellow": (self.width // 2, spacing * 2),
            "green": (self.width // 2, spacing * 3)
        }

    def draw(self, screen):
        # Draw the traffic light background image
        screen.blit(self.image, (self.x, self.y))

        # Draw the colored lights on top with a glow effect
        for color_name, pos in self.light_positions.items():
            x, y = self.x + pos[0], self.y + pos[1]
            color = self.colors[color_name] if color_name == self.state else self.colors["dark"]
            
            # Draw a smaller, semi-transparent circle for glow effect
            if color_name == self.state:
                glow_surface = pygame.Surface((self.light_radius * 3, self.light_radius * 3), pygame.SRCALPHA)
                pygame.draw.circle(glow_surface, (*color[:3], 80), (self.light_radius * 1.5, self.light_radius * 1.5), self.light_radius * 1.5)
                screen.blit(glow_surface, (x - self.light_radius * 1.5, y - self.light_radius * 1.5))
            
            # Draw the main light
            pygame.draw.circle(screen, color, (x, y), self.light_radius)
            # Draw a small white reflection
            pygame.draw.circle(screen, (255, 255, 255), (x - self.light_radius//4, y - self.light_radius//4), self.light_radius//4)


# ---------------- Vehicle Class ---------------------
class Vehicle:
    def __init__(self, kind, direction):
        self.kind = kind
        self.dir = direction
        self.speed = VEHICLE_TYPES[kind]["speed"]
        self.length = VEHICLE_TYPES[kind]["length"]
        self.width = VEHICLE_TYPES[kind]["width"]
        self.stopped = False
        self.in_intersection = False
        self.waiting_time = 0
        
        # Check if vehicle has an image
        if "image" in VEHICLE_TYPES[kind]:
            self.has_image = True
            self.image = VEHICLE_TYPES[kind]["image"]
            
            # Rotate based on direction
            if self.dir == NORTH:
                self.image = pygame.transform.rotate(self.image, 180)
            elif self.dir == EAST:
                self.image = pygame.transform.rotate(self.image, 90)
            elif self.dir == WEST:
                self.image = pygame.transform.rotate(self.image, -90)
        else:
            self.has_image = False
            self.color = VEHICLE_TYPES[kind]["color"]
            
            # Create vehicle surface
            self.image = pygame.Surface((self.length, self.width), pygame.SRCALPHA)
            pygame.draw.rect(self.image, self.color, (0, 0, self.length, self.width), 0, 5)
            
            # Windshield
            pygame.draw.rect(self.image, (200, 230, 255), (self.length-15, 5, 10, self.width-10), 0, 3)
            
            # Rotate based on direction
            if self.dir == NORTH:
                self.image = pygame.transform.rotate(self.image, 180)
            elif self.dir == EAST:
                self.image = pygame.transform.rotate(self.image, 90)
            elif self.dir == WEST:
                self.image = pygame.transform.rotate(self.image, -90)

        # Starting position
        if direction == NORTH:
            self.x, self.y = SCREEN_W // 2 - 40, 0 - 120
        elif direction == SOUTH:
            self.x, self.y = SCREEN_W // 2 + 20, SCREEN_H + 50
        elif direction == EAST:
            self.x, self.y = SCREEN_W + 60, SCREEN_H // 2 - 40
        elif direction == WEST:
            self.x, self.y = -120, SCREEN_H // 2 + 20

        self.rect = self.image.get_rect(center=(self.x, self.y))

    def check_collision(self, vehicles):
        safe_distance = 15
        for vehicle in vehicles:
            if vehicle == self:
                continue
            if self.dir == vehicle.dir:
                if self.dir == NORTH:
                    if vehicle.y > self.y and vehicle.y - (self.y + self.rect.height) < safe_distance:
                        return True
                elif self.dir == SOUTH:
                    if vehicle.y < self.y and self.y - (vehicle.y + vehicle.rect.height) < safe_distance:
                        return True
                elif self.dir == EAST:
                    if vehicle.x < self.x and self.x - (vehicle.x + vehicle.rect.width) < safe_distance:
                        return True
                elif self.dir == WEST:
                    if vehicle.x > self.x and vehicle.x - (self.x + self.rect.width) < safe_distance:
                        return True
        return False

    def should_stop(self, green_dir, traffic_lights, vehicles):
        # Define stop lines for each direction
        stop_lines = {
            NORTH: SCREEN_H // 2 - ROAD_WIDTH // 2 - 20,
            SOUTH: SCREEN_H // 2 + ROAD_WIDTH // 2 + 20,
            EAST: SCREEN_W // 2 + ROAD_WIDTH // 2 + 20,
            WEST: SCREEN_W // 2 - ROAD_WIDTH // 2 - 20
        }

        # Check for collisions with other vehicles
        if self.check_collision(vehicles):
            return True

        # Check if at intersection and light is red
        light_state = traffic_lights[self.dir].state
        at_intersection = False
        
        if self.dir == NORTH:
            at_intersection = self.y + self.rect.height >= stop_lines[NORTH]
        elif self.dir == SOUTH:
            at_intersection = self.y <= stop_lines[SOUTH]
        elif self.dir == EAST:
            at_intersection = self.x <= stop_lines[EAST]
        else:
            at_intersection = self.x + self.rect.width >= stop_lines[WEST]

        if at_intersection and not self.in_intersection:
            if light_state != "green":
                return True
            else:
                self.in_intersection = True

        return False

    def move(self, green_dir, traffic_lights, vehicles):
        if self.should_stop(green_dir, traffic_lights, vehicles):
            self.stopped = True
            self.waiting_time += 1
            return
            
        self.stopped = False
        self.waiting_time = 0
        
        if self.dir == NORTH:
            self.y += self.speed
        elif self.dir == SOUTH:
            self.y -= self.speed
        elif self.dir == EAST:
            self.x -= self.speed
        elif self.dir == WEST:
            self.x += self.speed
            
        self.rect.center = (self.x, self.y)

    def draw(self, surf):
        surf.blit(self.image, self.rect)

# ---------------- Traffic System --------------------
class TrafficSystem:
    def __init__(self):
        self.queues = {d: deque() for d in DIRECTIONS}
        self.green_dir = NORTH
        self.phase_timer = BASE_GREEN_TIME
        self.normal_cycle = True  # Whether we're in normal cycle or density override
        self.density_override_timer = 0
        self.max_vehicles = 18  # Maximum number of vehicles (reduced by 10%)
        self.green_times = {d: BASE_GREEN_TIME for d in DIRECTIONS}  # Individual green times for each direction

        # Initialize traffic lights
        self.traffic_lights = {}
        for direction, (x, y) in LIGHT_POS.items():
            self.traffic_lights[direction] = TrafficLight(x, y, direction)
            self.traffic_lights[direction].state = "red"
        self.traffic_lights[self.green_dir].state = "green"

    def get_density(self, direction):
        # Count vehicles in this direction that are waiting or approaching
        count = 0
        for vehicle in self.queues[direction]:
            # Count vehicles that are stopped or close to the intersection
            if (vehicle.stopped or 
                (direction == NORTH and vehicle.y > SCREEN_H//2 - ROAD_WIDTH) or
                (direction == SOUTH and vehicle.y < SCREEN_H//2 + ROAD_WIDTH) or
                (direction == EAST and vehicle.x < SCREEN_W//2 + ROAD_WIDTH) or
                (direction == WEST and vehicle.x > SCREEN_W//2 - ROAD_WIDTH)):
                count += 1
        return count

    def calculate_green_time(self, direction):
        # Calculate green time based on vehicle density
        density = self.get_density(direction)
        
        # More vehicles = longer green time, fewer vehicles = shorter green time
        if density == 0:
            return MIN_GREEN_TIME  # Minimum time if no vehicles
        elif density >= 5:
            return MAX_GREEN_TIME  # Maximum time for high density
        else:
            # Scale green time based on density (linear scaling)
            return MIN_GREEN_TIME + (density / 5) * (MAX_GREEN_TIME - MIN_GREEN_TIME)

    def update(self, dt):
        self.phase_timer -= dt
        
        # Update green time for current direction based on density
        self.green_times[self.green_dir] = self.calculate_green_time(self.green_dir)
        
        # Check for high density in any direction (3+ vehicles)
        high_density_dir = None
        max_density = 0
        for direction in DIRECTIONS:
            density = self.get_density(direction)
            if density >= 3 and density > max_density:
                high_density_dir = direction
                max_density = density
                
        # Handle density-based override
        if high_density_dir and high_density_dir != self.green_dir and self.normal_cycle:
            # Switch to density override mode
            self.normal_cycle = False
            self.traffic_lights[self.green_dir].state = "yellow"
            self.phase_timer = YELLOW_TIME
            
        elif not self.normal_cycle:
            # We're in density override mode
            if self.phase_timer <= 0:
                if self.traffic_lights[self.green_dir].state == "yellow":
                    # Switch to the high density direction
                    self.traffic_lights[self.green_dir].state = "red"
                    self.green_dir = high_density_dir
                    self.traffic_lights[self.green_dir].state = "green"
                    # Set green time based on density
                    self.phase_timer = self.calculate_green_time(self.green_dir)
                elif self.traffic_lights[self.green_dir].state == "green":
                    # Check if density is still high
                    if self.get_density(self.green_dir) <= 2:
                        # Return to normal cycle
                        self.traffic_lights[self.green_dir].state = "yellow"
                        self.phase_timer = YELLOW_TIME
                        self.normal_cycle = True
                    else:
                        # Extend green time based on current density
                        self.phase_timer = self.calculate_green_time(self.green_dir)
        
        # Normal cycle operation
        elif self.phase_timer <= 0 and self.normal_cycle:
            current_light = self.traffic_lights[self.green_dir]
            if current_light.state == "green":
                current_light.state = "yellow"
                self.phase_timer = YELLOW_TIME
            elif current_light.state == "yellow":
                current_light.state = "red"
                idx = DIRECTIONS.index(self.green_dir)
                self.green_dir = DIRECTIONS[(idx + 1) % len(DIRECTIONS)]
                self.traffic_lights[self.green_dir].state = "green"
                # Set green time based on density for the new direction
                self.phase_timer = self.calculate_green_time(self.green_dir)

        # Update all vehicles
        all_vehicles = []
        for d in DIRECTIONS:
            all_vehicles.extend(self.queues[d])

        for d in DIRECTIONS:
            for v in self.queues[d]:
                v.move(self.green_dir, self.traffic_lights, all_vehicles)

        # Remove vehicles that have left the screen
        for d in DIRECTIONS:
            self.queues[d] = deque([v for v in self.queues[d] if -200 < v.x < SCREEN_W + 200 and -200 < v.y < SCREEN_H + 200])

    def spawn_vehicle(self, direction):
        # Check if we've reached the maximum number of vehicles
        total_vehicles = sum(len(self.queues[d]) for d in DIRECTIONS)
        if total_vehicles >= self.max_vehicles:
            return
            
        kind = random.choice(list(VEHICLE_TYPES.keys()))
        v = Vehicle(kind, direction)
        self.queues[direction].appendleft(v)

    def draw(self, surf):
        # Draw background
        surf.blit(BACKGROUND, (0, 0))
        
        # Draw vehicles
        for d in DIRECTIONS:
            for v in self.queues[d]:
                v.draw(surf)
                
        # Draw traffic lights
        for d, light in self.traffic_lights.items():
            light.draw(surf)
            
        # Draw UI information
        mode_text = "Normal Cycle" if self.normal_cycle else "Density Override"
        mode_color = (50, 150, 50) if self.normal_cycle else (200, 100, 50)
        
        pygame.draw.rect(surf, (240, 240, 240, 200), (10, 10, 350, 180), 0, 5)
        pygame.draw.rect(surf, (200, 200, 200), (10, 10, 350, 180), 2, 5)
        
        title = title_font.render("Adaptive Traffic Management", True, (0, 0, 0))
        surf.blit(title, (20, 20))
        
        mode = font.render(f"Mode: {mode_text}", True, mode_color)
        surf.blit(mode, (20, 60))
        
        light_info = font.render(f"Green: {self.green_dir} ({self.phase_timer:.1f}s)", True, (0, 0, 0))
        surf.blit(light_info, (20, 80))
        
        # Draw density information and suggested green times
        for i, direction in enumerate(DIRECTIONS):
            density = self.get_density(direction)
            suggested_time = self.calculate_green_time(direction)
            color = (255, 0, 0) if density >= 3 else (0, 150, 0) if density > 0 else (100, 100, 100)
            
            density_text = font.render(f"{direction}: {density} vehicles", True, color)
            surf.blit(density_text, (20, 100 + i*20))
            
            # Show suggested green time for each direction
            time_color = (0, 100, 200) if direction == self.green_dir else (100, 100, 100)
            time_text = font.render(f"{suggested_time:.1f}s", True, time_color)
            surf.blit(time_text, (180, 100 + i*20))
        
        # Draw total vehicles count
        total_vehicles = sum(len(self.queues[d]) for d in DIRECTIONS)
        total_text = font.render(f"Total: {total_vehicles}/{self.max_vehicles}", True, (0, 0, 0))
        surf.blit(total_text, (20, 160))

# ---------------- Main Loop ------------------------
def main():
    system = TrafficSystem()
    spawn_timer = 0
    running = True
    
    while running:
        dt = clock.tick(FPS) / 1000
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                # Manual spawning for testing
                elif event.key == pygame.K_n:
                    system.spawn_vehicle(NORTH)
                elif event.key == pygame.K_s:
                    system.spawn_vehicle(SOUTH)
                elif event.key == pygame.K_e:
                    system.spawn_vehicle(EAST)
                elif event.key == pygame.K_w:
                    system.spawn_vehicle(WEST)

        # Random vehicle spawning with reduced frequency
        spawn_timer += dt
        if spawn_timer > random.uniform(2.0, 4.0):  # Reduced spawn rate
            system.spawn_vehicle(random.choice(DIRECTIONS))
            spawn_timer = 0

        system.update(dt)
        system.draw(screen)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
# MindCare - Reaction Time Test Game
"""
A simple reaction time test game with multiple screens.
"""

# ===== IMPORTS =====
import os
import sys
import time
import random
import statistics
import datetime as dt
import csv
import shutil

import pygame as pg
import matplotlib.pyplot as plt

# ===== INITIAL SETTINGS =====
# Game configuration constants 
WIDTH = 900          # Window width
HEIGHT = 600         # Window height
BG = (18, 18, 22)    # Background color (dark blue-gray)
FG = (240, 240, 240) # Foreground color (light gray)
ACCENT = (100, 150, 255)       # Button color (blue)
BUTTON_HOVER = (120, 170, 255) # Button color when mouse hovers
SQUARE = 70          # Size of the square in the game
MARGIN = 40          # Space from edges
FPS = 60             # Frames per second
SESSION_SECONDS = 30 # How long the game lasts

# Username screen constants
INPUT_BOX_WIDTH = 400
INPUT_BOX_HEIGHT = 50
CONTINUE_BTN_PADDING = 20

# Color mappings for buttons
SLEEP_COLORS = {
    "Excellent": (0, 255, 0),      # Green
    "Good": (255, 255, 0),         # Yellow
    "Not so good": (255, 165, 0),  # Orange
    "Bad": (255, 0, 0)             # Red
}

# Screen names 
WELCOME = 0
USERNAME = 0.5  # Page 0a - between WELCOME and MOOD
MOOD = 1
SLEEP = 2
MENU = 3
GAME = 4
RESULTS = 5


# ===== HELPER FUNCTIONS =====
def get_font(size, bold=True):
    """Helper function to create fonts with fallback."""
    try:
        return pg.font.SysFont("Courier New", size, bold=bold)
    except Exception:
        return pg.font.SysFont(None, size, bold=bold)


def update_user_baseline(username):
    """Helper to update user baseline based on username."""
    return get_user_baseline(username.strip()) if username.strip() else None


# ===== BUTTON CLASS =====
class Button:
    """A simple button that can be clicked and shows hover effects."""
    
    def __init__(self, x, y, width, height, text,
                 font_size=32, color=None, hover_color=None, text_color=None):
        """Create a new button at position (x, y) with given size and text."""
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.font = get_font(font_size, bold=True)
        self.hovered = False
        self.color = color if color is not None else ACCENT
        self.hover_color = (
            hover_color if hover_color is not None else BUTTON_HOVER
        )
        self.text_color = text_color
    
    def draw(self, screen):
        """Draw the button on the screen."""
        color = self.hover_color if self.hovered else self.color
        pg.draw.rect(screen, color, self.rect, border_radius=10)
        pg.draw.rect(screen, FG, self.rect, width=2, border_radius=10)
        
        # Text color: explicit if provided; otherwise auto-detect
        if self.text_color is not None:
            text_color = self.text_color
        else:
            text_color = (
                (255, 255, 255) if sum(self.color) < 400 else (0, 0, 0)
            )
        text_surf = self.font.render(self.text, True, text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)
    
    def check_hover(self, mouse_pos):
        """Check if mouse is over button and update hover state."""
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def is_clicked(self, mouse_pos):
        """Check if button was clicked."""
        return self.rect.collidepoint(mouse_pos)


# ===== WELCOME SCREEN =====
def draw_welcome_screen(screen, font_large, font_medium):
    """Draw the welcome screen."""
    screen.fill(BG)
    
    title = font_large.render("Welcome to MindCare", True, FG)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
    screen.blit(title, title_rect)
    
    start_text = font_medium.render("Click here to start", True, ACCENT)
    start_rect = start_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
    screen.blit(start_text, start_rect)
    
    text_width, text_height = start_text.get_size()
    padding = 20
    click_area = pg.Rect(
        WIDTH // 2 - (text_width // 2 + padding),
        HEIGHT // 2 + 40 - (text_height // 2 + padding),
        text_width + padding * 2,
        text_height + padding * 2
    )
    pg.draw.rect(screen, ACCENT, click_area, width=2, border_radius=10)


# ===== USERNAME SCREEN =====
def draw_username_screen(screen, font_large, font_medium, 
                         username_text, input_active, baseline_info=None):
    """Draw the username input screen."""
    screen.fill(BG)
    
    title = font_large.render("Enter Your Name", True, FG)
    title_rect = title.get_rect(center=(WIDTH // 2, 120))
    screen.blit(title, title_rect)
    
    # Draw input box
    input_box_x = (WIDTH - INPUT_BOX_WIDTH) // 2
    input_box_y = HEIGHT // 2 - 40
    input_box = pg.Rect(input_box_x, input_box_y, INPUT_BOX_WIDTH, 
                        INPUT_BOX_HEIGHT)
    
    # Draw border (highlight if active)
    border_color = ACCENT if input_active else FG
    pg.draw.rect(screen, border_color, input_box, width=2, border_radius=10)
    
    # Draw username text
    if username_text:
        display_text = username_text
    else:
        display_text = "Type your name here..."
    
    text_color = FG if username_text else (100, 100, 100)  # Gray placeholder
    text_surf = font_medium.render(display_text, True, text_color)
    text_rect = text_surf.get_rect(center=input_box.center)
    # Clamp text to input box width
    if text_rect.width > INPUT_BOX_WIDTH - 20:
        # Truncate text if too long
        while text_surf.get_width() > INPUT_BOX_WIDTH - 20 and display_text:
            display_text = display_text[:-1]
            text_surf = font_medium.render(display_text, True, text_color)
        text_rect = text_surf.get_rect(center=input_box.center)
    screen.blit(text_surf, text_rect)
    
    # Display baseline info if available and user has typed something
    if (
        baseline_info
        and username_text.strip()
        and baseline_info.get("session_count", 0) > 0
    ):
        font_small = get_font(20, bold=True)
        
        session_count = baseline_info.get("session_count", 0)
        total_hits = baseline_info.get("total_hits", 0)
        avg_rt = (
            baseline_info.get("total_mean_rt", 0.0) / session_count
            if session_count > 0 else 0.0
        )
        
        baseline_text = (
            f"Welcome back! Previous sessions: {session_count} |"
            f"Total hits: {total_hits}"
        )
        if avg_rt > 0:
            baseline_text += f" | Avg RT: {avg_rt:.1f}ms"
        
        baseline_surf = font_small.render(baseline_text, True, ACCENT)
        baseline_rect = baseline_surf.get_rect(
            center=(WIDTH // 2, HEIGHT // 2 + 20)
        )
        screen.blit(baseline_surf, baseline_rect)
    
    # Draw continue button
    continue_text = font_medium.render("Continue", True, ACCENT)
    continue_rect = continue_text.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 + 100)
    )
    screen.blit(continue_text, continue_rect)
    
    # Draw box around continue button
    continue_box = pg.Rect(
        continue_rect.x - CONTINUE_BTN_PADDING,
        continue_rect.y - CONTINUE_BTN_PADDING // 2,
        continue_rect.width + CONTINUE_BTN_PADDING * 2,
        continue_rect.height + CONTINUE_BTN_PADDING
    )
    pg.draw.rect(screen, ACCENT, continue_box, width=2, border_radius=10)


# ===== GENERIC TITLED SCREEN =====
def draw_screen_with_title(screen, title_text, font_large, buttons=None):
    """Draw a screen with a title and optional buttons."""
    screen.fill(BG)
    title = font_large.render(title_text, True, FG)
    title_rect = title.get_rect(center=(WIDTH // 2, 80))
    screen.blit(title, title_rect)
    
    if buttons:
        for btn in buttons:
            btn.draw(screen)


def get_hover_color(base_color):
    """Make a color slightly brighter for hover effect."""
    if base_color == (255, 255, 255):  # white
        return (220, 220, 220)
    if base_color == (0, 0, 0):        # black
        return (50, 50, 50)
    return tuple(min(255, c + 30) for c in base_color)


# ===== MAIN GAME =====
def get_random_position(size):
    """Get a random position for the square that stays within bounds."""
    x = random.randint(MARGIN, WIDTH - size - MARGIN)
    y = random.randint(MARGIN, HEIGHT - size - MARGIN)
    return x, y


def run_reaction_game(screen, clock, font):
    """Run the actual reaction time game."""
    square = pg.Rect(0, 0, SQUARE, SQUARE)
    square.topleft = get_random_position(SQUARE)
    
    session_start = time.perf_counter()
    trial_start = session_start
    hits = 0
    spawns = 1
    reaction_times = []
    exited_early = False
    mouse_was_over_square = False  # Track previous frame state
    
    running = True
    while running:
        clock.tick(FPS)
        
        elapsed = time.perf_counter() - session_start
        remaining = max(0.0, SESSION_SECONDS - elapsed)
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
                exited_early = True
            elif event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                running = False
                exited_early = True
        
        if remaining <= 0:
            break
        
        mouse_x, mouse_y = pg.mouse.get_pos()
        mouse_is_over_square = square.collidepoint(mouse_x, mouse_y)
        
        # Only trigger hit when mouse first enters the square 
        if mouse_is_over_square and not mouse_was_over_square:
            reaction_time_ms = (time.perf_counter() - trial_start) * 1000.0
            reaction_times.append(reaction_time_ms)
            hits += 1
            
            square.topleft = get_random_position(SQUARE)
            trial_start = time.perf_counter()
            spawns += 1
        
        mouse_was_over_square = mouse_is_over_square
        
        screen.fill(BG)
        pg.draw.rect(screen, FG, square, width=2)
        
        stats_text = (
            f"Time: {remaining:05.2f}s   Hits: {hits}   Spawns: {spawns}"
        )
        screen.blit(font.render(stats_text, True, FG), (12, 10))
        pg.display.flip()
    
    return hits, spawns, reaction_times, exited_early


# ===== USER MANAGEMENT =====
def get_user_baseline(username):
    """Get the baseline (sum of previous results) for a user."""
    try:
        csv_path = "follow_square_daily.csv"
        if not os.path.exists(csv_path):
            # Return empty baseline for new user
            return {
                "total_hits": 0,
                "total_mean_rt": 0.0,
                "session_count": 0
            }
        
        total_hits = 0
        total_mean_rt = 0.0
        count = 0
        
        with open(csv_path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if username column exists and matches
                row_username = row.get("username", "").strip()
                if row_username.lower() == username.strip().lower():
                    # Sum up the results
                    try:
                        hits_val = row.get("hits", "").strip()
                        mean_rt_val = row.get("mean_rt_ms", "").strip()
                        
                        if hits_val and hits_val.replace(".", "").isdigit():
                            total_hits += int(float(hits_val))
                        if mean_rt_val:
                            clean_rt = mean_rt_val.replace(",", "").strip()
                            if (
                                clean_rt
                                and clean_rt.replace(".", "").isdigit()
                            ):
                                total_mean_rt += float(clean_rt)
                                count += 1
                    except (ValueError, TypeError):
                        continue
        
        # Return baseline info (cumulative results)
        baseline = {
            "total_hits": total_hits,
            "total_mean_rt": total_mean_rt,
            "session_count": count
        }
        # Debug: print baseline info
        if count > 0:
            print(
                f"Loaded baseline for '{username}': {count} sessions, "
                f"{total_hits} total hits"
            )
        return baseline
    except Exception as e:
        print(f"Could not load user baseline: {e}")
        # Return empty baseline on error
        return {
            "total_hits": 0,
            "total_mean_rt": 0.0,
            "session_count": 0
        }


# ===== RESULTS =====
def save_to_csv(date, username, mood, sleep, hits, spawns, mean_rt):
    """Save game results to a CSV file, migrating old format if needed."""
    try:
        row = [
            date, username or "", mood or "", sleep or "", 
            hits, spawns, mean_rt
        ]
        header = [
            "date", "username", "mood", "sleep", 
            "hits", "spawns", "mean_rt_ms"
        ]
        csv_path = "follow_square_daily.csv"
        
        file_exists = os.path.exists(csv_path)
        needs_header = not file_exists
        needs_migration = False
        
        # If file exists, check if it has the username column
        if file_exists:
            with open(csv_path, "r", newline="") as f:
                reader = csv.reader(f)
                first_row = next(reader, None)
                if first_row and "username" not in first_row:
                    needs_migration = True
        
        # Migrate old format to new format if needed
        if needs_migration:
            backup_path = csv_path + ".backup"
            shutil.copy2(csv_path, backup_path)
            
            old_rows = []
            with open(csv_path, "r", newline="") as f:
                reader = csv.DictReader(f)
                for old_row in reader:
                    # Migrate old format: add empty username column
                    # Handle both old formats (with or without sleep column)
                    old_rows.append([
                        old_row.get("date", ""),
                        "",  # username - empty for old data
                        old_row.get("mood", ""),
                        old_row.get("sleep", ""),
                        old_row.get("hits", ""),
                        old_row.get("spawns", ""),
                        old_row.get("mean_rt_ms", "")
                    ])
            
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(old_rows)
        
        # Append new row
        with open(csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            if needs_header:
                writer.writerow(header)
            writer.writerow(row)
    except Exception as e:
        print(f"Could not save to CSV: {e}")


def create_simple_timeline(username=None):
    """
    Create two graphs from all stored sessions (filtered by username)

    Graph 1:
        - Timeline of mean reaction time per trial
        - X-axis: emotion labels
        - Y-axis: mean reaction time
        - Point color: sleep quality

    Graph 2:
        - Left: average reaction time per mood
        - Right: average reaction time per sleep quality
    """
    from collections import defaultdict

    csv_path = "follow_square_daily.csv"
    if not os.path.exists(csv_path):
        print("No data file found.")
        return None

    # ----- Load data from CSV -----
    trials = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Optional username filter
            if username:
                row_username = (row.get("username") or "").strip()
                if row_username != username:
                    continue

            mean_rt_str = (row.get("mean_rt_ms") or "").strip()
            mood_val = (row.get("mood") or "").strip() or "Unknown"
            sleep_val = (row.get("sleep") or "").strip() or "Unknown"

            if not mean_rt_str:
                continue

            clean_rt = mean_rt_str.replace(",", "").strip()
            try:
                rt = float(clean_rt)
            except ValueError:
                continue

            trials.append(
                {
                    "mean_rt": rt,
                    "mood": mood_val,
                    "sleep": sleep_val,
                }
            )

    if not trials:
        print("No valid trial data found.")
        return None

    # ==========================================
    # Graph 1: Timeline of mean reaction time
    # ==========================================
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("black")
    ax.set_facecolor("black")

    # Convert RGB tuples to matplotlib color format (0-1 range)
    sleep_color_map = {
        k: tuple(c/255.0 for c in v)
        for k, v in SLEEP_COLORS.items()
    }

    trial_positions = list(range(len(trials)))
    mean_rts = [t["mean_rt"] for t in trials]
    moods = [t["mood"] for t in trials]
    sleeps = [t["sleep"] for t in trials]

    # Scatter points coloured by sleep quality
    for trial_pos, mean_rt, sleep in zip(trial_positions, mean_rts, sleeps):
        color = sleep_color_map.get(sleep, "gray")
        ax.scatter(
            trial_pos,
            mean_rt,
            s=100,
            color=color,
            edgecolors="white",
            linewidth=1.5,
            zorder=3,
        )

    # Line connecting the points
    ax.plot(
        trial_positions,
        mean_rts,
        linestyle="-",
        linewidth=1,
        color="white",
        alpha=0.5,
        zorder=1,
    )

    ax.set_xticks(trial_positions)
    ax.set_xticklabels(
        moods, rotation=45, ha="right", color="white", fontsize=8
    )

    ax.set_xlabel(
        "Emotions", fontsize=12, fontweight="bold", color="white"
    )
    ax.set_ylabel(
        "Mean Reaction Time (ms)",
        fontsize=12,
        fontweight="bold",
        color="white",
    )
    title_text = "Trial Timeline - Mean Reaction Time Progression"
    if username:
        title_text += f" - {username}"
    ax.set_title(
        title_text, fontsize=14, fontweight="bold", color="white"
    )

    ax.tick_params(colors="white", axis="y")
    for spine in ax.spines.values():
        spine.set_color("white")

    ax.grid(True, alpha=0.3, color="gray")
    ax.invert_yaxis()

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="green", label="Excellent"),
        Patch(facecolor="yellow", label="Good"),
        Patch(facecolor="orange", label="Not so good"),
        Patch(facecolor="red", label="Bad"),
    ]
    ax.legend(
        handles=legend_elements,
        title="Sleep Quality",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True,
        framealpha=0.9,
        facecolor="white",
    )

    plt.tight_layout()
    timeline_filename = "trial_timeline.png"
    plt.savefig(timeline_filename, dpi=150, bbox_inches="tight")
    print(f"Timeline graph saved as: {timeline_filename}")
    plt.close(fig)

    # ==========================================
    # Graph 2: Simple averages by mood and sleep
    # ==========================================
    mood_to_rts = defaultdict(list)
    sleep_to_rts = defaultdict(list)
    for t in trials:
        mood_to_rts[t["mood"]].append(t["mean_rt"])
        sleep_to_rts[t["sleep"]].append(t["mean_rt"])

    mood_labels = list(mood_to_rts.keys())
    sleep_labels = list(sleep_to_rts.keys())

    mood_means = [statistics.mean(mood_to_rts[m]) for m in mood_labels]
    sleep_means = [statistics.mean(sleep_to_rts[s]) for s in sleep_labels]

    fig2, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    fig2.patch.set_facecolor("black")
    for ax2 in axes:
        ax2.set_facecolor("black")

    # Left: average RT by mood
    ax_mood = axes[0]
    x_mood = range(len(mood_labels))
    ax_mood.bar(list(x_mood), mood_means, edgecolor="white")
    ax_mood.set_xticks(list(x_mood))
    ax_mood.set_xticklabels(
        mood_labels, rotation=45, ha="right", color="white", fontsize=8
    )
    ax_mood.set_title(
        "Average Reaction Time by Mood",
        fontsize=12,
        fontweight="bold",
        color="white",
    )
    ax_mood.set_ylabel(
        "Mean Reaction Time (ms)",
        fontsize=12,
        fontweight="bold",
        color="white",
    )

    # Right: average RT by sleep quality
    ax_sleep = axes[1]
    x_sleep = range(len(sleep_labels))
    ax_sleep.bar(list(x_sleep), sleep_means, edgecolor="white")
    ax_sleep.set_xticks(list(x_sleep))
    ax_sleep.set_xticklabels(
        sleep_labels, rotation=45, ha="right", color="white", fontsize=8
    )
    ax_sleep.set_title(
        "Average Reaction Time by Sleep",
        fontsize=12,
        fontweight="bold",
        color="white",
    )

    # Styling for both subplots
    for ax2 in axes:
        ax2.tick_params(colors="white")
        for spine in ax2.spines.values():
            spine.set_color("white")
        ax2.grid(True, alpha=0.3, color="gray")

    plt.tight_layout()
    summary_filename = "reaction_summary.png"
    plt.savefig(summary_filename, dpi=150, bbox_inches="tight")
    print(f"Summary graph saved as: {summary_filename}")
    plt.close(fig2)

    return timeline_filename


# ===== MAIN PROGRAM =====
def main():
    """The main function that runs everything."""
    try:
        pg.init()
    except Exception as e:
        print(f"Error starting pygame: {e}")
        return
        
    # --- initialize mixer and start background music ---
    try:
        if not pg.mixer.get_init():
            pg.mixer.init()  # initialize audio mixer

        # build path relative to this script
        base_dir = os.path.dirname(__file__)
        music_path = (
            os.path.join(base_dir, "ES_Feelings - Ryan James Carr.wav")
        )

        pg.mixer.music.load(music_path)
        pg.mixer.music.set_volume(0.4)   # 0.0 (mute) to 1.0 (max)
        pg.mixer.music.play(-1)          # -1 = loop forever
    except Exception as e:
        print(f"Could not start background music: {e}")
    # ---------------------------------------------------

    screen = pg.display.set_mode((WIDTH, HEIGHT), pg.SCALED)
    pg.display.set_caption("MindCare - Reaction Time Test")
    clock = pg.time.Clock()
    
    font_large = get_font(48, bold=True)
    font_medium = get_font(32, bold=True)
    font_small = get_font(28, bold=True)
    
    current_screen = WELCOME
    username = ""  # Current user's name
    username_input_active = False  # Is the text input box active?
    user_baseline = None  # Store baseline info for current user
    mood = None
    sleep = None
    hits = 0
    spawns = 0
    reaction_times = []
    
    # Mood selection buttons (2x3 grid)
    moods = ["Sad", "Happy", "Angry", "Disgusted", "Afraid", "Restless"]
    mood_buttons = []
    btn_width, btn_height = 200, 60
    start_x = (WIDTH - btn_width * 2 - 20) // 2
    start_y = 180
    for i, mood_text in enumerate(moods):
        x = start_x + (i % 2) * (btn_width + 20)
        y = start_y + (i // 2) * (btn_height + 15)
        row = i // 2
        col = i % 2
        base_color = (0, 0, 0) if (row + col) % 2 == 0 else (255, 255, 255)
        hover_color = get_hover_color(base_color)
        mood_buttons.append(
            Button(x, y, btn_width, btn_height, mood_text, 28,
                   color=base_color, hover_color=hover_color)
        )
    
    # Sleep quality buttons (column)
    sleep_options = ["Excellent", "Good", "Not so good", "Bad"]
    sleep_buttons = []
    btn_width_sleep = 250
    start_x_sleep = (WIDTH - btn_width_sleep) // 2
    start_y_sleep = 180
    for i, sleep_text in enumerate(sleep_options):
        y = start_y_sleep + i * (btn_height + 15)
        base_color = SLEEP_COLORS.get(sleep_text, ACCENT)
        hover_color = get_hover_color(base_color)
        text_color = (0, 0, 0) if sleep_text in ["Excellent", "Bad"] else None
        sleep_buttons.append(
            Button(start_x_sleep, y, btn_width_sleep, btn_height,
                   sleep_text, 28, color=base_color,
                   hover_color=hover_color, text_color=text_color)
        )
    
    # Menu screen buttons
    play_btn = Button(WIDTH // 2 - 120, HEIGHT // 2, 240, 60, "PLAY", 36)
    exit_btn = Button(WIDTH // 2 - 120, HEIGHT // 2 + 80, 240, 60, "EXIT", 36)
    
    # Results screen buttons
    view_graph_btn = (
        Button(WIDTH // 2 - 120, HEIGHT // 2 - 20, 240, 60, "See Graph", 36)
    )
    play_again_btn = (
        Button(WIDTH // 2 - 120, HEIGHT // 2 + 50, 240, 60, "PLAY AGAIN", 36)
    )
    exit_btn_results = (
        Button(WIDTH // 2 - 120, HEIGHT // 2 + 130, 240, 60, "EXIT", 36)
    )

    # Back button (used on MOOD and SLEEP screens)
    back_btn = Button(50, HEIGHT - 80, 150, 50, "Back", 32)
    
    running = True
    while running:
        clock.tick(FPS)
        mouse_pos = pg.mouse.get_pos()
        
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False
            
            elif event.type == pg.KEYDOWN:
                # Handle text input for username screen
                if current_screen == USERNAME:
                    if event.key == pg.K_RETURN or event.key == pg.K_KP_ENTER:
                        # Enter key - continue if username is not empty
                        if username.strip():
                            user_baseline = update_user_baseline(username)
                            current_screen = MOOD
                            username_input_active = False
                    elif event.key == pg.K_BACKSPACE:
                        username = username[:-1]
                        user_baseline = update_user_baseline(username)
                    elif event.key == pg.K_ESCAPE:
                        username_input_active = False
                    else:
                        # Add character (limit to reasonable length)
                        if len(username) < 30 and event.unicode.isprintable():
                            username += event.unicode
                            user_baseline = update_user_baseline(username)
            
            elif event.type == pg.MOUSEBUTTONUP and event.button == 1:
                if current_screen == WELCOME:
                    # Reuse click area calculation from draw_welcome_screen
                    start_text = (
                        font_medium.render("Click here to start", True, ACCENT)
                    )
                    text_width, text_height = start_text.get_size()
                    padding = 20
                    click_area = pg.Rect(
                        WIDTH // 2 - (text_width // 2 + padding),
                        HEIGHT // 2 + 40 - (text_height // 2 + padding),
                        text_width + padding * 2,
                        text_height + padding * 2
                    )
                    if click_area.collidepoint(event.pos):
                        current_screen = USERNAME
                        username_input_active = True
                
                elif current_screen == USERNAME:
                    # Check if clicked on input box
                    input_box_x = (WIDTH - INPUT_BOX_WIDTH) // 2
                    input_box_y = HEIGHT // 2 - 40
                    input_box = pg.Rect(input_box_x, input_box_y, 
                                        INPUT_BOX_WIDTH, INPUT_BOX_HEIGHT)
                    
                    if input_box.collidepoint(event.pos):
                        username_input_active = True
                    else:
                        username_input_active = False
                    
                    # Check if clicked on continue button
                    continue_text = (
                        font_medium.render("Continue", True, ACCENT)
                        )
                    continue_rect = continue_text.get_rect(
                        center=(WIDTH // 2, HEIGHT // 2 + 100)
                    )
                    continue_box = pg.Rect(
                        continue_rect.x - CONTINUE_BTN_PADDING,
                        continue_rect.y - CONTINUE_BTN_PADDING // 2,
                        continue_rect.width + CONTINUE_BTN_PADDING * 2,
                        continue_rect.height + CONTINUE_BTN_PADDING
                    )
                    if (
                        continue_box.collidepoint(event.pos)
                        and username.strip()
                    ):
                        user_baseline = update_user_baseline(username)
                        current_screen = MOOD
                        username_input_active = False
                
                elif current_screen == MOOD:
                    # Back to username screen
                    if back_btn.is_clicked(event.pos):
                        current_screen = USERNAME
                    else:
                        # Choose mood and go to sleep screen
                        for i, btn in enumerate(mood_buttons):
                            if btn.is_clicked(event.pos):
                                mood = moods[i]
                                current_screen = SLEEP
                                break
                
                elif current_screen == SLEEP:
                    # Back to mood screen
                    if back_btn.is_clicked(event.pos):
                        current_screen = MOOD
                    else:
                        # Choose sleep quality and go to menu
                        for i, btn in enumerate(sleep_buttons):
                            if btn.is_clicked(event.pos):
                                sleep = sleep_options[i]
                                current_screen = MENU
                                break
                
                elif current_screen == MENU:
                    if play_btn.is_clicked(event.pos):
                        current_screen = GAME
                        hits, spawns, reaction_times, exited_early = (
                            run_reaction_game(screen, clock, font_small)
                        )
                        
                        if not exited_early:
                            date = dt.datetime.now().date().isoformat()
                            mean_rt = (
                                round(statistics.fmean(reaction_times), 1)
                                if reaction_times else 0.0
                            )
                            save_to_csv(date, username.strip(), mood, sleep, 
                                        hits, spawns, mean_rt)
                            
                            try:
                                create_simple_timeline(username.strip())
                            except Exception as e:
                                print(f"Could not create graph: {e}")
                            
                            current_screen = RESULTS
                        else:
                            current_screen = MENU
                    
                    elif exit_btn.is_clicked(event.pos):
                        running = False
                
                elif current_screen == RESULTS:
                    if view_graph_btn.is_clicked(event.pos):
                        # Open BOTH graphs
                        graph_files = [
                            "reaction_summary.png",
                            "trial_timeline.png"
                        ]
                        
                        for i, graph_file in enumerate(graph_files):
                            if os.path.exists(graph_file):
                                try:
                                    if sys.platform.startswith('darwin'):
                                        os.system(f'open "{graph_file}"')
                                    elif sys.platform.startswith('linux'):
                                        os.system(f'xdg-open "{graph_file}"')
                                    elif sys.platform.startswith('win'):
                                        os.startfile(graph_file)
                                    # Small delay between opening files
                                    if i == 0:  # After opening first file
                                        time.sleep(0.3)
                                except Exception as e:
                                    print(
                                        f"Could not open graph file "
                                        f"{graph_file}: {e}"
                                    )
                    elif play_again_btn.is_clicked(event.pos):
                        current_screen = WELCOME
                        username = ""
                        username_input_active = False
                        user_baseline = None
                        mood = None
                        sleep = None
                    elif exit_btn_results.is_clicked(event.pos):
                        running = False
        
        # Hover effects
        hover_buttons = {
            MOOD: mood_buttons + [back_btn],
            SLEEP: sleep_buttons + [back_btn],
            MENU: [play_btn, exit_btn],
            RESULTS: [view_graph_btn, play_again_btn, exit_btn_results]
        }
        for btn in hover_buttons.get(current_screen, []):
            btn.check_hover(mouse_pos)
        
        # Drawing
        if current_screen == WELCOME:
            draw_welcome_screen(screen, font_large, font_medium)
        elif current_screen == USERNAME:
            draw_username_screen(screen, font_large, font_medium, username, 
                                 username_input_active, user_baseline)
        elif current_screen == MOOD:
            draw_screen_with_title(screen, "How do you feel?", font_large, 
                                   mood_buttons)
            back_btn.draw(screen)
        elif current_screen == SLEEP:
            draw_screen_with_title(screen, "How did you sleep today?", 
                                   font_large, sleep_buttons)
            back_btn.draw(screen)
        elif current_screen == MENU:
            draw_screen_with_title(screen, "Ready to Play?", font_large)
            play_btn.draw(screen)
            exit_btn.draw(screen)
        elif current_screen == RESULTS:
            screen.fill(BG)
            title = font_large.render("Results Generated!", True, FG)
            title_rect = title.get_rect(center=(WIDTH // 2, 80))
            screen.blit(title, title_rect)
            
            if reaction_times:
                mean_rt = statistics.fmean(reaction_times)
                perf_text = font_medium.render(
                    f"Your average reaction time: {mean_rt:.1f} ms", True, FG
                )
                perf_rect = perf_text.get_rect(center=(WIDTH // 2, 140))
                screen.blit(perf_text, perf_rect)
            
            view_graph_btn.draw(screen)
            play_again_btn.draw(screen)
            exit_btn_results.draw(screen)
        
        pg.display.flip()
    
    pg.quit()


if __name__ == "__main__":
    main()

"""
Theme loading for mic-osd.

Priority (highest to lowest):
1. Config overrides (~/.config/hyprwhspr/config.json with osd_* keys)
2. Omarchy theme files (~/.config/omarchy/current/theme/)
3. Default values (hardcoded fallback)

This allows users to always override, whether on Omarchy or other desktops.
"""

import json
import os
import re
from pathlib import Path


# Default colors (fallback if theme not found)
DEFAULT_COLORS = {
    'background-color': (0.1, 0.1, 0.15, 0.95),
    'border-color': (0.2, 0.8, 1.0),        # Cyan
    'bar-color-left': (0.2, 0.8, 1.0),      # Cyan
    'bar-color-right': (0.0, 1.0, 0.6),     # Green
    'recording-dot': (1.0, 0.2, 0.33),      # Red
    'text-color': (0.8, 0.84, 0.96, 1.0),   # Light gray
}

# Default bar settings
DEFAULT_BAR_SETTINGS = {
    'num_bars': 32,
    'bar_width': 4,
    'bar_gap': 2,
    'min_bar_height': 2,
    'amplification': 4.0,
    'decay_rate': 0.85,
    'rise_rate': 0.5,
}


def hex_to_rgb(hex_color: str) -> tuple:
    """
    Convert hex color to RGB tuple (0.0-1.0 range).
    
    Args:
        hex_color: Color in #RRGGBB or #RRGGBBAA format
        
    Returns:
        Tuple of (r, g, b) or (r, g, b, a) floats
    """
    hex_color = hex_color.strip().lstrip('#')
    
    if len(hex_color) == 6:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
    elif len(hex_color) == 8:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        a = int(hex_color[6:8], 16) / 255.0
        return (r, g, b, a)
    else:
        raise ValueError(f"Invalid hex color: {hex_color}")


def load_config() -> dict:
    """
    Load osd_* settings from hyprwhspr config.json.

    Returns:
        Dict with 'colors' and 'bar_settings' keys
    """
    config_path = Path.home() / '.config' / 'hyprwhspr' / 'config.json'
    result = {'colors': {}, 'bar_settings': {}}

    if not config_path.exists():
        return result

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        # Map osd_* color keys to internal color names
        color_map = {
            'osd_bar_color_left': 'bar-color-left',
            'osd_bar_color_right': 'bar-color-right',
            'osd_background_color': 'background-color',
            'osd_border_color': 'border-color',
            'osd_recording_dot_color': 'recording-dot',
            'osd_text_color': 'text-color',
        }

        for config_key, internal_key in color_map.items():
            if config_key in config:
                try:
                    result['colors'][internal_key] = hex_to_rgb(config[config_key])
                except ValueError:
                    pass  # Skip invalid colors

        # Map osd_* bar settings
        bar_map = {
            'osd_num_bars': 'num_bars',
            'osd_bar_width': 'bar_width',
            'osd_bar_gap': 'bar_gap',
            'osd_min_bar_height': 'min_bar_height',
            'osd_amplification': 'amplification',
            'osd_decay_rate': 'decay_rate',
            'osd_rise_rate': 'rise_rate',
        }

        for config_key, internal_key in bar_map.items():
            if config_key in config:
                result['bar_settings'][internal_key] = config[config_key]

    except (json.JSONDecodeError, IOError):
        pass  # Return empty result on error

    return result


def load_theme() -> tuple:
    """
    Load theme colors and bar settings.

    Priority (highest to lowest):
    1. Config overrides (~/.config/hyprwhspr/config.json with osd_* keys)
    2. Omarchy theme files (~/.config/omarchy/current/theme/)
    3. Default values

    Returns:
        Tuple of (colors dict, bar_settings dict)
    """
    colors = DEFAULT_COLORS.copy()
    bar_settings = DEFAULT_BAR_SETTINGS.copy()
    theme_dir = Path.home() / '.config' / 'omarchy' / 'current' / 'theme'

    # Layer 1: Apply Omarchy theme (if present)
    mic_osd_path = theme_dir / 'mic-osd.css'
    if mic_osd_path.exists():
        try:
            colors.update(parse_css_colors(mic_osd_path))
        except Exception:
            pass

    # Fall back to swayosd.css for consistent OSD styling
    swayosd_path = theme_dir / 'swayosd.css'
    if swayosd_path.exists():
        try:
            swayosd_colors = parse_css_colors(swayosd_path)

            # Map swayosd colors to mic-osd colors
            if 'background-color' in swayosd_colors:
                bg = swayosd_colors['background-color']
                if len(bg) == 3:
                    bg = (*bg, 0.95)
                colors['background-color'] = bg

            if 'border-color' in swayosd_colors:
                colors['border-color'] = swayosd_colors['border-color']
                colors['bar-color-left'] = swayosd_colors['border-color']
                colors['bar-color-right'] = swayosd_colors['border-color']

            if 'progress' in swayosd_colors:
                colors['bar-color-left'] = swayosd_colors['progress']
                colors['bar-color-right'] = swayosd_colors['progress']

        except Exception:
            pass

    # Layer 2: Apply config overrides (highest priority)
    config = load_config()
    colors.update(config['colors'])
    bar_settings.update(config['bar_settings'])

    return colors, bar_settings


def parse_css_colors(css_path: Path) -> dict:
    """
    Parse @define-color directives from a CSS file.
    
    Args:
        css_path: Path to CSS file
        
    Returns:
        Dict of color name -> RGB(A) tuple
    """
    colors = {}
    
    # Pattern: @define-color name #hexvalue;
    pattern = re.compile(r'@define-color\s+([\w-]+)\s+(#[0-9a-fA-F]{6,8})\s*;')
    
    with open(css_path, 'r') as f:
        content = f.read()
    
    for match in pattern.finditer(content):
        name = match.group(1)
        hex_color = match.group(2)
        try:
            colors[name] = hex_to_rgb(hex_color)
        except ValueError:
            pass  # Skip invalid colors silently
    
    return colors


class Theme:
    """
    Theme singleton for easy access to colors and bar settings.
    """
    _instance = None
    _colors = None
    _bar_settings = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._colors, cls._bar_settings = load_theme()
        return cls._instance

    def get(self, name: str, default=None):
        """Get a color by name."""
        return self._colors.get(name, default or DEFAULT_COLORS.get(name))

    def get_bar_setting(self, name: str, default=None):
        """Get a bar setting by name."""
        return self._bar_settings.get(name, default or DEFAULT_BAR_SETTINGS.get(name))

    def reload(self):
        """Reload theme from disk."""
        self._colors, self._bar_settings = load_theme()
    
    @property
    def background(self):
        return self.get('background-color')
    
    @property
    def border(self):
        return self.get('border-color')
    
    @property
    def bar_left(self):
        return self.get('bar-color-left')
    
    @property
    def bar_right(self):
        return self.get('bar-color-right')
    
    @property
    def recording_dot(self):
        color = self.get('recording-dot')
        # Ensure alpha channel
        if len(color) == 3:
            return (*color, 1.0)
        return color
    
    @property
    def text(self):
        color = self.get('text-color')
        # Ensure alpha channel
        if len(color) == 3:
            return (*color, 1.0)
        return color

    # Bar settings properties
    @property
    def num_bars(self):
        return int(self.get_bar_setting('num_bars'))

    @property
    def bar_width(self):
        return int(self.get_bar_setting('bar_width'))

    @property
    def bar_gap(self):
        return int(self.get_bar_setting('bar_gap'))

    @property
    def min_bar_height(self):
        return int(self.get_bar_setting('min_bar_height'))

    @property
    def amplification(self):
        return float(self.get_bar_setting('amplification'))

    @property
    def decay_rate(self):
        return float(self.get_bar_setting('decay_rate'))

    @property
    def rise_rate(self):
        return float(self.get_bar_setting('rise_rate'))


# Global theme instance
theme = Theme()


class ThemeWatcher:
    """
    Watches for Omarchy theme changes and reloads the theme.
    
    Omarchy uses `ln -nsf` to atomically swap the theme symlink, which
    inotify/GLib.FileMonitor can't detect. Instead, we poll the symlink
    target every second (negligible overhead, theme changes are rare).
    """
    
    def __init__(self, on_theme_changed=None):
        """
        Initialize the theme watcher.
        
        Args:
            on_theme_changed: Optional callback to invoke after theme reload
        """
        self._timer_id = None
        self._last_target = None
        self._on_theme_changed = on_theme_changed
        self._theme_link = Path.home() / '.config' / 'omarchy' / 'current' / 'theme'
    
    def start(self):
        """Start polling the theme symlink for changes."""
        from gi.repository import GLib
        import os
        
        if not self._theme_link.exists():
            return False
        
        try:
            # Record initial target
            self._last_target = os.readlink(self._theme_link)
            # Poll every 1 second
            self._timer_id = GLib.timeout_add(1000, self._check_theme)
            return True
        except Exception:
            return False
    
    def stop(self):
        """Stop polling."""
        from gi.repository import GLib
        
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
    
    def _check_theme(self):
        """Check if theme symlink target has changed."""
        import os
        
        try:
            current_target = os.readlink(self._theme_link)
            if current_target != self._last_target:
                self._last_target = current_target
                self._reload_theme()
        except Exception:
            pass
        
        return True  # Keep polling
    
    def _reload_theme(self):
        """Reload theme."""
        theme.reload()
        if self._on_theme_changed:
            self._on_theme_changed()

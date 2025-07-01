import time
from multiprocessing import Queue
from typing import Any, Optional
import subprocess
# import Quartz # Removed as it's macOS-specific and no longer used

import pyautogui
from utils.screen import Screen


class Interpreter:
    def __init__(self, status_queue: Queue):
        self.status_queue = status_queue
        self.screen = Screen()
        
        # Configure PyAutoGUI
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 1.0  # Increased delay between actions
        
        # Check if we have accessibility permissions
        self._check_accessibility_permissions()

        # OS specific key mappings
        self.key_mappings = {
            'command': ['command'],  # macOS
            'option': ['alt'],  # macOS
            'control': ['ctrl'],
            'return': ['return'],
            'enter': ['return'], # Alias for return
            'space': ['space'],
            'esc': ['escape'],
            'win': ['win'],  # Windows
            'apps': ['apps']  # Windows context menu key
        }

    def _check_accessibility_permissions(self):
        """Check if the app has necessary permissions or inform the user."""
        import platform
        os_name = platform.system().lower()

        if os_name == "darwin":  # macOS
            try:
                # Try a simple mouse movement to test permissions
                current_pos = pyautogui.position()
                pyautogui.moveRel(0, 0) # This can fail if permissions are not granted
                pyautogui.moveTo(*current_pos)
            except Exception as e:
                # More specific error message for macOS
                error_message = (
                    "WARNING: macOS Accessibility Permissions Needed. \n"
                    "Please grant access in: \n"
                    "System Settings > Privacy & Security > Accessibility > Add this app."
                )
                self.status_queue.put(error_message)
                print(error_message)
        elif os_name == "windows":
            # For Windows, pyautogui generally works without special permissions
            # for most tasks. However, interacting with UAC-protected windows
            # or apps running as admin might require the script to be run as admin.
            info_message = (
                "INFO: On Windows, if you encounter issues controlling certain applications, "
                "try running this script/application as an Administrator."
            )
            # We don't want to spam this every time, perhaps only if an error occurs later.
            # For now, let's just print it once for awareness.
            print(info_message)
            # self.status_queue.put(info_message) # Optional: send to status queue
        # No specific checks for other OSes like Linux for now

    def process_command(self, command: dict[str, Any]) -> bool:
        print(f"DEBUG - Received command: {command}")
        
        command_type = command.get('type', '')
        command_value = command.get('value', '')
        x = command.get('x')
        y = command.get('y')
        description = command.get('description', 'Executing command...')
        
        self.status_queue.put(description)
        
        try:
            if command_type == 'click':
                return self._handle_click(x, y)
            elif command_type == 'move':
                return self._handle_move(x, y)
            elif command_type == 'drag':
                return self._handle_drag(x, y)
            elif command_type == 'scroll':
                return self._handle_scroll(command_value)
            elif command_type == 'type':
                return self._handle_type(command_value)
            elif command_type == 'press':
                return self._handle_press(command_value)
            elif command_type == 'hotkey':
                return self._handle_hotkey(command_value)
            else:
                print(f"Unknown command type: {command_type}")
                return False
        except Exception as e:
            print(f"Error executing command: {e}")
            return False

    def _handle_click(self, x: int, y: int) -> bool:
        """Click at specified coordinates."""
        try:
            print(f"DEBUG - Clicking at coordinates: ({x}, {y})")
            # Move first (if not already there)
            current_x, current_y = pyautogui.position()
            if current_x != x or current_y != y:
                pyautogui.moveTo(x=x, y=y, duration=0.5)
                time.sleep(0.2)  # Small pause after movement
            
            pyautogui.click(x=x, y=y)
            time.sleep(0.2)  # Small pause after click
            return True
        except Exception as e:
            self.status_queue.put(f'Click failed at ({x}, {y}): {e}')
            return False

    def _handle_type(self, text: str) -> bool:
        try:
            print(f"DEBUG - Typing text: {text}")
            
            # Get current text field position if possible
            try:
                x, y = pyautogui.position()
                # Highlight a small region around the cursor
                self.screen.highlight_region(x-50, y-10, 100, 20)
            except Exception as e:
                print(f"Error highlighting text field: {e}")
            
            # Type with interval between keys
            pyautogui.write(text, interval=0.1)
            return True
        except Exception as e:
            self.status_queue.put(f'Type failed for "{text}": {e}')
            return False

    def _handle_press(self, key: str) -> bool:
        try:
            # Map common key names
            mapped_key = self.key_mappings.get(key.lower(), [key])[0]
            print(f"DEBUG - Pressing key: {mapped_key} (original: {key})")
            
            # Special handling for enter/return key
            if key.lower() in ['enter', 'return']:
                print("DEBUG - Using special handling for enter/return key")
                pyautogui.keyDown('return')
                time.sleep(0.2)
                pyautogui.keyUp('return')
            else:
                # Press with duration
                pyautogui.keyDown(mapped_key)
                time.sleep(0.2)
                pyautogui.keyUp(mapped_key)
            
            return True
        except Exception as e:
            self.status_queue.put(f'Press failed for key "{key}": {e}')
            return False

    def _handle_hotkey(self, keys: str) -> bool:
        try:
            # Split and map the keys
            key_list = []
            for k in keys.split('+'):
                mapped = self.key_mappings.get(k.strip().lower(), [k.strip()])[0]
                key_list.append(mapped)
            
            print(f"DEBUG - Pressing hotkey combination: {key_list}")
            
            # The Mac-specific active window highlighting has been removed for cross-platform compatibility.
            # If active window highlighting is desired on other platforms,
            # it would need to be implemented using appropriate libraries (e.g., pygetwindow).

            # Press all keys in sequence
            for key in key_list:
                pyautogui.keyDown(key)
                time.sleep(0.1)
            
            # Release in reverse order
            for key in reversed(key_list):
                pyautogui.keyUp(key)
                time.sleep(0.1)
            
            return True
        except Exception as e:
            self.status_queue.put(f'Hotkey failed for "{keys}": {e}')
            return False

    def _handle_move(self, x: int, y: int) -> bool:
        """Move mouse to specified coordinates."""
        try:
            print(f"DEBUG - Moving mouse to coordinates: ({x}, {y})")
            pyautogui.moveTo(x=x, y=y, duration=0.5)
            time.sleep(0.2)  # Small pause after movement
            return True
        except Exception as e:
            self.status_queue.put(f'Mouse move failed to ({x}, {y}): {e}')
            return False

    def _handle_drag(self, x: int, y: int) -> bool:
        """Drag mouse to specified coordinates."""
        try:
            print(f"DEBUG - Dragging to coordinates: ({x}, {y})")
            pyautogui.dragTo(x=x, y=y, duration=1.0)  # Slower duration for drag
            time.sleep(0.2)  # Small pause after drag
            return True
        except Exception as e:
            self.status_queue.put(f'Drag failed to ({x}, {y}): {e}')
            return False

    def _handle_scroll(self, amount: int) -> bool:
        """Scroll the mouse wheel. Positive values scroll up, negative values scroll down."""
        try:
            print(f"DEBUG - Scrolling amount: {amount}")
            pyautogui.scroll(clicks=amount)
            time.sleep(0.2)  # Small pause after scroll
            return True
        except Exception as e:
            self.status_queue.put(f'Scroll failed with amount {amount}: {e}')
            return False 
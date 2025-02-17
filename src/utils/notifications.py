import subprocess

def send_mac_notification(title: str, message: str) -> None:
    """Send a push notification on macOS."""
    apple_script = f'display notification "{message}" with title "{title}"'
    subprocess.run(['osascript', '-e', apple_script]) 
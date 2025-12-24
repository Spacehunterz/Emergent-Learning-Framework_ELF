"""
Control script for Data face overlay

Usage:
    python overlay_control.py talk    # Start talking (lip-sync video)
    python overlay_control.py idle    # Stop talking (static image)
    python overlay_control.py quit    # Close overlay

For TTS integration:
    - Call 'talk' when TTS starts speaking
    - Call 'idle' when TTS finishes
"""

import socket
import sys

def send_command(cmd, port=5112):
    """Send a command to the overlay server"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(cmd.encode(), ('127.0.0.1', port))
        sock.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python overlay_control.py [talk|idle|quit]")
        print("  talk  - Switch to talking/lip-sync mode")
        print("  idle  - Switch to static/idle mode")
        print("  quit  - Close the overlay")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5112
    send_command(cmd, port)

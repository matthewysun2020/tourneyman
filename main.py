import subprocess
import time
import webbrowser
import tkinter as tk
from tkinter import font
from threading import Thread
import socket

def start_flask():
    global flask_process   
    flask_process = subprocess.Popen(['python', 'app.py'])

def stop_flask():
    global flask_process
    if flask_process:
        flask_process.terminate()  # Terminate the Flask subprocess
        flask_process = None  # Reset the global variable

def get_local_ip():
    # Get the local IP address of the device
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def display_url(url):
    root = tk.Tk()
    root.title("tourneyman")
    root.geometry("800x450")  # Set initial window size

    def _quit():
        root.quit()
        root.destroy()
        stop_flask()
        print("exited")

    root.protocol("WM_DELETE_WINDOW", _quit)

    # Define custom fonts
    title_font = font.Font(family="Bahnschrift SemiBold", size=35, weight="bold")
    text_font = font.Font(family="Bahnschrift", size=18)
    url_font = font.Font(family="Bahnschrift", size=18, underline=1)
    disclaimer_font = font.Font(family="Bahnschrift Light", size = 12)

    # Create title label
    title_label = tk.Label(root, text="tourneyman", font=title_font)
    title_label.pack(pady=20)

    # Create text label
    text_label = tk.Label(root, text="Welcome to tourneyman!\nAccess your tournament at:", font=text_font)
    text_label.pack(pady=10)

    # Create URL button
    url_button = tk.Button(root, text="Open tourneyman", font=url_font, fg="white", bg="#007bff", borderwidth=1, relief="groove", padx=10, pady=5)
    url_button.pack(pady=10)
    url_button.bind("<Button-1>", lambda e: webbrowser.open_new(url))

    # Create disclaimer label
    disclaimer_label = tk.Label(root, text="Please keep this window open.\n\nThis application is in development.\nPlease report any bugs.", font=disclaimer_font)
    disclaimer_label.pack(pady=10)

    root.mainloop()

def main():
    # Start the Flask server in a separate thread
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    # Give Flask some time to start up
    time.sleep(2)

    # Get the local IP address of the device
    local_ip = get_local_ip()

    # Define the port on which Flask is running
    port = 5000

    # Construct the URL
    url = f"http://{local_ip}:{port}"

    # Display the URL in a GUI
    display_url(url)

if __name__ == '__main__':
    main()

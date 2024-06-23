import subprocess
import time
import requests
import webbrowser
import tkinter as tk
from threading import Thread

def start_flask():
    subprocess.Popen(['python', 'app.py'], env={"PORT": "0"})

def get_localtunnel_url(port):
    result = subprocess.run(['lt', '--port', str(port)], capture_output=True, text=True)
    url_line = result.stdout.splitlines()[-1]  # Get the last line which should contain the URL
    return url_line.strip()

def start_localtunnel(port):
    process = subprocess.Popen(['lt', '--port', str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in process.stdout:
        if b'your url is:' in line:
            return line.decode().split(' ')[-1].strip()

def display_url(url):
    root = tk.Tk()
    root.title("Tournament URL")

    label = tk.Label(root, text="Access the tournament site at:")
    label.pack(pady=10)

    url_label = tk.Label(root, text=url, fg="blue", cursor="hand2")
    url_label.pack(pady=10)
    url_label.bind("<Button-1>", lambda e: webbrowser.open_new(url))

    root.mainloop()

def main():
    # Start the Flask server in a separate thread
    flask_thread = Thread(target=start_flask)
    flask_thread.start()

    # Give Flask some time to start up
    time.sleep(5)

    # Get the port Flask is running on (assuming default port 5000 for this example)
    port = 5000  # You might need to dynamically find the port if not fixed

    # Start Localtunnel and get the public URL
    url = start_localtunnel(port)

    # Display the URL in a GUI
    display_url(url)

if __name__ == '__main__':
    main()

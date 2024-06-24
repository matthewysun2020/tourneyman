import subprocess
import time
import webbrowser
import tkinter as tk
from tkinter import font
from threading import Thread
import socket

def start_flask():
    subprocess.Popen(['python', 'app.py'])

def get_local_ip():
    # Get the local IP address of the device
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
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

    # Define custom fonts
    title_font = font.Font(family="Arial", size=20, weight="bold")
    text_font = font.Font(family="Helvetica", size=14)

    # Create title label
    title_label = tk.Label(root, text="tourneyman", font=title_font)
    title_label.pack(pady=20)

    # Create text Label
    text_label = tk.Label(root, text="Welcome to tourneyman!\nAccess your tournament at:", font=text_font)
    text_label.pack(pady=10)

    # Create URL label
    url_label = tk.Label(root, text=url, font=text_font, fg="blue", cursor="hand2")
    url_label.pack(pady=10)
    url_label.bind("<Button-1>", lambda e: webbrowser.open_new(url))

    root.mainloop()

def temp():
    root = tk.Tk()
    root.title('Font Families')
    fonts=list(font.families())
    fonts.sort()

    def populate(frame):
        '''Put in the fonts'''
        listnumber = 1
        for i, item in enumerate(fonts):
            label = "listlabel" + str(listnumber)
            label = Label(frame,text=item,font=(item, 16))
            label.grid(row=i)
            label.bind("<Button-1>",lambda e,item=item:copy_to_clipboard(item))
            listnumber += 1

    def copy_to_clipboard(item):
        root.clipboard_clear()
        root.clipboard_append("font=('" + item.lstrip('@') + "', 12)")

    def onFrameConfigure(canvas):
        '''Reset the scroll region to encompass the inner frame'''
        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas = Canvas(root, borderwidth=0, background="#ffffff")
    frame = Frame(canvas, background="#ffffff")
    vsb = Scrollbar(root, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)

    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((4,4), window=frame, anchor="nw")

    frame.bind("<Configure>", lambda event, canvas=canvas: onFrameConfigure(canvas))

    populate(frame)

    root.mainloop()

def main():
    # Start the Flask server in a separate thread
    flask_thread = Thread(target=start_flask)
    flask_thread.start()
    print("Flask server started")

    # Give Flask some time to start up
    time.sleep(5)

    # Get the local IP address of the device
    local_ip = get_local_ip()

    # Define the port on which Flask is running
    port = 5000

    # Construct the URL
    url = f"http://{local_ip}:{port}"

    # Display the URL in a GUI
    display_url(url)
    temp()

if __name__ == '__main__':
    main()

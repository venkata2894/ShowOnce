from pynput import mouse
import time

def on_click(x, y, button, pressed):
    if pressed:
        print(f"Mouse clicked at ({x}, {y}) with {button}")

def test_mouse_listener():
    print("Starting mouse listener... Click anywhere (Testing for 5 seconds)")
    with mouse.Listener(on_click=on_click) as listener:
        time.sleep(5)
        listener.stop()

if __name__ == "__main__":
    test_mouse_listener()

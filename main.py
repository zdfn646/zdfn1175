import flet as ft
import math
import os
import base64

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# ================= 兼容新旧版本 Flet 的垫片 =================
def get_border_all(width, color):
    try: return ft.Border.all(width, color)
    except AttributeError: return ft.border.all(width, color)

def get_padding_symmetric(h, v):
    try: return ft.Padding.symmetric(horizontal=h, vertical=v)
    except AttributeError: return ft.padding.symmetric(horizontal=h, vertical=v)

def get_alignment_center():
    try: return ft.Alignment(0, 0)
    except AttributeError: return ft.alignment.center

def get_local_pos(e):
    x = getattr(e, "local_x", None)
    if x is not None: return x, getattr(e, "local_y", 0.0)
    if hasattr(e, "local_position") and e.local_position is not None:
        pos = e.local_position
        return getattr(pos, "dx", getattr(pos, "x", 0.0)), getattr(pos, "dy", getattr(pos, "y", 0.0))
    return 0.0, 0.0

# 读取图片为 Base64 (绝对解决手机端不显示图片的问题)
def get_img_src(filename):
    path = os.path.join(BASE_PATH, filename)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"
    return filename
# ============================================================

def main(page: ft.Page):
    page.title = "曲线行驶模拟"
    page.padding = 0
    page.spacing = 0

    # 强制横屏
    try:
        page.window.orientation = ft.Orientation.LANDSCAPE
    except:
        pass

    state = {
        "car_x": 300.0, "car_y": 500.0, "angle_rad": math.pi / 2, 
        "is_dragging": False, "is_rotating": False, 
        "drag_offset_x": 0.0, "drag_offset_y": 0.0, "last_angle": 0.0
    }
    HANDLE_RADIUS, HANDLE_DISTANCE = 20, 90

    # 加载图片
    bg_img = ft.Image(src=get_img_src("233c.png"), fit="cover", width=2000, height=2000)
    car_img = ft.Image(src=get_img_src("car2.png"), width=210, height=100, fit="contain")
    
    car_container = ft.Container(
        content=car_img, width=210, height=100, 
        rotate=ft.Rotate(angle=0), alignment=get_alignment_center()
    )
    handle_container = ft.Container(
        width=HANDLE_RADIUS * 2, height=HANDLE_RADIUS * 2, 
        bgcolor="#4CAF50", border=get_border_all(2, "#FFFFFF"), border_radius=HANDLE_RADIUS
    )

    # 安全退出逻辑
    def close_dialog(dlg):
        dlg.open = False
        page.update()

    def really_close(e):
        page.overlay.clear()
        page.controls.clear()
        page.bgcolor = ft.Colors.BLACK
        page.add(
            ft.Container(
                content=ft.Text("程序已安全退出", color="white", size=24, text_align="center"),
                alignment=get_alignment_center(), expand=True
            )
        )
        page.update()
        try: page.window.close()
        except: pass

    def show_exit_dialog(e):
        dlg = ft.AlertDialog(
            title=ft.Text("确认退出"),
            content=ft.Text("您确定要退出曲线行驶模拟吗？"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: close_dialog(dlg)),
                ft.TextButton("确定退出", on_click=really_close, style=ft.ButtonStyle(color=ft.Colors.RED)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    quit_btn = ft.Container(
        content=ft.Text("退出", color="#FFFFFF", weight="bold", size=16),
        bgcolor="#F44336", padding=get_padding_symmetric(20, 10),
        border_radius=8, top=30, right=30, on_click=show_exit_dialog
    )

    def update_ui():
        cx, cy, rad = state["car_x"], state["car_y"], state["angle_rad"]
        car_container.left, car_container.top = cx - 105, cy - 50
        car_container.rotate.angle = -math.degrees(rad)
        handle_x = cx + math.cos(rad) * HANDLE_DISTANCE
        handle_y = cy - math.sin(rad) * HANDLE_DISTANCE
        handle_container.left, handle_container.top = handle_x - HANDLE_RADIUS, handle_y - HANDLE_RADIUS
        page.update()

    def on_resize(e=None):
        if state["car_x"] == 300.0 and state["car_y"] == 500.0:
            state["car_x"] = page.width / 2 if page.width else 400
            state["car_y"] = page.height / 2 if page.height else 600
            update_ui()

    page.on_resize = on_resize

    def on_pan_start(e: ft.DragStartEvent):
        fx, fy = get_local_pos(e)
        cx, cy = state["car_x"], state["car_y"]
        handle_x = cx + math.cos(state["angle_rad"]) * HANDLE_DISTANCE
        handle_y = cy - math.sin(state["angle_rad"]) * HANDLE_DISTANCE

        if math.hypot(fx - handle_x, fy - handle_y) <= HANDLE_RADIUS + 20:
            state["is_rotating"] = True
            state["last_angle"] = math.atan2(cy - fy, fx - cx)
            return
        if math.hypot(fx - cx, fy - cy) < 100:
            state["is_dragging"] = True
            state["drag_offset_x"] = cx - fx
            state["drag_offset_y"] = cy - fy

    def on_pan_update(e: ft.DragUpdateEvent):
        fx, fy = get_local_pos(e)
        cx, cy = state["car_x"], state["car_y"]

        if state["is_dragging"]:
            state["car_x"] = fx + state["drag_offset_x"]
            state["car_y"] = fy + state["drag_offset_y"]
            update_ui()
        elif state["is_rotating"]:
            current_angle = math.atan2(cy - fy, fx - cx)
            delta_angle = current_angle - state["last_angle"]
            if delta_angle > math.pi: delta_angle -= 2 * math.pi
            elif delta_angle < -math.pi: delta_angle += 2 * math.pi
            state["angle_rad"] += delta_angle * 0.1  # 灵敏度调节
            state["last_angle"] = current_angle
            update_ui()

    def on_pan_end(e: ft.DragEndEvent):
        state["is_dragging"], state["is_rotating"] = False, False

    gesture_layer = ft.GestureDetector(
        on_pan_start=on_pan_start, on_pan_update=on_pan_update, on_pan_end=on_pan_end,
        content=ft.Container(bgcolor="transparent", expand=True), drag_interval=10,
    )

    page.add(
        ft.Stack(controls=[ft.Container(content=bg_img, expand=True), car_container, handle_container, gesture_layer, quit_btn], expand=True)
    )
    on_resize()

if __name__ == "__main__":
    try: ft.run(main)
    except AttributeError: ft.app(target=main)

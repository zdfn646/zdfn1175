import flet as ft
import math
import os
import base64
import time
import sys

# ================= 尝试引入安卓原生 API =================
try:
    from android import PythonActivity
    from android.runnable import run_on_ui_thread
    HAS_ANDROID = True
except ImportError:
    HAS_ANDROID = False
# =========================================================

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

    # 1. 尝试 Flet 自带横屏
    try:
        page.window.orientation = ft.Orientation.LANDSCAPE
        page.window.full_screen = True
    except:
        pass

    # 2. 使用安卓底层强制横屏 (最有效)
    if HAS_ANDROID:
        try:
            @run_on_ui_thread
            def force_landscape():
                # SCREEN_ORIENTATION_LANDSCAPE = 0
                PythonActivity.mActivity.setRequestedOrientation(0) 
            force_landscape()
        except:
            pass

    state = {
        "car_x": 300.0, "car_y": 500.0, "angle_rad": math.pi / 2, 
        "is_dragging": False, "is_rotating": False, 
        "drag_offset_x": 0.0, "drag_offset_y": 0.0, "last_angle": 0.0
    }
    
    CAR_W = 315
    CAR_H = 150
    HANDLE_RADIUS = 20
    HANDLE_DISTANCE = 135 

    bg_img = ft.Image(src=get_img_src("233c.png"), fit="cover", width=2000, height=2000)
    car_img = ft.Image(src=get_img_src("car2.png"), width=CAR_W, height=CAR_H, fit="contain")
    
    car_container = ft.Container(
        content=car_img, width=CAR_W, height=CAR_H, 
        rotate=ft.Rotate(angle=0), alignment=get_alignment_center()
    )
    handle_container = ft.Container(
        width=HANDLE_RADIUS * 2, height=HANDLE_RADIUS * 2, 
        bgcolor="#4CAF50", border=get_border_all(2, "#FFFFFF"), border_radius=HANDLE_RADIUS
    )

    # ================= 退出逻辑（调用底层强杀） =================
    def hide_exit_ui(e):
        exit_overlay.visible = False
        page.update()

    def really_close(e):
        # 关闭遮罩
        exit_overlay.visible = False
        page.update()

        # 如果在手机上，直接调用底层 finish()，直接退回桌面
        if HAS_ANDROID:
            try:
                @run_on_ui_thread
                def close_android():
                    PythonActivity.mActivity.finish()
                    os._exit(0)
                close_android()
                return
            except:
                pass
        
        # 如果在电脑上
        try:
            page.window.destroy()
        except:
            try:
                page.window.close()
            except:
                pass
        os._exit(0)

    def show_exit_ui(e):
        exit_overlay.visible = True
        page.update()

    exit_overlay = ft.Container(
        visible=False, expand=True, bgcolor="#80000000", alignment=get_alignment_center(),
        content=ft.Container(
            width=300, padding=20, bgcolor=ft.Colors.WHITE, border_radius=15,
            content=ft.Column([
                ft.Text("确认退出", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.Text("您确定要退出曲线行驶模拟吗？", size=14, color=ft.Colors.GREY_800),
                ft.Row([
                    ft.TextButton("取消", on_click=hide_exit_ui),
                    ft.TextButton("确定退出", on_click=really_close, style=ft.ButtonStyle(color=ft.Colors.RED)),
                ], alignment=ft.MainAxisAlignment.END)
            ], spacing=15)
        )
    )

    quit_btn = ft.Container(
        content=ft.Text("退出", color="#FFFFFF", weight="bold", size=16),
        bgcolor="#F44336", padding=get_padding_symmetric(20, 10),
        border_radius=8, top=30, right=30, on_click=show_exit_ui
    )

    # ★ 防抖机制（防闪烁）
    last_update_time = [0.0]
    def update_ui(force=False):
        now = time.time()
        if force or (now - last_update_time[0] > 0.03):
            cx, cy, rad = state["car_x"], state["car_y"], state["angle_rad"]
            car_container.left, car_container.top = cx - CAR_W / 2, cy - CAR_H / 2
            car_container.rotate.angle = -math.degrees(rad)
            
            handle_x = cx + math.cos(rad) * HANDLE_DISTANCE
            handle_y = cy - math.sin(rad) * HANDLE_DISTANCE
            handle_container.left, handle_container.top = handle_x - HANDLE_RADIUS, handle_y - HANDLE_RADIUS
            
            page.update()
            last_update_time[0] = now

    def on_resize(e=None):
        if state["car_x"] == 300.0 and state["car_y"] == 500.0:
            state["car_x"] = page.width / 2 if page.width else 400
            state["car_y"] = page.height / 2 if page.height else 600
            update_ui(force=True)

    page.on_resize = on_resize

    def on_pan_start(e: ft.DragStartEvent):
        fx, fy = get_local_pos(e)
        if fx == 0.0 and fy == 0.0: return 
        
        cx, cy = state["car_x"], state["car_y"]
        handle_x = cx + math.cos(state["angle_rad"]) * HANDLE_DISTANCE
        handle_y = cy - math.sin(state["angle_rad"]) * HANDLE_DISTANCE

        if math.hypot(fx - handle_x, fy - handle_y) <= HANDLE_RADIUS + 30:
            state["is_rotating"] = True
            state["last_angle"] = math.atan2(cy - fy, fx - cx)
            return
        if math.hypot(fx - cx, fy - cy) < (CAR_W / 2 + 30):
            state["is_dragging"] = True
            state["drag_offset_x"] = cx - fx
            state["drag_offset_y"] = cy - fy

    def on_pan_update(e: ft.DragUpdateEvent):
        fx, fy = get_local_pos(e)
        if fx == 0.0 and fy == 0.0: return 

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
            
            state["angle_rad"] += delta_angle * 0.1
            state["last_angle"] = current_angle
            update_ui()

    def on_pan_end(e: ft.DragEndEvent):
        state["is_dragging"], state["is_rotating"] = False, False
        update_ui(force=True) 

    gesture_layer = ft.GestureDetector(
        on_pan_start=on_pan_start, on_pan_update=on_pan_update, on_pan_end=on_pan_end,
        content=ft.Container(bgcolor="transparent", expand=True), drag_interval=10,
    )

    page.add(
        ft.Stack(
            controls=[
                ft.Container(content=bg_img, expand=True), 
                car_container, 
                handle_container, 
                gesture_layer, 
                quit_btn,
                exit_overlay
            ], 
            expand=True
        )
    )
    update_ui(force=True)

if __name__ == "__main__":
    try: ft.run(main)
    except AttributeError: ft.app(target=main)

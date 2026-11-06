import math
import os
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color, Line, Ellipse, PushMatrix, PopMatrix, Rotate

# 强制全屏（手机端生效）
Window.fullscreen = 'auto'
# 如果在电脑测试，可以取消下面这行的注释
# Window.size = (1000, 600)

class GameCanvas(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 加载图片纹理
        self.bg_texture = Image(source='233c.png').texture
        self.car_texture = Image(source='car2.png').texture
        
        # 参数初始化
        self.car_w = 180
        self.car_h = 90
        self.car_x = Window.width / 2
        self.car_y = Window.height / 2
        self.car_angle = 90.0  # 初始角度：90度朝上
        self.handle_dist = 135 # 旋转手柄距离（车头前方）
        
        self.is_dragging = False
        self.is_rotating = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.last_angle = 0.0

        # 绑定窗口尺寸变化
        Window.bind(on_resize=self.on_resize)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def on_resize(self, window, width, height):
        # 限制车不要跑出屏幕
        self.car_x = max(90, min(self.car_x, width - 90))
        self.car_y = max(45, min(self.car_y, height - 45))
        self.update_canvas()

    def update_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            # 1. 画背景
            Rectangle(texture=self.bg_texture, pos=(0, 0), size=(Window.width, Window.height))
            
            # 2. 画车身
            PushMatrix()
            # Kivy 中，逆时针旋转为正。利用增量计算时，角度无需取反
            Rotate(angle=self.car_angle, origin=(self.car_x, self.car_y))
            Rectangle(
                texture=self.car_texture,
                pos=(self.car_x - self.car_w / 2, self.car_y - self.car_h / 2),
                size=(self.car_w, self.car_h)
            )
            PopMatrix()
            
            # 3. 计算手柄位置（车头正前方）
            rad = math.radians(self.car_angle)
            handle_x = self.car_x + math.cos(rad) * self.handle_dist
            handle_y = self.car_y + math.sin(rad) * self.handle_dist
            
            # 4. 画连接线
            Color(0, 1, 0, 1) # 绿色
            Line(points=[self.car_x, self.car_y, handle_x, handle_y], width=2)
            
            # 5. 画旋转手柄（绿圈+白边）
            Color(0, 1, 0, 1)
            Ellipse(pos=(handle_x - 25, handle_y - 25), size=(50, 50))
            Color(1, 1, 1, 1)
            Line(circle=(handle_x, handle_y, 25), width=2)

    def on_touch_down(self, touch):
        rad = math.radians(self.car_angle)
        handle_x = self.car_x + math.cos(rad) * self.handle_dist
        handle_y = self.car_y + math.sin(rad) * self.handle_dist

        # 1. 点到了手柄？ (范围加大到 50，更好点)
        if math.hypot(touch.x - handle_x, touch.y - handle_y) <= 50: 
            self.is_rotating = True
            self.last_angle = math.atan2(touch.y - self.car_y, touch.x - self.car_x)
            return True
            
        # 2. 点到了车身？
        if math.hypot(touch.x - self.car_x, touch.y - self.car_y) < 110:
            self.is_dragging = True
            self.drag_offset_x = self.car_x - touch.x
            self.drag_offset_y = self.car_y - touch.y
            return True

        return False

    def on_touch_move(self, touch):
        if self.is_dragging:
            # 拖拽位置
            self.car_x = touch.x + self.drag_offset_x
            self.car_y = touch.y + self.drag_offset_y
            
            # 边界限制
            self.car_x = max(90, min(self.car_x, Window.width - 90))
            self.car_y = max(45, min(self.car_y, Window.height - 45))
            
            self.update_canvas()
            return True

        elif self.is_rotating:
            # ★ 核心修复：增量角度计算，绝对不跳变，手感极度顺滑
            current_angle = math.atan2(touch.y - self.car_y, touch.x - self.car_x)
            delta = current_angle - self.last_angle
            
            # 处理跨越 -180 / 180 度的突变
            if delta > math.pi: delta -= 2 * math.pi
            elif delta < -math.pi: delta += 2 * math.pi
            
            # 将增量累加到车头角度上
            self.car_angle += math.degrees(delta) 
            self.last_angle = current_angle
            
            self.update_canvas()
            return True

        return False

    def on_touch_up(self, touch):
        self.is_dragging = False
        self.is_rotating = False
        return False


class MainGame(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 1. 将画板放在底层
        self.game_canvas = GameCanvas()
        self.add_widget(self.game_canvas)
        
        # 2. 将退出按钮独立放在顶层，不会被画布遮挡
        self.quit_btn = Button(
            text="退 出", 
            size_hint=(None, None), 
            size=(120, 60),
            pos_hint={'right': 0.95, 'top': 0.95}, # 固定在右上角
            background_color=(0.95, 0.26, 0.21, 1), # 红色
            font_size='20sp',
            bold=True
        )
        self.quit_btn.bind(on_release=self.quit_app)
        self.add_widget(self.quit_btn)

    def quit_app(self, instance):
        # ★ 终极退出：既发退出信号，又强行杀掉系统进程
        App.get_running_app().stop()
        os._exit(0)

    # 拦截触摸事件，优先判断是否点到了按钮
    def on_touch_down(self, touch):
        if self.quit_btn.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        
        if self.game_canvas.on_touch_down(touch):
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.game_canvas.on_touch_move(touch):
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.game_canvas.on_touch_up(touch)
        return super().on_touch_up(touch)


class MyApp(App):
    def build(self):
        return MainGame()

if __name__ == '__main__':
    MyApp().run()
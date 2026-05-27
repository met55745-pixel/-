import json
import os
import socket
import threading
import webbrowser
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.clock import Clock
from kivy.core.window import Window

# Ссылка для симуляции оплаты СБП через внешнюю веб-страницу
QR_TARGET_URL = "https://huggingface.co/spaces/3pretka/spb_bank/tree/main"

# ==========================================
# ХАРДКОРНАЯ НАСТРОЙКА ОКНА И СЕТЕВОГО ХОСТА
# ==========================================
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000

# Четкий вертикальный формат экрана смарт-терминала SberPOS
Window.size = (430, 820)

# Премиальная цветовая палитра экосистемы (Темный глубокий зеленый неон)
COLOR_BG_DARK = (0.01, 0.06, 0.04, 1)
COLOR_SUCCESS_BG = (0.02, 0.04, 0.03, 1)
COLOR_SUCCESS_NEON = (0.23, 0.85, 0.39, 1)
COLOR_TEXT_WHITE = (1, 1, 1, 1)
COLOR_TEXT_MUTED = (0.5, 0.6, 0.5, 0.8)

# ==========================================
# КАСТОМНЫЕ СТИЛИЗОВАННЫЕ КОМПОНЕНТЫ ГРАФИКИ
# ==========================================

class GlassCard(BoxLayout):
    """
    Компонент высокотехнологичной стеклянной подложки.
    Использует RoundedRectangle для создания эффекта размытого матового стекла.
    """
    def __init__(self, bg_color=(1, 1, 1, 0.06), radius=24, **kwargs):
        super(GlassCard, self).__init__(**kwargs)
        self.radius = radius
        with self.canvas.before:
            Color(*bg_color)
            self.rect = RoundedRectangle(radius=[self.radius,], size=self.size, pos=self.pos)
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        """Динамически перерисовывает подложку при изменении геометрии окна"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class PremiumButton(Button):
    """
    Интерактивная кнопка управления с кастомным сглаженным фоном.
    Полностью убирает дефолтные текстуры Kivy для чистого flat-дизайна.
    """
    def __init__(self, bg_color=(0.1, 0.1, 0.1, 0.9), radius=16, **kwargs):
        super(PremiumButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.markup = True
        self.font_name = 'Roboto'
        self.current_bg = bg_color
        self.radius = radius
        
        with self.canvas.before:
            self.paint_color = Color(*self.current_bg)
            self.rect = RoundedRectangle(radius=[self.radius,], size=self.size, pos=self.pos)
        self.bind(size=self._update_canvas, pos=self._update_canvas)

    def _update_canvas(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class SbpTileButton(Button):
    """
    Модернизированная плитка СБП.
    Вместо генерации QR-кода отображает крупный, ровный, идеально отцентрованный текст.
    """
    def __init__(self, **kwargs):
        super(SbpTileButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 0.07)
            self.rect = RoundedRectangle(radius=[24,], size=self.size, pos=self.pos)
            
        # Вертикальный контейнер с глубокими отступами для центрирования
        self.inner_layout = BoxLayout(orientation='vertical', padding=(16, 40, 16, 40), spacing=10)
        
        # Крупный кастомный текст "по СБП" с поддержкой BB-кодов разметки
        self.lbl = Label(
            text="[b][size=22sp]Оплата[/size][/b]\n[size=16sp][color=#3cd964]по СБП[/color][/size]",
            markup=True, 
            halign='center', 
            valign='middle', 
            size_hint=(1, 1),
            line_height=1.2
        )
        
        self.inner_layout.add_widget(self.lbl)
        self.add_widget(self.inner_layout)
        
        self.bind(size=self._layout_everything, pos=self._layout_everything)

    def _layout_everything(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
        self.inner_layout.pos = instance.pos
        self.inner_layout.size = instance.size
        
        # УЛУЧШЕНИЕ: Принудительное ограничение ширины текстовой зоны.
        # Гарантирует, что слова не будут ломаться или переноситься по одной букве.
        self.lbl.text_size = (instance.width - 32, None)


class SmileTileButton(Button):
    """
    Плитка оплаты "Улыбкой" с полностью исправленным выравниванием текста.
    Ошибки с некорректными флагами 'b' полностью ликвидированы.
    """
    def __init__(self, **kwargs):
        super(SmileTileButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.markup = True
        self.text = "[color=#010805][b]Оплата улыбкой[/b]\n[size=12sp]Биометрия СберID[/size][/color]"
        
        # УЛУЧШЕНИЕ: Установлено корректное полное имя свойства 'bottom' вместо ошибочного 'b'
        self.valign = 'bottom'
        self.halign = 'center'
        self.padding = (0, 25) # Отступ снизу, чтобы текст не слипался с рамкой плитки
        
        with self.canvas.before:
            self.bg_color = Color(0.23, 0.85, 0.39, 1)
            self.rect = RoundedRectangle(radius=[24,], size=self.size, pos=self.pos)
            
        self.bind(size=self._layout_everything, pos=self._layout_everything)

    def _layout_everything(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
        self.text_size = instance.size
        
        # Очищаем старую графическую группу перед перерисовкой линий биометрии
        self.canvas.remove_group('smile_graphics')
        cx, cy = instance.center_x, instance.y + instance.height * 0.62
        
        # Прорисовка технологичных меток сканера лица Сбера
        with self.canvas:
            Color(0.01, 0.08, 0.05, 0.7)
            Line(circle=(cx, cy, 32), width=2.5, group='smile_graphics')
            Line(points=[cx - 40, cy + 20, cx - 40, cy + 40, cx - 20, cy + 40], width=3, cap='round', group='smile_graphics')
            Line(points=[cx + 40, cy + 20, cx + 40, cy + 40, cx + 20, cy + 40], width=3, cap='round', group='smile_graphics')
            Line(points=[cx - 40, cy - 20, cx - 40, cy - 40, cx - 20, cy - 40], width=3, cap='round', group='smile_graphics')
            Line(points=[cx + 40, cy - 20, cx + 40, cy - 40, cx + 20, cy - 40], width=3, cap='round', group='smile_graphics')


class MonolithicSuccessBadge(Widget):
    """
    Монолитный графический элемент успешного чека (зеленое кольцо и галочка).
    Центрируется автоматически по высшей математической точности.
    """
    def __init__(self, **kwargs):
        super(MonolithicSuccessBadge, self).__init__(**kwargs)
        with self.canvas:
            Color(*COLOR_SUCCESS_NEON)
            self.circle = Line(circle=(0, 0, 65), width=3.5)
            self.checkmark = Line(points=[], width=7.5, cap='round', joint='round')
            
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, instance, value):
        cx, cy = self.center_x, self.center_y
        self.circle.circle = (cx, cy, 65)
        # Массив точек для отрисовки геометрически выверенной галочки успеха
        self.checkmark.points = [cx - 30, cy - 6, cx - 8, cy - 28, cx + 32, cy + 22]


# ==========================================
# АРХИТЕКТУРА И ФУНКЦИОНАЛ ЭКРАНОВ
# ==========================================

class IdleScreen(Screen):
    """Сцена 1: Главный стартовый экран ожидания транзакции"""
    def __init__(self, **kwargs):
        super(IdleScreen, self).__init__(**kwargs)
        box = BoxLayout(orientation='vertical', padding=[30, 60, 30, 40], spacing=20)
        
        logo = Label(text="[b]SberPOS[/b] | Бизнес", markup=True, font_size='16sp',
                     color=(0.4, 0.9, 0.5, 0.8), size_hint_y=None, height=30)
        box.add_widget(logo)
        
        msg_layout = BoxLayout(orientation='vertical', size_hint_y=1)
        main_msg = Label(text="платите\n[b]как вам[/b]\n[color=#3cd964][b]удобно[/b][/color]",
                         markup=True, font_size='44sp', halign='center', valign='middle',
                         line_height=1.1, color=(1, 1, 1, 1))
        main_msg.bind(size=main_msg.setter('text_size'))
        msg_layout.add_widget(main_msg)
        box.add_widget(msg_layout)
        
        wave_card = GlassCard(orientation='horizontal', padding=15, size_hint_y=None, height=70, radius=20)
        wave_card.add_widget(Label(text="Приложите карту, смартфон или выберите метод",
                                   font_size='13sp', color=(0.5, 0.7, 0.6, 0.7), halign='center'))
        box.add_widget(wave_card)
        self.add_widget(box)


class MethodsScreen(Screen):
    """Сцена 2: Экран выбора метода оплаты с выводом динамической цены"""
    def __init__(self, **kwargs):
        super(MethodsScreen, self).__init__(**kwargs)
        self.main_box = BoxLayout(orientation='vertical', padding=[25, 50, 25, 40], spacing=20)
        
        top_bar = FloatLayout(size_hint_y=None, height=30)
        top_bar.add_widget(Label(text="оплата", font_size='15sp', color=(0.4, 0.5, 0.4, 1), 
                                 pos_hint={'center_x': 0.5, 'center_y': 0.5}))
        self.main_box.add_widget(top_bar)
        
        self.price_lbl = Label(text="[b]0 ₽[/b]", markup=True, font_size='46sp', color=(1, 1, 1, 1), 
                               size_hint_y=None, height=70)
        self.main_box.add_widget(self.price_lbl)
        
        arrow_box = BoxLayout(orientation='vertical', size_hint_y=None, height=40)
        arrow_box.add_widget(Label(text="Сверху приложите карту или выберите метод ниже:", 
                                   font_size='13sp', color=COLOR_TEXT_MUTED, halign='center'))
        self.main_box.add_widget(arrow_box)
        
        self.main_box.add_widget(Widget(size_hint_y=1))
        
        self.tiles_layout = BoxLayout(orientation='horizontal', spacing=16, size_hint_y=None, height=190)
        
        self.sbp_btn = SbpTileButton()
        self.smile_btn = SmileTileButton()
        
        self.tiles_layout.add_widget(self.sbp_btn)
        self.tiles_layout.add_widget(self.smile_btn)
        self.main_box.add_widget(self.tiles_layout)
        
        self.add_widget(self.main_box)

    def update_amount(self, amount):
        """Красиво форматирует число цены, добавляя пробелы между тысячами"""
        formatted_price = f"{int(amount):,}".replace(",", " ")
        self.price_lbl.text = f"[b]{formatted_price} ₽[/b]"


class QrScreen(Screen):
    """Сцена 3: Окно эмуляции обработки QR СБП платежа"""
    def __init__(self, **kwargs):
        super(QrScreen, self).__init__(**kwargs)
        self.box = BoxLayout(orientation='vertical', padding=[25, 50, 25, 40], spacing=20)
        self.box.add_widget(Label(text="[b]Оплата по QR-коду СБП[/b]", markup=True, font_size='20sp', size_hint_y=None, height=30))
        
        self.info_plate = GlassCard(size_hint_y=None, height=45, radius=12)
        self.amount_lbl = Label(text="Сумма к списанию: 0 ₽", font_size='14sp', color=(0.9, 0.9, 0.9, 1))
        self.info_plate.add_widget(self.amount_lbl)
        self.box.add_widget(self.info_plate)
        
        qr_container = GlassCard(orientation='vertical', padding=20, radius=24, size_hint=(1, 1))
        self.qr_trigger = PremiumButton(
            text="[color=#000000][b][ ИМИТАЦИЯ QR-КОДА ][/b]\n\nНажми сюда для\nсимуляции сканирования[/color]",
            bg_color=(1, 1, 1, 0.95), radius=18, halign='center'
        )
        qr_container.add_widget(self.qr_trigger)
        self.box.add_widget(qr_container)
        
        self.web_btn = PremiumButton(text="[b]Открыть копию сбп в браузере[/b]", bg_color=(0.1, 0.1, 0.1, 0.9), radius=16, size_hint_y=None, height=50)
        self.box.add_widget(self.web_btn)
        
        self.box.add_widget(PremiumButton(text="Назад", bg_color=(0.15, 0.2, 0.17, 0.6), radius=12, size_hint_y=None, height=45, on_press=self.go_back))
        self.add_widget(self.box)

    def setup_qr_data(self, amount, success_callback):
        self.amount_lbl.text = f"Сумма к списанию: {int(amount)} ₽"
        self.qr_trigger.on_press = success_callback
        self.web_btn.on_press = lambda: webbrowser.open(QR_TARGET_URL)

    def go_back(self, instance):
        self.manager.current = 'methods'


class BiometricScreen(Screen):
    """Сцена 4: Экран интерактивного ИИ-сканирования лица"""
    def __init__(self, **kwargs):
        super(BiometricScreen, self).__init__(**kwargs)
        box = BoxLayout(orientation='vertical', padding=[25, 50, 25, 40], spacing=20)
        box.add_widget(Label(text="[b]Оплата улыбкой СберID[/b]", markup=True, font_size='20sp', size_hint_y=None, height=30))
        
        camera_frame = GlassCard(orientation='vertical', padding=10, radius=28, size_hint=(1, 1))
        camera_lbl = Label(text="[color=#3cd964]Сканирование лица...\nСмотрите в камеру терминала[/color]", markup=True, halign='center', font_size='16sp')
        camera_frame.add_widget(camera_lbl)
        box.add_widget(camera_frame)
        self.add_widget(box)


class SuccessScreen(Screen):
    """Сцена 5: Монолитное финальное окно успешной транзакции"""
    def __init__(self, **kwargs):
        super(SuccessScreen, self).__init__(**kwargs)
        
        with self.canvas.before:
            Color(*COLOR_SUCCESS_BG)
            self.rect = Rectangle(size=Window.size, pos=(0, 0))
        self.bind(size=self._update_bg)

        layout = BoxLayout(orientation='vertical', padding=[30, 60, 30, 60], spacing=30)
        layout.add_widget(Widget(size_hint_y=0.15))
        
        self.badge = MonolithicSuccessBadge(size_hint=(None, None), size=(140, 140), pos_hint={'center_x': 0.5})
        layout.add_widget(self.badge)
        
        status_lbl = Label(text="УСПЕШНО!", font_size='34sp', bold=True, color=COLOR_TEXT_WHITE, size_hint_y=None, height=45)
        layout.add_widget(status_lbl)
        
        self.details_lbl = Label(text="Списано 0 ₽\nТранзакция завершена успешно.", font_size='16sp', 
                                 halign='center', valign='top', line_height=1.4, color=(0.65, 0.7, 0.67, 1),
                                 size_hint_y=None, height=60)
        self.details_lbl.bind(size=self.details_lbl.setter('text_size'))
        layout.add_widget(self.details_lbl)
        
        layout.add_widget(Widget(size_hint_y=0.25))
        self.add_widget(layout)

    def _update_bg(self, instance, value):
        self.rect.size = instance.size

    def set_details(self, amount):
        formatted_sum = f"{int(amount):,}".replace(",", " ")
        self.details_lbl.text = f"Списано {formatted_sum} ₽\nТранзакция завершена успешно."


# ==========================================
# КОРНЕВОЙ МЕНЕДЖЕР И СЕТЕВОЙ ПОТОК JSON
# ==========================================

class TerminalLayout(FloatLayout):
    def __init__(self, **kwargs):
        super(TerminalLayout, self).__init__(**kwargs)
        self.current_amount = 0
        self.current_client_socket = None
        
        with self.canvas.before:
            Color(*COLOR_BG_DARK) 
            self.bg_rect = Rectangle(size=Window.size, pos=(0, 0))
            Color(0.02, 0.24, 0.15, 0.35)
            self.glow = Ellipse(pos=(-100, Window.height - 300), size=(600, 400))
        self.bind(size=self._update_background)

        # УЛУЧШЕНИЕ: Длительность анимации FadeTransitions выставлена на 0.45 секунд.
        # Это дает плавный, дорогой, "вязкий" эффект смены интерфейсов.
        self.sm = ScreenManager(transition=FadeTransition(duration=0.45))
        
        self.idle_screen = IdleScreen(name='idle')
        self.methods_screen = MethodsScreen(name='methods')
        self.qr_screen = QrScreen(name='qr')
        self.biometric_screen = BiometricScreen(name='biometry')
        self.success_screen = SuccessScreen(name='success')
        
        self.sm.add_widget(self.idle_screen)
        self.sm.add_widget(self.methods_screen)
        self.sm.add_widget(self.qr_screen)
        self.sm.add_widget(self.biometric_screen)
        self.sm.add_widget(self.success_screen)
        
        self.add_widget(self.sm)
        
        # Навешиваем события кликов на модернизированные интерактивные плитки
        self.methods_screen.sbp_btn.bind(on_press=lambda inst: self.go_to_qr_screen())
        self.methods_screen.smile_btn.bind(on_press=lambda inst: self.go_to_biometric_screen())
        
        threading.Thread(target=self.start_network_server, daemon=True).start()

    def _update_background(self, instance, value):
        self.bg_rect.size = instance.size
        self.glow.pos = (-100, instance.height - 300)

    def go_to_qr_screen(self):
        self.qr_screen.setup_qr_data(self.current_amount, self.trigger_payment_success)
        self.sm.current = 'qr'

    def go_to_biometric_screen(self):
        self.sm.current = 'biometry'
        Clock.schedule_once(lambda dt: self.trigger_payment_success(), 2.5)

    def trigger_payment_success(self):
        self.success_screen.set_details(self.current_amount)
        self.sm.current = 'success'
        
        if self.current_client_socket:
            try:
                self.current_client_socket.sendall("success".encode('utf-8'))
                self.current_client_socket.close()
                self.current_client_socket = None
            except Exception as e:
                print("[SOCKET ERROR]", e)
                
        # Возврат в дефолтный режим ожидания (Idle) через 4 секунды после показа чека успеха
        Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'idle'), 4.0)

    def start_network_server(self):
        """
        Сетевой движок TCP-сервера.
        УЛУЧШЕНИЕ: Добавлена общая отказоустойчивость цикла. Если сокет падает, 
        он автоматически переинициализируется, не краша всё приложение.
        """
        while True:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server_socket.bind((LISTEN_IP, LISTEN_PORT))
                server_socket.listen(5)
                print(f"[CORE SERVER] Движок запущен на порту {LISTEN_PORT}")
                
                while True:
                    client_sock, client_addr = server_socket.accept()
                    try:
                        data = client_sock.recv(4096).decode('utf-8')
                        if data:
                            packet = json.loads(data)
                            self.current_amount = packet.get("amount", 0)
                            self.current_client_socket = client_sock
                            
                            # Потокобезопасный апдейт интерфейса через Clock.schedule_once
                            Clock.schedule_once(lambda dt: self.methods_screen.update_amount(self.current_amount), 0)
                            Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'methods'), 0)
                    except Exception as err:
                        print("[CLIENT DATA ERROR]", err)
                        client_sock.close()
            except Exception as e:
                print("[SERVER ERROR - REBOOTING CORE]", e)
                Clock.tick() # Небольшая микропауза перед перезапуском


class TerminalApp(App):
    def build(self):
        self.title = "SberPOS Smart Terminal Simulator Pro"
        return TerminalLayout()

if __name__ == '__main__':
    TerminalApp().run()

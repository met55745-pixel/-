import json
import socket
import threading
import os
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.clock import Clock

# ==========================================
# НАСТРОЙКИ СЕТИ И ХРАНИЛИЩА
# ==========================================
TERMINAL_IP = "127.0.0.1"  # Сюда впишешь IP телефона, когда подключишь к Wi-Fi
TERMINAL_PORT = 5000
DATABASE_FILE = "menu_database.json"

class SleekButton(Button):
    """Кастомная стильная кнопка с чистым цветом без стандартных текстур Kivy"""
    def __init__(self, bg_color=(0.15, 0.15, 0.15, 1), text_color=(1, 1, 1, 1), **kwargs):
        super(SleekButton, self).__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = bg_color
        self.color = text_color
        self.font_name = 'Roboto'

class ProductButton(SleekButton):
    """Особая кнопка товара, поддерживающая обычный клик и зажатие (Long Press)"""
    def __init__(self, product_name, product_price, main_layout_ref, **kwargs):
        super(ProductButton, self).__init__(**kwargs)
        self.p_name = product_name
        self.p_price = product_price
        self.main_layout = main_layout_ref
        self.text = f"{product_name}\n\n[color=888888]{int(product_price)} ₽[/color]"
        self.markup = True
        self.halign = 'center'
        self.font_size = '16sp'
        self.bg_color = (0.12, 0.12, 0.12, 1)
        self.size_hint_y = None
        self.height = 140
        
        self.long_press_triggered = False
        self.touch_event = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.long_press_triggered = False
            # Запускаем таймер на 1 секунду удержания
            self.touch_event = Clock.schedule_once(self._trigger_long_press, 1.0)
            # Перехватываем нажатие, возвращая True, чтобы Kivy не дублировал клик
            return True
        return False

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            # Если отпустили раньше секунды, отменяем таймер зажатия
            if self.touch_event:
                Clock.unschedule(self.touch_event)
            
            # Если это был обычный быстрый клик (зажатие не сработало), добавляем в корзину строго 1 раз
            if not self.long_press_triggered:
                self.main_layout.add_to_cart(self.p_name, self.p_price)
                
            return True
        return False

    def _trigger_long_press(self, dt):
        self.long_press_triggered = True
        # Вызываем окно удаления в основном контейнере
        self.main_layout.open_delete_item_popup(self, self.p_name, self.p_price)

class MainLayout(BoxLayout):
    cart_items = ListProperty([])
    total_price = NumericProperty(0)
    status_msg = StringProperty("Касса готова к работе")

    def __init__(self, **kwargs):
        super(MainLayout, self).__init__(orientation='horizontal', **kwargs)
        self.padding = 15
        self.spacing = 15

        # Установка красивого темно-угольного фона для всего приложения
        with self.canvas.before:
            Color(0.07, 0.07, 0.07, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

        # -----------------------------------------------------------------
        # ЛЕВАЯ ПАНЕЛЬ: ЧЕК И ИТОГИ
        # -----------------------------------------------------------------
        self.left_panel = BoxLayout(orientation='vertical', size_hint=(0.38, 1), spacing=10)
        
        # Заголовок чека
        self.left_panel.add_widget(Label(
            text="ТЕКУЩИЙ ЧЕК", 
            font_size='20sp', 
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None, 
            height=40
        ))
        
        # Область просмотра чека с красивой границей
        self.receipt_container = BoxLayout(orientation='vertical', padding=10)
        with self.receipt_container.canvas.before:
            Color(0.12, 0.12, 0.12, 1)
            self.rc_bg = Rectangle()
            Color(0.2, 0.2, 0.2, 1)
            self.rc_border = Line(rectangle=(0, 0, 0, 0), width=1)
        self.receipt_container.bind(size=self._update_receipt_bg, pos=self._update_receipt_bg)

        # Скролл-контейнер для динамического списка строк товаров
        self.cart_scroll = ScrollView(size_hint=(1, 1))
        
        # Вертикальный контейнер внутри скролла, куда будут накладываться строки товаров
        self.receipt_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.receipt_list.bind(minimum_height=self.receipt_list.setter('height'))
        
        # Заглушка, если чек пустой
        self.empty_label = Label(
            text="Выбранные товары отобразятся здесь...",
            font_size='15sp',
            color=(0.6, 0.6, 0.6, 1),
            halign='center',
            valign='middle'
        )
        self.receipt_list.add_widget(self.empty_label)
        
        self.cart_scroll.add_widget(self.receipt_list)
        self.receipt_container.add_widget(self.cart_scroll)
        self.left_panel.add_widget(self.receipt_container)
        
        # Информационная строка статуса отправки
        self.status_label = Label(
            text=self.status_msg,
            font_size='13sp',
            color=(0.5, 0.5, 0.5, 1),
            size_hint_y=None,
            height=25
        )
        self.bind(status_msg=self.status_label.setter('text'))
        self.left_panel.add_widget(self.status_label)

        # -----------------------------------------------------------------
        # БЛОК ИТОГА
        # -----------------------------------------------------------------
        self.total_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=45)
        
        self.total_label = Label(
            text="ИТОГО: 0 ₽", 
            font_size='24sp', 
            bold=True,
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle'
        )
        self.total_label.bind(size=self.total_label.setter('text_size'))
        
        self.total_box.add_widget(self.total_label)
        self.left_panel.add_widget(self.total_box)
        
        # Премиальная белая кнопка оплаты
        self.pay_btn = SleekButton(
            text="ОПЛАТИТЬ ЧЕРЕЗ ТЕРМИНАЛ", 
            bg_color=(1, 1, 1, 1), 
            text_color=(0, 0, 0, 1),
            font_size='16sp', 
            bold=True,
            size_hint_y=None, 
            height=60
        )
        self.pay_btn.bind(on_press=self.send_to_terminal)
        self.left_panel.add_widget(self.pay_btn)
        
        self.add_widget(self.left_panel)

        # -----------------------------------------------------------------
        # ПРАВАЯ ПАНЕЛЬ: СЕТКА МАРКЕТА (GRID)
        # -----------------------------------------------------------------
        self.right_panel = BoxLayout(orientation='vertical', size_hint=(0.62, 1))
        
        self.grid = GridLayout(cols=3, spacing=12, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        
        # Самая первая плитка — кнопка ПЛЮС
        self.add_plus_tile()
        
        # Подгружаем сохраненную базу данных позиций
        self.load_menu_from_database()

        self.market_scroll = ScrollView(size_hint=(1, 1))
        self.market_scroll.add_widget(self.grid)
        self.right_panel.add_widget(self.market_scroll)
        
        self.add_widget(self.right_panel)

    # -----------------------------------------------------------------
    # СЛУЖЕБНЫЕ МЕТОДЫ ГРАФИКИ
    # -----------------------------------------------------------------
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_receipt_bg(self, instance, value):
        self.rc_bg.pos = instance.pos
        self.rc_bg.size = instance.size
        self.rc_border.rectangle = (instance.x, instance.y, instance.width, instance.height)

    # -----------------------------------------------------------------
    # ЛОГИКА БАЗЫ ДАННЫХ (JSON-ПАМЯТЬ)
    # -----------------------------------------------------------------
    def load_menu_from_database(self):
        """Загрузка позиций из JSON файла базы при старте системы"""
        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                    saved_items = json.load(f)
                    for item in saved_items:
                        self.create_product_button(item["name"], item["price"], save_to_db=False)
            except Exception as e:
                self.status_msg = "Ошибка чтения базы данных меню"

    def save_menu_to_database(self):
        """Сохранение всех текущих кнопок сетки в JSON файл"""
        menu_data = []
        for widget in self.grid.children:
            if isinstance(widget, ProductButton):
                menu_data.append({"name": widget.p_name, "price": widget.p_price})
        
        menu_data.reverse()
        
        try:
            with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
                json.dump(menu_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.status_msg = "Не удалось сохранить изменения в базу"

    # -----------------------------------------------------------------
    # ЛОГИКА СЕТКИ ТОВАРОВ
    # -----------------------------------------------------------------
    def add_plus_tile(self):
        """Создает стартовую карточку добавления позиции"""
        plus_btn = SleekButton(
            text="+", 
            font_size='48sp', 
            bg_color=(0.12, 0.12, 0.12, 1),
            size_hint_y=None,
            height=140
        )
        plus_btn.bind(on_press=self.open_add_item_popup)
        self.grid.add_widget(plus_btn)

    def open_add_item_popup(self, instance):
        """Всплывающее окно добавления товара"""
        content_box = BoxLayout(orientation='vertical', padding=15, spacing=12)
        
        content_box.add_widget(Label(text="Название товара:", font_size='16sp', halign='left', size_hint_y=None, height=25))
        name_input = TextInput(multiline=False, font_size='16sp', background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), size_hint_y=None, height=45)
        content_box.add_widget(name_input)
        
        content_box.add_widget(Label(text="Цена товара (₽):", font_size='16sp', halign='left', size_hint_y=None, height=25))
        price_input = TextInput(multiline=False, input_filter='float', font_size='16sp', background_color=(0.15, 0.15, 0.15, 1), foreground_color=(1, 1, 1, 1), size_hint_y=None, height=45)
        content_box.add_widget(price_input)
        
        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        cancel_btn = SleekButton(text="ОТМЕНА", bg_color=(0.25, 0.25, 0.25, 1))
        ok_btn = SleekButton(text="OK", bg_color=(1, 1, 1, 1), text_color=(0, 0, 0, 1))
        
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(ok_btn)
        content_box.add_widget(btn_box)

        popup = Popup(
            title="Добавить позицию в меню", 
            content=content_box, 
            size_hint=(0.8, 0.55),
            background_color=(0.08, 0.08, 0.08, 1)
        )
        
        cancel_btn.bind(on_press=popup.dismiss)
        
        def process_ok(btn_instance):
            name = name_input.text.strip()
            price = price_input.text.strip()
            if name and price:
                self.create_product_button(name, float(price), save_to_db=True)
                popup.dismiss()
        
        ok_btn.bind(on_press=process_ok)
        popup.open()

    def create_product_button(self, name, price, save_to_db=True):
        """Генерирует умную плитку товара в сетке с биндом зажатия"""
        prod_btn = ProductButton(product_name=name, product_price=price, main_layout_ref=self)
        self.grid.add_widget(prod_btn)
        
        if save_to_db:
            self.save_menu_to_database()

    def open_delete_item_popup(self, button_instance, name, price):
        """Кастомное диалоговое меню удаления ячейки по зажатию"""
        content_box = BoxLayout(orientation='vertical', padding=15, spacing=15)
        
        msg_label = Label(
            text=f"Удалить позицию\n\"{name}\" ({int(price)} ₽) из меню?",
            font_size='16sp',
            halign='center',
            valign='middle'
        )
        msg_label.bind(size=msg_label.setter('text_size'))
        content_box.add_widget(msg_label)
        
        btn_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        no_btn = SleekButton(text="ОТМЕНА", bg_color=(0.25, 0.25, 0.25, 1))
        yes_btn = SleekButton(text="УДАЛИТЬ", bg_color=(0.4, 0.15, 0.15, 1), text_color=(1, 0.4, 0.4, 1))
        
        btn_box.add_widget(no_btn)
        btn_box.add_widget(yes_btn)
        content_box.add_widget(btn_box)
        
        popup = Popup(
            title="Редактирование меню",
            content=content_box,
            size_hint=(0.7, 0.4),
            background_color=(0.08, 0.08, 0.08, 1)
        )
        
        no_btn.bind(on_press=popup.dismiss)
        
        def confirm_delete(inst):
            self.grid.remove_widget(button_instance)
            self.save_menu_to_database()
            self.status_msg = f"Позиция \"{name}\" навсегда удалена"
            popup.dismiss()
            
        yes_btn.bind(on_press=confirm_delete)
        popup.open()

    # -----------------------------------------------------------------
    # РАБОТА С КОРЗИНОЙ И УПРАВЛЕНИЕ КОЛИЧЕСТВОМ
    # -----------------------------------------------------------------
    def add_to_cart(self, name, price):
        """Добавление объекта в массив данных или увеличение счетчика"""
        for item in self.cart_items:
            if item["name"] == name and item["price"] == price:
                self.increment_item(item)
                return

        item_data = {
            "name": name, 
            "price": price, 
            "quantity": 1,
            "row_layout": None,
            "qty_label": None
        }
        
        self.cart_items.append(item_data)
        self.total_price += price
        
        if self.empty_label in self.receipt_list.children:
            self.receipt_list.remove_widget(self.empty_label)
            
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=6)
        item_data["row_layout"] = row
        
        item_lbl = Label(
            text=f"{name} — {int(price)} ₽",
            font_size='14sp',
            color=(1, 1, 1, 1),
            halign='left',
            valign='middle'
        )
        item_lbl.bind(size=item_lbl.setter('text_size'))
        row.add_widget(item_lbl)
        
        minus_btn = SleekButton(
            text="-",
            font_size='14sp',
            bold=True,
            bg_color=(0.18, 0.18, 0.18, 1),
            size_hint=(None, 1),
            width=30
        )
        minus_btn.bind(on_press=lambda inst: self.decrement_item(item_data))
        row.add_widget(minus_btn)
        
        qty_lbl = Label(
            text="1",
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, 1),
            width=30,
            halign='center',
            valign='middle'
        )
        item_data["qty_label"] = qty_lbl
        row.add_widget(qty_lbl)
        
        plus_btn = SleekButton(
            text="+",
            font_size='14sp',
            bold=True,
            bg_color=(0.18, 0.18, 0.18, 1),
            size_hint=(None, 1),
            width=30
        )
        plus_btn.bind(on_press=lambda inst: self.increment_item(item_data))
        row.add_widget(plus_btn)
        
        single_delete_btn = SleekButton(
            text="x",
            font_size='13sp',
            bg_color=(0.18, 0.14, 0.14, 1),
            text_color=(0.8, 0.4, 0.4, 1),
            size_hint=(None, 1),
            width=30
        )
        single_delete_btn.bind(on_press=lambda inst: self.remove_single_item(item_data))
        row.add_widget(single_delete_btn)
        
        self.receipt_list.add_widget(row)
        self.total_label.text = f"ИТОГО: {int(self.total_price)} ₽"

    def increment_item(self, item_data):
        """Увеличение количества товара на +1"""
        item_data["quantity"] += 1
        self.total_price += item_data["price"]
        
        item_data["qty_label"].text = str(item_data["quantity"])
        self.total_label.text = f"ИТОГО: {int(self.total_price)} ₽"

    def decrement_item(self, item_data):
        """Уменьшение количества товара на -1 (но не ниже 1)"""
        if item_data["quantity"] > 1:
            item_data["quantity"] -= 1
            self.total_price -= item_data["price"]
            
            item_data["qty_label"].text = str(item_data["quantity"])
            self.total_label.text = f"ИТОГО: {int(self.total_price)} ₽"

    def remove_single_item(self, item_data):
        """Удаление одной конкретной позиции по клику на её крестик"""
        total_item_cost = item_data["price"] * item_data["quantity"]
        
        if item_data in self.cart_items:
            self.cart_items.remove(item_data)
            self.total_price -= total_item_cost
            
        self.receipt_list.remove_widget(item_data["row_layout"])
        
        if not self.cart_items:
            self.receipt_list.add_widget(self.empty_label)
            
        self.total_label.text = f"ИТОГО: {int(self.total_price)} ₽"
        self.status_msg = f"Удалено: {item_data['name']}"

    def clear_cart_after_payment(self):
        """Служебный метод полной очистки после проведения транзакции"""
        self.cart_items = []
        self.total_price = 0
        self.receipt_list.clear_widgets()
        self.total_label.text = "ИТОГО: 0 ₽"

    # -----------------------------------------------------------------
    # СЕТЕВОЙ МОДУЛЬ ОТПРАВКИ НА ТЕРМИНАЛ ПО IP
    # -----------------------------------------------------------------
    def send_to_terminal(self, instance):
        """Инициация отправки платежа по IP"""
        if self.total_price == 0:
            return
            
        self.status_msg = "Установление связи с терминалом..."
        
        raw_items_list = [f"{i['name']} (x{i['quantity']}) — {int(i['price'] * i['quantity'])} ₽" for i in self.cart_items]
        
        payload = {
            "amount": self.total_price,
            "items": raw_items_list
        }
        
        threading.Thread(target=self._network_worker, args=(payload,)).start()

    def _network_worker(self, payload):
        """Фоновый рабочий сокетов"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((TERMINAL_IP, TERMINAL_PORT))
            
            data_string = json.dumps(payload)
            s.sendall(data_string.encode('utf-8'))
            
            response = s.recv(1024).decode('utf-8')
            s.close()
            
            if "success" in response:
                Clock.schedule_once(self._payment_success, 0)
            else:
                Clock.schedule_once(lambda dt: setattr(self, 'status_msg', "Ошибка: Терминал отклонил платеж"), 0)
                
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self, 'status_msg', f"Терминал недоступен (Проверь IP)"), 0)

    def _payment_success(self, dt):
        """Срабатывает при успешном ответе от телефона"""
        self.clear_cart_after_payment()
        
        success_lbl = Label(
            text="ОПЛАЧЕНО УСПЕШНО!\nЧек закрыт.",
            font_size='16sp',
            color=(0.3, 0.8, 0.3, 1),
            halign='center'
        )
        self.receipt_list.add_widget(success_lbl)
        self.status_msg = "Чек успешно закрыт на терминале"

class PosApp(App):
    def build(self):
        self.title = "Premium POS Terminal v1.0"
        return MainLayout()

if __name__ == '__main__':
    PosApp().run()
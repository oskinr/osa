import tkinter as tk
from PIL import Image, ImageTk
import os
import shutil
import json
import pefile
import urllib.request
import sys
import customtkinter as ctk
from tkinter import messagebox
import subprocess  # для запуска исполняемых файлов
import pathlib     # для работы с путями
import win32com.client  # для асинхронного удаления файла


# Класс для отображения анимированной GIF
class AnimatedGif(tk.Label):
    def __init__(self, master, path):
        tk.Label.__init__(self, master)
        self.frames = []
        self.delay = 100  # Время между кадрами (мс)
        self.current_frame = 0
        self.load_gif(path)
        self.after(0, self.update_image)

    def load_gif(self, path):
        try:
            img = Image.open(path)
            while True:
                self.frames.append(ImageTk.PhotoImage(img.convert("RGBA")))
                img.seek(len(self.frames))  # Переходим к следующему кадру
        except EOFError:
            pass  # Последний кадр достигнут

    def update_image(self):
        if self.frames:
            self.config(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(self.delay, self.update_image)

# Логика проверки и скачивания обновлений
def extract_product_version_from_exe(file_path):
    """
    Извлекает номер версии продукта из файла EXE.
    
    :param file_path: путь к файлу .exe
    :return: строка с версией формата Major.Minor.Build.Revision или None в случае ошибки
    """
    try:
        pe = pefile.PE(file_path)
        fixed_file_info = pe.VS_FIXEDFILEINFO[0]
        product_version_ms = fixed_file_info.ProductVersionMS
        product_version_ls = fixed_file_info.ProductVersionLS
        major = product_version_ms >> 16 & 0xffff
        minor = product_version_ms & 0xffff
        patch = product_version_ls >> 16 & 0xffff
        build = product_version_ls & 0xffff
        return f"{major}.{minor}.{patch}.{build}"
    except Exception as e:
        return None

def fetch_latest_release(owner, repo):
    """
    Получает информацию о последней выпущенной версии проекта на GitHub.
    
    :param owner: владелец репозитория
    :param repo: название репозитория
    :return: словарь с номером версии и ссылкой на скачивание или None в случае ошибки
    """
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                "version": data.get("tag_name", "").lstrip('v'),
                "download_url": next((asset['browser_download_url'] for asset in data['assets']), None)
            }
    except Exception as err:
        print(f"Ошибка загрузки: {err}")
        return None

def compare_versions(current_version, latest_version):
    """
    Сравнивает две строки версий формата MAJOR.MINOR.BUILD.REVISION.
    
    :param current_version: текущая версия
    :param latest_version: последняя доступная версия
    :return: True, если текущая версия меньше последней
    """
    if current_version is None or latest_version is None:
        return False
    parts_current = map(int, current_version.split('.'))
    parts_latest = map(int, latest_version.split('.'))
    return tuple(parts_current) < tuple(parts_latest)

def download_file(url, output_filename):
    """
    Скачивает файл по указанной ссылке.
    
    :param url: URL файла
    :param output_filename: имя выходного файла
    """
    urllib.request.urlretrieve(url, output_filename)

def schedule_delete(filename):
    """Планирует удаление файла после завершения его работы."""
    shell = win32com.client.Dispatch("WScript.Shell")
    cmd = f'del /F "{filename}"'
    shell.Run(cmd, 0, False)

def offer_update_if_available(exe_path, owner, repo, window):
    """
    Проверяет доступные обновления и предлагает обновить приложение.
    
    :param exe_path: путь к исполняемому файлу приложения
    :param owner: владелец репозитория
    :param repo: название репозитория
    :param window: ссылка на главное окно Tkinter
    """
    current_version = extract_product_version_from_exe(exe_path)
    latest_release = fetch_latest_release(owner, repo)

    if latest_release is None:
        window.update_status("Ошибка: не удалось получить информацию о последних обновлениях.")
        return

    if latest_release["version"] is None:
        window.update_status("Ошибка: не удалось получить последнюю версию. Повторите попытку позже.")
        return

    if current_version is None:
        window.update_status("Ошибка: не удалось определить текущую версию программы.")
        return

    if compare_versions(current_version, latest_release["version"]):
        window.update_status(f"Обнаружено обновление!\nТекущая версия: {current_version}, новая версия: {latest_release['version']}.")
        result = messagebox.askyesno(
            "Доступно обновление!",
            f"Текущая версия: {current_version}, новая версия: {latest_release['version']}."
            "\nУстановить обновление?"
        )
        if result:
            # Скачиваем новую версию
            temp_file = "new_osa.exe"
            download_url = latest_release["download_url"]
            download_file(download_url, temp_file)

            # Резервируем старую версию
            old_file = "old_osa.exe"
            shutil.move(exe_path, old_file)

            # Переименовываем новую версию в osa.exe
            shutil.move(temp_file, exe_path)

            # Запускаем обновленную версию
            subprocess.Popen([exe_path])

            # Планируем удаление старой версии позже
            schedule_delete(old_file)

            # Начинаем процедуру исчезновения окна
            window.fade_out()
        else:
            # Если пользователь отказался от обновления, запускаем старую версию
            subprocess.Popen([exe_path])
            window.update_status("Старое приложение запущено.")
            # Сразу начинаем исчезновение окна
            window.fade_out()
    else:
        # Если обновления нет, запускаем текущую версию
        subprocess.Popen([exe_path])
        window.update_status("Ваше приложение уже актуально.")
        # Сразу начинаем исчезновение окна
        window.fade_out()

# Главное окно с информацией и анимацией
class UpdateWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Launcher osa")
        self.master.geometry("400x300")

        # Центрирование окна на экране
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        x = (ws // 2) - (400 // 2)
        y = (hs // 2) - (800 // 2)
        self.master.geometry('+{}+{}'.format(x, y))

        # Проверка наличия иконки
        app_dir = pathlib.Path(__file__).resolve().parent
        icon_path = os.path.join(app_dir, 'osa.ico')
        if os.path.exists(icon_path):
            self.master.iconbitmap(icon_path)

        # Надпись, которая появляется по буквам
        self.text_label = tk.Label(master, text="", font=("Helvetica", 16))
        self.text_label.pack(pady=10)

        # Панель с GIF-анимацией
        self.gif_panel = AnimatedGif(master, "osa.gif")
        self.gif_panel.pack(expand=True, fill="both")

        # Информационная панель
        self.status_label = tk.Label(master, text="", justify="left", wraplength=380)
        self.status_label.pack(pady=10)

        # Постепенное появление текста
        self.animate_text("Ося")

    def animate_text(self, text):
        index = 0
        def type_letter():
            nonlocal index
            if index < len(text):
                self.text_label.config(text=self.text_label.cget("text") + text[index])
                index += 1
                self.master.after(500, type_letter)  # следующая буква через 0.5 секунды
        type_letter()

    def update_status(self, text):
        self.status_label.config(text=text)
        self.master.update_idletasks()

    def fade_out(self):
        alpha = float(self.master.attributes("-alpha"))  # Получаем текущую прозрачность
        if alpha > 0:
            alpha -= 0.05  # уменьшаем прозрачность на 5%
            self.master.attributes("-alpha", alpha)
            self.master.after(50, self.fade_out)  # повторяем через 50 мс
        else:
            self.master.destroy()  # закрываем окно, когда прозрачность достигает нуля

# Главный вход в программу
if __name__ == "__main__":
    owner = "oskinr"   # Имя владельца репозитория на GitHub
    repo = "osa"       # Название вашего репозитория
    exe_path = r"osa.exe"  # Исполняемый файл
    new_file = os.path.join(os.path.dirname(exe_path), "osa_new.exe")
    # Создаем главное окно
    root = tk.Tk()
    window = UpdateWindow(root)

    # Начинаем проверку обновлений
    offer_update_if_available(exe_path, owner, repo, window)

    # Окно остается открытым
    root.mainloop()
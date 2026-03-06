import tkinter as tk
from PIL import Image, ImageTk
import os
import shutil
import json
import urllib.request
from tkinter import messagebox
import subprocess  # для запуска исполняемых файлов
import pathlib     # для работы с путями
import win32com.client  # для асинхронного удаления файла
import datetime    # для формирования расписания удаления

# Оптимизированный класс для отображения анимации GIF
class AnimatedGif(tk.Label):
    def __init__(self, master, path):
        super().__init__(master)
        self.frames = []
        self.delay = 100  # Задержка между кадрами (мс)
        self.current_frame = 0
        self.load_gif(path)
        self.start_animation()

    def load_gif(self, path):
        img = Image.open(path)
        while True:
            frame = ImageTk.PhotoImage(img.copy())
            self.frames.append(frame)
            try:
                img.seek(len(self.frames))  # переходим к следующему кадру
            except EOFError:
                break

    def start_animation(self):
        if self.frames:
            self.configure(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(self.delay, self.start_animation)

# Функция для извлечения версии продукта из файла EXE с помощью PowerShell
def extract_product_version_from_exe(file_path):
    """
    Извлекает версию продукта из файла EXE с помощью PowerShell.
    """
    command = [
        "powershell",
        "-Command",
        "(Get-ItemProperty -Path '{}').VersionInfo.ProductVersion".format(file_path)
    ]
    try:
        result = subprocess.check_output(command, universal_newlines=True)
        return result.strip()  # убираем лишние пробелы и символы перевода строки
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении команды PowerShell: {e}")
        return None
    except Exception as e:
        print(f"Общая ошибка: {e}")
        return None

# Логика проверки и скачивания обновлений
def fetch_latest_release(owner, repo):
    """
    Получает информацию о последней выпущенной версии проекта на GitHub.
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

# Сравнение двух версий
def compare_versions(current_version, latest_version):
    """
    Сравнивает две строки версий формата MAJOR.MINOR.BUILD.REVISION.
    """
    if current_version is None or latest_version is None:
        return False
    parts_current = list(map(int, current_version.split('.')))
    parts_latest = list(map(int, latest_version.split('.')))
    return parts_current < parts_latest

# Загрузка файла по ссылке
def download_file(url, output_filename):
    """
    Скачивает файл по указанной ссылке.
    """
    urllib.request.urlretrieve(url, output_filename)

# Планирование удаления файла позже через задание планировщика Windows
def schedule_delete(filename):
    """
    Планирует удаление файла позже через задание планировщика Windows.
    """
    shell = win32com.client.Dispatch("WScript.Shell")
    task_name = "DeleteOldFile"
    now = datetime.datetime.now()
    delay_minutes = 1  # подождем минуту перед удалением
    scheduled_time = now + datetime.timedelta(minutes=delay_minutes)
    formatted_time = scheduled_time.strftime("%H:%M")

    # Команда для удаления файла
    del_command = f'del /F "{filename}"'

    # Создаем задание в планировщике
    cmd = (
        f"schtasks /create /tn \"{task_name}\" "
        f"/tr \"{del_command}\" "
        f"/sc ONCE /st {formatted_time}"
    )
    shell.Run(cmd, 0, False)

    messagebox.showinfo("Новый файл скачен!",f"Задание на удаление старого файла запланировано на {scheduled_time}.")

# Предложение обновления пользователю
def offer_update_if_available(exe_path, owner, repo, window):
    """
    Проверяет доступные обновления и предлагает обновить приложение.
    """
    # Проверяем, существует ли файл osa.exe
    if not os.path.exists(exe_path):
        window.update_status("Файл osa.exe не найден. Скачиваем последнюю версию...")
        latest_release = fetch_latest_release(owner, repo)
        if latest_release is None:
            window.update_status("Ошибка: не удалось получить информацию о последних обновлениях.")
            return
        download_url = latest_release["download_url"]
        download_file(download_url, exe_path)
        window.update_status("Новая версия скачана. Запускаем приложение.")
        subprocess.Popen([exe_path])
        window.fade_out()
        return

    # Если файл существует, продолжаем обычную проверку обновлений
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

# Основное окно с информацией и анимацией
class UpdateWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Launcher")
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
        self.animate_text("О с я")

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
        alpha = float(self.master.attributes("-alpha"))
        if alpha > 0:
            alpha -= 0.05
            self.master.attributes("-alpha", alpha)
            self.master.after(50, self.fade_out)
        else:
            self.master.destroy()

# Основной цикл программы
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

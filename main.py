import re
import os
import shutil
import json
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import pathlib
import pefile
import urllib.request
import sys

def extract_product_version_from_exe(file_path):
    """
    Извлекает номер версии продукта из файла EXE.
    
    :param file_path: путь к файлу .exe
    :return: строка с версией формата Major.Minor.Build.Revision
    """
    try:
        pe = pefile.PE(file_path)
        if hasattr(pe, 'VS_VERSIONINFO'):
            fixed_file_info = pe.VS_FIXEDFILEINFO[0]
            product_version_ms = fixed_file_info.ProductVersionMS
            product_version_ls = fixed_file_info.ProductVersionLS
        
            major = product_version_ms >> 16 & 0xffff
            minor = product_version_ms & 0xffff
            patch = product_version_ls >> 16 & 0xffff
            build = product_version_ls & 0xffff
        
            return f"{major}.{minor}.{patch}.{build}"
        else:
            return "Версия не найдена"
    except Exception as e:
        return f"Ошибка: {e}"

def fetch_latest_release(owner, repo):
    """
    Получает информацию о последней выпущенной версии проекта на GitHub.
    
    :param owner: владелец репозитория
    :param repo: название репозитория
    :return: словарь с номером версии и ссылкой на скачивание
    """
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        headers = {'User-Agent': 'Mozilla/5.0'}  # Необходимый User-Agent для обхода ограничений API GitHub
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                "version": data.get("tag_name").lstrip('v'),
                "download_url": next((asset['browser_download_url'] for asset in data['assets']), None)
            }
    except urllib.error.HTTPError as http_err:
        print(f"HTTP Error occurred: {http_err}")
        return {"version": None}
    except urllib.error.URLError as url_err:
        print(f"URL Error occurred: {url_err}")
        return {"version": None}
    except Exception as err:
        print(f"An error occurred: {err}")
        return {"version": None}

def compare_versions(current_version, latest_version):
    """
    Сравнивает две строки версий формата MAJOR.MINOR.BUILD.REVISION.
    
    :param current_version: текущая версия
    :param latest_version: последняя доступная версия
    :return: True, если текущая версия меньше последней
    """
    def parse_version(version_str):
        parts = list(map(int, version_str.split('.')))
        while len(parts) < 4:
            parts.append(0)
        return tuple(parts[:4])

    current_parts = parse_version(current_version)
    latest_parts = parse_version(latest_version)
    return current_parts < latest_parts

def download_file(url, output_filename):
    """
    Скачивает файл по указанной ссылке.
    
    :param url: URL файла
    :param output_filename: имя выходного файла
    """
    urllib.request.urlretrieve(url, output_filename)

def offer_update_if_available(exe_path, owner, repo):
    """
    Проверяет доступность новой версии приложения и запрашивает подтверждение на обновление.
    
    :param exe_path: путь к исполняемому файлу приложения
    :param owner: владелец репозитория
    :param repo: название репозитория
    """
    current_version = extract_product_version_from_exe(exe_path)
    latest_release = fetch_latest_release(owner, repo)

    if latest_release["version"] is None:
        messagebox.showinfo("Нет связи с сервером",
                           "Не удалось подключиться к сети для проверки обновлений. Ваше приложение продолжит работу.")
        return

    if compare_versions(current_version, latest_release["version"]):
        result = messagebox.askyesno(
            "Доступно обновление!",
            f"Текущая версия: {current_version}, Новая версия: {latest_release['version']}.\nХотите установить обновление?"
        )
        if result:
            # Сохраняем резервную копию
            old_file = os.path.join(os.path.dirname(exe_path), "osa_old.exe")
            if not os.path.exists(old_file):  # Только если старое сохранение отсутствует
                shutil.copy2(exe_path, old_file)
                
            # Скачиваем новую версию
            download_url = latest_release["download_url"]
            download_file(download_url, "osa_new.exe")
            
            # Предлагает пользователю перезапустить программу
            messagebox.showwarning("Необходимо завершение работы",
                                   "Для продолжения установки обновления закройте запущенный экземпляр программы и повторно запустите osa_old новый переименуется в osa.exe его и используем.")
            sys.exit()  # Завершаем текущую сессию
    else:
        messagebox.showinfo("Нет обновлений",
                           "Ваше приложение уже актуально.")

# Точка входа в программу
if __name__ == "__main__":
    owner = "oskinr"   # Имя владельца репозитория на GitHub
    repo = "osa"       # Название вашего репозитория
    exe_path = r"osa.exe"  # Исполняемый файл
    new_file = os.path.join(os.path.dirname(exe_path), "osa_new.exe")

    # Проверяем наличие нового файла после перезапуска
    if os.path.exists(new_file):
        # Перемещаем новую версию поверх старой
        shutil.move(new_file, exe_path)
        messagebox.showinfo("Обновлено",
                            "Приложение успешно обновлено!")
        sys.exit()  # Выходим после успешной замены
    else:
        offer_update_if_available(exe_path, owner, repo)








# Настроим внешний вид
ctk.set_appearance_mode("Light")  # Тема по умолчанию: светлая
ctk.set_default_color_theme("blue")  # Тема цвета по умолчанию: синяя

# Глобальные переменные
global_selected_folder = ""  # Текущая выбранная папка
settings_path = 'settings.json'  # Путь к файлу настроек

# Создание файла настроек, если его ещё нет
if not os.path.exists(settings_path):
    with open(settings_path, 'w', encoding='utf-8') as settings_file:
        json.dump({}, settings_file, ensure_ascii=False, indent=4)

# Загрузка текущих настроек
with open(settings_path, 'r', encoding='utf-8') as settings_file:
    settings = json.load(settings_file)

# Ограничение вывода длинных сообщений
def limit_message(message, max_lines=10):
    lines = message.split('\n')
    if len(lines) > max_lines:
        return '\n\n'.join(lines[:max_lines]) + "\n... (дальше много строк)"
    return message

# Основная функция выбора папки
def select_folder():
    global global_selected_folder
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        global_selected_folder = folder_selected
        update_label_with_all_files()
        trim_button.configure(state='normal')
        apply_button.configure(state='normal')
    else:
        main_label.configure(text="Ничего не выбрано")
        trim_button.configure(state='disabled')
        apply_button.configure(state='disabled')

# Обновляем список файлов в папке
def update_label_with_all_files():
    global global_selected_folder
    if not global_selected_folder:
        return
    
    filenames = sorted(os.listdir(global_selected_folder))
    display_text = "Все файлы в папке:\n"
    for i, filename in enumerate(filenames):
        leading_spaces = len(filename) - len(filename.lstrip())
        warning_symbol = f"🟨 x{leading_spaces}" if leading_spaces > 0 else ""
        display_text += f"{i+1}. {warning_symbol} {filename}\n"
    
    scrollable_text.delete('1.0', ctk.END)
    scrollable_text.insert(ctk.END, display_text)

# Функция обрезки названий файлов
def trim_filenames():
    global global_selected_folder
    if not global_selected_folder:
        messagebox.showwarning("Предупреждение", "Сначала выберите папку!")
        return
    
    filenames = os.listdir(global_selected_folder)
    MAX_LINES = 15
    total_files = len(filenames)
    displayed_files = '\n'.join(filenames[:MAX_LINES])
    
    if total_files > MAX_LINES:
        remaining_files = total_files - MAX_LINES
        displayed_files += f"\n... ({remaining_files} скрытых файлов)"
    
    confirmation_message = (
        f"Планируется удалить начальную часть у {total_files} файлов.\n\n"
        f"Перечень обрабатываемых файлов:\n{displayed_files}\n\n"
        "Продолжить обрезку?"
    )
    
    answer = messagebox.askyesno("Подтверждение", confirmation_message)
    if not answer:
        return
    
    trimmed_files = []
    errors = []
    
    for filename in filenames:
        space_pos = filename.find(' ')
        if space_pos != -1:
            new_filename = filename[space_pos + 1:]
            old_path = os.path.join(global_selected_folder, filename)
            new_path = os.path.join(global_selected_folder, new_filename)
            
            try:
                os.rename(old_path, new_path)
                trimmed_files.append(new_filename)
            except OSError as err:
                errors.append(str(err))
    
    summary = f"Успешно обрезано файлов: {len(trimmed_files)}\n\n"
    for new in trimmed_files:
        summary += f"{new}\n"
    
    if errors:
        summary += f"\nВозникли ошибки при обработке некоторых файлов:\n{' '.join(errors)}"
    
    summary = limit_message(summary, max_lines=10)
    messagebox.showinfo("Итог обработки", summary)
    update_label_with_all_files()
    final_label.configure(text="Операция выполнена успешно.", text_color="green")

# Распределение файлов по папкам
def categorize_and_process_files():
    global global_selected_folder
    if not global_selected_folder:
        messagebox.showwarning("Предупреждение", "Сначала выберите папку!")
        return
    
    edo_prefixes = ['01.01.18', '01.03.07']
    files = os.listdir(global_selected_folder)
    file_list = '\n'.join(files)
    
    planned_folders = set()
    
    for filename in files:
        full_path = os.path.join(global_selected_folder, filename)
        category = 'ДИТ'
        for prefix in edo_prefixes:
            if filename.startswith(prefix):
                category = 'ЭДО'
                break
        
        found = False
        for district, regex in settings.items():
            match_obj = re.search(regex, filename)
            if match_obj:
                org_name = match_obj.group(2).strip()
                planned_folders.add(os.path.join(category, org_name))
                found = True
                break
        
        if not found:
            print(f'Файл "{filename}" не соответствует ни одному шаблону.')
    
    unique_planned_folders = sorted(planned_folders)
    MAX_LINES = 18
    displayed_folders = '\n'.join(unique_planned_folders[:MAX_LINES])
    
    if len(unique_planned_folders) > MAX_LINES:
        remaining_folders = len(unique_planned_folders) - MAX_LINES
        displayed_folders += f"\n... ({remaining_folders} скрытых папок)"
    
    confirm_message = f"Планируется создать следующие папки:\n\n{displayed_folders}\n\nПродолжить?"
    confirmed = messagebox.askyesno("Подтверждение", confirm_message)
    
    if confirmed:
        for filename in files:
            full_path = os.path.join(global_selected_folder, filename)
            category = 'ДИТ'
            for prefix in edo_prefixes:
                if filename.startswith(prefix):
                    category = 'ЭДО'
                    break
            
            found = False
            for district, regex in settings.items():
                match_obj = re.search(regex, filename)
                if match_obj:
                    org_name = match_obj.group(2).strip()
                    new_folder = os.path.join(global_selected_folder, category, org_name)
                    os.makedirs(new_folder, exist_ok=True)
                    destination = os.path.join(new_folder, filename)
                    shutil.move(full_path, destination)
                    print(f'Файл "{filename}" перемещён в папку "{new_folder}".')
                    found = True
                    break
            
            if not found:
                print(f'Файл "{filename}" не соответствует ни одному шаблону.')
        
        summary = f"Список файлов в {global_selected_folder}:\n{file_list}"
        summary = limit_message(summary, max_lines=10)
        messagebox.showinfo("Список файлов", summary)
    else:
        messagebox.showinfo("Отмена", "Процесс прерван пользователем.")

# Редактирование существующего района
def edit_district():
    selected_district = combo.get()
    if selected_district:
        old_regex = settings.get(selected_district, '')
        new_regex = simpledialog.askstring("Редактирование", f"Введите новое регулярное выражение для района '{selected_district}':", initialvalue=old_regex)
        if new_regex is not None and new_regex.strip():
            settings[selected_district] = new_regex
            save_settings()
            messagebox.showinfo("Готово", f"Регулярное выражение для района '{selected_district}' обновлено.")
        elif new_regex == '' or new_regex is None:
            del settings[selected_district]
            save_settings()
            messagebox.showinfo("Удалено", f"Регулярное выражение для района '{selected_district}' удалено.")
    else:
        messagebox.showwarning("Внимание", "Сначала выберите регион.")

# Добавление нового района
def add_district():
    new_district = simpledialog.askstring("Новый район", "Введите название нового района:", parent=root)
    if new_district and new_district.strip():
        new_regex = simpledialog.askstring("Регулярное выражение", f"Введите регулярное выражение для района '{new_district}':", parent=root)
        if new_regex and new_regex.strip():
            settings[new_district] = new_regex
            update_combo()  # Обновляем выпадающий список
            save_settings()  # Сохраняем изменения
            messagebox.showinfo("Готово", f"Район '{new_district}' успешно добавлен.")
        else:
            messagebox.showwarning("Ошибка", "Регулярное выражение должно быть указано.")
    else:
        messagebox.showwarning("Ошибка", "Название района должно быть указано.")

# Обновление выпадающего списка районов
def update_combo():
    combo.configure(values=list(settings.keys()))
    available_values = combo._values
    if len(available_values) > 0:
        combo.set(available_values[0])
    else:
        combo.set("")

# Сохранение настроек в JSON
def save_settings():
    # Готовим копию настроек, где заменяем экранированные символы
    prepared_settings = {key: val.replace('\\\\', '\\') for key, val in settings.items()}
    
    # Далее обычная сериализация
    with open(settings_path, 'w', encoding='utf-8') as settings_file:
        json.dump(prepared_settings, settings_file, ensure_ascii=False, indent=4)

# Изменение темы интерфейса
def change_theme(event=None):
    mode = theme_switch.get()
    ctk.set_appearance_mode(mode)

# Основной интерфейс
root = ctk.CTk()
root.title("Работа с файлами v1.7.0")
root.geometry("800x500")

# Проверка наличия иконки
app_dir = pathlib.Path(__file__).resolve().parent
icon_path = os.path.join(app_dir, 'osa.ico')
try:
    root.iconbitmap(icon_path)
except Exception as e:
    pass

# Верхняя панель с элементами управления
frame_top = ctk.CTkFrame(root)
frame_top.pack(fill=ctk.X, expand=True)

# Надпись сверху окна
main_label = ctk.CTkLabel(root, text="Выберите папку для дальнейшей работы.", font=("Arial", 12))
main_label.pack(pady=10)

# Переключатель тем
theme_switch = ctk.CTkSwitch(frame_top, text="Темная тема", onvalue="Dark", offvalue="Light", command=change_theme)
theme_switch.pack(side=ctk.LEFT, padx=10, pady=10)

# Кнопка выбора папки
select_button = ctk.CTkButton(frame_top, text="Выбрать папку", command=select_folder)
select_button.pack(side=ctk.LEFT, padx=10, pady=10)

# Кнопка обрезки названий файлов
trim_button = ctk.CTkButton(frame_top, text="Обрезать первую часть до пробела", state='disabled', command=trim_filenames)
trim_button.pack(side=ctk.LEFT, padx=10, pady=10)

# Кнопка распределения файлов
apply_button = ctk.CTkButton(frame_top, text="Распределить файлы", state='disabled', command=categorize_and_process_files)
apply_button.pack(side=ctk.RIGHT, padx=10, pady=10)

# Полоса прокрутки и текстовая область для просмотра файлов
scrollable_frame = ctk.CTkFrame(root)
scrollable_frame.pack(fill=ctk.BOTH, expand=True)

scrollbar = ctk.CTkScrollbar(scrollable_frame)
scrollbar.pack(side=ctk.RIGHT, fill=ctk.Y)

scrollable_text = ctk.CTkTextbox(scrollable_frame, wrap=ctk.WORD, yscrollcommand=scrollbar.set)
scrollable_text.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True)
scrollbar.configure(command=scrollable_text.yview)

# Нижняя метка состояния
final_label = ctk.CTkLabel(root, text="", font=("Arial", 12), text_color="green")
final_label.pack(side=ctk.BOTTOM, padx=20, pady=(0, 10))

# Выпадающий список районов
label_districts = ctk.CTkLabel(root, text="Выбор района:")
label_districts.pack(pady=5)
combo = ctk.CTkComboBox(root, values=list(settings.keys()), state="readonly")
combo.pack(pady=5)
update_combo()

# Кнопка добавления нового района
add_button = ctk.CTkButton(root, text="Добавить район", command=add_district)
add_button.pack(side=ctk.LEFT, padx=(10, 5))

# Кнопка редактирования текущего района
edit_button = ctk.CTkButton(root, text="Редактировать район", command=edit_district)
edit_button.pack(side=ctk.RIGHT, padx=(10, 10))

# Запуск приложения
root.mainloop()



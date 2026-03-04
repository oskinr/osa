# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringStruct,
    StringTable,
    StringFileInfo,
    VarStruct,
    VarFileInfo,
    VSVersionInfo,
)

a = Analysis(
    ['main.py'],               # Основной Python-файл
    pathex=[],                 # Дополнительные пути поиска модулей
    binaries=[],               # Бинарные зависимости
    datas=[('osa.ico', '.')],  # Включаемые дополнительные файлы (иконка)
    hiddenimports=[],          # Скрытые импорты
    hookspath=[],              # Пути поиска хуков
    hooksconfig={},            # Конфигурация хуков
    runtime_hooks=[],          # Хуки среды исполнения
    excludes=[],               # Исключённые модули
    noarchive=False,           # Не архивировать байт-код
    optimize=0,                # Уровень оптимизации (0, 1 или 2)
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],                        # Аргументы командной строки
    name='main',               # Имя исполняемого файла
    debug=False,               # Отладка выключена
    bootloader_ignore_signals=False,  # Сигналы операционной системы обрабатываются
    strip=False,               # Не удалять символьные таблицы
    upx=True,                  # Упаковка UPX включена
    upx_exclude=[],            # Исключение из упаковки
    runtime_tmpdir=None,       # Временная директория для хранения временных файлов
    console=False,             # Приложение без консоли
    disable_windowed_traceback=False,  # Показывать трассировку ошибок в окне GUI
    argv_emulation=False,      # Нет эмуляции аргументов командной строки
    target_arch=None,          # Целевая архитектура не задана
    codesign_identity=None,    # Подпись кода отключена
    entitlements_file=None,    # Нет файла прав подписывания
    version=VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=(1, 0, 0, 0),  # Версия файла
            prodvers=(1, 5, 0, 0),  # Версия продукта
            flags=0x0,               # Флаги (нет флагов)
            OS=0x4                   # Тип ОС (Windows NT)
        ),
        kids=[
            StringFileInfo([
                StringTable(
                    u'040904E4', [
                        StringStruct(u'ProductName', u'Работа с файлами'),  # Название продукта
                        StringStruct(u'ProductVersion', u'1.5.0.0'),         # Версия продукта (текстовая)
                        StringStruct(u'CompanyName', u'ULIY'),              # Компания-разработчик
                        StringStruct(u'LegalCopyright', u'Copyright © ULIY 2023'),  # Авторские права
                        StringStruct(u'FileDescription', u'Для работы с системой ЭДО'),  # Описание файла
                        StringStruct(u'FileVersion', u'1.0.0.0'),             # Версия файла (текстовая)
                        StringStruct(u'InternalName', u'osa'),              # Внутреннее название
                        StringStruct(u'OriginalFilename', u'osa.exe'),      # Исходное имя файла
                    ]
                )
            ]),
            VarFileInfo([VarStruct(u'TRANSLATION', [0, 1200])]),  # Информация о локализации
        ],
    ),
    icon=['osa.ico'],  # Иконка приложения
)
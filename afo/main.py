# Точка входа приложения

import sys
import os
import signal
import argparse
import time
import socket

# Для работы как exe (PyInstaller) и как модуль
if __name__ == '__main__' or getattr(sys, 'frozen', False):
    # Добавить родительскую папку в path для импортов
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from afo.server import Orchestrator
else:
    from .server import Orchestrator


def is_already_running(port: int) -> bool:
    # Проверить запущен ли уже экземпляр на этом порту
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return False
    except OSError:
        return True


def main():
    parser = argparse.ArgumentParser(description='AFO - настройка окружения под задачу')
    parser.add_argument('--no-browser', action='store_true', help='Не открывать браузер')
    parser.add_argument('--port', type=int, default=8420, help='Порт сервера')
    
    args = parser.parse_args()
    
    # Проверка на единственный экземпляр
    if is_already_running(args.port):
        print(f"AFO уже запущен на порту {args.port}")
        # Открыть браузер с существующим экземпляром
        import webbrowser
        webbrowser.open(f'http://localhost:{args.port}')
        sys.exit(0)
    
    orchestrator = Orchestrator()
    orchestrator.server.port = args.port
    
    def shutdown(signum=None, frame=None):
        print("\nВыход...")
        orchestrator.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    print(f"""
    AFO v1.0
    --------
    Сервер: http://localhost:{args.port}
    Ctrl+C для выхода
    """)
    
    orchestrator.start()
    
    if not args.no_browser:
        orchestrator.server.open_browser()
    
    # Основной цикл
    try:
        while orchestrator.running:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == '__main__':
    main()

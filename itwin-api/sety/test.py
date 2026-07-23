import sys
import os


parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
sys.path.append(os.path.abspath(os.path.join(parent_dir, '..')))


from sety.teplo.rasto import test


test()



from pathlib import Path

class Navigator:
    def __init__(self):
        self.current = Path("C:/")        # текущая директория
        self.history_back = []            # назад
        self.history_forward = []         # вперёд
        self.upload_target = None         # для /upload_to

    def cd(self, new_path: Path):
        if not new_path.exists():
            return False

        # добавляем в историю
        self.history_back.append(self.current)
        self.current = new_path
        self.history_forward.clear()
        return True

    def back(self):
        if not self.history_back:
            return False
        self.history_forward.append(self.current)
        self.current = self.history_back.pop()
        return True

    def forward(self):
        if not self.history_forward:
            return False
        self.history_back.append(self.current)
        self.current = self.history_forward.pop()
        return True

# глобальный навигатор
nav = Navigator()

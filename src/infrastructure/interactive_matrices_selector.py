import os


class InteractiveSelector:
    def __init__(self):
        self._selected_indices: set[int] = set()

    def _clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def _render_list(self, items: list[str], selected_indices: set[int]) -> str:
        lines = ["Список доступных аппаратов:", "=" * 40]

        for i, item in enumerate(items, 1):
            checkbox = "[✓]" if i in selected_indices else "[ ]"
            lines.append(f"{i:2d}. {checkbox} {item}")

        lines.extend([
            "=" * 40,
            "Инструкция:",
            "  • Введите номер аппарата для выбора/отмены",
            "  • Введите несколько номеров через пробел",
            "  • Введите 'готово' для подтверждения",
            "  • Введите 'отмена' для выхода",
            "",
            "Текущий выбор: " + ", ".join(
                items[i - 1] for i in sorted(selected_indices)
            ) if selected_indices else "Текущий выбор: нет выбора",
            ""
        ])

        return "\n".join(lines)

    def select_items(self, items: list[str]) -> list[str]:
        self._selected_indices.clear()

        while True:
            self._clear_screen()
            print(self._render_list(items, self._selected_indices))

            try:
                user_input = input("Введите номер(а) или команду: ").strip().lower()

                if user_input == "готово":
                    if not self._selected_indices:
                        print("\nВы не выбрали ни одного аппарата!")
                        input("Нажмите Enter для продолжения...")
                        continue
                    break

                if user_input == "отмена":
                    return []

                # Обрабатываем ввод номеров
                if user_input:
                    # Разбиваем на отдельные числа
                    parts = user_input.split()
                    for part in parts:
                        try:
                            num = int(part)
                            if 1 <= num <= len(items):
                                # Переключаем состояние выбора
                                if num in self._selected_indices:
                                    self._selected_indices.remove(num)
                                else:
                                    self._selected_indices.add(num)
                            else:
                                print(f"\nНомер {num} вне диапазона (1-{len(items)})")
                                input("Нажмите Enter для продолжения...")
                        except ValueError:
                            print(f"\n'{part}' не является числом!")
                            input("Нажмите Enter для продолжения...")

            except (EOFError, KeyboardInterrupt):
                # Пользователь нажал Ctrl+C или Ctrl+D
                print("\n\nОперация отменена.")
                return []

        return [items[i - 1] for i in sorted(self._selected_indices)]


class ColorfulInteractiveSelector(InteractiveSelector):

    COLORS = {
        'reset': '\033[0m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'cyan': '\033[96m',
        'bold': '\033[1m',
    }

    def _render_list(self, items: list[str], selected_indices: set[int]) -> str:
        lines = [
            f"{self.COLORS['bold']}Список доступных аппаратов:{self.COLORS['reset']}",
            "=" * 50
        ]

        for i, item in enumerate(items, 1):
            if i in selected_indices:
                checkbox = f"{self.COLORS['green']}[✓]{self.COLORS['reset']}"
                name = f"{self.COLORS['bold']}{item}{self.COLORS['reset']}"
            else:
                checkbox = "[ ]"
                name = item

            lines.append(f"{i:3d}. {checkbox} {name}")

        lines.extend([
            "=" * 50,
            f"{self.COLORS['yellow']}Инструкция:{self.COLORS['reset']}",
            f"  {self.COLORS['cyan']}•{self.COLORS['reset']} Введите номер аппарата для выбора/отмены",
            f"  {self.COLORS['cyan']}•{self.COLORS['reset']} Введите несколько номеров через пробел",
            f"  {self.COLORS['cyan']}•{self.COLORS['reset']} Введите {self.COLORS['green']}'готово'{self.COLORS['reset']} для подтверждения",
            f"  {self.COLORS['cyan']}•{self.COLORS['reset']} Введите {self.COLORS['yellow']}'отмена'{self.COLORS['reset']} для выхода",
            ""
        ])

        if selected_indices:
            selected_names = [items[i - 1] for i in sorted(selected_indices)]
            lines.append(
                f"{self.COLORS['green']}Выбрано: {', '.join(selected_names)}"
                f" ({len(selected_indices)} шт.){self.COLORS['reset']}"
            )
        else:
            lines.append(f"{self.COLORS['yellow']}Выбрано: нет выбора{self.COLORS['reset']}")

        lines.append("")
        return "\n".join(lines)

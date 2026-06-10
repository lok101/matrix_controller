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

                if user_input:
                    parts = user_input.split()
                    for part in parts:
                        try:
                            num = int(part)
                            if 1 <= num <= len(items):
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
                print("\n\nОперация отменена.")
                return []

        return [items[i - 1] for i in sorted(self._selected_indices)]

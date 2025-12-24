import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import tkinter.font as tkFont
from tklinenums import TkLineNumbers
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class Instruction:
    """Структура инструкции"""
    opcode: str
    operand1: str
    operand2: str
    raw: str


class Emulator:
    """Основной класс эмулятора процессора"""
    
    # Коды операций (4 бита)
    OPCODES = {
        'mov': 0b0000,
        'add': 0b0001,
        'sub': 0b0010,
        'mul': 0b0011,
        'div': 0b0100,
        'jmp': 0b0101,
        'jz':  0b0110,
        'jnz': 0b0111,
        'js':  0b1000,
        'jns': 0b1001,
        'and': 0b1010,
        'or':  0b1011,
        'xor': 0b1100,
        'not': 0b1101,
        'cmp': 0b1110,
        'inc': 0b1111
    }
    
    # Режимы адресации (2 бита)
    ADDRESSING_MODES = {
        'reg': 0b00,      # Регистровая (eax)
        'imm': 0b01,      # Непосредственная (5)
        'ind': 0b10,      # Косвенно-регистровая ([eax])
        'dir': 0b11       # Прямая ([5])
    }
    
    REG_NAMES = ['eax', 'ebx', 'ecx', 'edx']
    REG_MAP = {name: i for i, name in enumerate(REG_NAMES)}
    
    def __init__(self):
        """Инициализация эмулятора"""
        self.reset()
        
    def reset(self):
        """Сброс состояния эмулятора"""
        self.registers = {'eax': 0, 'ebx': 0, 'ecx': 0, 'edx': 0}
        self.flags = {'z': 0, 's': 0}  
        self.pc = 0  
        self.ir = None  
        self.memory = {}  
        self.program = [] 
        self.executed_count = 0
        self.running = False
        self.error_msg = None
        
    def parse_program(self, code: str) -> bool:
        """Парсинг программы из ассемблерного кода"""
        self.reset()
        lines = [l.strip() for l in code.split('\n')]
        lines = [l for l in lines if l and not l.startswith(';')]
        
        self.program = []
        for i, line in enumerate(lines):
            try:
                parts = line.split()
                if not parts:
                    continue
                    
                opcode = parts[0].lower()
                if opcode not in self.OPCODES:
                    self.error_msg = f"Строка {i+1}: Неизвестная команда '{opcode}'"
                    return False
                    
                operand1 = parts[1] if len(parts) > 1 else ''
                operand2 = parts[2] if len(parts) > 2 else ''
                
                self.program.append(Instruction(opcode, operand1, operand2, line))
                
            except Exception as e:
                self.error_msg = f"Строка {i+1}: {str(e)}"
                return False
        
        self.running = True
        self.pc = 0
        return True
    
    def set_memory(self, addr: int, value: int):
        """Установить значение в памяти"""
        if 0 <= addr < 4096:
            self.memory[addr] = value
    
    def get_memory(self, addr: int) -> int:
        """Получить значение из памяти"""
        return self.memory.get(addr, 0)
    
    def get_value(self, operand: str) -> int:
        """Получить значение операнда"""
        operand = operand.strip()
        
        # Косвенно-регистровая адресация [eax]
        if operand.startswith('[') and operand.endswith(']'):
            addr_reg = operand[1:-1].strip()
            if addr_reg in self.REG_MAP:
                addr = self.registers[addr_reg]
                return self.get_memory(addr)
            else:
                # Прямая адресация [123]
                try:
                    addr = int(addr_reg)
                    return self.get_memory(addr)
                except:
                    return 0
        
        # Регистровая адресация
        if operand in self.REG_MAP:
            return self.registers[operand]
        
        # Непосредственная адресация (число)
        try:
            return int(operand)
        except:
            return 0
    
    def set_value(self, operand: str, value: int):
        """Установить значение операнда"""
        operand = operand.strip()
        
        # Косвенно-регистровая адресация [eax]
        if operand.startswith('[') and operand.endswith(']'):
            addr_reg = operand[1:-1].strip()
            if addr_reg in self.REG_MAP:
                addr = self.registers[addr_reg]
                self.set_memory(addr, value)
            else:
                # Прямая адресация [123]
                try:
                    addr = int(addr_reg)
                    self.set_memory(addr, value)
                except:
                    pass
        
        # Регистровая адресация
        if operand in self.REG_MAP:
            self.registers[operand] = value
    
    def update_flags(self, result: int):
        """Обновить флаги на основе результата"""
        self.flags['z'] = 1 if result == 0 else 0
        self.flags['s'] = 1 if result < 0 else 0
    
    def encode_instruction(self, inst: Instruction) -> str:
        """Кодирование инструкции в двоичный формат (40 бит)"""
        opcode = self.OPCODES[inst.opcode]
        binary = format(opcode, '04b')  # 4 бита
        
        # полное кодирование с адресациями
        binary += '|00.0000000000000000|00.0000000000000000'
        
        return binary
    
    def decode_operand(self, operand: str) -> Tuple[int, str]:
        """Декодировать тип адресации и значение"""
        operand = operand.strip()
        
        if operand.startswith('[') and operand.endswith(']'):
            inner = operand[1:-1].strip()
            if inner in self.REG_MAP:
                return self.ADDRESSING_MODES['ind'], inner
            else:
                return self.ADDRESSING_MODES['dir'], inner
        
        if operand in self.REG_MAP:
            return self.ADDRESSING_MODES['reg'], operand
        
        try:
            int(operand)
            return self.ADDRESSING_MODES['imm'], operand
        except:
            return self.ADDRESSING_MODES['imm'], '0'
    
    def execute_step(self) -> bool:
        """Выполнить один шаг программы"""
        if not self.running or self.pc >= len(self.program):
            self.running = False
            return False
        
        inst = self.program[self.pc]
        self.ir = inst
        
        try:
            opcode = inst.opcode
            op1 = inst.operand1
            op2 = inst.operand2
            
            if opcode == 'mov':
                val = self.get_value(op2)
                self.set_value(op1, val)
            
            elif opcode == 'add':
                res = self.get_value(op1) + self.get_value(op2)
                self.set_value(op1, res)
                self.update_flags(res)
            
            elif opcode == 'sub':
                res = self.get_value(op1) - self.get_value(op2)
                self.set_value(op1, res)
                self.update_flags(res)
            
            elif opcode == 'mul':
                res = self.get_value(op1) * self.get_value(op2)
                self.set_value(op1, res)
            
            elif opcode == 'div':
                divisor = self.get_value(op2)
                if divisor != 0:
                    res = int(self.get_value(op1) / divisor)
                    self.set_value(op1, res)
            
            elif opcode == 'and':
                res = self.get_value(op1) & self.get_value(op2)
                self.set_value(op1, res)
            
            elif opcode == 'or':
                res = self.get_value(op1) | self.get_value(op2)
                self.set_value(op1, res)
            
            elif opcode == 'xor':
                res = self.get_value(op1) ^ self.get_value(op2)
                self.set_value(op1, res)
            
            elif opcode == 'not':
                res = ~self.get_value(op1)
                self.set_value(op1, res)
            
            elif opcode == 'inc':
                res = self.get_value(op1) + 1
                self.set_value(op1, res)
            
            elif opcode == 'cmp':
                res = self.get_value(op1) - self.get_value(op2)
                self.update_flags(res)
            
            elif opcode == 'jmp':
                self.pc = self.get_value(op1) - 1
            
            elif opcode == 'jz':
                if self.flags['z'] == 1:
                    self.pc = self.get_value(op1) - 1
            
            elif opcode == 'jnz':
                if self.flags['z'] == 0:
                    self.pc = self.get_value(op1) - 1
            
            elif opcode == 'js':
                if self.flags['s'] == 1:
                    self.pc = self.get_value(op1) - 1
            
            elif opcode == 'jns':
                if self.flags['s'] == 0:
                    self.pc = self.get_value(op1) - 1
            
            self.pc += 1
            self.executed_count += 1
            return True
            
        except Exception as e:
            self.error_msg = f"Ошибка выполнения: {str(e)}"
            self.running = False
            return False
    
    def run_auto(self, max_steps: int = 10000) -> bool:
        """Автоматическое выполнение программы"""
        steps = 0
        while self.running and self.pc < len(self.program) and steps < max_steps:
            self.execute_step()
            steps += 1
        
        if steps >= max_steps:
            self.error_msg = "Превышен лимит команд"
            return False
        
        return True


class EmulatorGUI:
    """Графический интерфейс эмулятора"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Эмулятор Процессора - Гарвардская архитектура")
        self.root.geometry("1400x900")
        self.emulator = Emulator()
        
        self.setup_styles()
        self.create_widgets()
        self.update_display()
    
    def setup_styles(self):
        """Настройка стилей"""
        self.root.configure(bg='#f0f0f0')
        self.mono_font = tkFont.Font(family="Courier New", size=10)
        self.header_font = tkFont.Font(family="Arial", size=12, weight="bold")
        self.label_font = tkFont.Font(family="Arial", size=9)
    
    def create_widgets(self):
        """Создание элементов интерфейса"""
        
        # Главное меню
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Заголовок
        header = ttk.Label(main_frame, text="Эмулятор Процессора", 
                          font=("Arial", 14, "bold"))
        header.pack(pady=5)
        
        subtitle = ttk.Label(main_frame, text="Гарвардская архитектура | 2-адресные команды",
                            font=("Arial", 10))
        subtitle.pack()
        
        # Ввод программы
        input_frame = ttk.LabelFrame(main_frame, text="Ввод программы (Ассемблер)", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        editor_container = ttk.Frame(input_frame)
        editor_container.pack(fill=tk.BOTH, expand=True)

        self.program_input = scrolledtext.ScrolledText(editor_container, height=8, width=80,
                                                       font=self.mono_font, wrap=tk.NONE)
        self.line_numbers = TkLineNumbers(editor_container, self.program_input, justify="center", colors=("#2197db", "#ffffff"))
        
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        self.program_input.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.program_input.bind("<<Modified>>", lambda event: self.root.after_idle(self.line_numbers.redraw), add=True)
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="Загрузить", 
                  command=self.load_program).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text=" Шаг", 
                  command=self.run_step).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Запуск", 
                  command=self.run_auto).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Сброс", 
                  command=self.reset).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(button_frame, text="Задача 1: Сумма", 
                  command=self.load_task1).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Задача 2: Свертка", 
                  command=self.load_task2).pack(side=tk.LEFT, padx=2)
        
        # Основная сетка отображения
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Левая колонка - Регистры
        left_frame = ttk.LabelFrame(display_frame, text="Регистры и Флаги", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Регистры общего назначения
        ttk.Label(left_frame, text="Регистры ОП:", font=self.header_font).pack(anchor=tk.W)
        
        for reg in ['eax', 'ebx', 'ecx', 'edx']:
            frame = ttk.Frame(left_frame)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{reg.upper()}:", width=6, font=self.label_font).pack(side=tk.LEFT)
            self.reg_vars = getattr(self, 'reg_vars', {})
            var = tk.StringVar(value="0")
            self.reg_vars[reg] = var
            ttk.Label(frame, textvariable=var, font=self.mono_font, 
                     foreground="blue", width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Счетчик команд и регистр команд
        ttk.Label(left_frame, text="Управление:", font=self.header_font).pack(anchor=tk.W)
        
        frame = ttk.Frame(left_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="PC:", width=6, font=self.label_font).pack(side=tk.LEFT)
        self.pc_var = tk.StringVar(value="0")
        ttk.Label(frame, textvariable=self.pc_var, font=self.mono_font, 
                 foreground="blue", width=15).pack(side=tk.LEFT, padx=5)
        
        frame = ttk.Frame(left_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="IR:", width=6, font=self.label_font).pack(side=tk.LEFT)
        self.ir_var = tk.StringVar(value="-")
        ttk.Label(frame, textvariable=self.ir_var, font=self.mono_font, 
                 foreground="blue", width=40).pack(side=tk.LEFT, padx=5)
        
        frame = ttk.Frame(left_frame)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text="Bin:", width=6, font=self.label_font).pack(side=tk.LEFT)
        self.bin_var = tk.StringVar(value="-")
        ttk.Label(frame, textvariable=self.bin_var, font=self.mono_font, 
                 foreground="darkgreen", width=40).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Флаги
        ttk.Label(left_frame, text="Флаги:", font=self.header_font).pack(anchor=tk.W)
        
        flag_frame = ttk.Frame(left_frame)
        flag_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(flag_frame, text="Z (Zero):", font=self.label_font).pack(side=tk.LEFT, padx=5)
        self.flag_z_var = tk.StringVar(value="0")
        self.flag_z_label = ttk.Label(flag_frame, textvariable=self.flag_z_var, 
                                     font=self.mono_font, foreground="red", width=3)
        self.flag_z_label.pack(side=tk.LEFT)
        
        ttk.Label(flag_frame, text="S (Sign):", font=self.label_font).pack(side=tk.LEFT, padx=20)
        self.flag_s_var = tk.StringVar(value="0")
        self.flag_s_label = ttk.Label(flag_frame, textvariable=self.flag_s_var, 
                                     font=self.mono_font, foreground="red", width=3)
        self.flag_s_label.pack(side=tk.LEFT)
        
        # Средняя колонка - Память и статус
        middle_frame = ttk.Frame(display_frame)
        middle_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        ttk.Label(middle_frame, text="Память данных (ОЗУ)", 
                 font=self.header_font).pack(anchor=tk.W, pady=5)
        
        self.memory_text = scrolledtext.ScrolledText(middle_frame, height=15, width=30,
                                                     font=self.mono_font, wrap=tk.NONE)
        self.memory_text.pack(fill=tk.BOTH, expand=True)
        self.memory_text.config(state=tk.DISABLED)
        
        # Статус и результаты
        ttk.Separator(middle_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        status_frame = ttk.Frame(middle_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="Статус:", font=self.label_font).pack(anchor=tk.W)
        self.status_var = tk.StringVar(value="Готов")
        ttk.Label(status_frame, textvariable=self.status_var, 
                 font=self.mono_font, foreground="green").pack(anchor=tk.W, padx=10)
        
        ttk.Label(status_frame, text="Команд выполнено:", 
                 font=self.label_font).pack(anchor=tk.W, pady=(10,0))
        self.exec_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.exec_var, 
                 font=self.mono_font, foreground="blue").pack(anchor=tk.W, padx=10)
        
        ttk.Label(status_frame, text="Результат (EAX):", 
                 font=self.label_font).pack(anchor=tk.W, pady=(10,0))
        self.result_var = tk.StringVar(value="0")
        ttk.Label(status_frame, textvariable=self.result_var, 
                 font=self.mono_font, foreground="blue", width=15).pack(anchor=tk.W, padx=10)
        
        # Правая колонка - Консоль
        right_frame = ttk.LabelFrame(display_frame, text="Консоль выполнения", padding=5)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.console = scrolledtext.ScrolledText(right_frame, height=15, width=40,
                                                 font=self.mono_font, wrap=tk.WORD)
        self.console.pack(fill=tk.BOTH, expand=True)
        self.console.config(state=tk.DISABLED)
        
        # Конфигурирование тегов для цветного вывода
        self.console.tag_config('info', foreground='blue')
        self.console.tag_config('success', foreground='green')
        self.console.tag_config('error', foreground='red')
    
    def log_console(self, message: str, tag: str = 'info'):
        """Логирование в консоль"""
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, message + '\n', tag)
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
    
    def update_display(self):
        """Обновить отображение интерфейса"""
        # Обновить регистры
        for reg in ['eax', 'ebx', 'ecx', 'edx']:
            self.reg_vars[reg].set(str(self.emulator.registers[reg]))
        
        # Обновить ПК и ИР
        self.pc_var.set(str(self.emulator.pc))
        if self.emulator.ir:
            self.ir_var.set(self.emulator.ir.raw)
            self.bin_var.set(self.emulator.encode_instruction(self.emulator.ir))
        else:
            self.ir_var.set("-")
            self.bin_var.set("-")
        
        # Обновить флаги
        z_val = str(self.emulator.flags['z'])
        s_val = str(self.emulator.flags['s'])
        self.flag_z_var.set(z_val)
        self.flag_s_var.set(s_val)
        
        fg_z = "green" if self.emulator.flags['z'] == 1 else "red"
        fg_s = "green" if self.emulator.flags['s'] == 1 else "red"
        self.flag_z_label.config(foreground=fg_z)
        self.flag_s_label.config(foreground=fg_s)
        
        # Обновить память
        self.memory_text.config(state=tk.NORMAL)
        self.memory_text.delete(1.0, tk.END)
        self.memory_text.insert(tk.END, "Адр    Значение\n")
        self.memory_text.insert(tk.END, "-" * 20 + "\n")
        
        if self.emulator.memory:
            for addr in sorted(self.emulator.memory.keys())[:30]:
                val = self.emulator.memory[addr]
                self.memory_text.insert(tk.END, f"[{addr:3d}]  {val:6d}\n")
        
        self.memory_text.config(state=tk.DISABLED)
        
        # Статус
        if self.emulator.running:
            self.status_var.set("Выполнение")
        elif self.emulator.pc >= len(self.emulator.program) and len(self.emulator.program) > 0:
            self.status_var.set("Завершено")
        else:
            self.status_var.set("Остановлено")
        
        self.exec_var.set(str(self.emulator.executed_count))
        self.result_var.set(str(self.emulator.registers['eax']))
    
    def load_program(self):
        """Загрузить программу"""
        code = self.program_input.get(1.0, tk.END)
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)
        
        if self.emulator.parse_program(code):
            self.log_console(f" Программа загружена ({len(self.emulator.program)} команд)", 'success')
            self.update_display()
        else:
            self.log_console(f"Ошибка: {self.emulator.error_msg}", 'error')
    
    def run_step(self):
        """Выполнить один шаг"""
        if not self.emulator.running:
            self.log_console("Ошибка: программа не загружена", 'error')
            return
        
        if self.emulator.execute_step():
            inst_text = f"[{self.emulator.executed_count}] {self.emulator.ir.raw}"
            self.log_console(inst_text, 'info')
            self.update_display()
        else:
            if self.emulator.error_msg:
                self.log_console(f"{self.emulator.error_msg}", 'error')
            else:
                self.log_console(" Программа завершена", 'success')
            self.update_display()
    
    def run_auto(self):
        """Автоматическое выполнение"""
        if not self.emulator.running:
            self.log_console("Ошибка: программа не загружена", 'error')
            return
        
        if self.emulator.run_auto():
            self.log_console(f" Выполнено {self.emulator.executed_count} команд", 'success')
        else:
            self.log_console(f"{self.emulator.error_msg}", 'error')
        
        self.update_display()
    
    def reset(self):
        """Сброс эмулятора"""
        self.emulator.reset()
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)
        self.log_console("Эмулятор сброшен", 'success')
        self.update_display()
    
    def load_task1(self):
        """Загрузить задачу 1: Сумма элементов массива"""
        program = """mov [0] 6
mov [1] 100
mov [2] 2
mov [3] 3
mov [4] 4
mov [5] 5
mov [6] 6
mov ecx [0]
add eax [ecx]
sub ecx 1
jnz 8"""
        
        self.program_input.delete(1.0, tk.END)
        self.program_input.insert(tk.END, program)
        
        self.emulator.reset()
        self.emulator.parse_program(program)
        
        for i in range(1, 7):
            self.emulator.set_memory(i, 100 + i - 1)
        self.emulator.set_memory(0, 6)
        
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)
        self.log_console(" Задача 1 загружена: Сумма элементов массива", 'success')
        self.update_display()
    
    def load_task2(self):
        """Загрузить задачу 2: Свертка двух массивов"""
        program = """mov [0] 10
mov [1] 1
mov [2] 1
mov [3] 1
mov [4] 1
mov [5] 1
mov [6] 1
mov [7] 1
mov [8] 1
mov [9] 1
mov [10] 1
mov [11] 2
mov [12] 2
mov [13] 2
mov [14] 2
mov [15] 2
mov [16] 2
mov [17] 2
mov [18] 2
mov [19] 2
mov [20] 2
mov ecx [0]
mov ebx ecx
add ebx [0]
mov edx [ecx]
mul edx [ebx]
add eax edx
sub ecx 1
jnz 22"""
        
        self.program_input.delete(1.0, tk.END)
        self.program_input.insert(tk.END, program)
        
        self.emulator.reset()
        self.emulator.parse_program(program)
        
        for i in range(1, 11):
            self.emulator.set_memory(i, 1)
        for i in range(11, 21):
            self.emulator.set_memory(i, 2)
        self.emulator.set_memory(0, 10)
        
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)
        self.log_console(" Задача 2 загружена: Свертка двух массивов", 'success')
        self.update_display()


def main():
    """Главная функция"""
    root = tk.Tk()
    gui = EmulatorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()

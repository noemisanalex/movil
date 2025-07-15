import json
import os
from dotenv import load_dotenv

load_dotenv()

TASKS_FILE = os.getenv("TASKS_FILE", "/data/data/com.termux/files/home/agp/tareas.json")

def get_tasks():
    """Carga las tareas desde el archivo JSON."""
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tasks(tasks):
    """Guarda las tareas en el archivo JSON."""
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

def add_task(task_description):
    """Añade una nueva tarea a la lista."""
    if not task_description:
        return "No puedes agregar una tarea vacía."
    tasks = get_tasks()
    tasks.append({"description": task_description, "completed": False})
    save_tasks(tasks)
    return f"Tarea añadida: '{task_description}'"

def list_tasks():
    """Muestra la lista de tareas pendientes."""
    tasks = get_tasks()
    pending_tasks = [task for task in tasks if not task["completed"]]
    if not pending_tasks:
        return "No tienes tareas pendientes."
    
    response = "Tus tareas pendientes son:\n"
    for i, task in enumerate(pending_tasks, 1):
        response += f"{i}. {task['description']}\n"
    return response

def complete_task(task_number):
    """Marca una tarea como completada."""
    try:
        task_index = int(task_number) - 1
        tasks = get_tasks()
        pending_tasks = [task for task in tasks if not task["completed"]]
        
        if 0 <= task_index < len(pending_tasks):
            # Find the actual index in the main tasks list
            task_to_complete = pending_tasks[task_index]
            for task in tasks:
                if task["description"] == task_to_complete["description"] and not task["completed"]:
                    task["completed"] = True
                    break
            save_tasks(tasks)
            return f"Tarea '{task_to_complete['description']}' marcada como completada."
        else:
            return "Número de tarea inválido."
    except ValueError:
        return "Por favor, di un número de tarea válido."

def handle_command(command):
    """Maneja los comandos de voz para el plugin de tareas."""
    if "agrega a mi lista de tareas" in command:
        task = command.split("agrega a mi lista de tareas")[-1].strip()
        return add_task(task)
    elif "cuáles son mis tareas" in command or "lista de tareas" in command:
        return list_tasks()
    elif "completa la tarea número" in command:
        task_num = command.split("completa la tarea número")[-1].strip()
        return complete_task(task_num)
    return None


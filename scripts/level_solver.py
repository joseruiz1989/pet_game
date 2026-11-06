#!/usr/bin/env python3
"""
Pet Rescue Saga - Level Solver & Generator
Verificador algorítmico y generador de niveles con solución garantizada.

Uso:
  python scripts/level_solver.py --verify <ruta_archivo_json>
  python scripts/level_solver.py --generate --count 100 --out <ruta_archivo_json>
"""

import sys
import json
import argparse
import random
from collections import deque
import heapq
import time

ROWS = 8
COLS = 6
BLOCK_COLORS = {'R', 'B', 'G', 'Y', 'P'}
PET_SYMBOLS = {'D', 'C'}
OBSTACLE_SYMBOLS = {'M'}


def board_to_hash(board):
    return '|'.join(''.join(row) for row in board)


def simulate_physics(board):
    """
    Aplica gravedad vertical y colapso de columnas vacías hacia la izquierda.
    Modifica la matriz in-place.
    """
    # 1. Gravedad vertical
    for c in range(COLS):
        empty_r = ROWS - 1
        for r in range(ROWS - 1, -1, -1):
            if board[r][c] != '.':
                if empty_r != r:
                    board[empty_r][c] = board[r][c]
                    board[r][c] = '.'
                empty_r -= 1

    # 2. Colapso de columnas vacías hacia la izquierda
    c = 0
    while c < COLS - 1:
        is_empty = all(board[r][c] == '.' for r in range(ROWS))
        if is_empty:
            # Buscar la primera columna no vacía a la derecha
            found_right = False
            for nc in range(c + 1, COLS):
                if any(board[r][nc] != '.' for r in range(ROWS)):
                    found_right = True
                    for r in range(ROWS):
                        board[r][c] = board[r][nc]
                        board[r][nc] = '.'
                    c -= 1  # Volver a revisar la columna actual
                    break
            if not found_right:
                break
        c += 1


def check_rescues(board):
    """
    Verifica si hay mascotas en la fila inferior (ROWS - 1).
    Las rescata y re-aplica física recursivamente en caso de cascadas.
    """
    rescued = 0
    for c in range(COLS):
        bottom = board[ROWS - 1][c]
        if bottom in PET_SYMBOLS:
            board[ROWS - 1][c] = '.'
            rescued += 1

    if rescued > 0:
        simulate_physics(board)
        rescued += check_rescues(board)

    return rescued


def get_connected_group(board, start_r, start_c):
    """
    Obtiene el grupo conectado de bloques del mismo color (4 direcciones).
    """
    target = board[start_r][start_c]
    if target not in BLOCK_COLORS:
        return []

    group = []
    visited = set()
    queue = deque([(start_r, start_c)])
    visited.add((start_r, start_c))

    while queue:
        r, c = queue.popleft()
        group.append((r, c))

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS:
                if (nr, nc) not in visited and board[nr][nc] == target:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

    return group


def solve_level(layout, max_moves, target_pets, max_iterations=6000):
    """
    Resuelve el nivel usando búsqueda heurística (A* / Best-First).
    Garantiza que el nivel tiene solución puramente combinatoria (sin boosters).
    
    Retorna: (solvable: bool, min_moves: int, path: list, iterations: int)
    """
    start_board = [list(row) for row in layout]
    initial_rescued = check_rescues(start_board)

    if initial_rescued >= target_pets:
        return True, 0, [], 0

    # Estado en cola de prioridad: (priority, moves_made, total_rescued, board, path)
    # Heurística: estimación de distancia restante
    # Cuantas más mascotas rescatadas y mayor altura de las mascotas restantes, menor prioridad (mejor)
    def calc_h(board, rescued):
        rem_pets = max(0, target_pets - rescued)
        if rem_pets == 0:
            return 0
        # Sumar distancias de mascotas al fondo
        dist = 0
        for r in range(ROWS):
            for c in range(COLS):
                if board[r][c] in PET_SYMBOLS:
                    dist += (ROWS - 1 - r)
        return rem_pets * 4 + dist

    h0 = calc_h(start_board, initial_rescued)
    # Priority queue: (f_score, tie_breaker, moves_made, total_rescued, board, path)
    counter = 0
    pq = [(h0, counter, 0, initial_rescued, start_board, [])]
    
    visited = {board_to_hash(start_board): 0}
    iterations = 0

    best_solution = None

    while pq and iterations < max_iterations:
        iterations += 1
        f, _, moves_made, total_rescued, cur_board, path = heapq.heappop(pq)

        if total_rescued >= target_pets:
            return True, moves_made, path, iterations

        if moves_made >= max_moves:
            continue

        # Encontrar todos los grupos de tamaño >= 2
        processed = set()
        available_moves = []

        for r in range(ROWS):
            for c in range(COLS):
                if (r, c) not in processed and cur_board[r][c] in BLOCK_COLORS:
                    grp = get_connected_group(cur_board, r, c)
                    for gr, gc in grp:
                        processed.add((gr, gc))
                    if len(grp) >= 2:
                        available_moves.append((r, c, grp))

        # Ordenar movimientos favoreciendo grupos más grandes o debajo de mascotas
        def move_score(item):
            r, c, grp = item
            # Verificar si hay mascotas arriba de este grupo
            under_pet = any(
                any(cur_board[above_r][gc] in PET_SYMBOLS for above_r in range(gr))
                for gr, gc in grp
            )
            return (1 if under_pet else 0, len(grp))

        available_moves.sort(key=move_score, reverse=True)

        for mr, mc, grp in available_moves:
            next_board = [list(row) for row in cur_board]
            for gr, gc in grp:
                next_board[gr][gc] = '.'

            simulate_physics(next_board)
            new_rescues = check_rescues(next_board)
            new_total = total_rescued + new_rescues

            next_path = path + [(mr, mc)]
            next_moves = moves_made + 1

            if new_total >= target_pets:
                return True, next_moves, next_path, iterations

            b_hash = board_to_hash(next_board)
            if b_hash not in visited or visited[b_hash] > next_moves:
                visited[b_hash] = next_moves
                h = calc_h(next_board, new_total)
                counter += 1
                heapq.heappush(pq, (next_moves + h, counter, next_moves, new_total, next_board, next_path))

    return False, None, None, iterations


def verify_file(file_path):
    """
    Verifica todos los niveles en un archivo JSON e imprime un informe detallado.
    """
    print(f"\n========================================================")
    print(f" VERIFICANDO NIVELES EN: {file_path}")
    print(f"========================================================")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            levels = json.load(f)
    except Exception as e:
        print(f"Error al abrir archivo: {e}")
        return False

    total = len(levels)
    passed = 0
    failed = 0

    for idx, lvl in enumerate(levels, 1):
        lvl_id = lvl.get('id', idx)
        name = lvl.get('name', f"Nivel {lvl_id}")
        moves = lvl.get('moves', 15)
        target_pets = lvl.get('targetPets', 2)
        layout = lvl.get('layout', [])

        t0 = time.time()
        solvable, min_moves, path, iters = solve_level(layout, moves, target_pets)
        dt = (time.time() - t0) * 1000

        if solvable:
            passed += 1
            path_str = " -> ".join(f"({r},{c})" for r, c in path[:5])
            if len(path) > 5:
                path_str += f" ... (+{len(path)-5} pasos)"
            print(f"  [OK] Nivel {lvl_id:>3} | {name:<28} | Resuelto en {min_moves:>2}/{moves:>2} movs ({dt:>5.1f}ms) | {path_str}")
        else:
            failed += 1
            print(f"  [FAIL] Nivel {lvl_id:>3} | {name:<28} | ¡NO SE PUDO RESOLVER en {moves} movs! ({dt:>5.1f}ms)")

    print(f"--------------------------------------------------------")
    print(f" TOTAL: {total} | SUPERADOS (OK): {passed} | FALLIDOS: {failed}")
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f" Tasa de solvabilidad: {success_rate:.1f}%")
    print(f"========================================================\n")
    return failed == 0


def generate_single_level(level_id, difficulty_tier):
    """
    Genera un único nivel verificado algorítmicamente según su nivel de dificultad.
    - tier 1 (Niveles 1-20): 2 mascotas, 3-4 colores, alta coherencia, 18-20 movs
    - tier 2 (Niveles 21-50): 2-3 mascotas, 4-5 colores, 16-19 movs
    - tier 3 (Niveles 51-80): 3 mascotas, 5 colores, algunos metales, 16-20 movs
    - tier 4 (Niveles 81-100): 3-4 mascotas, 5 colores, metales estratégicos, 17-22 movs
    """
    all_colors = ['R', 'B', 'G', 'Y', 'P']

    if difficulty_tier == 1:
        color_pool = all_colors[:3 + (level_id % 2)]  # 3 o 4 colores
        num_pets = 2
        max_moves = random.randint(18, 22)
        cohesion = 0.65
        metal_chance = 0.0
    elif difficulty_tier == 2:
        color_pool = all_colors[:4] if level_id % 3 != 0 else all_colors[:5]
        num_pets = 2 if level_id < 35 else 3
        max_moves = random.randint(16, 20)
        cohesion = 0.58
        metal_chance = 0.03 if level_id > 30 else 0.0
    elif difficulty_tier == 3:
        color_pool = all_colors
        num_pets = 3
        max_moves = random.randint(16, 20)
        cohesion = 0.52
        metal_chance = 0.06
    else:  # tier 4
        color_pool = all_colors
        num_pets = 3 if level_id < 90 else 4
        max_moves = random.randint(18, 22)
        cohesion = 0.48
        metal_chance = 0.08

    # Intentar generar candidatos hasta que el solver encuentre una solución garantizada
    max_attempts = 120
    for attempt in range(max_attempts):
        layout = [['.' for _ in range(COLS)] for _ in range(ROWS)]

        # Llenar bloques de colores
        for r in range(1, ROWS):
            for c in range(COLS):
                # Ocasionalmente bloque de metal en pisos medios
                if metal_chance > 0 and 2 <= r <= 5 and random.random() < metal_chance:
                    layout[r][c] = 'M'
                    continue

                neighbor = None
                if c > 0 and random.random() < cohesion and layout[r][c - 1] in color_pool:
                    neighbor = layout[r][c - 1]
                elif r > 1 and random.random() < cohesion and layout[r - 1][c] in color_pool:
                    neighbor = layout[r - 1][c]

                layout[r][c] = neighbor if neighbor else random.choice(color_pool)

        # Ubicar las mascotas en la fila superior (r=0) distribuidas
        available_cols = list(range(COLS))
        random.shuffle(available_cols)
        pet_cols = available_cols[:num_pets]
        pet_types = ['D', 'C']
        for i, col in enumerate(pet_cols):
            layout[0][col] = pet_types[i % len(pet_types)]

        # Verificar si el solver lo resuelve
        solvable, min_moves, path, _ = solve_level(layout, max_moves, num_pets, max_iterations=3500)
        if solvable and min_moves >= (1 if level_id <= 3 else 3):
            # Asignar un margen razonable de movimientos para que el jugador disfrute el nivel
            allowed_moves = max(min_moves + 3, max_moves)
            return {
                "id": level_id,
                "name": get_level_title(level_id),
                "moves": allowed_moves,
                "targetPets": num_pets,
                "layout": layout
            }

    # Si se agotan intentos, generar una versión de alta coherencia garantizada
    fallback_pool = all_colors[:3]
    layout = [['.' for _ in range(COLS)] for _ in range(ROWS)]
    for r in range(1, ROWS):
        for c in range(COLS):
            layout[r][c] = fallback_pool[(r // 2 + c // 2) % len(fallback_pool)]
    layout[0][1] = 'D'
    layout[0][4] = 'C'
    return {
        "id": level_id,
        "name": get_level_title(level_id),
        "moves": 18,
        "targetPets": 2,
        "layout": layout
    }


def get_level_title(level_id):
    adjectives = [
        "Aventura Inicial", "Parque Soleado", "Puente de Madera", "Valle Esmeralda",
        "Jardín Florido", "Sendero Feliz", "Colinas Azules", "Bosque Dulce",
        "Cascada Cristalina", "Refugio Cálido", "Camino Dorado", "Desafío de Colores",
        "Laberinto Felino", "Misión Canina", "Ruta Secreta", "Torre de Bloques",
        "Cueva Sorpresa", "Isla Flotante", "Campamento Amigo", "Rescate Heroico"
    ]
    idx = (level_id - 1) % len(adjectives)
    return f"Nivel {level_id} - {adjectives[idx]}"


def generate_batch(count, out_file):
    """
    Genera un conjunto de 'count' niveles verificados y los guarda en 'out_file'.
    """
    print(f"\n========================================================")
    print(f" GENERANDO {count} NIVELES CON SOLUCIÓN VERIFICADA")
    print(f" Destino: {out_file}")
    print(f"========================================================")

    levels = []
    t_start = time.time()

    for lvl_id in range(1, count + 1):
        if lvl_id <= 20:
            tier = 1
        elif lvl_id <= 50:
            tier = 2
        elif lvl_id <= 80:
            tier = 3
        else:
            tier = 4

        lvl_data = generate_single_level(lvl_id, tier)
        levels.append(lvl_data)

        if lvl_id % 10 == 0 or lvl_id == count:
            print(f"  -> Generados {lvl_id:>3}/{count} niveles verificados... ({(time.time()-t_start):.1f}s)")

    # Escribir archivo JSON
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(levels, f, indent=2, ensure_ascii=False)

    print(f"\n¡Éxito! Archivo guardado correctamente con {len(levels)} niveles.")
    print(f"Ahora verificando integridad del lote completo...\n")
    verify_file(out_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Pet Rescue Level Solver & Generator")
    parser.add_argument('--verify', type=str, help="Ruta del archivo JSON a verificar")
    parser.add_argument('--generate', action='store_true', help="Generar nuevos niveles")
    parser.add_argument('--count', type=int, default=100, help="Cantidad de niveles a generar")
    parser.add_argument('--out', type=str, default="data/levels/000001-001000/levels_000001-000100.json",
                        help="Ruta de salida para niveles generados")

    args = parser.parse_args()

    if args.verify:
        verify_file(args.verify)
    elif args.generate:
        generate_batch(args.count, args.out)
    else:
        # Por defecto, verificar el archivo actual
        default_file = "data/levels/000001-001000/levels_000001-000100.json"
        verify_file(default_file)


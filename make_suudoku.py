import random

def is_valid(board, row, col, num):
    for i in range(9):
        if board[row][i] == num or board[i][col] == num:
            return False
    start_row, start_col = 3 * (row // 3), 3 * (col // 3)
    for i in range(3):
        for j in range(3):
            if board[start_row + i][start_col + j] == num:
                return False
    return True

def solve(board):
    empty = find_empty(board)
    if not empty:
        return True
    row, col = empty
    nums = list(range(1, 10))
    random.shuffle(nums)  # 数字の順番をランダムにする
    for num in nums:
        if is_valid(board, row, col, num):
            board[row][col] = num
            if solve(board):
                return True
            board[row][col] = 0
    return False

def find_empty(board):
    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                return (i, j)
    return None

def generate_full_sudoku():
    board = [[0 for _ in range(9)] for _ in range(9)]
    fill_diagonal_boxes(board)  # 対角線上のボックスにランダムな数字を配置
    solve(board)
    return board

def fill_diagonal_boxes(board):
    for i in range(0, 9, 3):
        fill_box(board, i, i)

def fill_box(board, row_start, col_start):
    nums = list(range(1, 10))
    random.shuffle(nums)
    for i in range(3):
        for j in range(3):
            board[row_start + i][col_start + j] = nums.pop()

def remove_numbers_from_board(board, attempts=5):
    while attempts > 0:
        row, col = random.randint(0, 8), random.randint(0, 8)
        while board[row][col] == 0:
            row, col = random.randint(0, 8), random.randint(0, 8)
        backup = board[row][col]
        board[row][col] = 0
        board_copy = [row[:] for row in board]
        if not has_unique_solution(board_copy):
            board[row][col] = backup
            attempts -= 1
    return board

def has_unique_solution(board):
    solutions = []

    def solve_unique(board):
        if len(solutions) > 1:
            return
        empty = find_empty(board)
        if not empty:
            solutions.append([row[:] for row in board])
            return
        row, col = empty
        nums = list(range(1, 10))
        random.shuffle(nums)
        for num in nums:
            if is_valid(board, row, col, num):
                board[row][col] = num
                solve_unique(board)
                board[row][col] = 0

    solve_unique([row[:] for row in board])
    return len(solutions) == 1

if __name__ == "__main__":
    board = generate_full_sudoku()
    board = remove_numbers_from_board(board)
    if has_unique_solution(board):
        print("Generated Sudoku with a unique solution:")
        for row in board:
            print(row)
    else:
        print("Failed to generate a unique solution Sudoku. Try again.")

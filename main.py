import googleapiclient.errors
import time
import pygame
import random
import re
import os
from dotenv import load_dotenv
from make_suudoku import generate_full_sudoku, remove_numbers_from_board, has_unique_solution
from googleapiclient.discovery import build

# .envファイルの読み込み
load_dotenv()

# 環境変数の取得
API_KEY = os.getenv("API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# YouTube APIクライアントの設定
youtube = build("youtube", "v3", developerKey=API_KEY)


def get_live_video_id(channel_id):
    response = youtube.search().list(part="id", channelId=channel_id, type="video", eventType="live").execute()
    if "items" in response and len(response["items"]) > 0:
        live_video_id = response["items"][0]["id"]["videoId"]
        return live_video_id
    return None


def get_live_chat_id(video_id):
    response = youtube.videos().list(part="liveStreamingDetails", id=video_id).execute()
    live_chat_id = response["items"][0]["liveStreamingDetails"]["activeLiveChatId"]
    return live_chat_id


processed_message_ids = []


def get_live_chat_messages(live_chat_id):
    response = (
        youtube.liveChatMessages().list(liveChatId=live_chat_id, part="snippet,authorDetails", maxResults=200).execute()
    )
    messages = response.get("items", [])

    # 未処理のコメントのみをフィルタリング
    new_messages = [msg for msg in messages if msg["id"] not in processed_message_ids]
    return new_messages


# 定数の設定
WIDTH, HEIGHT = 700, 800  # 幅と高さを少し大きくする
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
FONT_SIZE = 36
LABEL_FONT_SIZE = 24
ERROR_FONT_SIZE = 18  # 誤答の文字サイズ
MARGIN = 50  # 余白を設定
ANIMATION_DURATION = 3  # アニメーションの長さ（秒）


debug = 0

# Pygameの初期化
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Sudoku Solver")
font = pygame.font.Font(None, FONT_SIZE)
label_font = pygame.font.Font(None, LABEL_FONT_SIZE)
error_font = pygame.font.Font(None, ERROR_FONT_SIZE)

# 数独ボードの生成
full_board = generate_full_sudoku()
board = full_board
if not debug:
    board = remove_numbers_from_board([row[:] for row in full_board])
if debug:
    board = [row[:] for row in full_board]
    board[0][0] = 0


# 入力の記録
user_inputs = {}
input_buffer = ""  # 入力バッファ


def draw_board(board):
    screen.fill(WHITE)
    cell_size = (WIDTH - 2 * MARGIN) // 9  # セルのサイズを計算
    board_height = MARGIN + 9 * cell_size  # ボードの高さを計算
    board_width = MARGIN + 9 * cell_size  # ボードの幅を計算

    for i in range(10):
        thickness = 1 if i % 3 != 0 else 3
        x_start = MARGIN + i * cell_size
        y_start = MARGIN + i * cell_size

        pygame.draw.line(screen, BLACK, (x_start, MARGIN), (x_start, board_height), thickness)
        pygame.draw.line(screen, BLACK, (MARGIN, y_start), (board_width, y_start), thickness)

    # 外枠の描画
    pygame.draw.line(screen, BLACK, (MARGIN, MARGIN), (board_width, MARGIN), 3)
    pygame.draw.line(screen, BLACK, (MARGIN, MARGIN), (MARGIN, board_height), 3)
    pygame.draw.line(screen, BLACK, (board_width, MARGIN), (board_width, board_height), 3)
    pygame.draw.line(screen, BLACK, (MARGIN, board_height), (board_width, board_height), 3)

    for i in range(9):
        for j in range(9):
            if board[i][j] != 0:
                text_color = BLUE if (i, j) not in user_inputs else BLACK
                text = font.render(str(board[i][j]), True, text_color)
                text_rect = text.get_rect(
                    center=(MARGIN + j * cell_size + cell_size // 2, MARGIN + i * cell_size + cell_size // 2)
                )
                screen.blit(text, text_rect)

    draw_user_inputs(cell_size)  # ユーザー入力の描画
    draw_labels(cell_size)  # 行と列のラベルの描画
    pygame.display.flip()


def draw_labels(cell_size):
    cols = "ABCDEFGHI"
    rows = "abcdefghi"
    for i in range(9):
        col_label = label_font.render(cols[i], True, BLACK)
        row_label = label_font.render(rows[i], True, BLACK)
        col_label_rect = col_label.get_rect(center=(MARGIN + i * cell_size + cell_size // 2, MARGIN - 20))
        row_label_rect = row_label.get_rect(center=(MARGIN - 20, MARGIN + i * cell_size + cell_size // 2))
        screen.blit(col_label, col_label_rect)
        screen.blit(row_label, row_label_rect)


def parse_comment(comment):
    # 入力をすべて大文字に変換し、小文字を無視するようにする
    match = re.match(r"([A-Ia-i])([a-i])([1-9])", comment)
    if not match:
        return None
    col, row, num = match.groups()
    print(col, row, num)
    col = col.upper()  # 列の文字を大文字に変換
    row = row.lower()  # 行の文字を小文字に変換
    col = ord(col) - ord("A")
    row = ord(row) - ord("a")
    num = int(num)
    return row, col, num


def check_completion(board):
    for row in board:
        if 0 in row:
            return False
    return True


def show_completion_animation():
    clear_font = pygame.font.Font(None, 72)  # クリア文字用フォントサイズ
    character_image = pygame.image.load("goaled_character.png")
    character_image = pygame.transform.scale(character_image, (160, 160))
    character_rect = character_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    for angle in range(0, 1801, 5):
        draw_board(board)
        display_comments()  # コメントの表示を追加
        rotated_image = pygame.transform.rotate(character_image, angle)
        rotated_rect = rotated_image.get_rect(center=character_rect.center)

        screen.blit(rotated_image, rotated_rect.topleft)

        text = clear_font.render("CLEAR!!!", True, RED)
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 4))
        screen.blit(text, text_rect)

        pygame.display.flip()
        pygame.time.wait(30)
    pygame.time.wait(500)


displayed_comments = []


def display_comments():
    cell_size = (WIDTH - 2 * MARGIN) // 9  # セルのサイズを計算
    start_y = MARGIN + 9 * cell_size + 10  # ボードの下に表示
    for i, comment in enumerate(displayed_comments[-5:]):  # 最新の5つのコメントを表示
        text = font.render(comment, True, BLACK)
        text_rect = text.get_rect(topleft=(MARGIN, start_y + i * 30))
        screen.blit(text, text_rect)
    pygame.display.flip()


def handle_input(board, full_board, comment):
    parsed = parse_comment(comment)
    if not parsed:
        return "Invalid input format. Use format 'Ab8'."
    row, col, num = parsed
    cell_position = f"{chr(col + ord('A'))}{chr(row + ord('a'))}{num}"
    if board[row][col] != 0:
        displayed_comments.append(f"- : {cell_position} -> {comment}")
        animate_cell_already_filled(row, col)
        return f"Cell {comment[:2]} is already solved."
    if full_board[row][col] == num:
        displayed_comments.append(f"o : {cell_position} -> {comment}")
        animate_correct_input(row, col, num)
        board[row][col] = num
        if (row, col) in user_inputs:
            del user_inputs[(row, col)]  # 正解したので誤答の出力を削除
        if check_completion(board):
            show_completion_animation()
        return f"Placed {num} at {comment[:2]}."
    else:
        displayed_comments.append(f"x : {cell_position} -> {comment}")
        animate_incorrect_input(row, col, num)  # 入力された不正解の値を渡す
        if (row, col) in user_inputs:
            if num not in user_inputs[(row, col)]:
                user_inputs[(row, col)].append(num)
        else:
            user_inputs[(row, col)] = [num]
        return f"{num} is not a valid number for cell {comment[:2]}."


def draw_user_inputs(cell_size):
    error_positions = {
        1: (0.2, 0.2),
        2: (0.5, 0.2),
        3: (0.8, 0.2),
        4: (0.2, 0.5),
        5: (0.5, 0.5),
        6: (0.8, 0.5),
        7: (0.2, 0.8),
        8: (0.5, 0.8),
        9: (0.8, 0.8),
    }
    for (row, col), nums in user_inputs.items():
        for num in nums:
            if num in error_positions:
                x_offset, y_offset = error_positions[num]
                x = MARGIN + col * cell_size + int(cell_size * x_offset)
                y = MARGIN + row * cell_size + int(cell_size * y_offset)
                text = error_font.render(f"x{num}", True, RED)
                text_rect = text.get_rect(center=(x, y))
                screen.blit(text, text_rect)


def animate_correct_input(row, col, num):
    cell_size = (WIDTH - 2 * MARGIN) // 9
    x = MARGIN + col * cell_size + cell_size // 2
    y = MARGIN + row * cell_size + cell_size // 2
    total_frames = 20  # フレーム数を増やしてスピードをゆっくりにする

    # バウンドアニメーション
    for i in range(total_frames):
        offset = (total_frames - i) if i < total_frames / 2 else (i - total_frames / 2)
        scale = 10 - 9 * (i / total_frames)  # 最初10倍にし、徐々に1倍に近づける
        screen.fill(WHITE, (x - cell_size // 2, y - cell_size // 2, cell_size, cell_size))
        draw_board(board)
        display_comments()  # コメントの表示を追加
        text = font.render(str(num), True, BLUE)
        text_rect = text.get_rect(center=(x, y - offset))
        text = pygame.transform.scale(text, (int(text_rect.width * scale), int(text_rect.height * scale)))
        text_rect = text.get_rect(center=(x, y - offset))
        screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(int(ANIMATION_DURATION * 100 / total_frames))

    # マンハッタン距離に基づく波状アニメーションの追加
    max_distance = 9  # 最大マンハッタン距離を9に設定
    base_color = (173, 216, 230)  # 基本の薄い青色
    for distance in range(1, max_distance + 1):
        draw_board(board)
        draw_user_inputs(cell_size)
        display_comments()  # コメントの表示を追加
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if abs(dx) + abs(dy) == distance:  # マンハッタン距離が一致するセルを処理
                    new_row = row + dy
                    new_col = col + dx
                    if 0 <= new_row < 9 and 0 <= new_col < 9:
                        propagate_x = MARGIN + new_col * cell_size + cell_size // 2
                        propagate_y = MARGIN + new_row * cell_size + cell_size // 2
                        color_intensity = 1 - (distance - 1) / (max_distance - 1)
                        wave_color = (
                            int(WHITE[0] * (1 - color_intensity) + base_color[0] * color_intensity),
                            int(WHITE[1] * (1 - color_intensity) + base_color[1] * color_intensity),
                            int(WHITE[2] * (1 - color_intensity) + base_color[2] * color_intensity),
                        )
                        pygame.draw.rect(
                            screen,
                            wave_color,
                            (propagate_x - cell_size // 2, propagate_y - cell_size // 2, cell_size, cell_size),
                        )
                        if board[new_row][new_col] != 0:  # 数字がある場合のみ表示
                            text = font.render(str(board[new_row][new_col]), True, BLUE)
                            text_rect = text.get_rect(center=(propagate_x, propagate_y))
                            screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(100)  # 各距離ごとに一時停止
    draw_board(board)
    draw_user_inputs(cell_size)
    display_comments()  # コメントの表示を追加
    pygame.display.flip()


def animate_cell_already_filled(row, col):
    cell_size = (WIDTH - 2 * MARGIN) // 9
    x = MARGIN + col * cell_size + cell_size // 2
    y = MARGIN + row * cell_size + cell_size // 2
    for _ in range(3):
        pygame.draw.rect(screen, RED, (x - cell_size // 2, y - cell_size // 2, cell_size, cell_size), 3)
        pygame.display.flip()
        pygame.time.wait(100)
        pygame.draw.rect(screen, WHITE, (x - cell_size // 2, y - cell_size // 2, cell_size, cell_size), 3)
        draw_board(board)
        draw_user_inputs(cell_size)
        display_comments()  # コメントの表示を追加
        pygame.display.flip()
        pygame.time.wait(100)

    max_distance = 9  # 最大マンハッタン距離を9に設定
    base_color = (255, 182, 193)  # 基本の薄い赤色（ライトピンク）

    for distance in range(1, max_distance + 1):
        draw_board(board)
        draw_user_inputs(cell_size)
        display_comments()  # コメントの表示を追加
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if abs(dx) + abs(dy) == distance:  # マンハッタン距離が一致するセルを処理
                    new_row = row + dy
                    new_col = col + dx
                    if 0 <= new_row < 9 and 0 <= new_col < 9:
                        propagate_x = MARGIN + new_col * cell_size + cell_size // 2
                        propagate_y = MARGIN + new_row * cell_size + cell_size // 2
                        color_intensity = 1 - (distance - 1) / (max_distance - 1)
                        wave_color = (
                            int(WHITE[0] * (1 - color_intensity) + base_color[0] * color_intensity),
                            int(WHITE[1] * (1 - color_intensity) + base_color[1] * color_intensity),
                            int(WHITE[2] * (1 - color_intensity) + base_color[2] * color_intensity),
                        )
                        pygame.draw.rect(
                            screen,
                            wave_color,
                            (propagate_x - cell_size // 2, propagate_y - cell_size // 2, cell_size, cell_size),
                        )
                        if board[new_row][new_col] != 0:  # 数字がある場合のみ表示
                            text = font.render(str(board[new_row][new_col]), True, BLUE)
                            text_rect = text.get_rect(center=(propagate_x, propagate_y))
                            screen.blit(text, text_rect)
                        elif (new_row, new_col) == (row, col):  # 不正解の値を表示
                            text = font.render("X", True, RED)
                            text_rect = text.get_rect(center=(propagate_x, propagate_y))
                            screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(100)  # 各距離ごとに一時停止
    draw_board(board)
    draw_user_inputs(cell_size)
    pygame.display.flip()


def animate_incorrect_input(row, col, incorrect_value):
    cell_size = (WIDTH - 2 * MARGIN) // 9
    x = MARGIN + col * cell_size + cell_size // 2
    y = MARGIN + row * cell_size + cell_size // 2

    # シェイクアニメーション
    for _ in range(2):
        for dx in [-5, 5, -3, 3, -1, 1, 0]:
            screen.fill(WHITE, (x - cell_size // 2, y - cell_size // 2, cell_size, cell_size))
            draw_board(board)
            draw_user_inputs(cell_size)
            display_comments()  # コメントの表示を追加
            text = font.render(str(incorrect_value), True, RED)  # 不正解の値を表示
            text_rect = text.get_rect(center=(x + dx, y))
            screen.blit(text, text_rect)
            pygame.display.flip()
            pygame.time.wait(int(ANIMATION_DURATION * 100 / 10))

    # 波状アニメーションの追加
    max_distance = 9  # 最大マンハッタン距離を9に設定
    base_color = (255, 182, 193)  # 基本の薄い赤色（ライトピンク）

    for distance in range(1, max_distance + 1):
        draw_board(board)
        draw_user_inputs(cell_size)
        display_comments()  # コメントの表示を追加
        for dx in range(-distance, distance + 1):
            for dy in range(-distance, distance + 1):
                if abs(dx) + abs(dy) == distance:  # マンハッタン距離が一致するセルを処理
                    new_row = row + dy
                    new_col = col + dx
                    if 0 <= new_row < 9 and 0 <= new_col < 9:
                        propagate_x = MARGIN + new_col * cell_size + cell_size // 2
                        propagate_y = MARGIN + new_row * cell_size + cell_size // 2
                        color_intensity = 1 - (distance - 1) / (max_distance - 1)
                        wave_color = (
                            int(WHITE[0] * (1 - color_intensity) + base_color[0] * color_intensity),
                            int(WHITE[1] * (1 - color_intensity) + base_color[1] * color_intensity),
                            int(WHITE[2] * (1 - color_intensity) + base_color[2] * color_intensity),
                        )
                        pygame.draw.rect(
                            screen,
                            wave_color,
                            (propagate_x - cell_size // 2, propagate_y - cell_size // 2, cell_size, cell_size),
                        )
                        if board[new_row][new_col] != 0:  # 数字がある場合のみ表示
                            text = font.render(str(board[new_row][new_col]), True, BLUE)
                            text_rect = text.get_rect(center=(propagate_x, propagate_y))
                            screen.blit(text, text_rect)
                        elif (new_row, new_col) == (row, col):  # 不正解の値を表示
                            text = font.render(str(incorrect_value), True, RED)
                            text_rect = text.get_rect(center=(propagate_x, propagate_y))
                            screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(100)  # 各距離ごとに一時停止
    draw_board(board)
    draw_user_inputs(cell_size)
    display_comments()  # コメントの表示を追加
    pygame.display.flip()


def main():
    running = True
    global input_buffer, board, full_board, user_inputs, displayed_comments  # グローバル変数を使って入力バッファを更新
    draw_board(board)
    display_comments()  # コメントの表示

    last_fetch_time = time.time()
    video_id = get_live_video_id(CHANNEL_ID)
    live_chat_id = get_live_chat_id(video_id) if video_id else None
    while running:
        current_time = time.time()
        # ライブコメント
        if live_chat_id and current_time - last_fetch_time >= 10:
            new_messages = get_live_chat_messages(live_chat_id)
            for msg in new_messages:
                message_text = msg["snippet"]["displayMessage"]
                processed_message_ids.append(msg["id"])
                message = handle_input(board, full_board, message_text)
                print(message)
                draw_board(board)
                display_comments()
                # 数独が完成した場合、新しい数独を生成
                if check_completion(board):
                    full_board = generate_full_sudoku()
                    if not debug:
                        board = remove_numbers_from_board([row[:] for row in full_board])
                    else:
                        board = [row[:] for row in full_board]
                        board[0][0] = 0

                    user_inputs = {}
                    displayed_comments = []
                    draw_board(board)
                    display_comments()

            last_fetch_time = current_time
        # 手動でのキー入力？
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    message = handle_input(board, full_board, input_buffer)
                    print(message)
                    draw_board(board)  # ボードの再描画
                    display_comments()  # コメントの表示
                    input_buffer = ""  # 入力バッファをクリア

                    # 数独が完成した場合、新しい数独を生成
                    if check_completion(board):
                        full_board = generate_full_sudoku()
                        if not debug:
                            board = remove_numbers_from_board([row[:] for row in full_board])
                        else:
                            board = [row[:] for row in full_board]
                            board[0][0] = 0

                        user_inputs = {}
                        displayed_comments = []
                        draw_board(board)
                        display_comments()

                elif event.key == pygame.K_BACKSPACE:
                    input_buffer = input_buffer[:-1]
                else:
                    input_buffer += event.unicode
                print(f"Current input: {input_buffer}")  # デバッグ用に現在の入力を表示

    pygame.quit()


if __name__ == "__main__":
    main()

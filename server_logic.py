"""
Imports
"""
import random

"""
Helper Functions
"""
# Helper function to get a dict of moves surrounding a tile
def get_surround_moves(head_pos: dict):
    return {"left": {'x': head_pos['x']-1, 'y': head_pos['y']}, "up": {'x': head_pos['x'], 'y': head_pos['y']+1}, "right": {'x': head_pos['x']+1, 'y': head_pos['y']}, "down": {'x': head_pos['x'], 'y': head_pos['y']-1}}

"""
Weight Calculation Functions
"""
# Avoid edge
def avoid_edge(weights: dict, possible_moves: dict, board_height: int, board_width: int):
    
    # Iterate through all possible moves and reduce weights on them if they're out of bounds
    for dir_key, dir_value in possible_moves.items():
        if dir_value['x'] < 0 or dir_value['x'] >= board_width or dir_value['y'] < 0 or dir_value['y'] >= board_height:
             weights[dir_key] += -100

# Avoid hitting self
def avoid_self(weights: dict, possible_moves: dict, body_pos: list):
    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in body_pos:
            weights[dir_key] += -100

# Avoid hitting other snakes
def avoid_others(weights: dict, possible_moves: dict, you_id: str, snakes: list):
    # Create a list containing the positions of all snake tiles that's not you
    # Except for tail, will become open next turn as snake moves
    snake_tiles = []
    
    for snake in snakes:
        # If snake is self, ignore
        if snake['id'] == you_id: continue
        # Adding body list except for last element, which is tail
        snake_tiles += snake['body'][:-1]

    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in snake_tiles:
            weights[dir_key] += -100

# TODO: avoid going somewhere that could lead to being eaten
# Fine if snake is smaller
def avoid_eaten(weights: dict, possible_moves: dict, you: dict, snakes: list):

    # Create a dict of moves and the tiles that they are adjacent to (snake heads there could eat you next turn)
    adj_to_moves = {}
    for dir_key, dir_value in possible_moves.items():
        # Adjacent tile for this direction
        adj_dir = get_surround_moves(dir_value)
        # Get rid of the position of our snake's head and add to dict
        adj_to_moves[dir_key] = [x for x in adj_dir.values() if x != you['head']]

    
    # Get your snake's size
    your_size = len(you['body'])
    # Generate a list of positions for heads of snakes that are larger to or equal size to you
    larger_snake_heads = []
    for snake in snakes:
        if len(snake['body']) >= your_size:
            larger_snake_heads.append(snake['head'])

    # Reduce weighting of moves that could have you eaten
    # Iterate through each move
    for dir_key, dir_value in adj_to_moves.items():
        # Iterate through each position adjacent to move
        for pos in dir_value:
            # If snake in one of these tiles, reduce weight
            if pos in larger_snake_heads:
                weights[dir_key] += -50
                break





    
    
    
# TODO: Don't wall yourself in
# Implementation: Higher weighting towards direction with less body?
# Implementation: weight based on distance to each tile on snake

# TODO: Don't get walled in by other snakes
# 


# TODO: lower weights towards snakes


# TODO: higher weights towards food, unless we're the biggest snake


"""
Main Functions
"""
# Process weights (wrapper for all above)
def calc_weights(data: dict, weights: dict):
    # Generate a dict of possible moves and their coordinates
    possible_moves = get_surround_moves(data["you"]["head"])



    # Avoid edge
    avoid_edge(weights, possible_moves, data['board']['height'], data['board']['width'])
    # Avoid self
    avoid_self(weights, possible_moves, data["you"]["body"])
    # Avoid others
    avoid_others(weights, possible_moves, data["you"]["id"], data["board"]["snakes"])
    # Avoid being eaten
    avoid_eaten(weights, possible_moves, data["you"], data["board"]["snakes"])

# Calculates weights and chooses optimal move
def choose_move(data: dict) -> str:
    # Dictionary of possible moves and their weights
    # weight of -100 and less indicates a move that would kill the snake (e.g. wall, hitting neck)
    move_weights = {"left": 0, "up": 0, "right": 0, "down": 0}   

    # Calculate weights for move_weights
    calc_weights(data, move_weights)

    # Get the maxiumum weight
    max_val = max(move_weights.values())
    # Get list of keys with max value - multiple dirs could have same weight
    max_keys = [k for k in move_weights if move_weights[k] == max_val]
    # Randomly select direction from options
    move = random.choice(max_keys)



    print(f"MOVE {data['turn']}: {move} picked. Weights: {move_weights}")

    return move

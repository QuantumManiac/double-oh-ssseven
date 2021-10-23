"""
Imports
"""
import random
"""
Helper Functions
"""

global BOARD_HEIGHT
global BOARD_WIDTH
global DATA

# Helper function to get a dict of moves surrounding a tile
def get_surround_moves(head_pos: dict):
    return {
        "left": {
            "x": head_pos["x"] - 1,
            "y": head_pos["y"]
        },
        "up": {
            "x": head_pos["x"],
            "y": head_pos["y"] + 1
        },
        "right": {
            "x": head_pos["x"] + 1,
            "y": head_pos["y"]
        },
        "down": {
            "x": head_pos["x"],
            "y": head_pos["y"] - 1
        }
    }

def dist(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2) 

def abs_dist(p1: dict, p2: dict):
    return (abs(p1['x'] - p2['x']) ** 2 + abs(p1['y'] - p2['y']) ** 2) ** 0.5

def tile_out_of_bounds(tile:dict):
    global BOARD_HEIGHT
    global BOARD_WIDTH
    return tile['x'] < 0 or tile['x'] == BOARD_WIDTH or tile['y'] < 0 or tile['y'] == BOARD_HEIGHT

def flood_fill(tile: dict,  not_possible_moves: list, visited: list):
    # Check if tile is a snake body

    possible_moves = 1
    if tile in not_possible_moves:
        return 0
    if tile_out_of_bounds(tile):
        return 0
    if tile in visited:
        return 0

    visited.append(tile)
    
    possible_moves += flood_fill({ 'x': tile['x'] + 1, 'y': tile['y']}, not_possible_moves, visited) 
    possible_moves += flood_fill({ 'x': tile['x'] - 1, 'y': tile['y']}, not_possible_moves, visited) 
    possible_moves += flood_fill({ 'x': tile['x'], 'y': tile['y'] + 1}, not_possible_moves, visited)
    possible_moves += flood_fill({ 'x': tile['x'], 'y': tile['y'] - 1}, not_possible_moves, visited)

    return possible_moves
    
 
    # Check if tile is out of bou
    

def dont_get_enclosed(weights: dict, possible_moves: dict):
    global DATA
    # Get a list of all the snake body tiles on the table (ignoring tails because they clear tile next turn)
    snake_tiles = []
    for snake in DATA["board"]["snakes"]:
        snake_tiles += snake["body"][:-1]

    # Add weightings for each direction based on flood filling
    for dir_key, dir_value in possible_moves.items():
        visited = []
        flood_fill_value = flood_fill(dir_value, snake_tiles, visited)
        # If the snake body is too big to fill up the enclosed area, will end up in death so need to avoid
        if DATA["you"]["length"] > flood_fill_value:
            weights[dir_key] -= 10 * ((BOARD_HEIGHT * BOARD_WIDTH) - flood_fill_value)
        else:
            weights[dir_key] += 10 * flood_fill_value
        




"""
Weight Calculation Functions
"""


# Avoid edge
def avoid_edge(weights: dict, possible_moves: dict):
    global BOARD_HEIGHT
    global BOARD_WIDTH

    # Iterate through all possible moves and reduce weights on them if they're out of bounds
    for dir_key, dir_value in possible_moves.items():
        if dir_value["x"] < 0 or dir_value["x"] >= BOARD_WIDTH or dir_value[
                "y"] < 0 or dir_value["y"] >= BOARD_HEIGHT:
            weights[dir_key] += -100


# Avoid hitting self
def avoid_self(weights: dict, possible_moves: dict):
    global DATA
    
    body_pos = DATA["you"]["body"]

    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in body_pos:
            weights[dir_key] += -100

    # Iterate through every body tile and set a weight for each direction based on distance
    # i = 0
    # for body in body_pos:
    #     for dir_key, dir_value in possible_moves.items():
            
    #         # Get distance from the coordinate of the move to the tile
    #         dist = abs_dist(dir_value, body)

    #         # Ignore if the body tile is the head (0 distance apart)
    #         if dist == 0: continue
            
    #         # Negatively weight directions based on the reciprocal of the distance to each tile
    #         weights[dir_key] += -10 * (1 / dist)
    #     i += 1
        

# TODO Food finding (maybe improve?) 
# TODO Ignore food if biggest snake
# TODO Account for body moving in flood fill algo
# TODO Tweak weights



# Avoid hitting other snakes
def avoid_others(weights: dict, possible_moves: dict):
    global DATA
    
    you_id, snakes = DATA["you"]["id"], DATA["board"]["snakes"]

    # Create a list containing the positions of all snake tiles that"s not you
    # Except for tail, will become open next turn as snake moves
    snake_tiles = []

    for snake in snakes:
        # If snake is self, ignore
        if snake["id"] == you_id: continue
        # Adding body list except for last element, which is tail
        snake_tiles += snake["body"][:-1]

    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in snake_tiles:
            weights[dir_key] += -100


# TODO: avoid going somewhere that could lead to being eaten
# Fine if snake is smaller
def avoid_eaten(weights: dict, possible_moves: dict):
    global DATA

    you, snakes = DATA["you"], DATA["board"]["snakes"]

    # Create a dict of moves and the tiles that they are adjacent to (snake heads there could eat you next turn)
    adj_to_moves = {}
    for dir_key, dir_value in possible_moves.items():
        # Adjacent tile for this direction
        adj_dir = get_surround_moves(dir_value)
        # Get rid of the position of our snake"s head and add to dict
        adj_to_moves[dir_key] = [
            x for x in adj_dir.values() if x != you["head"]
        ]

    # Get your snake"s size
    your_size = you["length"]
    # Generate a list of positions for heads of snakes that are larger to or equal size to you
    larger_snake_heads = []
    for snake in snakes:
        if snake["length"] >= your_size:
            larger_snake_heads.append(snake["head"])

    # Reduce weighting of moves that could have you eaten
    # Iterate through each move
    for dir_key, dir_value in adj_to_moves.items():
        # Iterate through each position adjacent to move
        for pos in dir_value:
            # If snake in one of these tiles, reduce weight
            if pos in larger_snake_heads:
                weights[dir_key] += -50
                break

def find_food(weights: dict, possible_moves: dict):
    global DATA 
    
    head = DATA["you"]["head"]
    height, width = DATA["board"]["height"], DATA["board"]["width"]
    max_move = width + height
    
    food_tiles = DATA["board"]["food"]
    
    # Check if there is a food adjacent
    for dir_key, dir_value in possible_moves.items():
        if dir_value in food_tiles:
            weights[dir_key] += 50
            return
    # Add weights based on distance to all food tiles
    for food in food_tiles:
        # If food to right
        if food["x"] > head["x"]:
            weights["right"] += max_move - (food["x"] - head["x"])
        # If food to left
        elif food["x"] < head["x"]:
            weights["left"] += max_move - (head["x"] - food["x"])
        # If food to right
        if food["y"] > head["y"]:
            weights["up"] += max_move - (food["y"] - head["y"])
        # If food to left
        elif food["y"] < head["y"]:
            weights["down"] += max_move - (head["y"] - food["y"])

def setup(data: dict):
    global BOARD_HEIGHT
    global BOARD_WIDTH
    global DATA
    DATA = data
    BOARD_HEIGHT, BOARD_WIDTH = DATA["board"]["height"], DATA["board"]["width"]


    
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
def calc_weights():
    # Dictionary of possible moves and their weights
    # weight of -100 and less indicates a move that would kill the snake (e.g. wall, hitting neck)
    weights = {"left": 0, "up": 0, "right": 0, "down": 0}

    # Generate a dict of possible moves and their coordinates
    possible_moves = get_surround_moves(DATA['you']['head'])

    # Avoid edge
    avoid_edge(weights, possible_moves)
    # Avoid self
    avoid_self(weights, possible_moves) 
    # Avoid others
    avoid_others(weights, possible_moves)
    # Avoid being eaten
    avoid_eaten(weights, possible_moves)
    # Find food
    find_food(weights, possible_moves)
    # Don't get enclosed
    dont_get_enclosed(weights, possible_moves)

    return weights


def choose_move(weights: dict):
    # Get the maxiumum weight
    max_val = max(weights.values())
    # Get list of keys with max value - multiple dirs could have same highest weight
    max_keys = [k for k in weights if weights[k] == max_val]
    # Randomly select direction from options
    move = random.choice(max_keys)

    return move


# Main function - sends off the
def make_move(data: dict) -> str:
    setup(data)

    # Calculate the weightings for each move
    move_weights = calc_weights()
    # Choose the optimal move based on the move weights
    move = choose_move(move_weights)
    # Round the floats into ints to allow for easiest viewing
    for key, value in move_weights.items():
        move_weights[key] = round(value, 2)
    
    # Debug - print weights and chosen move
    print(f"MOVE {DATA['turn']}: {move} picked. Weights: {move_weights}")

    return move

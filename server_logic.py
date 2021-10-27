"""
Imports
"""

import random
"""
Global Vars
"""
# Debug toggle
DEBUG = True

# Game info
BOARD_HEIGHT = None  # Height of board
BOARD_WIDTH = None  # Width of board
DATA = None  # Data from the server request

# Weights
WEIGHT_BESIDE_BODY = None  # Weight towards adjacent snake tile
WEIGHT_BESIDE_FOOD = None  # Weight towards adjacent food tile
WEIGHT_BESIDE_EDGE = None  # Weight towards adjacent tiles out of bounds
WEIGHT_AVOID_EATEN_TILE = None  # Weights to avoid going into tile that may result in you being eaten by a bigger snake
SMALLER_HEAD_EXPONENT = None  # Exponentiated weight towards smaller snakes' heads
FOOD_WEIGHT_FACTOR = None  # Modifier based on distance for weights towards food tiles
LOW_HEALTH_THRESH = None  # Threshold for when the snake is at low health and will thus start searching for food when it otherwise wouldn't
CLOSEST_FOOD_WEIGHT_FACTOR = None  # Weight towards the closest food tile
WEIGHT_AVOID_CRAMPED = None  # Negative weight for moves that would lead into an enclosed area that the snake would not be able to fit in
WEIGHT_FLOOD_FILL = None  # Weight modifier for flood filled tile counts
WEIGHT_AVOID_BORDER = None  # Weight towards the direction opposite to the edge when on a boarder tile
MIN_DIST_THRESH = None  # The minimal distance threshold when doing depth-2 flood fill - all snake tiles within this radius are deleted
"""
Helper Functions
"""


# Get a dict of moves surrounding a tile
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


# Check if snake is largest of all snakes on the board by a margin of two
def is_snake_largest_by_two() -> bool:

    # Create a list of snake lengths and sort it descending
    snake_lengths = [x['length'] for x in DATA['board']['snakes']]
    snake_lengths.sort(reverse=True)

    # Get length of our snake
    you_length = DATA['you']['length']

    # If we're the only snake on the board
    if len(snake_lengths) == 1:
        return True

    # Check if we're the largest snake and the second-largest is smaller by at least 2
    return snake_lengths[
        0] == you_length and snake_lengths[0] >= snake_lengths[1] + 2


# Check if a tile is occupied by another snake
def is_occupied(pos: dict):
    global DATA

    # Check if tile is any of the occupied tiles
    for snake in DATA['board']['snakes']:
        if pos in snake["body"]:
            return True
    return False


def tile_out_of_bounds(tile: dict):

    # Return boolean based on if given tile is out of bounds or not
    return tile['x'] < 0 or tile['x'] == BOARD_WIDTH or tile['y'] < 0 or tile[
        'y'] == BOARD_HEIGHT


# Check if a tile is able to be occupied
def is_possible_move(pos: dict):
    # Check if space is not occupied by snake tile and not out of bounds
    return not is_occupied(pos) and not tile_out_of_bounds(pos)


# Return the absolute distance between tiles
def abs_dist(p1: dict, p2: dict):
    return (abs(p1['x'] - p2['x'])**2 + abs(p1['y'] - p2['y'])**2)**0.5


# Flood fill from a given tile and return the count of tiles that have been  flooded
def flood_fill(tile: dict, not_possible_moves: list, visited: list) -> int:
    # Check if tile is a snake body

    # Variable to found the number of flood-filled tiles
    possible_moves = 1

    # Tile is not counted because it is a tile occupied by a snake
    if tile in not_possible_moves:
        return 0
    # Tile is not counted because it is out of bounds
    if tile_out_of_bounds(tile):
        return 0
    # Tile is not counted because it has already been visited
    if tile in visited:
        return 0

    # Append the currently visited tile to the list of visited tiles
    visited.append(tile)

    # Recursively flood-filling in all directions and adding to the count
    possible_moves += flood_fill({
        'x': tile['x'] + 1,
        'y': tile['y']
    }, not_possible_moves, visited)
    possible_moves += flood_fill({
        'x': tile['x'] - 1,
        'y': tile['y']
    }, not_possible_moves, visited)
    possible_moves += flood_fill({
        'x': tile['x'],
        'y': tile['y'] + 1
    }, not_possible_moves, visited)
    possible_moves += flood_fill({
        'x': tile['x'],
        'y': tile['y'] - 1
    }, not_possible_moves, visited)

    # Return count of flood-filled tiles
    return possible_moves


# Check if the snake is on the border tiles of the board
def snake_on_edge(possible_moves: dict) -> bool:
    # Would be on border if any of the possible moves for the snake are out of bounds
    for dir_key, dir_value in possible_moves.items():
        if tile_out_of_bounds(dir_value):
            return True
    return False


# Use flood-filling to avoid making a move into an enclosed space
def dont_get_enclosed(weights: dict, possible_moves: dict):

    # Get a list of all the snake body tiles on the table (ignoring tails because they clear tile next turn)
    snake_tiles = []
    for snake in DATA["board"]["snakes"]:
        snake_tiles += snake["body"][:-1]
    # Get list of snakes
    snakes = DATA["board"]["snakes"]

    # Generate list of heads that are of snakes that are bigger than you but outside the minimum distance threshold UNLESS the snake is on the border tiles
    heads = []
    for snake in snakes:
        if abs_dist(snake["head"], DATA['you']['head']) > MIN_DIST_THRESH and (
                snake["length"] >= DATA['you']['length']
                or snake_on_edge(possible_moves)):
            heads.append(snake['head'])

    # Depth 2 flood fill blocker tiles are the snake tiles and tiles adjacent to heads specified above
    snake_tiles_and_adj = snake_tiles + generate_head_markers(heads)
    # Combine depth 1 and 2 flood fill blocker tiles
    flood_fill_data = [snake_tiles, snake_tiles_and_adj]

    # Add weightings for each direction based on flood filling
    for dir_key, dir_value in possible_moves.items():

        for blocked_tiles in flood_fill_data:
            visited = []
            # Get count of flood filled tiles for direction
            flood_fill_value = flood_fill(dir_value, blocked_tiles, visited)
            # Avoid moving in direction if the number of flood filled tiles is less than your snake's size (can't fit)
            if DATA["you"]["length"] > flood_fill_value:
                weights[dir_key] += WEIGHT_AVOID_CRAMPED * (
                    (BOARD_HEIGHT * BOARD_WIDTH) - flood_fill_value)
            else:
                # Else weight depending on how much empty space there is
                weights[dir_key] += WEIGHT_FLOOD_FILL * flood_fill_value


# Generate a list of head tiles of snakes that are smaller than us
def get_smaller_heads() -> list:
    # Get size of your snake
    my_size = DATA['you']['length']
    # Get list of heads that are smaller than your snake's
    heads = [
        x["head"] for x in DATA['board']['snakes'] if x["length"] < my_size
    ]

    return heads


# Generate a list of valid tiles surrounding each head in the given list
def generate_head_markers(heads: list) -> list:
    head_markers = []
    for head in heads:
        # Get the surrounding tiles for the head
        possible_moves = get_surround_moves(head)
        for move in possible_moves.values():
            # Check if the tile is valid
            if is_possible_move(move):
                head_markers.append(move)
    return head_markers


# Generate a list of all opponent snakes' head positions on the board
def get_all_heads() -> list:
    global DATA
    heads = [x["head"] for x in DATA["board"]["snakes"] if x != DATA["you"]]
    return heads


"""
Weight Calculation Functions
"""


# Avoid going out of edge
def avoid_edge(weights: dict, possible_moves: dict):

    # Iterate through all possible moves and reduce weights on them if they're out of bounds
    for dir_key, dir_value in possible_moves.items():
        if tile_out_of_bounds(dir_value):
            weights[dir_key] += WEIGHT_BESIDE_EDGE


# Avoid hitting self
def avoid_self(weights: dict, possible_moves: dict):

    # Get the positions of your body tiles
    body_pos = DATA["you"]["body"]

    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in body_pos:
            weights[dir_key] += WEIGHT_BESIDE_BODY


# Avoid hitting other snakes
def avoid_others(weights: dict, possible_moves: dict):

    you_id, snakes = DATA["you"]["id"], DATA["board"]["snakes"]

    # Create a list containing the positions of all snake tiles that's not you
    snake_tiles = []

    for snake in snakes:
        # If snake is self, ignore
        if snake["id"] == you_id: continue
        # Adding body list except for last element, which is tail
        snake_tiles += snake["body"][:-1]

    # Iterate through each of the directions and see if the body is in any of those coordinates. If they are, reduce its weight
    for dir_key, dir_value in possible_moves.items():
        if dir_value in snake_tiles:
            weights[dir_key] += WEIGHT_BESIDE_BODY


# Use look-ahead to avoid getting eaten by bigger snakes
def avoid_eaten(weights: dict, possible_moves: dict):

    # Get info for snakes
    you, snakes = DATA["you"], [
        x for x in DATA["board"]["snakes"] if x != DATA["you"]
    ]

    # Create a dict of moves and the tiles that they are adjacent to (snake heads there could eat you next turn)
    adj_to_moves = {}
    for dir_key, dir_value in possible_moves.items():
        # Adjacent tile for this direction
        adj_dir = get_surround_moves(dir_value)
        # Get rid of the position of our snake's head and add to dict
        adj_to_moves[dir_key] = [
            x for x in adj_dir.values() if x != you["head"]
        ]

    # Generate a list of positions for heads of snakes that are larger to or equal size to you
    larger_snake_heads = [
        x["head"] for x in snakes if x["length"] >= you["length"]
    ]

    # Reduce weighting of moves that could have you eaten
    # Iterate through each move
    for dir_key, dir_value in adj_to_moves.items():
        # Iterate through each position adjacent to move
        for pos in dir_value:
            # If snake in one of these tiles, reduce weight
            if pos in larger_snake_heads:
                weights[dir_key] += WEIGHT_AVOID_EATEN_TILE
                break


# Weight towards smaller snakes' heads when in agressive mode
def find_smaller_heads(weights: dict, possible_moves: dict):

    # Get a list of the tiles adjacent to smaller snakes' heads
    heads = get_smaller_heads()
    head_markers = generate_head_markers(heads)
    # Get position of your head
    your_head = DATA["you"]["head"]
    # Variable for maximum move length in Manhattan distance
    max_move = BOARD_HEIGHT + BOARD_WIDTH

    # Iterate through each head marker and weight towards it based on distance
    for marker in head_markers:
        # If marker to right
        if marker["x"] > your_head["x"]:
            weights["right"] += (max_move - (marker["x"] - your_head["x"])
                                 ) * len(heads)**SMALLER_HEAD_EXPONENT
        # If marker to left
        elif marker["x"] < your_head["x"]:
            weights["left"] += (max_move - (your_head["x"] - marker["x"])
                                ) * len(heads)**SMALLER_HEAD_EXPONENT
        # If marker to right
        if marker["y"] > your_head["y"]:
            weights["up"] += (max_move - (marker["y"] - your_head["y"])
                              ) * len(heads)**SMALLER_HEAD_EXPONENT
        # If marker to left
        elif marker["y"] < your_head["y"]:
            weights["down"] += (max_move - (your_head["y"] - marker["y"])
                                ) * len(heads)**SMALLER_HEAD_EXPONENT


def find_food(weights: dict, possible_moves: dict):

    # Get position of your head
    head = DATA["you"]["head"]
    # Variable for maximum move length in Manhattan distance
    max_move = BOARD_HEIGHT + BOARD_WIDTH
    # Get your health
    health = DATA['you']['health']
    # Get the list of food tiles
    food_tiles = DATA["board"]["food"]
    # Check if we're the biggest snake by a margin of two
    biggest_snake_by_two = is_snake_largest_by_two()
    # Add weightings to directions when they have food right beside the head of the snake
    for dir_key, dir_value in possible_moves.items():
        # Weight negatively if biggest snake by two and health high
        if dir_value in food_tiles:
            weights[dir_key] += (
                -WEIGHT_BESIDE_FOOD * 3
            ) if biggest_snake_by_two and health > LOW_HEALTH_THRESH else WEIGHT_BESIDE_FOOD

    # Add weights based on distance to all food tiles
    if (not biggest_snake_by_two or health < LOW_HEALTH_THRESH):
        # Variable to track the position of the food closest to the snake
        min_foods = []
        for food in food_tiles:
            # If food to right
            if food["x"] > head["x"]:
                weights["right"] += (
                    max_move - (food["x"] - head["x"])) * FOOD_WEIGHT_FACTOR
            # If food to left
            elif food["x"] < head["x"]:
                weights["left"] += (
                    max_move - (head["x"] - food["x"])) * FOOD_WEIGHT_FACTOR
            # If food to right
            if food["y"] > head["y"]:
                weights["up"] += (max_move -
                                  (food["y"] - head["y"])) * FOOD_WEIGHT_FACTOR
            # If food to left
            elif food["y"] < head["y"]:
                weights["down"] += (
                    max_move - (head["y"] - food["y"])) * FOOD_WEIGHT_FACTOR
            # Update minimum distance food if applicable
            if not min_foods or abs_dist(min_foods[0], head) > abs_dist(
                    head, food):
                min_foods = [food]
            elif (abs_dist(min_foods[0], head) == abs_dist(head, food)):
                min_foods.append(food)
        # If food of minimum distance does exist, weight it with relevant weighting
        if not min_foods == {"x": 1000, "y": 1000}:
            for food in min_foods:
                # If food to right
                if food["x"] > head["x"]:
                    weights["right"] += CLOSEST_FOOD_WEIGHT_FACTOR
                # If food to left
                elif food["x"] < head["x"]:
                    weights["left"] += CLOSEST_FOOD_WEIGHT_FACTOR
                # If food to right
                if food["y"] > head["y"]:
                    weights["up"] += CLOSEST_FOOD_WEIGHT_FACTOR
                # If food to left
                elif food["y"] < head["y"]:
                    weights["down"] += CLOSEST_FOOD_WEIGHT_FACTOR


# Avoid border tiles by weighting the direction opposite to the edge
def avoid_border(weights: dict):

    head = DATA['you']['head']
    # If edgge to left
    if head["x"] == 0:
        weights["right"] += WEIGHT_AVOID_BORDER
    # If edge to right
    elif head["x"] == BOARD_WIDTH:
        weights["left"] += WEIGHT_AVOID_BORDER
    # If edge to down
    if head["y"] == 0:
        weights["up"] += WEIGHT_AVOID_BORDER
    # If edge to up
    elif head["y"] == BOARD_HEIGHT:
        weights["down"] += WEIGHT_AVOID_BORDER


"""
Main Functions
"""


# Set up global variables from board data
def setup(data: dict):
    # Declare globals
    global BOARD_HEIGHT, BOARD_WIDTH, DATA, WEIGHT_BESIDE_FOOD, WEIGHT_BESIDE_BODY, WEIGHT_BESIDE_EDGE, SMALLER_HEAD_EXPONENT, WEIGHT_AVOID_EATEN_TILE, FOOD_WEIGHT_FACTOR, LOW_HEALTH_THRESH, CLOSEST_FOOD_WEIGHT_FACTOR, WEIGHT_AVOID_CRAMPED, WEIGHT_FLOOD_FILL, WEIGHT_AVOID_BORDER, MIN_DIST_THRESH

    # Set weights (TWEAK HERE)
    WEIGHT_BESIDE_BODY = -10000
    WEIGHT_BESIDE_FOOD = 50
    WEIGHT_BESIDE_EDGE = -10000
    FOOD_WEIGHT_FACTOR = 0.5
    LOW_HEALTH_THRESH = 30
    WEIGHT_AVOID_EATEN_TILE = -1000
    SMALLER_HEAD_EXPONENT = 2
    CLOSEST_FOOD_WEIGHT_FACTOR = 500
    WEIGHT_AVOID_CRAMPED = -7500
    WEIGHT_FLOOD_FILL = 100
    WEIGHT_AVOID_BORDER = 200
    MIN_DIST_THRESH = 1

    # Get data from request
    DATA = data
    # Get board dimensions from request data
    BOARD_HEIGHT, BOARD_WIDTH = DATA["board"]["height"], DATA["board"]["width"]


# Process weights (wrapper for all above)
def calc_weights():
    # Dictionary of possible moves and their weights
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
    # Find smaller heads
    find_smaller_heads(weights, possible_moves)
    # Don't get enclosed
    dont_get_enclosed(weights, possible_moves)
    # Avoid being at edge tiles
    avoid_border(weights)

    return weights


# Use the
def choose_move(weights: dict) -> str:
    # Get the maxiumum weight
    max_val = max(weights.values())
    # Get list of keys with max value - multiple dirs could have same highest weight
    max_keys = [k for k in weights if weights[k] == max_val]
    # Randomly select direction from options
    move = random.choice(max_keys)

    return move


# Main function - sends off the chosen move to the server
def make_move(data: dict) -> str:
    # Set up data for current board state
    setup(data)

    # Calculate the weightings for each move
    move_weights = calc_weights()
    # Choose the optimal move based on the move weights
    move = choose_move(move_weights)

    # Debug - print weights and chosen move
    if DEBUG:
        # Round the floats for better viewing in logs
        for key, value in move_weights.items():
            move_weights[key] = round(value, 2)

        # Print logs
        print(f"MOVE {DATA['turn']}: {move} picked. Weights: {move_weights}")

    return move

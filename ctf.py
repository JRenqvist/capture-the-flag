""" Main file for the game.
"""
import pygame
from pygame.locals import *
from pygame.color import *
import pymunk
from argparse import ArgumentParser
import manual

manual.disp_manual("./data/Manual/welcome.png")
manual.disp_manual("./data/Manual/instructions.png")
manual.disp_manual("./data/Manual/information.png")


# Calls pygame and pymunk to initialize the game. pygame handles visual ascepts and pymunk handles physics
# ----- Initialisation ----- #

# -- Initialise the display
pygame.init()
pygame.display.set_mode()

# -- Initialise the clock
clock = pygame.time.Clock()

# -- Initialise the physics engine
space = pymunk.Space()
space.gravity = (0.0, 0.0)
space.damping = 0.1  # Adds friction to the ground for all objects

# -- Import from the ctf framework
# The framework needs to be imported after initialisation of pygame
import ai
import images
import gameobjects
import maps


# -- Constants
FRAMERATE = 50
frames_passed_since_shoot = 0

# -- Variables

#   Define the current level
current_map = maps.map0

#   List of all game objects
game_objects_list = []
bases_list = []
tanks_list = []
bullet_list = []
numbered_tanks = []
ai_list = []
explosion_list = []
# Dictionary of all collision types
collision_types = {
    "bullet": 1,
    "tank": 2,
    "stone": 3,
    "wood": 4,
    "metal": 5,
    "bounds": 6
}

# Gamemodes
play_FOW = False

# Resize the screen to the size of the current level
screen = pygame.display.set_mode(current_map.rect().size)

# Generate the background
background = pygame.Surface(screen.get_size())

# Create the flag
flag = gameobjects.Flag(current_map.flag_position[0], current_map.flag_position[1])
game_objects_list.append(flag)


def single_or_multiplayer():
    """ Handles hot-seat multiplayer. Returns 1 if singleplayer, 2 if multiplayer """
    arg_parser = ArgumentParser()

    arg_parser.add_argument("--singleplayer", nargs="?", const=True, type=bool)
    arg_parser.add_argument("--multiplayer", nargs="?", const=True, type=bool)

    args = arg_parser.parse_args()

    if args.singleplayer:
        play_type = 1
    elif args.multiplayer:
        play_type = 2
    else:
        play_type = 1

    return play_type


# -- Functions
def create_background():
    """Copy the grass tile all over the level area"""
    for x in range(0, current_map.width):
        for y in range(0, current_map.height):
            # The call to the function "blit" will copy the image
            # contained in "images.grass" into the "background"
            # image at the coordinates given as the second argument
            background.blit(images.grass, (x * images.TILE_SIZE, y * images.TILE_SIZE))


def create_boxes():
    """Create the boxes"""
    global game_objects_list
    for x in range(0, current_map.width):
        for y in range(0, current_map.height):
            # Get the type of boxes
            box_type = current_map.boxAt(x, y)
            # If the box type is not 0 (aka grass tile), create a box
            if (box_type != 0):
                # Create a "Box" using the box_type, aswell as the x,y coordinates,
                # and the pymunk space
                box = gameobjects.get_box_with_type(x, y, box_type, space)
                game_objects_list.append(box)


def create_tanks():
    """Create the tanks"""
    global tanks_list, ai_list

    # Loop over the starting poistion
    for i in range(0, len(current_map.start_positions)):

        # Get the starting position of the tank "i"
        pos = current_map.start_positions[i]

        if i < single_or_multiplayer():
            # Create the tank, images.tanks contains the image representing the tank
            tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[i], space)
            tanks_list.append(tank)

        else:
            tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[i], space)
            artificial_intelligence = ai.Ai(tank, game_objects_list, tanks_list, space, current_map)
            ai_list.append(artificial_intelligence)
            tanks_list.append(tank)


def tank_shoot(event, tank, player):
    """Checks if player shoots """

    event_key = None
    if player == 0:
        event_key = K_RETURN
    elif player == 1:
        event_key = K_SPACE

    if event.type == KEYDOWN and event.key == event_key:
        for i in range(0, len(current_map.start_positions)):
            if tank.frames_since_last_shoot > 50 and i == player:
                bullet = tanks_list[i].shoot(space)
                bullet_list.append(bullet)
                tank.frames_since_last_shoot = 0


def create_bases():
    """Create the bases"""
    global bases_list

    for i in range(0, len(current_map.start_positions)):
        pos = current_map.start_positions[i]
        base = gameobjects.GameVisibleObject(pos[0], pos[1], images.bases[i])
        bases_list.append(base)


def create_bounds():
    """Adds outer lines to prevent tanks from going out of bounds"""
    global space

    x_bound = current_map.width
    y_bound = current_map.height
    static_body = space.static_body
    static_lines = [
        pymunk.Segment(static_body, (0, 0), (0, y_bound), 0.0),
        pymunk.Segment(static_body, (0, 0), (x_bound, 0), 0.0),
        pymunk.Segment(static_body, (x_bound, y_bound), (0, y_bound), 0.0),
        pymunk.Segment(static_body, (x_bound, y_bound), (x_bound, 0), 0.0),
    ]
    for line in static_lines:
        line.collision_type = 6
        line.elasticity = 0
        line.friction = 1

    space.add(*static_lines)


def create_explosion(bullet):
    """creates an explosion"""
    global explosion_list

    exp = gameobjects.Explosion(bullet.x, bullet.y)
    explosion_list.append(exp)

    # Creates an explosionsound
    explosion_sound = pygame.mixer.Sound("./data/explosionsound.wav")
    pygame.mixer.Sound.play(explosion_sound)
    pygame.mixer.music.stop()


def detect_exit(event):
    """Check if we receive a QUIT event (for instance, if the user press the
    close button of the window) or if the user press the escape key."""
    global running

    if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
        running = False


def move_tank(event, player):
    """Detects arrow key presses and moves tank"""

    if player == 0:
        if event.type == KEYDOWN and event.key == K_UP:
            tanks_list[player].accelerate()
        elif event.type == KEYDOWN and event.key == K_DOWN:
            tanks_list[player].decelerate()
        elif event.type == KEYDOWN and event.key == K_LEFT:
            tanks_list[player].turn_left()
        elif event.type == KEYDOWN and event.key == K_RIGHT:
            tanks_list[player].turn_right()

        # If arrow key is released, stop moving/turning
        elif event.type == KEYUP and (event.key == K_UP or event.key == K_DOWN):
            tanks_list[player].stop_moving()
        elif event.type == KEYUP and (event.key == K_LEFT or event.key == K_RIGHT):
            tanks_list[player].stop_turning()

    elif single_or_multiplayer() == 2 and player == 1:
        if event.type == KEYDOWN and event.key == K_w:
            tanks_list[player].accelerate()
        elif event.type == KEYDOWN and event.key == K_s:
            tanks_list[player].decelerate()
        elif event.type == KEYDOWN and event.key == K_a:
            tanks_list[player].turn_left()
        elif event.type == KEYDOWN and event.key == K_d:
            tanks_list[player].turn_right()

        # If arrow key is released, stop moving/turning
        elif event.type == KEYUP and (event.key == K_w or event.key == K_s):
            tanks_list[player].stop_moving()
        elif event.type == KEYUP and (event.key == K_a or event.key == K_d):
            tanks_list[player].stop_turning()


def ai_shoot(ai_tank, pos):
    """ Shoot function for the Ai """
    if ai_tank.tank.frames_since_last_shoot > 50:
        if ai_tank.maybe_shoot(pos):
            bullet = ai_tank.tank.shoot(space, True)
            bullet_list.append(bullet)
            ai_tank.tank.frames_since_last_shoot = 0


def tank_destroyed():
    """Checks if any tanks have been destroyed"""
    global numbered_tanks, tanks_list, ai_list

    for tank_num in range(0, len(current_map.start_positions)):
        if tank_num not in numbered_tanks:

            # Puts flag down
            if flag.is_on_tank:
                flag.is_on_tank = False

            # Reset tanks to start position
            numbered_tanks.insert(tank_num, tank_num)
            pos = current_map.start_positions[tank_num]
            tank = gameobjects.Tank(pos[0], pos[1], pos[2], images.tanks[tank_num], space)
            tanks_list.insert(tank_num, tank)

            # tank_offset variable considers if we are playing single or multiplayer and adjusts the index accordingly
            tank_offset = 1 if single_or_multiplayer() == 1 else 2

            if tanks_list[tank_num].start_position == ai_list[tank_num - tank_offset].tank.start_position:
                ai_list[tank_num - tank_offset] = ai.Ai(tank, game_objects_list, tanks_list, space, current_map)


def collision_detection():
    """Is called when a bullet collides with objects"""

    handler = space.add_collision_handler(collision_types["bullet"], collision_types["tank"])
    handler.pre_solve = collision_bullet_tank

    handler = space.add_collision_handler(collision_types["bullet"], collision_types["stone"])
    handler.pre_solve = collision_bullet_other(collision_types["stone"])

    handler = space.add_collision_handler(collision_types["bullet"], collision_types["wood"])
    handler.pre_solve = collision_bullet_other(collision_types["wood"])

    handler = space.add_collision_handler(collision_types["bullet"], collision_types["metal"])
    handler.pre_solve = collision_bullet_other(collision_types["metal"])

    handler = space.add_collision_handler(collision_types["bullet"], collision_types["bounds"])
    handler.pre_solve = collision_bullet_other(collision_types["bounds"])


def collision_bullet_tank(arb, space, data):
    """Is called when a bullet collides with a tank"""
    global tanks_list, numbered_tanks, bullet_list

    # Creates an explosion when a tank collides with a bullet
    bullet = arb.shapes[1].parent
    create_explosion(bullet)

    try:
        # Find index of removed tank
        index_removed_tank = tanks_list.index(arb.shapes[1].parent)
    except ValueError:
        pass

    try:
        # Delete from both lists
        del numbered_tanks[index_removed_tank]
        tanks_list.remove(arb.shapes[1].parent)
    except ValueError:
        pass

    try:
        # Delete bullet
        bullet_list.remove(arb.shapes[0].parent)
        space.remove(arb.shapes[0], arb.shapes[0].body)
    except ValueError:
        pass

    try:
        # Delete from physics engine
        space.remove(arb.shapes[1], arb.shapes[1].body)
    except ValueError:
        pass

    return False


def collision_bullet_other(type):
    """Is called when a bullet collides with a box"""

    def collision_bullet_box(arb, space, data):
        global tanks_list, bullet_list, game_objects_list

        if type == 3:       # If box is stoneblock
            try:
                bullet_list.remove(arb.shapes[0].parent)
                space.remove(arb.shapes[0], arb.shapes[0].body)
            except ValueError:
                pass
            return False

        elif type == 4:    # If box is woodblock
            try:
                # Creates an explosion when a tank collides with a bullet
                bullet = arb.shapes[1].parent
                create_explosion(bullet)

                bullet_list.remove(arb.shapes[0].parent)
                space.remove(arb.shapes[0], arb.shapes[0].body)
            except ValueError:
                pass

            try:
                game_objects_list.remove(arb.shapes[1].parent)
                space.remove(arb.shapes[1], arb.shapes[1].body)
            except ValueError:
                pass
            return True

        elif type == 5:     # If type is metalblock
            try:
                bullet_list.remove(arb.shapes[0].parent)
                space.remove(arb.shapes[0], arb.shapes[0].body)
            except ValueError:
                pass
            return False

    def collision_bullet_bound(arb, space, data):
        global bullet_list

        try:
            bullet_list.remove(arb.shapes[0].parent)
            space.remove(arb.shapes[0], arb.shapes[0].body)
        except ValueError:
            pass
        return False

    return collision_bullet_box if type != 6 else collision_bullet_bound


def create_fog_background(screen):
    """ Creates a single black Surface() on which we draw however many circles we need """
    fog = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    pygame.draw.rect(fog, (0, 0, 0, 255), pygame.Rect(0, 0, current_map.width * 40, current_map.height * 40))

    ai_tank_list = [ai.tank for ai in ai_list]

    for tank in tanks_list:
        gen_fog = True
        if tank in ai_tank_list:
            gen_fog = False

        if gen_fog:
            circle = gameobjects.FogOfwar(current_map, tank, fog)
            circle.update()

    screen.blit(fog, (0, 0))


def main_loop():
    """Main loop of the game"""
    global tanks_list, game_objects_list, bullet_list, bases_list, skip_update, running

    # -- Handle the events
    for event in pygame.event.get():
        detect_exit(event)

        for tank in tanks_list:
            move_tank(event, tanks_list.index(tank))
            tank_shoot(event, tank, tanks_list.index(tank))

    collision_detection()

    tank_destroyed()

    # Tries to constantly grab flag for all tanks
    for tank in tanks_list:
        tank.try_grab_flag(flag)

    # -- Update physics
    if skip_update == 0:
        # Loop over all the game objects and update their speed in function of their
        # acceleration.
        for obj in game_objects_list:
            obj.update()
        skip_update = 2
    else:
        skip_update -= 1

    #   Check collisions and update the objects position
    space.step(1 / FRAMERATE)

    #   Update object that depends on an other object position (for instance a flag)
    for obj in game_objects_list:
        obj.post_update()

    # -- Update Display

    # Display the background on the screen
    screen.blit(background, (0, 0))

    # Update the display of the game objects on the screen
    for obj in game_objects_list:
        obj.update_screen(screen)

    # Adds bases to the screen
    for base in bases_list:
        base.update_screen(screen)

    # Update tanks position and flag position if on tank
    for tank in tanks_list:
        tank.update_screen(screen)
        tank.update()
        tank.post_update()
        tank.frames_since_last_shoot += 1
        # Checks if tank has won
        if tank.has_won():
            running = False

    # Update bullet positions
    for bullet in bullet_list:
        bullet.update_screen(screen)
        bullet.update()

    collision_detection()

    # Displays the explosion
    if explosion_list:
        for exp in explosion_list:
            exp.update_screen(screen)
            explosion_list.remove(exp)

    # Handles the Ai
    for ai_tank in ai_list:
        ai_tank.decide()

        if ai_tank.maybe_shoot(ai_tank.tank.body.position):
            ai_shoot(ai_tank, ai_tank.tank.body.position)

        if ai_tank.tank.has_won():
            running = False

    # Checks for gamemodes to play
    if play_FOW:
        create_fog_background(screen)

    #   Redisplay the entire screen (see double buffer technique)
    pygame.display.flip()

    #   Control the game framerate
    clock.tick(FRAMERATE)


# -- Starts the game
create_background()

create_boxes()

create_tanks()


# Create numbered list where numbers correspond to tank in tank_list (Used incollision detection)
# Creates after tanks_list is defined in function create_tanks
numbered_tanks = list(range(len(tanks_list)))

create_bases()

# Updates all objects every 3rd frame inside a while loop. If the user presses the X or ESCAPE, the game quits.
# ----- Main Loop -----#

# -- Control whether the game run
running = True
skip_update = 0

create_bounds()

while running:
    main_loop()

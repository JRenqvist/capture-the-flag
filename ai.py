""" This file contains function and classes for the Artificial Intelligence used in the game.
"""

import math
from collections import defaultdict, deque

import pymunk
from pymunk import Vec2d
import gameobjects

# NOTE: use only 'map0' during development!

MIN_ANGLE_DIF = math.radians(3)   # 3 degrees, a bit more than we can turn each tick


# Converts an angle in cartesian coordinate space to angle in computer coordinate space (only positive values)
def angle_between_vectors(vec1, vec2):
    """ Since Vec2d operates in a cartesian coordinate space we have to
        convert the resulting vector to get the correct angle for our space.
    """
    vec = vec1 - vec2
    vec = vec.perpendicular()
    return vec.angle


# Returns the difference between two angles in radians
def periodic_difference_of_angles(angle1, angle2):
    """ Compute the difference between two angles.
    """
    return (angle1 % (2 * math.pi)) - (angle2 % (2 * math.pi))


# This class controls all of the AI in the game. If a wooden box or other player is infront, shoots. Also checks position of flag and moves towards it.
class Ai:
    """ A simple ai that finds the shortest path to the target using
    a breadth first search. Also capable of shooting other tanks and or wooden
    boxes. """

    def __init__(self, tank, game_objects_list, tanks_list, space, currentmap):
        self.tank = tank
        self.game_objects_list = game_objects_list
        self.tanks_list = tanks_list
        self.space = space
        self.currentmap = currentmap
        self.flag = None
        self.max_x = currentmap.width - 1
        self.max_y = currentmap.height - 1
        self.flag_start_position = self.currentmap.flag_position
        self.tank.ACCELERATION *= 1.3
        self.tank.NORMAL_MAX_SPEED *= 1.3

        self.path = deque()
        self.move_cycle = self.move_cycle_gen()
        self.update_grid_pos()

    def update_grid_pos(self):
        """ This should only be called in the beginning, or at the end of a move_cycle. """
        self.grid_pos = self.get_tile_of_position(self.tank.body.position)

    def decide(self):
        """ Main decision function that gets called on every tick of the game.
        """
        cycle = self.move_cycle
        next(cycle)

    def maybe_shoot(self, current_pos):
        """ Makes a raycast query in front of the tank. If another tank
            or a wooden box is found, then we shoot.
        """

        angle = self.tank.body.angle
        ray_offset = 0.5

        # Calculate start position x and y of our raycast
        ray_x_start = current_pos[0] - ray_offset * math.sin(angle)
        ray_y_start = current_pos[1] + ray_offset * math.cos(angle)
        start = Vec2d(ray_x_start, ray_y_start)

        # Calculates the end position of our raycast
        highest_dimension_coord = max(self.currentmap.width, self.currentmap.height)
        ray_x_end = highest_dimension_coord * math.sin(-angle)
        ray_y_end = highest_dimension_coord * math.cos(angle)
        end = Vec2d(ray_x_end, ray_y_end)
        end = end + self.tank.body.position

        ray = self.space.segment_query_first(start, end, 0, pymunk.ShapeFilter())

        # Try statement to catch Segments (outer bounds) not having a .shape
        try:
            if ray.shape.parent.shape.collision_type in [2, 4]:
                return True
        except AttributeError:
            pass

    def move_cycle_gen(self):
        """ A generator that iteratively goes through all the required steps
            to move to our goal.
        """

        # Finds the shortest path. If we cant find one, take consideration to metal tiles
        self.shortest_path = self.find_shortest_path()
        if not self.shortest_path:
            self.shortest_path = self.find_shortest_path(True)

        # Generator for movement of ai tank
        while True:

            # Updates shortest path if flag has ben picked up and moved
            if self.shortest_path:

                if self.shortest_path[-1] != self.get_target_tile():
                    self.shortest_path = self.find_shortest_path()

                    if not self.shortest_path:
                        self.shortest_path = self.find_shortest_path(True)

            # If shortest_path is empty, we have picked up the flag
            # Generate new shortest_path to base
            if not self.shortest_path:
                self.shortest_path = self.find_shortest_path()

                if not self.shortest_path:
                    self.shortest_path = self.find_shortest_path(True)

                yield
                continue

            node = self.shortest_path.popleft()
            yield
            current_angle, turn_to_angle = self.update_angles(node)

            # When tank starts on the correct node, calls continue so calculate the next note
            if self.correct_pos(node):
                continue

            # If we don't have the correct angle, keep turning until we do
            while not self.correct_angle(current_angle, turn_to_angle):

                current_angle, turn_to_angle = self.turn(current_angle, turn_to_angle, node)
                yield

            # Calls the turn function one last time to stop turning
            current_angle, turn_to_angle = self.turn(current_angle, turn_to_angle, node)

            # If we don't have the correct position, keep accelerating until we do
            while not self.correct_pos(node):
                current_angle, turn_to_angle = self.accelerate(node)
                yield

            # Calls the accelerate function one last time to stop accelerating
            current_angle, turn_to_angle = self.accelerate(node)

    def shortest_angle(self, current_angle, target_angle):
        """ Returns the angle which we have to turn to
            Helper function to turn() """

        angle_difference = periodic_difference_of_angles(target_angle, current_angle)

        # Ensure the difference is between -pi and pi for smallest turn
        if angle_difference > math.pi:
            angle_difference -= 2 * math.pi
        elif angle_difference < -math.pi:
            angle_difference += 2 * math.pi

        return angle_difference

    def update_angles(self, node):
        """ Returns the updated values of the requested angle (turn_to_angle)
            and current angle (current_angle) """

        turn_to_angle = angle_between_vectors(self.tank.body.position, node)
        if turn_to_angle < 0 or turn_to_angle > 2 * math.pi:
            turn_to_angle = periodic_difference_of_angles(turn_to_angle, 0)

        current_angle = self.tank.body.angle
        if current_angle < 0 or current_angle > 2 * math.pi:
            current_angle = periodic_difference_of_angles(current_angle, 0)

        return current_angle, turn_to_angle

    def accelerate(self, goto_node):
        """ Accelerate the tank """

        if self.correct_pos(goto_node):
            self.tank.stop_moving()
        else:
            self.tank.accelerate()

        current_angle, turn_to_angle = self.update_angles(goto_node)
        return current_angle, turn_to_angle

    def correct_pos(self, goto_node):
        """ Returns true if our position is sufficiently close
            to the center of a tile"""

        current_node = self.tank.body.position
        distance = current_node.get_distance(goto_node)

        if -0.1 <= distance <= 0.1:
            return True
        else:
            return False

    def correct_angle(self, angle, correct_angle):
        """ Returns true if angle and correct_angle are sufficiently close """

        bounds = correct_angle - MIN_ANGLE_DIF <= angle <= correct_angle + MIN_ANGLE_DIF
        return bounds

    def turn(self, current_angle, turn_to_angle, node):
        """ Turns the tank to the appropriate angle """

        if self.shortest_angle(current_angle, turn_to_angle) < 0:
            self.tank.turn_left()
        elif self.shortest_angle(current_angle, turn_to_angle) >= 0:
            self.tank.turn_right()

        if self.correct_angle(current_angle, turn_to_angle):
            self.tank.stop_turning()

        current_angle, turn_to_angle = self.update_angles(node)
        return current_angle, turn_to_angle

    def find_shortest_path(self, include_metal_box=False):
        """ A simple Breadth First Search using integer coordinates as our nodes.
            Edges are calculated as we go, using an external function.
        """

        shortest_path = []  # Shortest path. List of Vec2d items
        visited = set()     # Set of visited nodes
        parents = {}        # Dictionary to store paths to different nodes
        queue = deque()     # stores the different neighbors to a given node

        source_node = self.get_source_tile()

        queue.append(source_node)
        visited.add(source_node)

        while queue:
            # Takes out the first node in queue
            node = queue.popleft()

            # Checks if the tank reach the flag position, otherwise continues the search
            if node == self.get_target_tile():
                shortest_path.append(node)

                # Continues the search until it reaches the flag position
                while node != source_node:
                    node = parents[node]
                    shortest_path.append(node)

                # Reverses the path to find the shortest path from base to target
                shortest_path.reverse()

                break

            # Goes through every neighbor to a given node and append it to the parent dictionary
            for neighbor in self.get_tile_neighbors(node, include_metal_box):
                if neighbor not in visited:

                    queue.append(neighbor)
                    visited.add(neighbor)
                    parents[neighbor] = node

        return deque(shortest_path)

    def get_source_tile(self):
        """ Returns position of the flag if we have it. If we do not have the flag,
            returns the position of our home base"""

        if self.get_target_tile() == self.tank.start_position:
            x, y = self.flag.x, self.flag.y
        else:
            x, y = self.tank.body.position
        return Vec2d(x // 1 + 0.5, y // 1 + 0.5)

    def get_target_tile(self):
        """ Returns position of the flag if we don't have it. If we do have the flag,
            return the position of our home base.
        """

        if self.tank.flag is not None:
            x, y = self.tank.start_position
        else:
            self.get_flag()  # Ensure that we have initialized it.
            x, y = self.flag.x, self.flag.y
        return Vec2d(x // 1 + 0.5, y // 1 + 0.5)

    def get_flag(self):
        """ This has to be called to get the flag, since we don't know
            where it is when the Ai object is initialized.
        """

        if self.flag is None:
            # Find the flag in the game objects list
            for obj in self.game_objects_list:
                if isinstance(obj, gameobjects.Flag):
                    self.flag = obj
                    break
        return self.flag

    def get_tile_of_position(self, position_vector):
        """ Converts and returns the float position of our tank to an integer position. """
        x, y = position_vector
        return Vec2d(int(x), int(y))

    def get_tile_neighbors(self, coord_vec, include_metal_box):
        """ Returns all bordering grid squares of the input coordinate.
            A bordering square is only considered accessible if it is grass
            or a wooden box.
        """

        neighbors = []              # Find the coordinates of the tiles' four neighbors
        available_neighbors = []    # Filter out the available neighbours a tank can get to

        neighbors.append(coord_vec + Vec2d(0, 1))
        neighbors.append(coord_vec + Vec2d(1, 0))
        neighbors.append(coord_vec + Vec2d(0, -1))
        neighbors.append(coord_vec + Vec2d(-1, 0))

        width = self.currentmap.width
        height = self.currentmap.height

        # Appends to available_neighbours if a neighbour is accessible
        for i in range(len(neighbors)):
            x, y = neighbors[i][0], neighbors[i][1]

            # Last statement is dependant on if we want to include metal boxes as accessible tiles or not
            if (0 <= x <= width and 0 <= y <= height) and ((self.currentmap.boxAt(int(x // 1), int(y // 1)) in [0, 2])
                                                           if not include_metal_box else
                                                           (self.currentmap.boxAt(int(x // 1), int(y // 1)) in [0, 2, 3])):
                available_neighbors.append(neighbors[i])

        return available_neighbors

    def filter_tile_neighbors(self, coord):
        """ Used to filter the tile to check if it is a neighbor of the tank.
        """
        return

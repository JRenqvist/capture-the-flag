import pygame


def image_dimensions(file_path):
    """ Returns the width and height of given image """
    with open(file_path, 'rb') as img_file:
        img_file.seek(0)
        img_file.seek(16)

        width_bytes = img_file.read(4)
        height_bytes = img_file.read(4)
        width = int.from_bytes(width_bytes, byteorder='big')
        height = int.from_bytes(height_bytes, byteorder='big')
        return width, height


def disp_manual(file_path):
    """ Shows the user manual at the start of the game """

    x, y = image_dimensions(file_path)

    screen = pygame.display.set_mode((x, y))

    pygame.display.set_caption("Manual")

    image = pygame.image.load(file_path).convert()
    screen.blit(image, (0, 0))

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        pygame.display.flip()

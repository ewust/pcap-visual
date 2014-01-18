#!/usr/bin/python

import sys
import pygame
import math
pygame.init()




class Arrow(object):
    color = [255, 255, 255]
    def __init__(self, direction, start_time, end_time, above_text=None, start_text=None, end_text=None, below_text=None):
        self.direction = direction
        self.start = start_time
        self.end = end_time
        self.start_text = start_text
        self.end_text = end_text
        self.above_text = above_text
        self.below_text = below_text

def get_norm_slope(start, end):
    rise = float(end[1]-start[1])
    run = float(end[0]-start[0])
    #print '%f - %f = rise: %f, run: %f' % (start[1], end[1], rise, run)
    if run != 0:
        rise_n = (rise/abs(run)) #if run < 0 else (rise/run)
        run_n = run/abs(run) #-1 if (run < 0 and rise > 0) else 1
    else:
        # TODO:
        rise_n = -1 if rise < 0 else 1
        run_n = 0
    return (rise_n, run_n)


class Display(object):
    def __init__(self, w=1024, h=740, max_time=1.000):
        self.w = w
        self.h = h
        self.max_time = max_time
        self.window = pygame.display.set_mode((self.w, self.h))
        self.arrows = []

    def add_arrow(self, arrow):
        self.arrows.append(arrow)


    def render(self):
        # our playing field is going to be W-200, H-100
        # so time*(H-100)/max_time gives px height for each arrow
        self.window.fill([0, 0, 0])

        px_per_time = (self.h - 100) / self.max_time
        for arrow in self.arrows:
            start = [100 if arrow.direction else self.w - 100, arrow.start * px_per_time + 100]
            end = [self.w - 100 if arrow.direction else 100, arrow.end * px_per_time + 100]

            rise, run = get_norm_slope(start, end)

            x = end[0]
            y = end[1]
            rise *= 10
            run *= 10
            endcap_pts = [[x+rise, y-run], [x-rise, y+run], [x+2*run, y+2*rise]]


            print '\'%s\': rise: %f, run: %f; -- x: %f, y: %f' % (arrow.above_text, rise, run, x, y)

            pygame.draw.aaline(self.window, Arrow.color, start, end, True)
            # triangle endcap
            pygame.draw.aalines(self.window, Arrow.color, True, endcap_pts, True)

            # render above text
            text = arrow.above_text
            font = pygame.font.Font(None, 30)
            text_img = font.render(text, 1, (255, 0, 0))
            if run == 0:
                text_img = pygame.transform.rotate(text_img, 90)
            elif arrow.direction:
                text_img = pygame.transform.rotate(text_img, -(180.0/math.pi)*math.atan2(rise,run))
            else:
                text_img = pygame.transform.rotate(text_img, (180.0/math.pi)*math.atan2(rise,-run))

            run /= 10.0
            rise /= 10.0
            shift_w = (self.w - 200.0 - font.size(text)[0]) / 2.0
            x = (start[0] + end[0])/ 2.0
            y = (start[1] + end[1])/ 2.0

            if not(arrow.direction):
                # subtract off the lip if we rotated text to the left (upper left corner is not upper left corner of text)
                y -= (text_img.get_height() - font.size(text)[1])

            x -= (font.size(text)[0]/2.0)
            y -= (font.size(text)[0]/2.0)*rise*run
            # place above
            #x += (font.size(text)[1])*abs(run)
            #y -= (font.size(text)[1])

            shift_x = font.size(text)[1]*rise
            shift_y = font.size(text)[1]*run
            if not(arrow.direction):
                shift_y = -shift_y
                shift_x = -shift_x
                pass
            #pygame.draw.aaline(self.window, Arrow.color, [x,y], [x+shift_x, y-shift_y], True)
            x += shift_x
            y -= shift_y

            self.window.blit(text_img, [x, y])


        pygame.display.flip()



d = Display()
a = Arrow(1, 0.000, 0.080)
d.add_arrow(Arrow(1, 0.000, 0.080, "SYN"))
d.add_arrow(Arrow(0, 0.100, 0.185, "SYN+ACK"))
d.add_arrow(Arrow(0, 0.4, 0.8, "Moooo"))
d.add_arrow(Arrow(1, 0.210, 0.275, "ACK"))
d.add_arrow(Arrow(1, 0.3, 0.8, "Wooooooooooooooooooooo"))

d.add_arrow(Arrow(0, 0.9, 0.9, "Hi"))
d.add_arrow(Arrow(1, 0.95, 0.95, "Hello"))
d.render()




clock = pygame.time.Clock()


#input handling (somewhat boilerplate code):
while True:
    clock.tick(10)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit(0)
        else:
            #print event
            pass


import sys, pygame, json, configparser
from copy import deepcopy
from genericpath import exists
from time import time
from matplotlib.colors import to_rgb
from calc_batting import get_bat_hitbox, get_name, hit_ball, get_hitbox, get_box_movement
from pygame import Rect, Vector2, Vector3
from memory_engine import *
from visualizer import canvas

class DisplayableInfo:
    def __init__(self, data) -> None:
        self.data = data
        self.valid = True
        self.time_created = time()
    
    def get_alpha_from_fade(self, now_time:float, delay:float, fade_duration:float) -> float:
        MAX_ALPHA = 255
        
        if fade_duration == 0.0:
            if now_time < delay:
                return 0.0
            else: 
                return MAX_ALPHA

        fade = (now_time - delay) / fade_duration
        alpha = min(max(0.0, fade), 1.0) * MAX_ALPHA
        return alpha

    def draw_detailed_text(self, m_surface:pygame.Surface):
        global force_hit
        data = self.data["t"]
        # data = last_hit_value["t"]
        
        if force_hit:
            data = ["FORCING"] + data

        width, height = m_surface.get_width(), m_surface.get_height()
        my_square = get_inscribed_square_rect(0, 0, width, height)
        # m_surface = get_my_surface(x,y, width, height)

        num_lines = sum([len(d.splitlines()) for d in data])

        font = pygame.font.SysFont(get_config_value("GRAPHICS", "font", str), int(my_square.height // (max(num_lines, 1))))
        font_height = font.get_height() * 1.2
        offset = font_height * 1.0
        text_y = offset

        for xx, d in enumerate(data):
            for yy, l in enumerate(d.splitlines()):
                text = font.render(f" {l} ", True, get_config_color("text_color"), get_config_color("text_outline"))
                
                text_rect = text.get_rect()
                text_rect.left = 0
                text_rect.y = text_y

                m_surface.blit(text, text_rect)
                text_y += font_height
            text_y += font_height

class DisplayHitView(DisplayableInfo):
    def __init__(self, data) -> None:
        super().__init__(data)
        self.horizontal_delay = get_config_value("VISUAL_TOGGLES", "horizontal_fade_delay", float)
        self.horizontal_fade  = get_config_value("VISUAL_TOGGLES", "horizontal_fade_in_timer", float)
        
        self.vertical_delay = get_config_value("VISUAL_TOGGLES", "vertical_fade_delay", float)
        self.vertical_fade  = get_config_value("VISUAL_TOGGLES", "vertical_fade_in_timer", float)
        
    
    def draw(self):
        self.draw_vertical_trajectory(get_sub_screen(get_config_value("VISUAL_TOGGLES", "vertical_path_screen")))
        self.draw_horizontal_trajectory(get_sub_screen(get_config_value("VISUAL_TOGGLES", "horizontal_path_screen")))
        self.draw_detailed_text(get_sub_screen(get_config_value("VISUAL_TOGGLES", "text_screen")))
    
    def is_valid(self) -> bool:
        if not self.valid:
            return False

        is_replay =         DolphinBool(0x80872540)
        game_state =        DolphinByte(0x80892aaa)
        was_contact_made =  DolphinBool(0x808909a1)

        self.valid &= not is_replay.live_value
        self.valid &= game_state.live_value in [0x1, 0x2]
        self.valid &= was_contact_made.live_value
        return self.valid

    def draw_horizontal_trajectory(self, m_surface:pygame.Surface):
        # data = last_hit_value["v"]
        data = self.data["v"]

        alpha = 255
        if self.valid:
            now_time = time() - self.time_created
            delay = self.horizontal_delay
            duration = self.horizontal_fade
            alpha = self.get_alpha_from_fade(now_time, delay, duration)

        original_surface = m_surface
        m_surface = pygame.Surface(m_surface.get_size(), pygame.SRCALPHA)

        m_width, m_height = m_surface.get_width(), m_surface.get_height()
        my_square = get_inscribed_square_rect(0, 0, m_width, m_height)
        # m_surface = get_my_surface(my_square.left, my_square.top, my_square.width, my_square.height)

        corner = Vector2(0.5, -0.05)
        right_post = Vector3(57.0, 0.0, 57.0)
        left_post = Vector3(-57.0, 0.0, 57.0)
        left_part = Vector3(-41.5, 0.0, 82.5)
        middle_part = Vector3(-13.0, 0.0, 100.0)
        right_part = Vector3(16.0, 0.0, 100.0)
        
        scale = 1 / 120.0

        def unNormalize(p):
            p1 = Vector2(p[0], 1.0 - p[1]) + corner
            return Vector2(p1.x * my_square.width, p1.y* my_square.height)

        def coord_to_normal(p: Vector3)-> Vector2:
            p2 = Vector2( p.x, p.z )
            p2 *= scale
            return p2

        def plot_point(p:Vector3):
            return unNormalize(coord_to_normal(p))

        stadium_color = (*get_config_color("stadium_line"), alpha)
        line_color = (*get_config_color("ball_trajectory"), alpha)
        line_outline_color = (*get_config_color("ball_trajectory_outline"), alpha)

        pygame.draw.polygon(m_surface, stadium_color, [ plot_point(Vector3(0,0,0)), plot_point(left_post), plot_point(left_part), plot_point(middle_part), plot_point(right_part), plot_point(right_post)], width=LINE_WIDTH)


        if get_config_value("VISUAL_TOGGLES", "display_bases", bool):
            pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(19, 0,19)), LINE_WIDTH)
            pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(-19,0, 19)), LINE_WIDTH)
            pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(0, 0, 38)), LINE_WIDTH)
            pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(0, 0, 19)), int(LINE_WIDTH // 1.5))

        # draw extra trajectories
        if get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_horizontal", bool):
            for e in self.data["e"]:
                new_points = []
                for p in e["FlightDetails"]["Path"]:
                    new_points.append(Vector3(p["X"], p["Y"], p["Z"]))
                
                for i in range(len(new_points) - 1):
                    pygame.draw.line(m_surface, line_outline_color, plot_point(new_points[i]), plot_point(new_points[i+1]), width=ADDITIONAL_TRAJ_LINE_OUTLINE)
                for i in range(len(new_points) - 1):
                    pygame.draw.line(m_surface, line_color, plot_point(new_points[i]), plot_point(new_points[i+1]), width=ADDITIONAL_TRAJ_LINE_WIDTH)

        new_points = []
        for p in data["FlightDetails"]["Path"]:
            new_points.append(Vector3(p["X"], p["Y"], p["Z"]))
            
        for i in range(len(new_points) - 1):
            pygame.draw.line(m_surface, line_outline_color, plot_point(new_points[i]), plot_point(new_points[i+1]), width=BOLD_LINE_WIDTH)
        for i in range(len(new_points) - 1):
            pygame.draw.line(m_surface, line_color, plot_point(new_points[i]), plot_point(new_points[i+1]), width=LINE_WIDTH)  
        
        original_surface.blit(m_surface, (0,0))



    def draw_vertical_trajectory(self, m_surface:pygame.Surface):
        alpha = 255
        if self.valid:
            now_time = time() - self.time_created
            delay = self.vertical_fade
            duration = self.vertical_delay
            alpha = self.get_alpha_from_fade(now_time, delay, duration)

        # data = last_hit_value["v"]
        original_surface = m_surface
        m_surface = pygame.Surface(original_surface.get_size(), pygame.SRCALPHA)

        data = self.data["v"]
        m_width, m_height = m_surface.get_width(), m_surface.get_height()

        my_square = get_inscribed_square_rect(0, 0, m_width, m_height)
        # m_surface = get_my_surface(my_square.left, my_square.top, my_square.width, my_square.height)

        scale = 1 / 120.0

        corner = Vector2(0.1, -0.1)
        def unNormalize(p):
            p1 = Vector2(p[0], 1.0 - p[1]) + corner
            return Vector2(p1.x * my_square.width, p1.y* my_square.height)

        def coord_to_normal(p: Vector3)-> Vector2:
            p2 = Vector2( p.zx.length(), p.y )
            p2 *= scale
            return p2

        def plot_point(p:Vector3):
            return unNormalize(coord_to_normal(p))

        top_post = plot_point(Vector3(0.0, 100.0, 0.0)) 
        right_post = plot_point(Vector3(100.0, 0.0, 0.0))
        corner_post = plot_point(Vector3(0.0, 0.0, 0.0))

        stadium_color = (*get_config_color("stadium_line"), alpha)
        line_color = (*get_config_color("ball_trajectory"), alpha)
        line_outline_color = (*get_config_color("ball_trajectory_outline"), alpha)

        pygame.draw.line(m_surface, stadium_color, corner_post, right_post, width=LINE_WIDTH)
        pygame.draw.line(m_surface, stadium_color, corner_post, top_post, width=LINE_WIDTH)

        if get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_vertical", bool):
            for e in self.data["e"]:
                new_points = []
                for p in e["FlightDetails"]["Path"]:
                    new_points.append(plot_point(Vector3(p["X"], p["Y"], p["Z"])))
                
                for i in range(len(new_points) - 1):
                    pygame.draw.line(m_surface, line_outline_color, new_points[i], new_points[i+1], width=ADDITIONAL_TRAJ_LINE_OUTLINE)
                for i in range(len(new_points) - 1):
                    pygame.draw.line(m_surface, line_color, new_points[i], new_points[i+1], width=ADDITIONAL_TRAJ_LINE_WIDTH)
        
        new_points = []
        for p in data["FlightDetails"]["Path"]:
            new_points.append(plot_point(Vector3(p["X"], p["Y"], p["Z"])))
        
        for i in range(len(new_points) - 1):
            pygame.draw.line(m_surface, line_outline_color, new_points[i], new_points[i+1], width=BOLD_LINE_WIDTH)
        for i in range(len(new_points) - 1):
            pygame.draw.line(m_surface, line_color, new_points[i], new_points[i+1], width=LINE_WIDTH)

        original_surface.blit(m_surface, (0,0))
    

class DisplayStrikeView(DisplayableInfo):
    def __init__(self, data) -> None:
        super().__init__(data)
        self.strike_delay = get_config_value("VISUAL_TOGGLES", "strike_fade_delay", float)
        self.strike_fade = get_config_value("VISUAL_TOGGLES", "strike_fade_in_timer", float)

    def draw(self):
        self.draw_strike_view(get_sub_screen(get_config_value("VISUAL_TOGGLES", "plate_screen")))
        self.draw_detailed_text(get_sub_screen(get_config_value("VISUAL_TOGGLES", "text_screen")))

    def is_valid(self) -> bool:
        if not self.valid:
            return False

        is_replay    =       DolphinBool(0x80872540)
        game_state   =       DolphinByte(0x80892aaa)
        missed_ball  =       DolphinBool(0x80890b18)
        hit_by_pitch =       DolphinBool(0x808909a3)

        self.valid &= not is_replay.live_value
        self.valid &= game_state.live_value in [0x1]
        self.valid &= (missed_ball.live_value or hit_by_pitch.live_value)
        return self.valid

    def draw_strike_view(self, my_surface:pygame.Surface):
        alpha = 255
        if self.valid:
            now_time = time() - self.time_created
            delay = self.strike_delay
            duration = self.strike_fade
            alpha = self.get_alpha_from_fade(now_time, delay, duration)
        
        v_m = mat([
            [-1.0, 0.0, -4.371138828673793e-08, -4.6246648821579583e-07], 
            [1.1962544732568858e-08, 0.8923089504241943, -0.27367112040519714, 2.4584131240844727], 
            [4.17900665183879e-08, -0.29321905970573425, -0.9560452699661255, -11.874273300170898], 
            [0.0, 0.0, 0.0, 1.0]])

        p_m = mat([
            [-2.5199999809265137, 0.0, -0.0, 0.0], 
            [0.0, -3.5999999046325684, -0.0, 0.0], 
            [0.0, 0.0, -0.001956947147846222, -1.0019569396972656], 
            [0.0, 0.0, -1.0, 0]])

        my_square = get_inscribed_screen(0, 0, my_surface.get_width(), my_surface.get_height())

        c = canvas(pygame.Surface(my_square.size, pygame.SRCALPHA))

        original_screen = my_surface
        # screen = pygame.Surface(original_screen)

        c.set_projection(p_m)
        c.set_view(v_m)
        
        # my_surface.fill((255, 0, 0), my_surface.get_rect())
        c.screen.fill(get_config_color("background"))

        # colors 
        strike_zone_color =     (*get_config_color("strike_zone"), alpha)
        player_hitbox_color =   (*get_config_color("player_hitbox"), alpha)
        player_pos_color =      (*get_config_color("player_position"), alpha)
        bat_hitbox_color =      (*get_config_color("bat_hitbox"), alpha)
        player_movement_color = (*get_config_color("player_movement_box"), alpha)
        ball_color =            (*get_config_color("ball"), alpha)

        ball_radius = get_config_value("VISUAL_TOGGLES", "ball_radius", float)

        # draw strikezone
        strike_zone_bottom = 0.5
        strike_zone_top = 1.5
        strike_zone_left = -0.54
        strike_zone_right = 0.54

        if get_config_value("VISUAL_TOGGLES", "edge_of_ball_counts_as_strike", bool):
            strike_zone_left += ball_radius
            strike_zone_right -= ball_radius


        box = [Vector3(strike_zone_left, strike_zone_bottom, 0.0), Vector3(strike_zone_left, strike_zone_top, 0.0), Vector3(strike_zone_right, strike_zone_top, 0.0), Vector3(strike_zone_right, strike_zone_bottom, 0.0)]
        left_post = [Vector3(strike_zone_left, 0.0, 0.0), Vector3(strike_zone_left, strike_zone_bottom, 0.0)]
        right_post = [Vector3(strike_zone_right, 0.0, 0.0), Vector3(strike_zone_right, strike_zone_bottom, 0.0)]

        # read values
        vals = self.data["read_values"]
        bat_p = Vector3(vals["batter_x"], vals["strike_y"], 0.0)
        batter_id = vals["batter_id"]
        batter_p = Vector3(vals["model_x"], 0.0, vals["model_z"])
        handedness = vals["handedness"]
        
        strike_p = Vector3(vals["strike_x"], vals["strike_y"], 0.0)
        if vals["hit_by_pitch"]:
            strike_p.z = batter_p.z

        hbox_bat = get_bat_hitbox(batter_id, bat_p.x, handedness)
        hbox_batter = get_hitbox(batter_id)

        batter_width =          hbox_batter[0] / 100
        batter_hitbox_near =    hbox_batter[1] / 100
        batter_hitbox_far =     hbox_batter[2] / 100

        if handedness == 0:
            batter_hitbox_near = batter_hitbox_near
            batter_hitbox_far = -batter_hitbox_far
        else:
            batter_hitbox_near = -batter_hitbox_near
            batter_hitbox_far = batter_hitbox_far

        batter_hitbox_height = 2.0

        if handedness == 1:
            bat_p.x *= -1

        hitbox1_scale_x = abs(hbox_bat[0] - bat_p.x)
        hitbox2_scale_x = abs(hbox_bat[1] - bat_p.x)
        hitbox_scale_y = 0.3
        hitbox_scale_z = 0.3
        hitbox_1_scaling = Vector3(hitbox1_scale_x, hitbox_scale_y, 0.0)
        hitbox_2_scaling = Vector3(hitbox2_scale_x, hitbox_scale_y, 0.0)
        if handedness == 1:
            hitbox1_offset = Vector3(hitbox1_scale_x*0.5, 0, 0)
            hitbox2_offset = Vector3(-hitbox2_scale_x*0.5, 0, 0)
        else:
            hitbox1_offset = Vector3(-hitbox1_scale_x*0.5, 0, 0)
            hitbox2_offset = Vector3(hitbox2_scale_x*0.5, 0, 0)


        box_movement = get_box_movement(batter_id)

        offset_x = box_movement["EasyBattingSpotHorizontal"]
        offset_z = box_movement["EasyBattingSpotVertical"]

        box_offset = Vector3(offset_x, 0.0, offset_z)

        m_near = box_movement["HorizontalRangeNear"]
        m_far = box_movement["HorizontalRangeFar"]
        m_front = box_movement["VerticalRangeFront"]
        m_back = box_movement["VerticalRangeBack"]


        if handedness == 1:
            m_near *= -1
            m_far *= -1
            box_offset = box_offset.elementwise() * Vector3(-1, 1, 1).elementwise()

        movement_points = [
            Vector3(m_near, 0.0, m_front)+ box_offset, 
            Vector3(m_far, 0.0, m_front) + box_offset, 
            Vector3(m_far, 0.0, m_back)+ box_offset, 
            Vector3(m_near, 0.0, m_back)+ box_offset
            ]

        # draw batter movement
        if get_config_value("VISUAL_TOGGLES", "display_player_movement", bool):
            c.draw_lines(movement_points, closed=True, color=player_movement_color, line_width=HITBOX_LINE_WIDTH)

        #draw hitbox
        if get_config_value("VISUAL_TOGGLES", "display_player_hitbox", bool):
            
            #draw batter
            c.draw_cube(batter_p, scale=Vector3(batter_hitbox_near, batter_hitbox_height, 0.0), offset=Vector3(
                batter_hitbox_near*0.5, batter_hitbox_height*0.5, -batter_p.z), color=player_hitbox_color, line_width=HITBOX_LINE_WIDTH)        
            c.draw_cube(batter_p, scale=Vector3(batter_hitbox_far, batter_hitbox_height, 0.0), offset=Vector3(
                batter_hitbox_far*0.5, batter_hitbox_height*0.5, -batter_p.z), color=player_hitbox_color, line_width=HITBOX_LINE_WIDTH)
        
            # draw player position
            c.draw_point(batter_p, color=player_pos_color, line_width=HITBOX_LINE_WIDTH)

        #draw strike zone
        if get_config_value("VISUAL_TOGGLES", "display_strike_zone", bool):
            # draw strike zone 
            c.draw_lines(box, strike_zone_color, line_width=HITBOX_LINE_WIDTH, closed=True)
            # screen.draw_lines(left_post, strike_zone_color, line_width=HITBOX_LINE_WIDTH)
            # screen.draw_lines(right_post, strike_zone_color, line_width=HITBOX_LINE_WIDTH)

        #draw bat
        if get_config_value("VISUAL_TOGGLES", "display_bat_hitbox", bool):            
            # draw bat
            c.draw_cube(bat_p, scale=hitbox_1_scaling, offset=hitbox1_offset, color=bat_hitbox_color, line_width=HITBOX_LINE_WIDTH)
            c.draw_cube(bat_p, scale=hitbox_2_scaling, offset=hitbox2_offset, color=bat_hitbox_color, line_width=HITBOX_LINE_WIDTH)
        
        #draw ball
        if get_config_value("VISUAL_TOGGLES", "display_ball_hitbox", bool):
            # draw ball
            # screen.draw_point(strike_p, color=get_config_color("ball"), line_width=HITBOX_LINE_WIDTH)
            c.draw_sphere(strike_p, radius=ball_radius, color=ball_color, line_width=2)

        original_screen.blit(c.screen, my_square)
        

def get_config_value(section:str, v:str, type=None):
    if section in config.sections():
        if v in config[section]:
            if type == bool:
                return config[section].getboolean(v)
            if type == int:
                return config[section].getint(v)
            if type == float:
                return config[section].getfloat(v)
            if type == "color":
                return get_config_color(config[section])

            return config[section][v]
    
    return None

def get_config_color(name) -> Vector3:
    rgb = to_rgb(config["COLORS"][name])
    return Vector3(*rgb) * 255

def optional_text(s:str, b:bool): return s if b else ""

def blit_text(surface, text, pos, font) -> None:
    words = [word.split(' ') for word in text.splitlines()]  # 2D array where each row is a list of words.
    space = font.size(' ')[0]  # The width of a space.
    max_width, max_height = surface.get_size()
    x, y = pos
    for line in words:
        for word in line:
            word_surface = font.render(word, 0, get_config_color("text_color"), get_config_color("text_outline"))
            word_width, word_height = word_surface.get_size()
            if x + word_width >= max_width:
                x = pos[0]  # Reset the x.
                y += word_height  # Start on new row.
            surface.blit(word_surface, (x, y))
            x += word_width + space
        x = pos[0]  # Reset the x.
        y += word_height  # Start on new row.

def get_game_state_text() -> str:
    this_missed_ball = read_values['missed_ball']
    these_strikes = read_values['strikes']
    these_balls = read_values['balls']
    this_hit_by_pitch = read_values['hit_by_pitch']
    this_is_strike = read_values["is_strike"]

    if not this_hit_by_pitch and this_missed_ball:
        if this_is_strike:
            these_strikes -= 1
        else:
            these_balls -= 1

    runners_text = ""
    runners_value = read_values["where_are_runners"] >> 4
    if(runners_value) > 0:
        runners_text = "Runners on "
        runners_ord = []
        if runners_value & 0x1 != 0:
            runners_ord.append(ordinal(1))
        if runners_value & 0x10 != 0:
            runners_ord.append(ordinal(2))
        if runners_value & 0x100 != 0:
            runners_ord.append(ordinal(3))
        runners_text += ", ".join(runners_ord) + "\n"

    return (
          optional_text(f"{'Top of the' if read_values['inning_half'] == 0 else 'Bottom of the'} {ordinal(read_values['inning'])}\n",                                get_config_value("TEXT_TOGGLES", "display_inning_text", bool))
        + optional_text(f"{get_config_value('TEXT_TOGGLES', 'display_home_name', str)}: {read_values['home_score']}, {get_config_value('TEXT_TOGGLES', 'display_away_name',str)}: {read_values['away_score']}\n",       get_config_value("TEXT_TOGGLES", "display_score_text", bool))
        + optional_text(f"Stars: {get_config_value('TEXT_TOGGLES', 'display_home_name')}: {read_values['home_stars']}, {get_config_value('TEXT_TOGGLES', 'display_away_name')}: {read_values['away_stars']}\n",get_config_value("TEXT_TOGGLES", "display_star_count_text", bool))
        + optional_text(f"{these_balls}-{these_strikes}, {read_values['outs']} {'Out' if read_values['outs'] == 1 else 'Outs'}\n",                                   get_config_value("TEXT_TOGGLES", "display_count_text", bool))
        + optional_text(f"{runners_text}",                                                                                                                           get_config_value("TEXT_TOGGLES", "display_runners_text", bool))
        + optional_text(f"Pitcher: {get_name(read_values['pitcher_id'])}\n",                                                                                         get_config_value("TEXT_TOGGLES", "display_pitcher_text", bool))  
        + optional_text(f"Batter: {get_name(read_values['batter_id'])}\n",                                                                                           get_config_value("TEXT_TOGGLES", "display_batter_text", bool))
    )

CALCULATE_ADDRESSES = {
    "game_id": DolphinWord(0x802EBF8C),

    "batter_id": DolphinHalfWord(0x80890972),
    "pitcher_id": DolphinHalfWord(0x80890ADA),

    "easy_batting": DolphinByte(0x8089098A),
    "handedness": DolphinByte(0x8089098B),

    "batter_x": DolphinFloat(0x8089095C),
    "batter_y": DolphinFloat(0x80890960),
    "batter_z": DolphinFloat(0x80890964),

    "model_x": DolphinFloat(0x80890910),
    "model_z": DolphinFloat(0x80890914),

    "ball_x": DolphinFloat(0x80890934),
    "ball_y": DolphinFloat(0x80890938),
    "ball_z": DolphinFloat(0x8089093C),

    "chem": DolphinByte(0x808909ba),

    "slap_or_charge": DolphinByte(0x8089099b),
    "is_hit_star": DolphinByte(0x808909b1),

    "pitch_1": DolphinByte(0x80890b21),
    "pitch_2": DolphinByte(0x80890b1f),

    "charge_up": DolphinFloat(0x80890968),
    "charge_down": DolphinFloat(0x8089096C),

    "frame": DolphinHalfWord(0x80890976),

    "rand_1": DolphinHalfWord(0x802ec010),
    "rand_2": DolphinHalfWord(0x802ec012),
    "rand_3": DolphinHalfWord(0x802ec014),

    # extra things to read

    "team_batting": DolphinWord(0x80892990),
    "team_pitching": DolphinWord(0x80892994),

    "port_home": DolphinWord(0x80892a78),
    "port_away": DolphinWord(0x80892a7c),

    "stars_home": DolphinByte(0x80892ad6),
    "stars_away": DolphinByte(0x80892ad7),

    "p1_input": DolphinHalfWord(0x8089392c),
    "p2_input": DolphinHalfWord(0x8089393c),
    "p3_input": DolphinHalfWord(0x8089394c),
    "p4_input": DolphinHalfWord(0x8089395c),

    "strike_x": DolphinFloat(0x80890A14),
    "strike_y": DolphinFloat(0x80890A18),

    "strike_left_side": DolphinFloat(0x80890a3c),
    "strike_right_side": DolphinFloat(0x80890a40),

    "swung" : DolphinBool(0x808909A9),
    "is_strike": DolphinBool(0x80890b17),

    "inning": DolphinWord(0x808928a0),
    "inning_half": DolphinBool(0x8089294d),

    "strikes": DolphinWord(0x80892968),
    "balls": DolphinWord(0x8089296c),
    "outs": DolphinWord(0x80892970),

    "where_are_runners" : DolphinHalfWord(0x80892734),

    "home_score":DolphinHalfWord(0x808928a4),
    "away_score":DolphinHalfWord(0x808928ca),

    "home_stars":DolphinByte(0x80892ad6),
    "away_stars":DolphinByte(0x80892ad7),
}

EVERY_FRAME_ADDRESSES = {
    "was_contact_made": DolphinBool(0x808909a1),
    "missed_ball": DolphinBool(0x80890b18),
    "hit_by_pitch": DolphinBool(0x808909a3),
    "is_replay": DolphinBool(0x80872540),
    "gamestate" : DolphinByte(0x80892aaa)
}

def missed_ball():

    res = {
        "handedness":read_values["handedness"],
        "model_x": read_values["model_x"],

        "strike_x": read_values["strike_x"],
        "strike_y": read_values["strike_y"],

        "batter_x": read_values["batter_x"],

        "strike_range_left" : read_values["strike_left_side"],
        "strike_range_right" : read_values["strike_right_side"],

        "hitbox" : get_hitbox(read_values["batter_id"])
    }

    if res["handedness"] == 0:
        hitbox_left = res["model_x"] - (res["hitbox"][2] / 100) 
        hitbox_right = res["model_x"] + (res["hitbox"][1] / 100)
    else:
        hitbox_left = res["model_x"] - (res["hitbox"][1] / 100)
        hitbox_right = res["model_x"] + (res["hitbox"][2] / 100)

    hitbox_near, hitbox_far = get_bat_hitbox(read_values["batter_id"], read_values["batter_x"], read_values["handedness"])

    res["hitbox_near"] = hitbox_near
    res["hitbox_far"] = hitbox_far

    these_strikes = read_values['strikes']
    these_balls = read_values['balls']
    this_hit_by_pitch = read_values['hit_by_pitch']
    this_is_strike = read_values["is_strike"]

    if not this_hit_by_pitch:
        if this_is_strike:
            these_strikes -= 1
        else:
            these_balls -= 1

    result_text = "Result: "

    if this_hit_by_pitch:
        result_text += "Hit By Pitch"
    elif this_is_strike:
        result_text += "Strike"
    else:
        result_text += "Ball"

    runners_text = ""
    runners_value = read_values["where_are_runners"] >> 4
    if(runners_value) > 0:
        runners_text = "Runners on "
        runners_ord = []
        if runners_value & 0x1 != 0:
            runners_ord.append(ordinal(1))
        if runners_value & 0x10 != 0:
            runners_ord.append(ordinal(2))
        if runners_value & 0x100 != 0:
            runners_ord.append(ordinal(3))
        runners_text += ", ".join(runners_ord) + "\n"

    pitch_type = "Curve"
    if read_values["pitch_1"] == 1 and read_values["pitch_2"] == 2:
        pitch_type = "Charge"
    elif read_values["pitch_1"] == 1 and read_values["pitch_2"] == 3:
        pitch_type = "Perfect Charge"
    elif read_values["pitch_1"] == 2 and read_values["pitch_2"] == 0:
        pitch_type = "Change Up"



    bat_distance = min(abs(hitbox_near - res["strike_x"]), abs(hitbox_far - res["strike_x"]))
    
    text = [
        get_game_state_text(),

          optional_text(f"Ball (x,y): ({res['strike_x']:.2f}, {res['strike_y']:.2f})\n",                            get_config_value("TEXT_TOGGLES", "display_ball_coordinate_text", bool))
        + optional_text(f"Batter Hitbox: {hitbox_left:.2f} to {hitbox_right:.2f}\n",                                get_config_value("TEXT_TOGGLES", "display_batter_hitbox_text", bool))
        + optional_text(f"Bat Hitbox: {min(hitbox_near, hitbox_far):.2f} to {max(hitbox_near, hitbox_far):.2f}\n",  get_config_value("TEXT_TOGGLES", "display_bat_hitbox_text", bool))
        + optional_text(f"Distance To Edge Of Bat: {bat_distance:.2f}\n",                                           get_config_value("TEXT_TOGGLES", "display_distance_from_bat", bool))
        + optional_text(f"Strike Box: {res['strike_range_left']:.2f} to {res['strike_range_right']:.2f}\n",         get_config_value("TEXT_TOGGLES", "display_strike_zone_text", bool))
        + optional_text(f"Pitch Type: {pitch_type}\n",                                                              get_config_value("TEXT_TOGGLES", "display_pitch_type_text", bool))
        + optional_text('Swung\n',                                                                                  get_config_value("TEXT_TOGGLES", "display_if_swung_text", bool) and read_values['swung'])
        + optional_text(f"{result_text}\n",                                                                         get_config_value("TEXT_TOGGLES", "display_batting_result_ball_strike_hbp", bool))
    ]

    global all_events
    all_events.append(DisplayStrikeView({"k": "StrikeBall", "v": res, "t": text, "read_values":deepcopy(read_values)}))

def ordinal(n):
    return "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])

def calculate_trajectory():
    global force_hit
    if force_hit:
        ball_pos = last_hit_value.data["v"]["FlightDetails"]["Path"][0]
        ball_acc = last_hit_value.data["v"]["BallDetails"]["Acceleration"]
        ball_vel = last_hit_value.data["v"]["BallDetails"]["Velocity"]
        write_vec3(0x80890b38, Vector3(ball_pos["X"], ball_pos["Y"], ball_pos["Z"]))
        write_vec3(0x80890e50, Vector3(ball_vel["X"], ball_vel["Y"], ball_vel["Z"]))
        write_vec3(0x80890e5c, Vector3(ball_acc["X"], ball_acc["Y"], ball_acc["Z"]))
        return

    team_batting = read_values["team_batting"]
    
    num_stars = [read_values["stars_home"],
                    read_values["stars_away"]][team_batting]

    port = [read_values["port_home"], read_values["port_away"]][team_batting]

    all_input = [read_values["p1_input"], read_values["p2_input"], read_values["p3_input"], read_values["p4_input"]]

    batting_input = all_input[port]
    
    stick_left =    (batting_input & 1) != 0
    stick_right =   (batting_input & 2) != 0
    stick_down =    (batting_input & 4) != 0
    stick_up =      (batting_input & 8) != 0

    pitch_type = 0

    if read_values["pitch_1"] == 1 and read_values["pitch_2"] == 2:
        pitch_type = 1
    elif read_values["pitch_1"] == 1 and read_values["pitch_2"] == 3:
        pitch_type = 2
    elif read_values["pitch_1"] == 2 and read_values["pitch_2"] == 0:
        pitch_type = 3

    is_starred = get_config_value("USAGE", "is_starred", bool)

    read_values["pitch_type"] = pitch_type

    read_values["stick_up"] = stick_up
    read_values["stick_down"] = stick_down
    read_values["stick_left"] = stick_left
    read_values["stick_right"] = stick_right

    read_values["num_stars"] = num_stars

    res = hit_ball(
        batter_id=read_values["batter_id"],
        pitcher_id=read_values["pitcher_id"],
        easy_batting=read_values["easy_batting"],
        handedness=read_values["handedness"],
        batter_x=read_values["batter_x"],
        ball_x=read_values["ball_x"],
        ball_z=read_values["ball_z"],
        chem=read_values["chem"],
        hit_type=read_values["slap_or_charge"],
        is_star_hit=read_values["is_hit_star"],
        pitch_type=read_values["pitch_type"],
        charge_up=read_values["charge_up"],
        charge_down=read_values["charge_down"],
        frame=read_values["frame"],
        rand_1=read_values["rand_1"],
        rand_2=read_values["rand_2"],
        rand_3=read_values["rand_3"],
        stick_up=read_values["stick_up"],
        stick_down=read_values["stick_down"],
        stick_left=read_values["stick_left"],
        stick_right=read_values["stick_right"],
        num_stars=read_values["num_stars"],
        is_starred=is_starred,
    )

    e = []

    if "Vertical Details" in res and len(res["Vertical Details"]["Zones"]) > 1 and (get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_vertical", bool) or get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_horizontal", bool)):
        for i in range(5):
            if i != res["Vertical Details"]["Selected Zone"]:
                new_res = hit_ball(
                    batter_id=read_values["batter_id"],
                    pitcher_id=read_values["pitcher_id"],
                    easy_batting=read_values["easy_batting"],
                    handedness=read_values["handedness"],
                    batter_x=read_values["batter_x"],
                    ball_x=read_values["ball_x"],
                    ball_z=read_values["ball_z"],
                    chem=read_values["chem"],
                    hit_type=read_values["slap_or_charge"],
                    is_star_hit=read_values["is_hit_star"],
                    pitch_type=read_values["pitch_type"],
                    charge_up=read_values["charge_up"],
                    charge_down=read_values["charge_down"],
                    frame=read_values["frame"],
                    rand_1=read_values["rand_1"],
                    rand_2=read_values["rand_2"],
                    rand_3=read_values["rand_3"],
                    stick_up=read_values["stick_up"],
                    stick_down=read_values["stick_down"],
                    stick_left=read_values["stick_left"],
                    stick_right=read_values["stick_right"],
                    num_stars=read_values["num_stars"],
                    is_starred=is_starred,
                    override_vertical_range = i,
                )

                e.append(new_res)

    runners_text = ""
    runners_value = read_values["where_are_runners"] >> 4
    if(runners_value) > 0:
        runners_text = "Runners on "
        runners_ord = []
        if runners_value & 1 != 0:
            runners_ord.append(ordinal(1))
        if runners_value & 10 != 0:
            runners_ord.append(ordinal(2))
        if runners_value & 100 != 0:
            runners_ord.append(ordinal(3))
        runners_text += ", ".join(runners_ord) + "\n"
    
    stick_text = f'{optional_text("Up ", stick_up)}{optional_text("Down ", stick_down)}{optional_text("Left ", stick_left)}{optional_text("Right ", stick_right)}{optional_text("Neutral", not any([stick_up, stick_down, stick_left, stick_right]))}'

    if read_values["slap_or_charge"] == 3:
        text = [
            get_game_state_text(),

              optional_text(f'{["Slap", "Charge", "Captain Star", "Bunt"][read_values["slap_or_charge"]]}\n',                                                                                                   get_config_value("TEXT_TOGGLES" ,"display_hit_charge_bunt_text", bool))
            + optional_text(f'Contact Zone: {res["Contact"]["ContactZone"]}\n',                                                                                                                                 get_config_value("TEXT_TOGGLES" ,"display_contact_zone_text", bool))
            + optional_text(f'Contact Quality: {res["Contact"]["ContactQuality"] * 100: .1f}%\n',                                                                                                               get_config_value("TEXT_TOGGLES" ,"display_contact_quality_text", bool))
            + optional_text(f'Dist: {res["FlightDetails"]["Distance"]:.2f}\n',                                                                                                                                  get_config_value("TEXT_TOGGLES" ,"display_ball_distance_text", bool))
            + optional_text(f'Hit Ground: {res["FlightDetails"]["Path"][-1]}\n',                                                                                                                                get_config_value("TEXT_TOGGLES" ,"display_hit_ground_text", bool))
            + optional_text(f'Stick Input: {stick_text}\n',                                                                                                                                                     get_config_value("TEXT_TOGGLES" ,"display_stick_input_text", bool))
            + optional_text(f'Power: {res["BallDetails"]["Power"]}\n',                                                                                                                                          get_config_value("TEXT_TOGGLES" ,"display_power_text", bool))
        ]
    else:
        text = [
            get_game_state_text(),

              optional_text(optional_text("Star Hit\n", read_values["is_hit_star"]),                                                                                                                            get_config_value("TEXT_TOGGLES" ,"display_if_star_hit", bool))
            + optional_text(f'{["Slap", "Charge", "Captain Star", "Bunt"][read_values["slap_or_charge"]]}\n',                                                                                                   get_config_value("TEXT_TOGGLES" ,"display_hit_charge_bunt_text", bool))
            + optional_text(optional_text(f'Charge Up: {read_values["charge_up"]:.2f}\nCharge Down: {read_values["charge_down"]:.2f}\n', read_values["charge_up"] > 0.0),                                       get_config_value("TEXT_TOGGLES" ,"display_charge_up_text", bool))
            + optional_text(f'Contact Zone: {res["Contact"]["ContactZone"]}\n',                                                                                                                                 get_config_value("TEXT_TOGGLES" ,"display_contact_zone_text", bool))
            + optional_text(f'Contact Quality: {res["Contact"]["ContactQuality"] * 100: .1f}%\n',                                                                                                               get_config_value("TEXT_TOGGLES" ,"display_contact_quality_text", bool))
            + optional_text(f'Dist: {res["FlightDetails"]["Distance"]:.2f}\n',                                                                                                                                  get_config_value("TEXT_TOGGLES" ,"display_ball_distance_text", bool))
            + optional_text(f'Hit Ground: {res["FlightDetails"]["Path"][-1]}\n',                                                                                                                                get_config_value("TEXT_TOGGLES" ,"display_hit_ground_text", bool))
            + optional_text(f'Stick Input: {stick_text}\n',                                                                                                                                                     get_config_value("TEXT_TOGGLES" ,"display_stick_input_text", bool))
            + optional_text(f'Frame: {read_values["frame"]}\n',                                                                                                                                                 get_config_value("TEXT_TOGGLES" ,"display_contact_frame_text", bool))
            + optional_text(f'RNG: {read_values["rand_1"]}, {read_values["rand_2"]}, {read_values["rand_3"]}\n',                                                                                                get_config_value("TEXT_TOGGLES" ,"display_rng_text", bool))
            + optional_text(f'Power: {res["BallDetails"]["Power"]}\n',                                                                                                                                          get_config_value("TEXT_TOGGLES" ,"display_power_text", bool))
            + optional_text(f'Contact Power: {res["PowerDetails"]["CalculatedContactPower"]:.2f}\nCharacter Power: {res["PowerDetails"]["CalculatedCharacterPower"]:.2f}\n',                                    get_config_value("TEXT_TOGGLES" ,"display_char_contact_power_text", bool))
            + optional_text(f'Char Traj Bonus: {res["PowerDetails"]["FieldBonus"]:.2f}\n',                                                                                                                      get_config_value("TEXT_TOGGLES" ,"display_char_field_traj_bonus_text", bool))
            + optional_text(optional_text(f'Selected Vertical Range: {["Low", "Mid-Low", "Mid", "Mid-High", "High"][res["Vertical Details"]["Selected Zone"]]}\n', len(res["Vertical Details"]["Zones"]) > 1),  get_config_value("TEXT_TOGGLES" ,"display_selected_vertical_range_text", bool))
        ]

    global all_events
    all_events.append(DisplayHitView({"k": "Hit", "v": res, "t": text, "e": e, "read_values":deepcopy(read_values)}))

def get_rect(a, b, c, d) -> Rect:
    return Rect(a, b, c, d)

def get_inscribed_square_rect(x, y, width, height) -> Rect:
    small_square = min(width, height)

    center_x, center_y = x + (width / 2), y + (height / 2)

    upper_y = center_y - (small_square / 2)
    left_x = center_x - (small_square / 2)
    return get_rect(left_x, upper_y, small_square, small_square)

def get_inscribed_screen(x, y, width, height)->Rect:
    center_x, center_y = x + (width / 2), y + (height / 2)
    
    r = Rect(0, 0, 0, 0)

    r.width = height * 1.3
    r.height = height

    if r.width > width:
        convert = width / r.width

        r.width = r.width * convert
        r.height = r.height * convert
    
    if r.height > height:
        convert = height / r.height

        r.width = r.width * convert
        r.height = r.height * convert

    r.centerx = center_x
    r.centery = center_y

    return r

def get_my_surface(x, y, width, height)-> pygame.Surface:
    return screen.subsurface(x, y, width, height)
   
def draw_unhooked_screen(my_screen:pygame.Surface):
    # width, height = my_screen.get_width(), my_screen.get_height()

    s = "Unhooked from Dolphin"
    font = pygame.font.SysFont(get_config_value("GRAPHICS", "font", str), int(height / 8))
    blit_text(my_screen, s, (0,0), font)

def new_read(name:str, v):
    return read_values.get(name, None) == v and last_read_values.get(name, None) != v

def update_read_values():
    for k, v in CALCULATE_ADDRESSES.items():
        read_values[k] = v.live_value
   
def update_every_frame_values():
    for k, v in EVERY_FRAME_ADDRESSES.items():
        read_values[k] = v.live_value

read_values = {}
last_read_values = {}

last_hit_value = {}
all_events = []
config = None


config = configparser.ConfigParser()
config.read("config.ini")
size = width, height = get_config_value("GRAPHICS", "x_dimension", int), get_config_value("GRAPHICS", "y_dimension", int)

LINE_WIDTH = get_config_value("GRAPHICS", "line_width", int)
HITBOX_LINE_WIDTH = get_config_value("GRAPHICS", "hitbox_line_width", int)
BOLD_LINE_WIDTH = get_config_value("GRAPHICS", "bold_line_width", int)

ADDITIONAL_TRAJ_LINE_WIDTH = get_config_value("GRAPHICS", "additional_trajectory_line_width", int)
ADDITIONAL_TRAJ_LINE_OUTLINE = get_config_value("GRAPHICS", "additional_trajectory_line_outline", int)
force_hit = False
previous_event = -1

SCREEN_REGIONS = {
    "TOP" : (0,0,width, height / 3),
    "MID" : (0,height / 3,width, height / 3),
    "MIDDLE" : (0,height / 3,width, height / 3),
    "BOTTOM" : (0,height * 2/ 3,width, height / 3),
    "NONE" : (0,0,0,0),
}

defined_screens = {}

def get_sub_screen(region_name:str):
    new_name = region_name.upper()

    if new_name in defined_screens:
        return defined_screens[new_name]
    elif new_name not in SCREEN_REGIONS:
        return get_sub_screen("NONE")
    else:
        s = screen.subsurface(SCREEN_REGIONS.get(new_name, (0,0,0,0)))
        defined_screens[new_name] = s
        return s

def main():
    global size, width, height, last_hit_value, last_read_values, read_values, all_events, config, screen, force_hit, previous_event

    background = get_config_color("background")

    pygame.init()
    screen = pygame.display.set_mode(size)

    def increase_event_watch():
        global previous_event, force_hit, all_events

        if force_hit:
            return

        if previous_event == -1:
            pass
        elif previous_event + 1 < len(all_events):
            previous_event += 1
        else:
            previous_event = -1

    def decrease_event_watch():
        global previous_event, force_hit

        if force_hit:
            return

        if len(all_events) == 0:
            return

        if previous_event > 0:
            # view previous entry
            previous_event -= 1
        
        # if viewing first entry
        elif previous_event == 0:
            # skip
            pass

        # if not viewing, but displaying current data
        elif previous_event == -1 and all_events[previous_event].is_valid():
            # if there are at least 2 object
            if len(all_events) >= 2:
                # show second to most recent
                previous_event = len(all_events) - 2
            
            # else if 1 object
            else:
                # show first
                previous_event = 0
        # not viewing anything
        else:
            # show last
            previous_event = len(all_events) - 1

    def reset_bat_watch():
        global previous_event, force_hit

        if force_hit:
            force_hit = False
        
        previous_event = -1

    def toggle_force_bat_hit():
        global previous_event, force_hit

        if force_hit or not get_config_value("USAGE", "allow_forced_rehits", bool):
            force_hit = False
            return
        
        if previous_event == -1:
            return

        if last_hit_value.data["k"] == "Hit":
            force_hit = True
            
    def save():
        global all_events

        r_data = [x.data["read_values"] for x in all_events]

        file_string = "game {0}.json"

        file_numbered_string = "game {0} ({1}).json"

        file_name = file_string.format(read_values['game_id'])

        if exists(file_name):
            i = 1
            
            file_name = file_numbered_string.format(read_values['game_id'], i)

            while exists(file_name):
                i+=1
                file_name = file_numbered_string.format(read_values['game_id'], i)
        
        with open(file_name, "w") as f:
            json.dump(r_data, f, indent=2)

    def load(filename):
        global read_values
        if not exists(filename):
            return
        
        with open(filename, "r") as f:
            j = json.load(f)
        
        for jj in j:
            read_values = jj

            if read_values["hit_by_pitch"] or read_values["missed_ball"]:
                missed_ball()
            elif read_values["was_contact_made"]:
                calculate_trajectory()        

    if len(sys.argv) > 1:
        load(sys.argv[1])

    if get_config_value("USAGE", "calibration", bool):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: 
                    sys.exit()

            screen.fill((255, 0, 0))       



            for i in [get_sub_screen(get_config_value("VISUAL_TOGGLES", "plate_screen", str))]:
                my_screen = get_inscribed_screen(*i.get_rect())
                new_screen = i.subsurface(my_screen)
                new_screen.fill(background)
            
            for i in [get_sub_screen(get_config_value("VISUAL_TOGGLES", "horizontal_path_screen", str)), get_sub_screen(get_config_value("VISUAL_TOGGLES", "vertical_path_screen", str))]:
                my_screen = get_inscribed_square_rect(*i.get_rect())
                new_screen = i.subsurface(my_screen)
                new_screen.fill(background)

            for i in [get_sub_screen(get_config_value("VISUAL_TOGGLES", "text_screen", str))]:
                my_screen = i.get_rect()
                new_screen = i.subsurface(my_screen)
                new_screen.fill(background)

            pygame.draw.line(screen, (0,0,0), (0, height * 1/3), (width, height * 1/3))
            pygame.draw.line(screen, (0,0,0), (0, height * 2/3), (width, height * 2/3))

            pygame.display.flip()

    while True:
        for event in pygame.event.get():

            if event.type == pygame.QUIT: 
                sys.exit()
            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_LEFT:
                   decrease_event_watch()

                elif event.key == pygame.K_RIGHT:
                    increase_event_watch()

                elif event.key == pygame.K_SPACE:
                    reset_bat_watch()

                elif event.key == pygame.K_f:
                    toggle_force_bat_hit()
                
                elif event.key == pygame.K_s:
                    save()                    

            # print(event)
        screen.fill(background)       
        pygame.draw.line(screen, (0,0,0), (0, height * 1/3), (width, height * 1/3))
        pygame.draw.line(screen, (0,0,0), (0, height * 2/3), (width, height * 2/3))

        if not dme.is_hooked():
            dme.hook()

            # let user know it's unhooked
            draw_unhooked_screen(get_sub_screen("top"))
            draw_unhooked_screen(get_sub_screen("mid"))
            draw_unhooked_screen(get_sub_screen("bottom"))
            pygame.display.flip()
            continue

        try:
            update_every_frame_values()
        except:
            # unable to talk to dolphin
            dme.un_hook()

        data_events = [
            {"name": "was_contact_made", "value": True, "func": calculate_trajectory},
            {"name": "missed_ball", "value": True, "func": missed_ball},
            {"name": "hit_by_pitch", "value": True, "func": missed_ball},
        ]

        if not read_values["is_replay"] and read_values["gamestate"] in [0x1, 0x2]:
            for d in data_events:
                if new_read(d["name"], d["value"]):
                    update_read_values()

                    d["func"]()

        last_read_values = {k: v for k, v in read_values.items()}

        if len(all_events) == 0:
            # if there is no recorded hit, end
            pygame.display.flip()
            continue

        if previous_event == -1 and not all_events[-1].is_valid():
            pygame.display.flip()
            continue

        last_hit_value = all_events[previous_event]

        last_hit_value.draw()

        pygame.display.flip()

if __name__ == "__main__":
    main()

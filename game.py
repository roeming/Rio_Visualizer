import configparser
from copy import deepcopy
from genericpath import exists
import sys, pygame, _dolphin_memory_engine as dme, json
from matplotlib.colors import to_rgb
from calc_batting import get_bat_hitbox, get_name, hit_ball, get_hitbox
from pygame import Rect, Vector2, Vector3


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

def get_config_color(name) -> tuple:
    rgb = to_rgb(config["COLORS"][name])
    return Vector3(*rgb) * 255

def read_word(addr) -> int:
    return dme.read_word(addr)

def read_byte(addr) -> int:
    return dme.read_byte(addr)

def read_bool(addr) -> int:
    return read_byte(addr) != 0

def read_half_word(addr) -> int:
    return read_word(addr) >> 16

def read_float(addr) -> float:
    return dme.read_float(addr)

def write_float(addr, value):
    dme.write_float(addr, value)

def write_vec3(addr, value:Vector3):
    dme.write_float(addr + 0, value.x)
    dme.write_float(addr + 4, value.y)
    dme.write_float(addr + 8, value.z)

def optional_text(s:str, b:bool):
    if b: return s
    return ""

def blit_text(surface, text, pos, font):
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

def get_game_state():
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
    "game_id": (read_word, 0x802EBF8C),

    "batter_id": (read_half_word, 0x80890972),
    "pitcher_id": (read_half_word, 0x80890ADA),

    "easy_batting": (read_byte, 0x8089098A),
    "handedness": (read_byte, 0x8089098B),

    "batter_x": (read_float, 0x8089095C),
    "batter_z": (read_float, 0x80890964),

    "model_x": (read_float, 0x80890910),

    "ball_x": (read_float, 0x80890934),
    "ball_y": (read_float, 0x80890938),
    "ball_z": (read_float, 0x8089093C),

    "chem": (read_byte, 0x808909ba),

    "slap_or_charge": (read_byte, 0x8089099b),
    "is_hit_star": (read_byte, 0x808909b1),

    "pitch_1": (read_byte, 0x80890b21),
    "pitch_2": (read_byte, 0x80890b1f),

    "charge_up": (read_float, 0x80890968),
    "charge_down": (read_float, 0x8089096C),

    "frame": (read_half_word, 0x80890976),

    "rand_1": (read_half_word, 0x802ec010),
    "rand_2": (read_half_word, 0x802ec012),
    "rand_3": (read_half_word, 0x802ec014),

    # extra things to read

    "team_batting": (read_word, 0x80892990),
    "team_pitching": (read_word, 0x80892994),

    "port_home": (read_word, 0x80892a78),
    "port_away": (read_word, 0x80892a7c),

    "stars_home": (read_byte, 0x80892ad6),
    "stars_away": (read_byte, 0x80892ad7),

    "p1_input": (read_half_word, 0x8089392c),
    "p2_input": (read_half_word, 0x8089393c),
    "p3_input": (read_half_word, 0x8089394c),
    "p4_input": (read_half_word, 0x8089395c),

    "strike_x": (read_float, 0x80890A14),
    "strike_y": (read_float, 0x80890A18),

    "strike_left_side": (read_float, 0x80890a3c),
    "strike_right_side": (read_float, 0x80890a40),

    "swung" : (read_bool, 0x808909A9),
    "is_strike": (read_bool, 0x80890b17),

    "inning": (read_word, 0x808928a0),
    "inning_half": (read_bool, 0x8089294d),

    "strikes": (read_word, 0x80892968),
    "balls": (read_word, 0x8089296c),
    "outs": (read_word, 0x80892970),

    "where_are_runners" : (read_half_word, 0x80892734),

    "home_score":(read_half_word, 0x808928a4),
    "away_score":(read_half_word, 0x808928ca),

    "home_stars":(read_byte, 0x80892ad6),
    "away_stars":(read_byte, 0x80892ad7),
}

EVERY_FRAME_ADDRESSES = {
    "was_contact_made": (read_bool, 0x808909a1),
    "missed_ball": (read_bool, 0x80890b18),
    "hit_by_pitch": (read_bool, 0x808909a3),
    "is_replay": (read_bool, 0x80872540),
    "is_glory_shot": (read_bool, 0x8087253C)
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

    text = [
        get_game_state(),

          optional_text(f"Ball (x,y): ({res['strike_x']:.2f}, {res['strike_y']:.2f})\n",                            get_config_value("TEXT_TOGGLES", "display_ball_coordinate_text", bool))
        + optional_text(f"Batter Hitbox: {hitbox_left:.2f} to {hitbox_right:.2f}\n",                                get_config_value("TEXT_TOGGLES", "display_batter_hitbox_text", bool))
        + optional_text(f"Bat Hitbox: {min(hitbox_near, hitbox_far):.2f} to {max(hitbox_near, hitbox_far):.2f}\n",  get_config_value("TEXT_TOGGLES", "display_bat_hitbox_text", bool))
        + optional_text(f"Strike Box: {res['strike_range_left']:.2f} to {res['strike_range_right']:.2f}\n",         get_config_value("TEXT_TOGGLES", "display_strike_zone_text", bool))
        + optional_text(f"Pitch Type: {pitch_type}\n",                                                              get_config_value("TEXT_TOGGLES", "display_pitch_type_text", bool))
        + optional_text('Swung\n',                                                                                  get_config_value("TEXT_TOGGLES", "display_if_swung_text", bool) and read_values['swung'])
        + optional_text(f"{result_text}\n",                                                                         get_config_value("TEXT_TOGGLES", "display_batting_result_ball_strike_hbp", bool))
    ]

    global last_hits
    last_hits.append({"k": "StrikeBall", "v": res, "t": text, "read_values":deepcopy(read_values)})

def ordinal(n):
    return "%d%s" % (n,"tsnrhtdd"[(n//10%10!=1)*(n%10<4)*n%10::4])

def calculate_trajectory():
    global force_hit
    if force_hit:
        ball_pos = last_hit_value["v"]["FlightDetails"]["Path"][0]
        ball_acc = last_hit_value["v"]["BallDetails"]["Acceleration"]
        ball_vel = last_hit_value["v"]["BallDetails"]["Velocity"]
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
            get_game_state(),

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
            get_game_state(),

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

    global last_hits
    last_hits.append({"k": "Hit", "v": res, "t": text, "e": e, "read_values":deepcopy(read_values)})


def get_rect(a, b, c, d) -> Rect:
    return Rect(a, b, c, d)

def get_inscribed_square_rect(x, y, width, height) -> Rect:
    small_square = min(width, height)

    center_x, center_y = x + (width / 2), y + (height / 2)

    upper_y = center_y - (small_square / 2)
    left_x = center_x - (small_square / 2)
    return get_rect(left_x, upper_y, small_square, small_square)

def get_my_surface(x, y, width, height)-> pygame.surface:
    return screen.subsurface(x, y, width, height)

def draw_detailed_text(x, y, width, height):
    global force_hit

    data = last_hit_value["t"]
    
    if force_hit:
        data = ["FORCING"] + data

    my_square = get_inscribed_square_rect(x, y, width, height)
    m_surface = get_my_surface(x,y, width, height)

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



def draw_strike_view(x, y, width, height):
    data = last_hit_value["v"]
    my_square = get_inscribed_square_rect(x, y, width, height)
    my_surface = get_my_surface(x, y, width, height)

    my_square.x = 0
    my_square.y = 0

    origin = Vector2(width/2, -height/3)
    scale = get_config_value("VISUAL_TOGGLES", "strike_view_scale", float)

    def unNormalize(p):
        return origin + Vector2(my_square.left + scale *  p[0] * my_square.width, my_square.bottom - scale * p[1] * my_square.height)
    
    # draw ground
    ground_start, ground_end = unNormalize((-2, 0)), unNormalize((2, 0))

    strike_points = [unNormalize((data["strike_range_left"], 0.5)), unNormalize((data["strike_range_left"], 1.5)), unNormalize((data["strike_range_right"], 1.5)), unNormalize((data["strike_range_right"], 0.5))]

    ball_location = unNormalize((data["strike_x"], data["strike_y"]))

    model_x = data["model_x"]

    player_near =  data["hitbox"][1] / 100
    player_far =  data["hitbox"][2] / 100

    if data["handedness"] == 0:
        bottomright = (model_x + player_near, 0.0)
        topleft = (model_x - player_far, 2.0)
    else:
        bottomright = (model_x - player_near, 0.0)
        topleft = (model_x + player_far, 2.0)

    # for r in [player_near, player_far]:
    
    br = bottomright
    tl = topleft

    br = unNormalize(br)
    tl = unNormalize(tl)

    bat_top_corner = unNormalize((data["hitbox_near"], data["strike_y"]+0.35))
    bat_bottom_corner = unNormalize((data["hitbox_far"], data["strike_y"]-0.35))

    #draw ground
    if get_config_value("VISUAL_TOGGLES", "display_ground", bool):
        pygame.draw.line(my_surface, get_config_color("ground"), ground_start, ground_end, width=LINE_WIDTH)

    #draw hitbox
    if get_config_value("VISUAL_TOGGLES", "display_player_hitbox", bool):
        pygame.draw.polygon(my_surface, get_config_color("player_hitbox"), [br, (br.x, tl.y), tl, (tl.x, br.y)], width=LINE_WIDTH)
    
        #draw player_center
        pygame.draw.polygon(my_surface, get_config_color("player_position"), [unNormalize((model_x, 0.0)), unNormalize((model_x, 2.0))], width=LINE_WIDTH)

    #draw strike zone
    if get_config_value("VISUAL_TOGGLES", "display_strike_zone", bool):
        pygame.draw.lines(my_surface, get_config_color("strike_zone"), closed=True, points=strike_points, width=LINE_WIDTH)

    #draw bat
    if get_config_value("VISUAL_TOGGLES", "display_bat_hitbox", bool):
        pygame.draw.polygon(my_surface, get_config_color("bat_hitbox"), [bat_top_corner, (bat_top_corner.x, bat_bottom_corner.y), bat_bottom_corner, (bat_bottom_corner.x, bat_top_corner.y)], width=LINE_WIDTH)

    #draw ball
    if get_config_value("VISUAL_TOGGLES", "display_ball_hitbox", bool):
        pygame.draw.circle(my_surface, get_config_color("ball"), ball_location, radius=5, width=LINE_WIDTH)



def draw_horizontal_trajectory(x, y, m_width, m_height):
    data = last_hit_value["v"]

    my_square = get_inscribed_square_rect(x, y, m_width, m_height)
    m_surface = get_my_surface(my_square.left, my_square.top, my_square.width, my_square.height)

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
    
    stadium_color = get_config_color("stadium_line")
    line_color = get_config_color("ball_trajectory")
    line_outline_color = get_config_color("ball_trajectory_outline")

    pygame.draw.polygon(m_surface, stadium_color, [ plot_point(Vector3(0,0,0)), plot_point(left_post), plot_point(left_part), plot_point(middle_part), plot_point(right_part), plot_point(right_post)], width=LINE_WIDTH)

    if get_config_value("VISUAL_TOGGLES", "display_bases", bool):
        pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(19, 0,19)), LINE_WIDTH)
        pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(-19,0, 19)), LINE_WIDTH)
        pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(0, 0, 38)), LINE_WIDTH)
        pygame.draw.circle(m_surface, stadium_color, plot_point(Vector3(0, 0, 19)), int(LINE_WIDTH // 1.5))


    # draw extra trajectories
    if get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_horizontal", bool):
        for e in last_hit_value["e"]:
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
    

def draw_vertical_trajectory(x, y, m_width, m_height):
    data = last_hit_value["v"]

    my_square = get_inscribed_square_rect(x, y, m_width, m_height)
    m_surface = get_my_surface(my_square.left, my_square.top, my_square.width, my_square.height)

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

    stadium_color = get_config_color("stadium_line")
    line_color = get_config_color("ball_trajectory")
    line_outline_color = get_config_color("ball_trajectory_outline")

    pygame.draw.line(m_surface, stadium_color, corner_post, right_post, width=LINE_WIDTH)
    pygame.draw.line(m_surface, stadium_color, corner_post, top_post, width=LINE_WIDTH)

    if get_config_value("VISUAL_TOGGLES", "display_multiple_trajectories_vertical", bool):
        for e in last_hit_value["e"]:
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
    
def draw_unhooked_screen(x, y, m_width, m_height):
    s = "Unhooked from Dolphin"
    my_screen = screen.subsurface(x, y, m_width, m_height)
    font = pygame.font.SysFont(get_config_value("GRAPHICS", "font", str), int(height / 8))
    blit_text(my_screen, s, (0,0), font)

def new_read(name:str, v):
    return read_values.get(name, None) == v and last_read_values.get(name, None) != v

def update_read_values():
    for k, v in CALCULATE_ADDRESSES.items():
        read_values[k] = v[0](v[1])
   
def update_every_frame_values():
    for k, v in EVERY_FRAME_ADDRESSES.items():
        read_values[k] = v[0](v[1])

read_values = {}
last_read_values = {}

last_hit_value = {}
last_hits = []
config = None


config = configparser.ConfigParser()
config.read("config.ini")
size = width, height = get_config_value("GRAPHICS", "x_dimension", int), get_config_value("GRAPHICS", "y_dimension", int)

LINE_WIDTH = get_config_value("GRAPHICS", "line_width", int)
BOLD_LINE_WIDTH = get_config_value("GRAPHICS", "bold_line_width", int)

ADDITIONAL_TRAJ_LINE_WIDTH = get_config_value("GRAPHICS", "additional_trajectory_line_width", int)
ADDITIONAL_TRAJ_LINE_OUTLINE = get_config_value("GRAPHICS", "additional_trajectory_line_outline", int)
force_hit = False
previous_batting = -1

SCREEN_REGIONS = {
    "TOP" : (0,0,width, height / 3),
    "MID" : (0,height / 3,width, height / 3),
    "MIDDLE" : (0,height / 3,width, height / 3),
    "BOTTOM" : (0,height * 2/ 3,width, height / 3),
}

def get_screen_region(region_name:str):
    return SCREEN_REGIONS.get(region_name.upper(), (0,0,0,0))


def main():
    global size, width, height, last_hit_value, last_read_values, read_values, last_hits, config, screen, force_hit, previous_batting

    background = get_config_color("background")

    pygame.init()
    screen = pygame.display.set_mode(size)
    
    displayable_data = False

    def increase_bat_watch():
        global previous_batting, force_hit

        if force_hit:
            return

        if previous_batting == -1:
            pass
        elif previous_batting + 1 < len(last_hits):
            previous_batting += 1
        else:
            previous_batting = -1

    def decrease_bat_watch():
        global previous_batting, force_hit

        if force_hit:
            return

        if previous_batting > 0:
            # view previous entry
            previous_batting -= 1
        
        # if viewing first entry
        elif previous_batting == 0:
            # skip
            pass

        # if not viewing, but displaying current data
        elif previous_batting == -1 and displayable_data == True:
            # if there are at least 2 object
            if len(last_hits) >= 2:
                # show second to most recent
                previous_batting = len(last_hits) - 2
            
            # else if 1 object
            else:
                # show first
                previous_batting = 0
        # not viewing anything
        else:
            # show last
            previous_batting = len(last_hits) - 1

    def reset_bat_watch():
        global previous_batting, force_hit

        if force_hit:
            force_hit = False
        
        previous_batting = -1

    def toggle_force_bat_hit():
        global previous_batting, force_hit

        if force_hit or not get_config_value("USAGE", "allow_forced_rehits", bool):
            force_hit = False
            return
        
        if previous_batting == -1:
            return

        if last_hit_value["k"] == "Hit":
            force_hit = True
            
    def save():
        global last_hits

        r_data = [x["read_values"] for x in last_hits]

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

    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT: 
                sys.exit()
            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_LEFT:
                   decrease_bat_watch()

                elif event.key == pygame.K_RIGHT:
                    increase_bat_watch()

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
            draw_unhooked_screen(*get_screen_region("top"))
            draw_unhooked_screen(*get_screen_region("mid"))
            draw_unhooked_screen(*get_screen_region("bottom"))
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

        displayable_data = False
        if not read_values["is_replay"] and not read_values["is_glory_shot"]:
            for d in data_events:
                if new_read(d["name"], d["value"]):
                    update_read_values()

                    d["func"]()

                if read_values[d["name"]] == d["value"]:
                    displayable_data = True

        last_read_values = {k: v for k, v in read_values.items()}

        if len(last_hits) == 0 or (previous_batting == -1 and not displayable_data):
            # if there is no recorded hit, end
            pygame.display.flip()
            continue


        last_hit_value = last_hits[previous_batting]


        if last_hit_value["k"] == "Hit":
            draw_vertical_trajectory(*get_screen_region(get_config_value("VISUAL_TOGGLES", "vertical_path_screen")))

            draw_horizontal_trajectory(*get_screen_region(get_config_value("VISUAL_TOGGLES", "horizontal_path_screen")))

            draw_detailed_text(*get_screen_region(get_config_value("VISUAL_TOGGLES", "text_screen")))

        elif last_hit_value["k"] == "StrikeBall" or last_hit_value["k"] == "HBP":
            draw_strike_view(*get_screen_region(get_config_value("VISUAL_TOGGLES", "plate_screen")))
            draw_detailed_text(*get_screen_region(get_config_value("VISUAL_TOGGLES", "text_screen")))

        pygame.display.flip()

if __name__ == "__main__":
    main()

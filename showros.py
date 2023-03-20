# Copyright (c) 2023 Matthew Earl
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
#     The above copyright notice and this permission notice shall be included
#     in all copies or substantial portions of the Software.
# 
#     THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#     OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
#     MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
#     NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
#     OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
#     USE OR OTHER DEALINGS IN THE SOFTWARE.


import sys
import re

import pydem
import messages


# animation data taken from player.qc
animations = [
    ["axrun1", "axrun2", "axrun3", "axrun4", "axrun5", "axrun6"],
    ["rockrun1", "rockrun2", "rockrun3", "rockrun4", "rockrun5", "rockrun6"],
    ["stand1", "stand2", "stand3", "stand4", "stand5"],
    ["axstnd1", "axstnd2", "axstnd3", "axstnd4", "axstnd5", "axstnd6",
     "axstnd7", "axstnd8", "axstnd9", "axstnd10", "axstnd11", "axstnd12"],
    ["axpain1", "axpain2", "axpain3", "axpain4", "axpain5", "axpain6"],
    ["pain1", "pain2", "pain3", "pain4", "pain5", "pain6"],
    ["axdeth1", "axdeth2", "axdeth3", "axdeth4", "axdeth5", "axdeth6",
     "axdeth7", "axdeth8", "axdeth9"],
    ["deatha1", "deatha2", "deatha3", "deatha4", "deatha5", "deatha6",
     "deatha7", "deatha8", "deatha9", "deatha10", "deatha11"],
    ["deathb1", "deathb2", "deathb3", "deathb4", "deathb5", "deathb6",
     "deathb7", "deathb8", "deathb9"],
    ["deathc1", "deathc2", "deathc3", "deathc4", "deathc5", "deathc6",
     "deathc7", "deathc8", "deathc9", "deathc10", "deathc11", "deathc12",
     "deathc13", "deathc14", "deathc15"],
    ["deathd1", "deathd2", "deathd3", "deathd4", "deathd5", "deathd6",
     "deathd7", "deathd8", "deathd9"],
    ["deathe1", "deathe2", "deathe3", "deathe4", "deathe5", "deathe6",
     "deathe7", "deathe8", "deathe9"],
    ["nailatt1", "nailatt2"],
    ["light1", "light2"],
    ["rockatt1", "rockatt2", "rockatt3", "rockatt4", "rockatt5", "rockatt6"],
    ["shotatt1", "shotatt2", "shotatt3", "shotatt4", "shotatt5", "shotatt6"],
    ["axatt1", "axatt2", "axatt3", "axatt4", "axatt5", "axatt6"],
    ["axattb1", "axattb2", "axattb3", "axattb4", "axattb5", "axattb6"],
    ["axattc1", "axattc2", "axattc3", "axattc4", "axattc5", "axattc6"],
    ["axattd1", "axattd2", "axattd3", "axattd4", "axattd5", "axattd6"],
]


# frame_lookup goes from (animation name, number) to frame number
frame_lookup = {}
frame_num = 0
for anim in animations:
    for frame in anim:
        val = (re.sub(r'\d', '', frame),
               int(re.sub(r'[^\d]', '', frame)))
        frame_lookup[val] = frame_num
        frame_num += 1

# anim_lens goes from animation name to a length
anim_lens = {
    re.sub(r'\d', '', anim[0]): len(anim)
    for anim in animations
}

# attack animation for each view model
view_model_to_attack_anim = {
    'progs/v_axe.mdl': 'axatt',
    'progs/v_shot.mdl': 'shotatt',
    'progs/v_shot2.mdl': 'shotatt',
    'progs/v_nail.mdl': 'nailatt',
    'progs/v_nail2.mdl': 'nailatt',
    'progs/v_rock.mdl': 'rockatt',
    'progs/v_rock2.mdl': 'rockatt',
    'progs/v_light.mdl': 'light',
}

# frame rate for each animation
anim_fps = 10


def get_view_entity(block):
    return next(iter(m
                     for m in block.messages
                     if isinstance(m, messages.SetViewMessage))).viewentity_id

def get_time(block):
    return next(iter(m.time
                     for m in block.messages
                     if isinstance(m, messages.TimeMessage)))


def get_player_update(block):
    return next(iter(m
                     for m in block.messages
                     if isinstance(m, messages.EntityUpdateMessage)
                     if m.num == view_entity))


def get_client_data(block):
    return next(iter(m
                     for m in block.messages
                     if isinstance(m, messages.ClientDataMessage)))

def get_models(block):
    server_info_msg = next(iter(m
                                for m in block.messages
                                if isinstance(m, messages.ServerInfoMessage)))
    return [m.decode('utf-8') for m in server_info_msg.models_precache]


class BlockFixer:
    def __init__(self, models):
        self._current_anim = None
        self._anim_start_time = 0
        self._last_health = None
        self._models = models

    def _set_anim(self, anim, t):
        if self._current_anim != anim:
            self._current_anim = anim
            self._anim_start_time = t

    def _set_frame(self, upd, anim_name, anim_frame_num):
        upd.flags &= ~messages.UpdateFlags.MODEL
        upd.flags |= messages.UpdateFlags.FRAME
        upd.modelindex = None
        upd.frame = frame_lookup[anim_name, anim_frame_num]

    def fix(self, block):
        # Extract all the relevant info from the block. Leave blocks that don't
        # have the relevant bits untouched.
        try:
            t = get_time(block)
            upd = get_player_update(block)
            cd = get_client_data(block)
        except StopIteration:
            return

        # Only modify blocks that have the eyes model.
        if (upd.modelindex is None
                or self._models[upd.modelindex] != 'progs/eyes.mdl'):
            return

        # Start attack animation when first person weapon animation starts.
        weapon_model = self._models[cd.weapon]
        axe = weapon_model == 'progs/v_axe.mdl'
        attack_anim = view_model_to_attack_anim[weapon_model]
        if cd.weaponframe != 0:
            self._set_anim(attack_anim, t)

        # Start pain animation when we lose health.  Don't show pain for small
        # damage losses so we don't go into a pain animation every time we lose
        # 1HP after a MH.
        if self._last_health is not None and cd.health <= self._last_health - 5:
            self._set_anim('axpain' if axe else 'pain', t)
        self._last_health = cd.health

        if self._current_anim is not None:
            anim_len = anim_lens[self._current_anim]
            anim_frame_num = int((t - self._anim_start_time) * anim_fps) + 1
            if anim_frame_num > anim_len:
                self._current_anim = None
                self._anim_start_time = t

        # Restart the attack anim if we're still attacking.
        if self._current_anim is None and cd.weaponframe != 0:
            self._set_anim(attack_anim, t)
            anim_frame_num = 1

        # Default to run animation.
        if self._current_anim is None:
            anim_name = 'axrun' if axe else 'rockrun'
            anim_len = anim_lens[anim_name]
            anim_frame_num = (int((t - self._anim_start_time) * anim_fps)
                              % anim_len) + 1
        else:
            anim_name = self._current_anim

        # Actually modify the block to show the desired frame.
        self._set_frame(upd, anim_name, anim_frame_num)


if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(f"usage: {sys.argv[0]} input-demo output-demo [view-entity]",
              file=sys.stderr)
        raise SystemExit(1)
    in_fname, out_fname = sys.argv[1:3]

    dem = pydem.parse_demo(in_fname)
    server_info_block_idx = 0
    while dem.blocks[server_info_block_idx].messages == [messages.NopMessage()]:
        server_info_block_idx += 1

    if len(sys.argv) == 3:
        view_entity = get_view_entity(dem.blocks[server_info_block_idx])
    else:
        view_entity = int(sys.argv[3])

    models = get_models(dem.blocks[server_info_block_idx])

    bf = BlockFixer(models)
    for block in dem.blocks:
        bf.fix(block)

    with open(out_fname, 'wb') as f:
        dem.write(f)

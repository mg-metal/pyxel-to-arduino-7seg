import pyxel
import serial
import time
import os

# Arduinoと接続
ser = serial.Serial("COM3", 115200, timeout=0.1)
# ser = serial.Serial("COM3", 9600, timeout=0.1)
time.sleep(2)   # Arduino起動待ち

# アニメパターン数： MAX 300フレーム
# タプル要素の並び順は pattern10, pattern01, duration, flicker_delay
# パターンのビット順は DP,G,F,E,D,C,B,A
patternList = [ (0b00000000, 0b00000000, 0, 0) ] * 24

def seva_pattern_list(pattern_list, filename="resource/pattern_list.txt"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w") as f:
        for p in pattern_list:
            line = f"{p[0]},{p[1]},{p[2]},{p[3]}\n"
            f.write(line)
    print("Saved:", filename)

def load_pattern_list(filename="resource/pattern_list.txt"):
    pattern_list = []
    try:
        with open(filename, "r") as f:
            for line in f:
                # 改行削除、カンマで分割
                parts = line.strip().split(",")
                if len(parts) != 4:
                    continue    # 不正データは読み飛ばす

                # 整数に変換
                try:
                    pattern10 = int(parts[0])
                    pattern01 = int(parts[1])
                    duration = int(parts[2])
                    flicker_delay = int(parts[3])
                    pattern_list.append((pattern10, pattern01, duration, flicker_delay))
                except ValueError:
                    # 変換失敗データも読み飛ばす
                    continue
        print(f"Loaded {len(pattern_list)} patterns from {filename}")
        return pattern_list
    except:
        print("Pattern file not found. Using default list.")
        return None

def collide_mouse_rect(x, y, w, h):
    if x <= pyxel.mouse_x <= x+w and y <= pyxel.mouse_y <= y + h:
        return True
    else:
        return False

class Seg:
    def __init__(self, x, y, length, type):
        self.x = x
        self.y = y
        self.length = length
        self.stroke_w = 2 if length >= 12 else 1    # 太い: 2  細い: 1 (Type:'c'は使用せず)
        self.type = type    # 垂直: 'v'  水平: 'h'  丸: 'c'
        self.light_on = False

    def update(self):
        if pyxel.btn(pyxel.MOUSE_BUTTON_LEFT):
            stw = self.stroke_w
            length = self.length
            if self.type == 'v' and collide_mouse_rect(self.x-stw, self.y+stw, 1+stw*2, length-stw*2) \
                or self.type == 'h' and collide_mouse_rect(self.x+stw, self.y-stw, length-stw*2, 1+stw*2)\
                or self.type == 'c' and collide_mouse_rect(self.x-length, self.y-length, length*2, length*2):
                self.light_on = False if pyxel.btn(pyxel.KEY_SHIFT) else True

    def draw(self):
        color = 8 if self.light_on else 13
        if self.type == 'v':
            self.draw_seg_v(self.x, self.y, self.length, color)
        elif self.type == 'h':
            self.draw_seg_h(self.x, self.y, self.length, color)
        elif self.type == 'c':
            self.draw_seg_c(self.x, self.y, self.length, color)

    def draw_seg_v(self, x, y, length, color):
        pyxel.line(x-1, y+1, x-1, y+length-1, color)
        pyxel.line(x+0, y+0, x+0, y+length-0, color)
        pyxel.line(x+1, y+1, x+1, y+length-1, color)
        if self.stroke_w == 2:
            pyxel.line(x-2, y+2, x-2, y+length-2, color)
            pyxel.line(x+2, y+2, x+2, y+length-2, color)

    def draw_seg_h(self, x, y, length, color):
        pyxel.line(x+1, y-1, x+length-1, y-1, color)
        pyxel.line(x+0, y+0, x+length+0, y+0, color)
        pyxel.line(x+1, y+1, x+length-1, y+1, color)
        if self.stroke_w == 2:
            pyxel.line(x+2, y-2, x+length-2, y-2, color)
            pyxel.line(x+2, y+2, x+length-2, y+2, color)

    def draw_seg_c(self, x, y, length, color):
        pyxel.circ(x, y, length, color)

class Seg7Led:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        seg_a = Seg(x+3, y+3, w-8, 'h')
        seg_b = Seg(x+w-4, y+5, h//2-7, 'v')
        seg_c = Seg(x+w-4, y+5+h//2-7+4, h//2-7, 'v')
        seg_d = Seg(x+3, y+h-3, w-8, 'h')
        seg_e = Seg(x+2, y+5+h//2-7+4, h//2-7, 'v')
        seg_f = Seg(x+2, y+5, h//2-7, 'v')
        seg_g = Seg(x+3, y+h//2, w-8, 'h')
        seg_dp = Seg(x+w, y+h-3, 2, 'c')    # 式が確立できていないので半径はリテラル

        self.segs = [seg_a, seg_b, seg_c, seg_d, seg_e, seg_f, seg_g, seg_dp]
        self.ptrn_val = 0b0

    def update(self):
        self.ptrn_val = 0b0
        for i in reversed(range(len(self.segs))):
            self.segs[i].update()
            self.ptrn_val <<= 1
            bit_val = 0b1 if self.segs[i].light_on else 0b0
            self.ptrn_val |= bit_val
        return self.ptrn_val

    def draw(self):
        pyxel.rect(self.x-2, self.y-1, self.w+self.w//5+1, self.h+self.w//7, 0)
        for i in range(len(self.segs)):
            self.segs[i].draw()

    def load_pattern(self, pattern:int):
        for i in range(len(self.segs)):
            light_on = True if (pattern >> i) & 1  else False
            self.segs[i].light_on = light_on


class TextBox:
    def __init__(self, x, y, max_cnt, init_txt):
        self.x = x
        self.y = y
        self.max_cnt = max_cnt
        self.w = max_cnt * 4 + 1
        self.h = 8
        self.txt = init_txt
        self.bgcol = 0
        self.is_editing = False

    def update(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if not(self.is_editing) and collide_mouse_rect(self.x, self.y, self.w, self.h):
                self.is_editing = True
                self.txt = ""   # MEMO: 暫定的な挙動
            elif self.is_editing and not(collide_mouse_rect(self.x, self.y, self.w, self.h)):
                self.is_editing = False
        if self.is_editing:
            if pyxel.btnp(pyxel.KEY_0): self.txt += "0"
            if pyxel.btnp(pyxel.KEY_1): self.txt += "1"
            if pyxel.btnp(pyxel.KEY_2): self.txt += "2"
            if pyxel.btnp(pyxel.KEY_3): self.txt += "3"
            if pyxel.btnp(pyxel.KEY_4): self.txt += "4"
            if pyxel.btnp(pyxel.KEY_5): self.txt += "5"
            if pyxel.btnp(pyxel.KEY_6): self.txt += "6"
            if pyxel.btnp(pyxel.KEY_7): self.txt += "7"
            if pyxel.btnp(pyxel.KEY_8): self.txt += "8"
            if pyxel.btnp(pyxel.KEY_9): self.txt += "9"

        return self.to_int()

    def draw(self):
        self.bgcol = 13 if self.is_editing else 0
        pyxel.rect(self.x, self.y, self.w, self.h, self.bgcol)
        pyxel.text(self.x+1, self.y+1, self.txt, 7)

    def to_int(self):
        try:
            return int(self.txt)
        except ValueError:
            return 0
        
    def load_int(self, num:int):
        self.txt = str(num)


class App:
    def __init__(self):
        pyxel.init(600, 400, display_scale=2)
        pyxel.mouse(True)
        self.index = 0

        self.seg7led0 = [0] * len(patternList)
        self.seg7led1 = [0] * len(patternList)
        self.tbox_duration = [0] * len(patternList)
        self.tbox_flicker_delay = [0] * len(patternList)
        x = 0
        y = 0
        h = 55
        column = 0
        for i in range(len(patternList)):
            if i % 6 == 0:
                x = 20 + column * 125
                y = 40
                column += 1
            self.seg7led0[i] = Seg7Led(x, y, 25, 46)
            self.seg7led1[i] = Seg7Led(x+7+25, y, 25, 46)
            self.tbox_duration[i] = TextBox(x+65, y+3, 10, "100")
            self.tbox_flicker_delay[i] = TextBox(x+65, y+13, 10, "5")
            y += h

        pyxel.run(self.update, self.draw)

    def update(self):
        global patternList
        if pyxel.btnp(pyxel.KEY_SPACE):
            ptn_len = len(patternList)
            ser.write(ptn_len.to_bytes(2, 'big'))
            for i in range(ptn_len):
                pattern10, pattern01, duration, flicker_delay = patternList[i]
                ser.write(pattern10.to_bytes(1, 'big'))
                ser.write(pattern01.to_bytes(1, 'big'))
                ser.write(duration.to_bytes(2, 'big'))
                ser.write(flicker_delay.to_bytes(2, 'big'))
                while ser.read() != b'R':   # ハンドシェイク
                    pass

        ptrn_vals = [0,0,0,0]
        for i in range(len(patternList)):
            ptrn_vals[0] = self.seg7led0[i].update()
            ptrn_vals[1] = self.seg7led1[i].update()
            ptrn_vals[2] = self.tbox_duration[i].update()
            ptrn_vals[3] = self.tbox_flicker_delay[i].update()
            patternList[i] = ptrn_vals.copy()   # MEMO: どハマりした。。。

        if pyxel.btnp(pyxel.KEY_S):
            seva_pattern_list(patternList)

        if pyxel.btnp(pyxel.KEY_L):
            loaded = load_pattern_list()
            if loaded:
                patternList = loaded    # global指定せずにこの文を追加してエラー。これはAIに聞かないと反応できなかった
                for i in range(len(patternList)):
                    self.seg7led0[i].load_pattern(patternList[i][0])
                    self.seg7led1[i].load_pattern(patternList[i][1])
                    self.tbox_duration[i].load_int(patternList[i][2])
                    self.tbox_flicker_delay[i].load_int(patternList[i][3])

    def draw(self):
        pyxel.cls(1)
        pyxel.text(10, 10, f"Press SPACE to send patterns", 7)
        for i in range(len(patternList)):
            self.seg7led0[i].draw()
            self.seg7led1[i].draw()
            self.tbox_duration[i].draw()
            self.tbox_flicker_delay[i].draw()
            x = self.tbox_flicker_delay[i].x
            y = self.tbox_flicker_delay[i].y
            pyxel.text(x, y+14, format(self.seg7led0[i].ptrn_val, '08b'), 7)
            pyxel.text(x, y+24, format(self.seg7led1[i].ptrn_val, '08b'), 7)


App()

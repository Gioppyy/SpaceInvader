import g2d, random, json, time
from actor import *

MAX_LEVEL = 5

with open("settings.json") as settings_file:
    settings = json.load(settings_file)

keybinds = settings["keybinds"]
p_settings = settings["player"]
images = settings["images"]

class Barrier(Actor):
    def __init__(self, pos):
        self._w, self._h = 32, 24
        self._x, self._y = pos
        self._x -= self._w / 2

        self._life = 500

    def move(self, pos):
        for other in arena.collisions():
            arena.kill(other)
            self._life -= 100
            if self._life <= 100:
                arena.kill(self)

    def pos(self):
        return self._x, self._y

    def size(self):
        return self._w, self._h

    def sprite(self):
        return 175, 1352


class Bomb(Actor):
    def __init__(self, pos):
        self._w, self._h = 4, 8
        self._x, self._y = pos
        self._x -= self._w / 2

    def move(self, arena):
        for other in arena.collisions():
            if isinstance(other, Player):
                if not other.isInvincible():
                    arena.kill(self)
                    arena.decrease_lives()

                    dec = arena.get_score() - (100 + (100 * arena.get_level()))
                    if dec >= 0:
                        arena.set_score(dec)

                    if arena.get_lives() == 0:
                        arena.set_status(False, "Alien")
                        arena.kill_all(Bomb)
                    else:
                        other.make_invincible()
                        other.set_hitted(g2d._time.get_ticks())

            elif isinstance(other, Missile):
                arena.kill(self)
                arena.kill(other)
            elif isinstance(other, Bomb):
                arena.kill(self)

        aw, ah = arena.size()
        self._y += 4
        if self._y > ah:
            arena.kill(self)

    def pos(self):
        return self._x, self._y

    def size(self):
        return self._w, self._h

    def sprite(self):
        return 204, 531


class Missile(Actor):
    def __init__(self, pos, p_id):
        self._w, self._h = 4, 8
        self._x, self._y = pos
        self._x -= self._w / 2
        self._y -= self._h

        self._id = p_id

    def move(self, arena):
        for other in arena.collisions():
            if isinstance(other, Alien):
                if arena.get_level() < MAX_LEVEL:
                    arena.kill(self)
                    arena.kill(other)

                    inc = arena.get_score() + (100 + (100 * arena.get_level()))
                    arena.set_score(inc)

                    alive_aliens = arena.there_are_alive_mobs(Alien)
                    if not alive_aliens:
                        arena.kill_all(Alien)
                        arena.increase_level()
                        arena.spawn_mobs(Alien)
                else:
                    arena.set_status(False, "Player")
            elif isinstance(other, Bomb):
                arena.kill(self)
                arena.kill(other)

        self._y -= 6
        if self._y <= 120:
            arena.kill(self)

    def get_id(self):
        return self._id

    def pos(self):
        return self._x, self._y

    def size(self):
        return self._w, self._h

    def sprite(self):
        return 4, 10


class Alien(Actor):
    def __init__(self, pos: Point):
        self._x, self._y = pos
        self._w, self._h = 32, 20
        self._dx, self._dy = 4, 8
        self._xmin, self._xmax = self._x, self._x + 450 - (50 * arena.get_level())
        self._pose = 0

    def move(self, arena: Arena):
        for other in arena.collisions():
            if isinstance(other, Missile):
                arena.kill(self)

        if self._xmin <= self._x + self._dx <= self._xmax:
            self._x += self._dx
        else:
            self._dx = -self._dx
            self._y += self._dy

        if random.random() < 0.003 + (0.002 * arena.get_level()):
            arena.spawn(Bomb(self.pos()))

        self._pose = arena.count() // 8 % 2

    def pos(self) -> Point:
        return self._x, self._y

    def size(self) -> Point:
        return self._w, self._h

    def sprite(self) -> Point:
        return 130, 519 if self._pose else 548


class Player(Actor):
    def __init__(self, pos, p_id):
        self._x, self._y = pos
        self._w, self._h = 28, 16
        self._speed = p_settings["speed"]
        self._id = p_id

        self._invincible = False
        self._last_life_lose = 0
        self._invincible_time = p_settings["invincible_duration"]

        self._cooldown = False
        self._last_shot_time = 0
        self._cooldown_time = p_settings["cooldown_duration"]

    def move(self, arena: Arena):
        keys = arena.current_keys()
        current_time = g2d._time.get_ticks()

        if not self._invincible or ( current_time - self._last_life_lose >= self._invincible_time ):
            self._invincible = False

        if keybinds[f"player{self._id}"]["left"] in keys:
            self._x -= self._speed
        elif keybinds[f"player{self._id}"]["right"] in keys:
            self._x += self._speed

        if keybinds[f"player{self._id}"]["up"] in keys:
            if not self._cooldown or (
                current_time - self._last_shot_time >= self._cooldown_time
            ):
                arena.spawn(Missile((self._x + 20, self._y), self._id))
                self._cooldown = True
                self._last_shot_time = current_time

        aw, ah = arena.size()
        self._x = min(max(self._x, 0), aw - self._w)
        self._y = min(max(self._y, 0), ah - self._h)

    def hit(self, arena: Arena):
        arena.kill(self)

    def set_hitted(self, current_time):
        self._last_life_lose = current_time

    def isInvincible(self) -> (bool):
        return self._invincible

    def make_invincible(self):
        self._invincible = True

    def get_image_path(self):
        return images[f"tank{self._id}"]

    def pos(self) -> Point:
        return self._x, self._y

    def size(self) -> Point:
        return self._w, self._h

    def sprite(self) -> Point:
        return 35, 35


with open("scoreboard.json", "r") as file:
    scoreboard = json.load(file)
written = False


def show_result(winner):
    global written

    if winner == "Alien":
        g2d.draw_image("./img/lose.png", (50, 100))
    else:
        g2d.draw_image("./img/win.png", (50, 100))

    # Save score
    if written == False:
        global scoreboard

        data = {
            "score": arena.get_score(),
            "level": arena.get_level(),
            "win": arena.get_status()[0],
            "timestamp": time.strftime("%m/%d/%Y %H:%M"),
        }
        
        scoreboard.append(data)

        with open("scoreboard.json", "w") as file:
            json.dump(scoreboard, file, indent=4)
            written = True

def get_best_score():
    if scoreboard != []:
        max = scoreboard[0]["score"]
        for score in scoreboard:
            if score["score"] > max:
                max = score["score"]
        return max
    else:
        return 0


def tick():
    g2d.clear_canvas()
    g2d.set_color((0, 0, 0))
    g2d.draw_image(images["bg"], (0, 0), arena.size())

    if arena.get_status()[0]:
        g2d.set_color((10, 79, 153))
        g2d.draw_rect((0, 0), (600, 120))

        max_score = get_best_score()
        if arena.get_score() > max_score:
            max_score = arena.get_score()
        
        n = 30
        for _ in range(arena.get_lives()):
            g2d.draw_image(images["heart"], (n, 0), (100, 100))
            n += 70

        g2d.set_color((255, 255, 255))
        g2d.draw_text(f"Best Score: {max_score}", (n + 150, 35), 20)
        g2d.draw_text(f"Current Score: {arena.get_score()}", (n + 150, 65), 20)
        g2d.draw_text(f"Current Level: {arena.get_level()+1}", (n + 145, 95), 20)

        for a in arena.actors():
            if isinstance(a, Player):
                if not a.isInvincible():
                    g2d.draw_image(a.get_image_path(), a.pos(), a.sprite())
                else: g2d.draw_image(images["tank_hitted"], a.pos(), a.sprite())
            elif isinstance(a, Missile):
                g2d.draw_image(images[f"projectile{a.get_id()}"], a.pos(), a.sprite())
            elif a.sprite() != None:
                g2d.draw_image(
                    images["invades"],
                    a.pos(),
                    a.sprite(),
                    a.size(),
                )
            else:
                pass
    else:
        show_result(arena.get_status()[1])

    arena.tick(g2d.current_keys())


def main():
    global g2d, arena
    import g2d

    arena = Arena((600, 600))
    arena.spawn_mobs(Alien)

    arena.spawn(Player((230, 500), 1))
    arena.spawn(Player((250, 500), 2))

    for n in range(3):
        arena.spawn(Barrier(((n+1)*150, 450)))

    g2d.init_canvas(arena.size())
    g2d.main_loop(tick)


if __name__ == "__main__":
    main()

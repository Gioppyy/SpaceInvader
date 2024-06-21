#!/usr/bin/env python3

import g2d, random, json, time, os
from actor import *

MAX_LEVEL = 5

with open("settings.json") as settings_file:
    settings = json.load(settings_file)

keybinds = settings["keybinds"]
p_settings = settings["player"]
images = settings["images"]
boosts = p_settings["boosts"]

class Boost(Actor):
    def __init__(self, pos):
        self._w, self._h = 24, 14
        self._x, self._y = pos
        self._x -= self._w / 2

    def move(self, pos):
        for other in arena.collisions():
            if isinstance(other, Barrier):
                arena.kill(self)
            elif isinstance(other, Player):
                arena.kill(self)
                # controlla se il player non ha già un booster attivo
                if not other.have_active_booster():
                    # prende un booster casualmente
                    boost = boosts[random.randrange(len(boosts))]
                    if "score" in boost:
                        # aggiunge dello score al totale
                        score_boost = boost.replace("score_+", "")
                        arena.set_score(arena.get_score() + int(score_boost))
                    elif "life" in boost:
                        # givva una vita al player
                        arena.give_lives(1)
                    elif "speed" in boost:
                        # raddoppia la velocità del player che prende il booster (temporaneamente)
                        other.set_speed(other.get_speed() * 2)
                    elif "shot" in boost:
                        # raddoppia la velocità di sparo del player che prende il booster (temporanemaente)
                        other.set_shot_speed(other.get_shot_speed() // 2)

                    # attiva il booster
                    other.active_booster(g2d._time.get_ticks(), "boost")
                else:
                    # se il player ha un booster attivo cancella il prop booster
                    arena.kill(self)

        aw, ah = arena.size()
        
        # se il prop del booster si trova troppo in basso lo killa
        self._y += 4
        if self._y > ah:
            arena.kill(self)

    def pos(self):
        return self._x, self._y

    def size(self):
        return self._w, self._h

    def sprite(self):
        return 96, 1250


class Barrier(Actor):
    def __init__(self, pos):
        self._w, self._h = 32, 24
        self._x, self._y = pos
        self._x -= self._w / 2

        self._life = 500

    def move(self, pos):
        for other in arena.collisions():
            arena.kill(other)

            # rimuove della vita alla barriera
            self._life -= 100

            # se la barriera non ha più vita la rimuove
            if self._life <= 100:
                arena.kill(self)

    def pos(self):
        return self._x, self._y

    def size(self):
        return self._w, self._h

    def sprite(self):
        return 175, 1352

"""
    Proiettile creato dall'alieno
"""
class Bomb(Actor):
    def __init__(self, pos):
        self._w, self._h = 4, 8
        self._x, self._y = pos
        self._x -= self._w / 2

    def move(self, arena):
        for other in arena.collisions():
            if isinstance(other, Player):
                # controlla se il player non è invincibile
                if not other.isInvincible():
                    # killa il player e toglie una vita
                    arena.kill(self)
                    arena.decrease_lives()

                    # rimuove dei punti allo score totale
                    dec = arena.get_score() - (100 + (100 * arena.get_level()))
                    if dec >= 0:
                        arena.set_score(dec)

                    # se il count delle vite e' a 0 finisce la partita
                    if arena.get_lives() == 0:
                        arena.set_status(False, "Alien")
                        arena.kill_all(Bomb)
                    else:
                        # se ha ancora delle vite rende invincibile il player
                        other.make_invincible(g2d._time.get_ticks())

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


"""
    Proiettile creato dal player
"""
class Missile(Actor):
    def __init__(self, pos, p_id):
        self._w, self._h = 4, 8
        self._x, self._y = pos
        self._x -= self._w / 2
        self._y -= self._h

        self._id = p_id

    def move(self, arena):
        for other in arena.collisions():
            if isinstance(other, Bomb):
                arena.kill(self)
                arena.kill(other)
            elif isinstance(other, Alien):
                # controlla se il livello è il livello corrente non è maggiore dell'ultimo
                if arena.get_level() <= MAX_LEVEL:
                    arena.kill(self)
                    arena.kill(other)

                    # genera un booster con una probabilita' del 10%  
                    if random.random() <= 0.1:
                        arena.spawn(Boost(self.pos()))

                    # aggiunge al giocatore i punti per l'uccisione con un boost in base al livello
                    inc = arena.get_score() + (100 + (100 * arena.get_level()))

                    # controlla se uno dei due player ha un booster attivo ed in caso lo raddoppia
                    if p1.have_active_booster():
                        if "point_x2" == p1.get_boost():
                            inc *= 2
                    elif p2.have_active_booster():
                        if "point_x2" == p2.get_boost():
                            inc *= 2
                    arena.set_score(inc)

                    # prende tutti gli alieni vivi
                    alive_aliens = arena.there_are_alive_mobs(Alien)
                    # se non ci sono alieni vivi                    
                    if not alive_aliens:
                        # elimina i possibili alieni buggati
                        arena.kill_all(Alien)
                        # aumenta il livello
                        arena.increase_level()
                        # genera la nuova ondata di alieni 
                        arena.spawn_mobs(Alien)
                else:
                    arena.set_status(False, "Player")

        self._y -= 6
        # se il missile si trova troppo in alto lo killa
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

"""
   Classe alieno 
"""
class Alien(Actor):
    def __init__(self, pos: Point):
        self._x, self._y = pos
        self._w, self._h = 32, 20
        self._dx, self._dy = 4, 8
        self._xmin, self._xmax = self._x, self._x + 450 - (50 * arena.get_level())
        self._pose = 0

    def move(self, arena: Arena):
        # muove l'alieno e se tocca uno dei due massimi lo manda dall'altra parte e lo abbassa
        if self._xmin <= self._x + self._dx <= self._xmax:
            self._x += self._dx
        else:
            self._dx = -self._dx
            self._y += self._dy

        """ 
            calcola un numero casuale e gli da un boost in base al livello,
            se il boost è maggiore di 0.01 lo setta a 0.01 per non far diventare il gioco impossibile
        """ 
        prob_shot_boost = (0.002 * arena.get_level())
        if prob_shot_boost >= 0.008: prob_shot_boost = 0.008
        if random.random() < 0.002 + prob_shot_boost:
            arena.spawn(Bomb(self.pos()))

        self._pose = arena.count() // 8 % 2

    def pos(self) -> Point:
        return self._x, self._y

    def size(self) -> Point:
        return self._w, self._h

    def sprite(self) -> Point:
        return 130, 519 if self._pose else 548

"""
   Classe player 
"""
class Player(Actor):
    def __init__(self, pos, p_id):
        self._a = self
        self._id = p_id

        self._x, self._y = pos
        self._w, self._h = 28, 16

        self._speed = p_settings["speed"]

        self._boost = ""
        self._boost_active = False
        self._boost_actived_time = 0
        self._boost_duration = p_settings["boost_duration"]

        self._invincible = False
        self._last_life_lose = 0
        self._invincible_time = p_settings["invincible_duration"]

        self._cooldown = False
        self._last_shot_time = 0
        self._cooldown_time = p_settings["cooldown_duration"]

    def reset_settings(self):
        self._speed = p_settings["speed"]
        self._boost_duration = p_settings["boost_duration"]
        self._invincible_time = p_settings["invincible_duration"]
        self._cooldown_time = p_settings["cooldown_duration"]

    def move(self, arena: Arena):
        keys = arena.current_keys()
        current_time = g2d._time.get_ticks()

        # controlla se l'invincibilità è scaduta ed in caso la rimuove
        if not self._invincible or ( current_time - self._last_life_lose >= self._invincible_time ):
            self._invincible = False

        # controlla se il boost è scaduto ed in caso lo toglie
        if not self._boost_active or ( current_time - self._boost_actived_time >= self._boost_duration ):
            self._boost_active = False
            self.reset_settings()

        # gestisce il movimento del player a sinistra e destra
        if keybinds[f"player{self._id}"]["left"] in keys:
            self._x -= self._speed
        elif keybinds[f"player{self._id}"]["right"] in keys:
            self._x += self._speed

        # gestisce lo sparo tramite il tasto impostato nel settings.json
        if keybinds[f"player{self._id}"]["up"] in keys:
            if not self._cooldown or (
                current_time - self._last_shot_time >= self._cooldown_time
            ):
                arena.spawn(Missile((self._x + 20, self._y),  self._id))
                self._cooldown = True
                self._last_shot_time = current_time


        aw, ah = arena.size()
        self._x = min(max(self._x, 0), aw - self._w)
        self._y = min(max(self._y, 0), ah - self._h)

    def hit(self, arena: Arena):
        arena.kill(self)

    def set_shot_speed(self, speed):
        self._cooldown_time = speed

    def get_shot_speed(self):
        self._cooldown_time

    def get_speed(self):
        return self._speed

    def set_speed(self, speed):
        self._speed = speed

    def have_active_booster(self):
        return self._boost_active

    def active_booster(self, current_time, boost):
        self._boost_active = True
        self._boost_actived_time = current_time
        self._boost = boost

    def get_boost(self):
        return self._boost

    def isInvincible(self) -> (bool):
        return self._invincible

    def make_invincible(self, current_time):
        self._invincible = True
        self._last_life_lose = current_time

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
    global g2d, arena, p1, p2
    import g2d

    arena = Arena((600, 600))
    arena.spawn_mobs(Alien)

    p1 = Player((230, 500), 1)
    p2 = Player((250, 500), 2)
    arena.spawn(p1)
    arena.spawn(p2)

    for n in range(3):
        arena.spawn(Barrier(((n+1)*150, 450)))

    g2d.init_canvas(arena.size())
    g2d.main_loop(tick)


if __name__ == "__main__":
    main()

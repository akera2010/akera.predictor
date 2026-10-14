"""Player catalogue used by the demo simulator, the synthetic-data fallback of the
training script and the table-tennis Elo seeds.

Ratings here are rough *approximations* (Elo-like scale) chosen by hand to make the
demo plausible; they are NOT official rankings and change constantly in reality.
Names of tennis / table-tennis tour players are real public athletes. The
"Setka Cup" / "TT Elite Series"-style league rosters are FICTIONAL placeholder
names (those leagues have hundreds of rotating low-profile players).
"""
from __future__ import annotations

# (name, country, approx_rank, approx_rating, clay_adj, grass_adj)
ATP = [
    ("Carlos Alcaraz", "ESP", 1, 2250, 40, 30), ("Jannik Sinner", "ITA", 2, 2245, -10, 15),
    ("Alexander Zverev", "GER", 3, 2075, 20, -30), ("Novak Djokovic", "SRB", 4, 2120, 0, 40),
    ("Taylor Fritz", "USA", 5, 2010, -50, 40), ("Jack Draper", "GBR", 6, 1985, -10, 20),
    ("Ben Shelton", "USA", 7, 1980, -40, 20), ("Alex de Minaur", "AUS", 8, 1985, -30, 25),
    ("Lorenzo Musetti", "ITA", 9, 1975, 45, 0), ("Holger Rune", "DEN", 10, 1950, 20, -10),
    ("Daniil Medvedev", "RUS", 11, 1990, -70, -10), ("Casper Ruud", "NOR", 12, 1960, 60, -60),
    ("Andrey Rublev", "RUS", 13, 1940, 10, -20), ("Jakub Mensik", "CZE", 14, 1945, -20, 0),
    ("Felix Auger-Aliassime", "CAN", 15, 1950, -30, 10), ("Tommy Paul", "USA", 16, 1935, 0, 15),
    ("Francisco Cerundolo", "ARG", 17, 1910, 50, -50), ("Karen Khachanov", "RUS", 18, 1920, 0, 0),
    ("Alejandro Davidovich Fokina", "ESP", 19, 1915, 30, -20), ("Jiri Lehecka", "CZE", 20, 1920, -10, 10),
    ("Arthur Fils", "FRA", 21, 1925, 20, -10), ("Stefanos Tsitsipas", "GRE", 22, 1915, 50, -30),
    ("Frances Tiafoe", "USA", 23, 1900, -20, 20), ("Grigor Dimitrov", "BUL", 24, 1905, 0, 20),
    ("Ugo Humbert", "FRA", 25, 1890, -30, 30), ("Tomas Machac", "CZE", 26, 1895, 0, 0),
    ("Joao Fonseca", "BRA", 27, 1900, 30, -10), ("Alexander Bublik", "KAZ", 28, 1895, -20, 40),
    ("Hubert Hurkacz", "POL", 29, 1900, -40, 50), ("Flavio Cobolli", "ITA", 30, 1890, 40, -20),
    ("Jaume Munar", "ESP", 31, 1860, 30, -30), ("Denis Shapovalov", "CAN", 32, 1880, -20, 30),
    ("Giovanni Mpetshi Perricard", "FRA", 33, 1860, -30, 50), ("Sebastian Baez", "ARG", 34, 1850, 60, -60),
    ("Alex Michelsen", "USA", 35, 1860, -10, 10), ("Matteo Berrettini", "ITA", 36, 1870, 0, 50),
    ("Brandon Nakashima", "USA", 37, 1865, -10, 10), ("Learner Tien", "USA", 38, 1870, -10, 0),
    ("Pedro Martinez", "ESP", 52, 1810, 50, -50), ("Roberto Bautista Agut", "ESP", 55, 1810, 10, 0),
]
ATP_CHALLENGER = [
    ("Martin Landaluce", "ESP", 105, 1765, 20, -10), ("Hamad Medjedovic", "SRB", 108, 1760, 0, 0),
    ("Dalibor Svrcina", "CZE", 100, 1745, 0, 0), ("Roberto Carballes Baena", "ESP", 120, 1715, 40, -40),
    ("Pablo Llamas Ruiz", "ESP", 130, 1720, 40, -40), ("Carlos Taberner", "ESP", 150, 1710, 40, -40),
    ("Daniel Merida", "ESP", 160, 1700, 30, -30), ("Bernabe Zapata Miralles", "ESP", 170, 1700, 40, -40),
    ("Albert Ramos-Vinolas", "ESP", 200, 1690, 50, -50), ("Luca Van Assche", "FRA", 125, 1730, 10, 0),
    ("Dominic Stricker", "SUI", 140, 1720, -10, 20), ("Federico Cina", "ITA", 180, 1700, 20, 0),
    ("Jerome Kym", "SUI", 165, 1705, 10, 0), ("Coleman Wong", "HKG", 135, 1725, -10, 10),
    ("Elmer Moller", "DEN", 175, 1700, 30, -20), ("Rei Sakamoto", "JPN", 190, 1690, 0, 0),
]
ATP_ITF = [
    ("Oriol Roca Batalla", "ESP", 310, 1630, 30, -30), ("Alejandro Moro Canas", "ESP", 330, 1625, 30, -30),
    ("Nikolas Sanchez Izquierdo", "ESP", 280, 1640, 30, -30), ("Carlos Lopez Montagud", "ESP", 360, 1610, 30, -30),
    ("Alvaro Lopez San Martin", "ESP", 400, 1600, 30, -30), ("Javier Barranco Cosano", "ESP", 380, 1605, 30, -30),
]
WTA = [
    ("Aryna Sabalenka", "BLR", 1, 2200, -10, 10), ("Iga Swiatek", "POL", 2, 2160, 60, -20),
    ("Coco Gauff", "USA", 3, 2090, 20, -20), ("Amanda Anisimova", "USA", 4, 2040, -10, 30),
    ("Elena Rybakina", "KAZ", 5, 2060, -10, 40), ("Jessica Pegula", "USA", 6, 2030, -30, 10),
    ("Madison Keys", "USA", 7, 1990, 0, 10), ("Mirra Andreeva", "RUS", 8, 2040, 20, 0),
    ("Jasmine Paolini", "ITA", 9, 1980, 30, 10), ("Zheng Qinwen", "CHN", 10, 1990, 10, -30),
    ("Elina Svitolina", "UKR", 11, 1960, 20, 0), ("Emma Navarro", "USA", 12, 1950, 0, 0),
    ("Karolina Muchova", "CZE", 13, 1970, 0, 10), ("Ekaterina Alexandrova", "RUS", 14, 1950, -20, 30),
    ("Belinda Bencic", "SUI", 15, 1955, -10, 20), ("Clara Tauson", "DEN", 16, 1945, -10, 10),
    ("Diana Shnaider", "RUS", 17, 1940, 0, 0), ("Liudmila Samsonova", "RUS", 18, 1935, -20, 30),
    ("Daria Kasatkina", "AUS", 19, 1920, 30, -30), ("Naomi Osaka", "JPN", 20, 1955, -40, -20),
    ("Paula Badosa", "ESP", 21, 1930, 30, -20), ("Jelena Ostapenko", "LAT", 22, 1915, 10, 10),
    ("Marta Kostyuk", "UKR", 23, 1920, 10, 0), ("Victoria Mboko", "CAN", 24, 1940, 0, 0),
    ("Linda Noskova", "CZE", 25, 1925, 0, 0), ("Emma Raducanu", "GBR", 26, 1905, -20, 20),
    ("Barbora Krejcikova", "CZE", 27, 1910, 10, 30), ("Leylah Fernandez", "CAN", 28, 1910, 0, 0),
    ("Elise Mertens", "BEL", 29, 1905, 10, 0), ("Beatriz Haddad Maia", "BRA", 30, 1890, 20, 0),
    ("Jessica Bouzas Maneiro", "ESP", 45, 1860, 20, 10), ("Cristina Bucsa", "ESP", 60, 1820, 10, 0),
]
WTA_CHALLENGER = [
    ("Sara Sorribes Tormo", "ESP", 110, 1760, 50, -40), ("Rebeka Masarova", "ESP", 115, 1755, 20, 0),
    ("Nuria Parrizas Diaz", "ESP", 150, 1720, 20, -20), ("Aliona Bolsova", "ESP", 170, 1700, 30, -20),
    ("Irene Burillo Escorihuela", "ESP", 180, 1700, 30, -30), ("Guiomar Maristany", "ESP", 190, 1690, 30, -30),
    ("Kaitlin Quevedo", "ESP", 160, 1710, 20, -10), ("Leyre Romero Gormaz", "ESP", 140, 1725, 30, -20),
]
WTA_ITF = [
    ("Marina Bassols Ribera", "ESP", 260, 1640, 30, -30), ("Andrea Lazaro Garcia", "ESP", 330, 1620, 30, -30),
    ("Carlota Martinez Cirez", "ESP", 350, 1610, 30, -30), ("Lucia Cortez Llorca", "ESP", 380, 1600, 30, -30),
]

# Table tennis: (name, country, approx_world_rank, approx_rating)
TT_MEN = [
    ("Wang Chuqin", "CHN", 1, 2300), ("Lin Shidong", "CHN", 2, 2275), ("Hugo Calderano", "BRA", 3, 2235),
    ("Tomokazu Harimoto", "JPN", 4, 2240), ("Truls Moregard", "SWE", 5, 2210), ("Liang Jingkun", "CHN", 6, 2215),
    ("Felix Lebrun", "FRA", 7, 2205), ("Fan Zhendong", "CHN", 8, 2250), ("Lin Yun-Ju", "TPE", 9, 2180),
    ("Alexis Lebrun", "FRA", 10, 2165), ("Xiang Peng", "CHN", 11, 2185), ("Darko Jorgic", "SLO", 12, 2150),
    ("Dang Qiu", "GER", 13, 2140), ("Shunsuke Togami", "JPN", 14, 2140), ("Jang Woojin", "KOR", 15, 2135),
    ("Patrick Franziska", "GER", 16, 2120), ("Anton Kallberg", "SWE", 17, 2115), ("Sora Matsushima", "JPN", 18, 2130),
    ("Zhou Qihao", "CHN", 19, 2155), ("Lin Gaoyuan", "CHN", 20, 2160), ("Benedikt Duda", "GER", 21, 2105),
    ("Lim Jonghoon", "KOR", 22, 2095), ("Simon Gauzy", "FRA", 23, 2090), ("Yukiya Uda", "JPN", 24, 2095),
    ("Quadri Aruna", "NGR", 26, 2075), ("Omar Assar", "EGY", 28, 2075), ("Marcos Freitas", "POR", 30, 2070),
    ("Kanak Jha", "USA", 35, 2055), ("Alvaro Robles", "ESP", 40, 2030),
]
TT_WOMEN = [
    ("Sun Yingsha", "CHN", 1, 2300), ("Wang Manyu", "CHN", 2, 2260), ("Chen Xingtong", "CHN", 3, 2215),
    ("Kuai Man", "CHN", 4, 2205), ("Wang Yidi", "CHN", 5, 2205), ("Hina Hayata", "JPN", 6, 2200),
    ("Miwa Harimoto", "JPN", 7, 2210), ("Mima Ito", "JPN", 8, 2170), ("Shin Yubin", "KOR", 9, 2140),
    ("Satsuki Odo", "JPN", 10, 2150), ("Cheng I-Ching", "TPE", 11, 2120), ("Bernadette Szocs", "ROU", 12, 2100),
    ("Joo Cheonhui", "KOR", 13, 2090), ("Adriana Diaz", "PUR", 14, 2080), ("Han Ying", "GER", 15, 2080),
    ("Sofia Polcanova", "AUT", 18, 2060), ("Maria Xiao", "ESP", 40, 1985),
]
# FICTIONAL placeholder rosters for Setka Cup / TT Elite Series style leagues.
TT_LEAGUE = [
    ("Oleh Kovalenko", "UKR", 0, 1720), ("Dmytro Shevchuk", "UKR", 0, 1690), ("Vitalii Moroz", "UKR", 0, 1700),
    ("Andrii Bondar", "UKR", 0, 1660), ("Serhii Tkachuk", "UKR", 0, 1740), ("Yurii Melnyk", "UKR", 0, 1650),
    ("Ihor Savchenko", "UKR", 0, 1710), ("Maksym Lysenko", "UKR", 0, 1680), ("Bohdan Kravets", "UKR", 0, 1730),
    ("Taras Polishchuk", "UKR", 0, 1670), ("Jakub Dvorak", "CZE", 0, 1715), ("Tomas Kral", "CZE", 0, 1695),
    ("Petr Novotny", "CZE", 0, 1675), ("Lukas Vesely", "CZE", 0, 1705), ("Marek Horak", "CZE", 0, 1690),
    ("Michal Cerny", "CZE", 0, 1725), ("Tomasz Wisniewski", "POL", 0, 1700), ("Piotr Zielinski", "POL", 0, 1685),
    ("Kamil Wozniak", "POL", 0, 1710), ("Pawel Kaminski", "POL", 0, 1665), ("Adrian Lewandowski", "POL", 0, 1720),
    ("Rafal Dabrowski", "POL", 0, 1695),
]

TENNIS_TOURNAMENTS = {
    "ATP": [("ATP 500 Viena", "indoor", 3), ("ATP 500 Basilea", "indoor", 3), ("ATP 250 Estocolmo", "indoor", 3),
            ("ATP 250 Almaty", "hard", 3), ("ATP Masters 1000 Shanghái", "hard", 3)],
    "WTA": [("WTA 1000 Wuhan", "hard", 3), ("WTA 500 Ningbo", "hard", 3), ("WTA 500 Tokio", "hard", 3),
            ("WTA 250 Osaka", "hard", 3)],
    "Challenger": [("ATP Challenger Olbia", "hard", 3), ("ATP Challenger Valencia", "clay", 3),
                   ("ATP Challenger Brest", "indoor", 3), ("WTA 125 Valencia", "clay", 3)],
    "ITF": [("ITF M25 Sabadell", "clay", 3), ("ITF W35 Madrid", "clay", 3), ("ITF M15 Monastir", "hard", 3)],
}
TT_TOURNAMENTS = {
    "WTT": [("WTT Champions Montpellier", 5), ("WTT Star Contender Londres", 5), ("WTT China Smash", 7)],
    "ITTF": [("ITTF Mixed Team World Cup", 5), ("ITTF World Cup Macao", 7)],
    "Setka Cup": [("Setka Cup Kyiv", 5)],
    "TT Elite Series": [("TT Elite Series Wroclaw", 5)],
    "Czech Liga Pro": [("Czech Liga Pro Ostrava", 5)],
}


def tennis_pool(category: str) -> list[tuple]:
    return {
        "ATP": ATP, "WTA": WTA,
        "Challenger": ATP_CHALLENGER + WTA_CHALLENGER,
        "ITF": ATP_ITF + WTA_ITF,
    }[category]


def tennis_player_index() -> dict[str, dict]:
    out = {}
    for tour, lists in (("ATP", (ATP, ATP_CHALLENGER, ATP_ITF)), ("WTA", (WTA, WTA_CHALLENGER, WTA_ITF))):
        for lst in lists:
            for name, cc, rank, rating, clay, grass in lst:
                out[name] = {"name": name, "country": cc, "rank": rank, "rating": rating,
                             "clay": clay, "grass": grass, "tour": tour}
    return out


def tt_player_index() -> dict[str, dict]:
    out = {}
    for gender, lst in (("M", TT_MEN), ("W", TT_WOMEN), ("M", TT_LEAGUE)):
        for name, cc, rank, rating in lst:
            out[name] = {"name": name, "country": cc, "rank": rank or None, "rating": rating, "gender": gender,
                         "fictional": lst is TT_LEAGUE}
    return out

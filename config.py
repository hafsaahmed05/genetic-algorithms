import numpy as np

# ==========================================
# CONSTANTS & DATA
# ==========================================

ACTIVITIES = {
    'SLA101A': {'enrollment': 40, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA101B': {'enrollment': 35, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA191A': {'enrollment': 45, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA191B': {'enrollment': 40, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA201':  {'enrollment': 60, 'pref': ['Glen', 'Banks', 'Zeldin', 'Lock', 'Singer'], 'other': ['Richards', 'Uther', 'Shaw']},
    'SLA291':  {'enrollment': 50, 'pref': ['Glen', 'Banks', 'Zeldin', 'Lock', 'Singer'], 'other': ['Richards', 'Uther', 'Shaw']},
    'SLA303':  {'enrollment': 25, 'pref': ['Glen', 'Zeldin'], 'other': ['Banks']},
    'SLA304':  {'enrollment': 20, 'pref': ['Singer', 'Uther'], 'other': ['Richards']},
    'SLA394':  {'enrollment': 15, 'pref': ['Tyler', 'Singer'], 'other': ['Richards', 'Zeldin']},
    'SLA449':  {'enrollment': 30, 'pref': ['Tyler', 'Zeldin', 'Uther'], 'other': ['Shaw']},
    'SLA451':  {'enrollment': 90, 'pref': ['Lock', 'Banks', 'Zeldin'], 'other': ['Tyler', 'Singer', 'Shaw', 'Glen']},
}

ROOMS = {
    'Slater 003': 32,
    'Roman 201':  40,
    'Roman 216':  80,
    'Loft 206':   55,
    'Loft 310':   48,
    'Beach 201':  18,
    'Beach 301':  25,
    'Frank 119':  95,
    'James 325':  110,
}

TIMES = [10, 11, 12, 13, 14, 15]
FACILITATORS = ['Lock', 'Glen', 'Banks', 'Richards', 'Shaw', 'Singer', 'Uther', 'Tyler', 'Numen', 'Zeldin']

POP_SIZE = 500

rng = np.random.default_rng()

# HELPERS & INITIALIZATION

def format_time(t):
    if t <= 11: return f"{t} AM"
    if t == 12: return "12 PM"
    return f"{t - 12} PM"

def generate_random_schedule():
    schedule = {}
    for act in ACTIVITIES.keys():
        schedule[act] = {
            'room': rng.choice(list(ROOMS.keys())),
            'time': int(rng.choice(TIMES)),
            'fac':  str(rng.choice(FACILITATORS)),
        }
    return schedule

def generate_initial_population(size=POP_SIZE):
    return [generate_random_schedule() for _ in range(size)]
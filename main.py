import random
import copy
import math
import sys
import numpy as np
import plotext as plt
import csv
from datetime import datetime

# Fix Windows terminal encoding for plotext
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==========================================
# 1. CONSTANTS & DATA BINDINGS
# ==========================================

ACTIVITIES = {
    'SLA101A': {'enrollment': 40, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA101B': {'enrollment': 35, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA191A': {'enrollment': 45, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA191B': {'enrollment': 40, 'pref': ['Glen', 'Lock', 'Banks'], 'other': ['Numen', 'Richards', 'Shaw', 'Singer']},
    'SLA201': {'enrollment': 60, 'pref': ['Glen', 'Banks', 'Zeldin', 'Lock', 'Singer'], 'other': ['Richards', 'Uther', 'Shaw']},
    'SLA291': {'enrollment': 50, 'pref': ['Glen', 'Banks', 'Zeldin', 'Lock', 'Singer'], 'other': ['Richards', 'Uther', 'Shaw']},
    'SLA303': {'enrollment': 25, 'pref': ['Glen', 'Zeldin'], 'other': ['Banks']},
    'SLA304': {'enrollment': 20, 'pref': ['Singer', 'Uther'], 'other': ['Richards']},
    'SLA394': {'enrollment': 15, 'pref': ['Tyler', 'Singer'], 'other': ['Richards', 'Zeldin']},
    'SLA449': {'enrollment': 30, 'pref': ['Tyler', 'Zeldin', 'Uther'], 'other': ['Shaw']}, 
    'SLA451': {'enrollment': 90, 'pref': ['Lock', 'Banks', 'Zeldin'], 'other': ['Tyler', 'Singer', 'Shaw', 'Glen']}
}

ROOMS = {
    'Slater 003': 32,
    'Roman 201': 40,
    'Roman 216': 80,
    'Loft 206': 55,
    'Loft 310': 48,
    'Beach 201': 18,
    'Beach 301': 25,
    'Frank 119': 95,
    'James 325': 110
}

TIMES = [10, 11, 12, 13, 14, 15] # Represented as ints
FACILITATORS = ['Lock', 'Glen', 'Banks', 'Richards', 'Shaw', 'Singer', 'Uther', 'Tyler', 'Numen', 'Zeldin']

def format_time(t):
    if t <= 11: return f"{t} AM"
    if t == 12: return "12 PM"
    return f"{t-12} PM"

# ==========================================
# 2. POPULATION GENERATION
# ==========================================

rng = np.random.default_rng()

def generate_random_schedule():
    schedule = {}
    for act in ACTIVITIES.keys():
        schedule[act] = {
            'room': rng.choice(list(ROOMS.keys())),
            'time': rng.choice(TIMES),
            'fac': rng.choice(FACILITATORS)
        }
    return schedule

def generate_initial_population(size=250):
    return [generate_random_schedule() for _ in range(size)]

# ==========================================
# 3. FITNESS FUNCTION
# ==========================================

def calculate_fitness(schedule):
    fitness = 0.0
    
    # Trackers
    room_time_map = {}
    fac_load = {f: 0 for f in FACILITATORS}
    fac_time_map = {f: {t: [] for t in TIMES} for f in FACILITATORS}
    
    for act, details in schedule.items():
        room = details['room']
        time = int(details['time'])
        fac = str(details['fac'])
        
        # Room overlap tracking
        rt = (str(room), time)
        if rt not in room_time_map: room_time_map[rt] = []
        room_time_map[rt].append(act)
        
        # Facilitator tracking
        fac_load[fac] += 1
        fac_time_map[fac][time].append((act, room))
        
        # Room size constraints
        cap = ROOMS[room]
        enr = ACTIVITIES[act]['enrollment']
        if cap < enr:
            fitness -= 0.5
        elif cap > 3 * enr:
            fitness -= 0.4
        elif cap > 1.5 * enr:
            fitness -= 0.2
        else:
            fitness += 0.3
            
        # Facilitator assignments
        if fac in ACTIVITIES[act]['pref']:
            fitness += 0.5
        elif fac in ACTIVITIES[act]['other']:
            fitness += 0.2
        else:
            fitness -= 0.1
            
    # Resolve Room overlap conflicts
    for rt, acts in room_time_map.items():
        if len(acts) > 1:
            fitness -= (0.5 * len(acts))
            
    # Resolve Facilitator loads
    for f in FACILITATORS:
        load = fac_load[f]
        if load > 4:
            fitness -= 0.5
        elif load > 0 and load < 3: # 1 or 2 activities
            if f == 'Tyler' and load < 2: # No penalty for Tyler if load == 1
                pass
            else:
                fitness -= 0.4
                
        # Time slot counts for facilitator
        times_scheduled = sorted([t for t in TIMES if len(fac_time_map[f][t]) > 0])
        for t in times_scheduled:
            acts_in_slot = len(fac_time_map[f][t])
            if acts_in_slot == 1:
                fitness += 0.2
            elif acts_in_slot > 1:
                fitness -= (0.2 * acts_in_slot)
                
        # Facilitator Consecutive time slots
        for i in range(len(times_scheduled) - 1):
            t1 = times_scheduled[i]
            t2 = times_scheduled[i+1]
            if t2 - t1 == 1:
                # Add 0.5 for consecutive
                fitness += 0.5
                # Romans/Beach logic
                for act1, r1 in fac_time_map[f][t1]:
                    for act2, r2 in fac_time_map[f][t2]:
                        hrb1 = ('Roman' in r1 or 'Beach' in r1)
                        hrb2 = ('Roman' in r2 or 'Beach' in r2)
                        if hrb1 != hrb2:
                            fitness -= 0.4

    # Activity specifics: SLA 101 A and B
    s101a = schedule.get('SLA101A')
    s101b = schedule.get('SLA101B')
    if s101a and s101b:
        diff = abs(int(s101a['time']) - int(s101b['time']))
        if diff > 4: fitness += 0.5
        elif diff == 0: fitness -= 0.5
        
    # Activity specifics: SLA 191 A and B
    s191a = schedule.get('SLA191A')
    s191b = schedule.get('SLA191B')
    if s191a and s191b:
        diff = abs(int(s191a['time']) - int(s191b['time']))
        if diff > 4: fitness += 0.5
        elif diff == 0: fitness -= 0.5
        
    # Activity specifics: 191 and 101 consecutive
    for a191 in ['SLA191A', 'SLA191B']:
        for a101 in ['SLA101A', 'SLA101B']:
            if a191 in schedule and a101 in schedule:
                t1 = int(schedule[a191]['time'])
                t2 = int(schedule[a101]['time'])
                r1 = str(schedule[a191]['room'])
                r2 = str(schedule[a101]['room'])
                diff = abs(t1 - t2)
                if diff == 1:
                    fitness += 0.5
                    hrb1 = ('Roman' in r1 or 'Beach' in r1)
                    hrb2 = ('Roman' in r2 or 'Beach' in r2)
                    if hrb1 != hrb2:
                        fitness -= 0.4
                elif diff == 2:
                    fitness += 0.25
                elif diff == 0:
                    fitness -= 0.25
                    
    return fitness

# ==========================================
# 4. GENETIC OPERATORS
# ==========================================

def get_probabilities(fitnesses):
    arr = np.array(fitnesses)
    # subtracting max helps prevent exponent overflow
    exp_f = np.exp(arr - np.max(arr))
    return exp_f / np.sum(exp_f)

def choose_parents(population, probabilities):
    indices = rng.choice(len(population), size=2, p=probabilities, replace=False)
    return population[indices[0]], population[indices[1]]

def crossover(p1, p2): # Uniform crossover
    child = {}
    for act in p1.keys():
        if rng.random() < 0.5:
            child[act] = copy.deepcopy(p1[act])
        else:
            child[act] = copy.deepcopy(p2[act])
    return child

def mutate(child, mutation_rate):
    for act in child.keys():
        if rng.random() < mutation_rate:
            feature = rng.choice(['room', 'time', 'fac'])
            if feature == 'room':
                child[act]['room'] = str(rng.choice(list(ROOMS.keys())))
            elif feature == 'time':
                child[act]['time'] = int(rng.choice(TIMES)) # ensure int type
            elif feature == 'fac':
                child[act]['fac'] = str(rng.choice(FACILITATORS))
    return child

# ==========================================
# 5. MAIN EVOLUTION LOOP
# ==========================================

def run_evolution():
    POP_SIZE = 250
    population = generate_initial_population(POP_SIZE)
    mutation_rate = 0.01
    
    gen = 0
    history_best = []
    history_avg = []
    history_worst = []
    
    prev_avg = None
    plateau_count = 0
    mutation_halves = 0
    
    print("Starting Evolution...")
    
    while True:
        gen += 1
        fitnesses = [calculate_fitness(ind) for ind in population]
        best_f = max(fitnesses)
        worst_f = min(fitnesses)
        avg_f = sum(fitnesses) / POP_SIZE
        
        history_best.append(best_f)
        history_avg.append(avg_f)
        history_worst.append(worst_f)
        
        imp_pct = 0
        if prev_avg is not None:
            imp_pct = (avg_f - prev_avg) / abs(prev_avg) if prev_avg != 0 else 0
            
        print(f"Gen {gen:3d} | Best: {best_f:6.2f} | Avg: {avg_f:6.2f} | Worst: {worst_f:6.2f} | Imp: {imp_pct*100:6.3f}% | MR: {mutation_rate:.6f}")
        
        # Check termination condition -> Halve mutation rate if plateaus
        if prev_avg is not None and imp_pct < 0.01:
            plateau_count += 1
        else:
            plateau_count = 0
            
        if plateau_count >= 5:
            mutation_rate /= 2.0
            mutation_halves += 1
            plateau_count = 0
            print(f"  -> Plateau detected. Halving Mutation Rate to {mutation_rate:.6f}")
            
        # Stopping criteria: G >= 100 AND either extreme plateau or minimal improvement
        if gen >= 100:
            if mutation_halves >= 5 and imp_pct <= 0.01:
                 print("\nStopping condition met: Gen >= 100, mutation rate minimized, and low improvement.")
                 break
            if plateau_count >= 10:
                 print("\nStopping condition met: Hard plateau reached.")
                 break
                 
        prev_avg = avg_f
        
        # Next generation
        next_gen = []
        best_index = fitnesses.index(best_f)
        # Elitism: keep best schedule to prevent regression
        next_gen.append(copy.deepcopy(population[best_index]))
        
        probs = get_probabilities(fitnesses)
        while len(next_gen) < POP_SIZE:
            p1, p2 = choose_parents(population, probs)
            child = crossover(p1, p2)
            child = mutate(child, mutation_rate)
            next_gen.append(child)
            
        population = next_gen
        
    return population[fitnesses.index(best_f)], best_f, history_best, history_avg, history_worst

# ==========================================
# 6. OUTPUT & CHARTING
# ==========================================

def print_schedule(schedule):
    print("\n" + "="*60)
    print("FINAL OPTIMAL SCHEDULE")
    print("="*60)
    # Group by activity
    sorted_acts = sorted(schedule.keys())
    for act in sorted_acts:
        details = schedule[act]
        t = format_time(details['time'])
        print(f"{act:8s} | Room: {details['room']:11s} | Time: {t:6s} | Fac: {details['fac']}")
        
    print("\n" + "="*60)
    # Output to file
    with open('best_schedule.txt', 'w') as f:
        f.write("FINAL OPTIMAL SCHEDULE\n")
        f.write("="*60 + "\n")
        for act in sorted_acts:
             details = schedule[act]
             f.write(f"{act:8s} | Room: {details['room']:11s} | Time: {format_time(details['time']):6s} | Fac: {details['fac']}\n")

if __name__ == '__main__':
    best_schedule, best_fit, h_best, h_avg, h_worst = run_evolution()
    
    print(f"\nFinal Best Fitness: {best_fit}")
    print_schedule(best_schedule)
    
    # Plotting tracking metrics
    plt.plot(h_best, label="Best Fitness")
    plt.plot(h_avg, label="Average Fitness")
    plt.plot(h_worst, label="Worst Fitness")
    plt.title("Fitness over Generations")
    plt.xlabel("Generation")
    plt.ylabel("Fitness Score")
    plt.show()
    
    # CSV export
    with open('fitness_history.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Generation', 'Best', 'Average', 'Worst'])
        for i in range(len(h_best)):
            writer.writerow([i+1, h_best[i], h_avg[i], h_worst[i]])
    print("\nExported schedule to 'best_schedule.txt' and stats to 'fitness_history.csv'")

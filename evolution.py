import copy
import csv
import numpy as np
from datetime import datetime
from config import ACTIVITIES, FACILITATORS, TIMES, ROOMS, POP_SIZE, format_time, rng, generate_initial_population
from fitness import calculate_fitness

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
    population = generate_initial_population(POP_SIZE)
    mutation_rate = 0.01
    
    gen = 0
    history_best = []
    history_avg = []
    history_worst = []
    
    prev_avg = None
    plateau_count = 0
    mutation_halves = 0
    
    log_path = f"results/run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file = open(log_path, 'w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow(['Timestamp', 'Generation', 'Best', 'Average', 'Worst', 'Improvement%', 'MutationRate'])
    
    print("Starting Evolution...")
    
    while True:
        gen += 1
        fitnesses = [calculate_fitness(ind) for ind in population]
        best_f = max(fitnesses)
        worst_f = min(fitnesses)
        avg_f = sum(fitnesses) / len(population)
        
        history_best.append(best_f)
        history_avg.append(avg_f)
        history_worst.append(worst_f)
        
        imp_pct = 0
        if prev_avg is not None:
            imp_pct = (avg_f - prev_avg) / abs(prev_avg) if prev_avg != 0 else 0
            
        print(f"Gen {gen:3d} | Best: {best_f:6.2f} | Avg: {avg_f:6.2f} | Worst: {worst_f:6.2f} | Imp: {imp_pct*100:6.3f}% | MR: {mutation_rate:.6f}")
        log_writer.writerow([datetime.now().isoformat(), gen, round(best_f, 4), round(avg_f, 4), round(worst_f, 4), round(imp_pct * 100, 4), round(mutation_rate, 6)])
        
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
        
    log_file.close()
    print(f"\nLog saved to '{log_path}'")
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
    with open('results/best_schedule.txt', 'w') as f:
        f.write("FINAL OPTIMAL SCHEDULE\n")
        f.write("="*60 + "\n")
        for act in sorted_acts:
             details = schedule[act]
             f.write(f"{act:8s} | Room: {details['room']:11s} | Time: {format_time(details['time']):6s} | Fac: {details['fac']}\n")
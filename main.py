import sys
import os
import csv
import matplotlib.pyplot as plt
from config import POP_SIZE, format_time
from evolution import run_evolution

os.makedirs('results', exist_ok=True)

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

if __name__ == '__main__':
    if '--gui' in sys.argv:
        from gui import SchedulerGUI
        import tkinter as tk
        root = tk.Tk()
        SchedulerGUI(root)
        root.mainloop()
        sys.exit()

    best_schedule, best_fit, h_best, h_avg, h_worst = run_evolution()

    print(f"\nFinal Best Fitness: {best_fit}")

    # Print schedule
    print("\n" + "=" * 60)
    print("FINAL OPTIMAL SCHEDULE")
    print("=" * 60)
    sorted_acts = sorted(best_schedule.keys())
    for act in sorted_acts:
        d = best_schedule[act]
        print(f"{act:8s} | Room: {d['room']:11s} | Time: {format_time(d['time']):6s} | Fac: {d['fac']}")

    # Write to file
    with open('results/best_schedule.txt', 'w') as f:
        f.write("FINAL OPTIMAL SCHEDULE\n")
        f.write("=" * 60 + "\n")
        for act in sorted_acts:
            d = best_schedule[act]
            f.write(f"{act:8s} | Room: {d['room']:11s} | Time: {format_time(d['time']):6s} | Fac: {d['fac']}\n")
    
    # Plotting tracking metrics
    plt.figure(figsize=(10, 5))
    plt.plot(h_best,  label="Best Fitness",    color="green")
    plt.plot(h_avg,   label="Average Fitness", color="blue")
    plt.plot(h_worst, label="Worst Fitness",   color="red")
    plt.title("Fitness over Generations")
    plt.xlabel("Generation")
    plt.ylabel("Fitness Score")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("results/fitness_plot.png", dpi=150)
    plt.show()

    # CSV export
    with open('results/fitness_history.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Generation', 'Best', 'Average', 'Worst'])
        for i in range(len(h_best)):
            writer.writerow([i + 1, h_best[i], h_avg[i], h_worst[i]])

    print("\nExported schedule to 'results/best_schedule.txt' and stats to 'results/fitness_history.csv'")